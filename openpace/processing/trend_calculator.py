"""
Longitudinal Trend Calculator

Pre-computes time-series trends for fast visualization in the OSCAR-style timeline view.
Calculates battery depletion rates, lead impedance trends, and arrhythmia burden over time.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import numpy as np
from scipy import stats
import logging

from openpace.database.models import Patient, Observation, LongitudinalTrend

logger = logging.getLogger(__name__)


class TrendCalculator:
    """
    Calculates longitudinal trends from observations.

    Pre-computes trends and stores them in the LongitudinalTrend table
    for fast retrieval during visualization.
    """

    def __init__(self, db_session: Session):
        self.session = db_session

    def calculate_trend(self, patient_id: str, variable_name: str,
                       start_date: datetime = None,
                       end_date: datetime = None) -> Optional[LongitudinalTrend]:
        """
        Calculate trend for a specific variable over time.

        Args:
            patient_id: Patient identifier
            variable_name: Universal variable name
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            LongitudinalTrend object or None if insufficient data
        """
        # Query observations
        query = self.session.query(Observation).join(
            Observation.transmission
        ).filter(
            Observation.transmission.has(patient_id=patient_id),
            Observation.variable_name == variable_name,
            Observation.value_numeric.isnot(None)
        )

        if start_date:
            query = query.filter(Observation.observation_time >= start_date)
        if end_date:
            query = query.filter(Observation.observation_time <= end_date)

        observations = query.order_by(Observation.observation_time).all()

        if len(observations) < 2:
            logger.info(f"Insufficient data for trend: {variable_name} (only {len(observations)} points)")
            return None

        # Extract time points and values
        time_points = [obs.observation_time.isoformat() for obs in observations]
        values = [obs.value_numeric for obs in observations]

        # Calculate statistics
        min_value = float(np.min(values))
        max_value = float(np.max(values))
        mean_value = float(np.mean(values))
        std_dev = float(np.std(values))

        # Create or update trend
        trend = self.session.query(LongitudinalTrend).filter_by(
            patient_id=patient_id,
            variable_name=variable_name
        ).first()

        if trend:
            # Update existing
            trend.time_points = time_points
            trend.values = values
            trend.min_value = min_value
            trend.max_value = max_value
            trend.mean_value = mean_value
            trend.std_dev = std_dev
            trend.start_date = observations[0].observation_time
            trend.end_date = observations[-1].observation_time
            trend.computed_at = datetime.utcnow()
        else:
            # Create new
            trend = LongitudinalTrend(
                patient_id=patient_id,
                variable_name=variable_name,
                time_points=time_points,
                values=values,
                min_value=min_value,
                max_value=max_value,
                mean_value=mean_value,
                std_dev=std_dev,
                start_date=observations[0].observation_time,
                end_date=observations[-1].observation_time
            )
            self.session.add(trend)

        self.session.commit()
        return trend

    def calculate_all_trends(self, patient_id: str) -> List[LongitudinalTrend]:
        """
        Calculate trends for all variables for a patient.

        Args:
            patient_id: Patient identifier

        Returns:
            List of computed trends
        """
        # Get unique variables for this patient
        variables = self.session.query(Observation.variable_name).join(
            Observation.transmission
        ).filter(
            Observation.transmission.has(patient_id=patient_id),
            Observation.value_numeric.isnot(None)
        ).distinct().all()

        trends = []
        for (var_name,) in variables:
            trend = self.calculate_trend(patient_id, var_name)
            if trend:
                trends.append(trend)

        return trends


class BatteryTrendAnalyzer:
    """
    Analyzes battery depletion trends and predicts ERI date.

    Uses linear regression to estimate when battery will reach
    Elective Replacement Indicator (ERI) threshold.
    """

    ERI_THRESHOLD = 2.2  # Volts

    @staticmethod
    def analyze_battery_depletion(trend: LongitudinalTrend) -> Dict[str, Any]:
        """
        Analyze battery voltage trend and predict ERI date.

        Args:
            trend: LongitudinalTrend for battery_voltage

        Returns:
            Dictionary with analysis results
        """
        if trend.variable_name != 'battery_voltage':
            raise ValueError("Trend must be for battery_voltage")

        if len(trend.values) < 3:
            return {'error': 'Insufficient data points for analysis'}

        # Convert time points to days since first observation
        time_points = [datetime.fromisoformat(tp) for tp in trend.time_points]
        start_time = time_points[0]
        days = [(tp - start_time).total_days for tp in time_points]

        # Linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(days, trend.values)

        # Predict ERI date
        eri_date = None
        days_to_eri = None

        if slope < 0:  # Battery is depleting
            # Calculate when voltage reaches ERI threshold
            days_to_eri = (BatteryTrendAnalyzer.ERI_THRESHOLD - intercept) / slope

            if days_to_eri > 0:
                eri_date = start_time + timedelta(days=days_to_eri)

        # Calculate depletion rate (V/year)
        depletion_rate_per_year = slope * 365.25

        return {
            'current_voltage': trend.values[-1],
            'depletion_rate_v_per_year': depletion_rate_per_year,
            'slope': slope,
            'intercept': intercept,
            'r_squared': r_value ** 2,
            'p_value': p_value,
            'eri_threshold': BatteryTrendAnalyzer.ERI_THRESHOLD,
            'predicted_eri_date': eri_date.isoformat() if eri_date else None,
            'days_to_eri': days_to_eri,
            'years_to_eri': days_to_eri / 365.25 if days_to_eri else None,
        }


class LeadImpedanceTrendAnalyzer:
    """
    Analyzes lead impedance trends to detect fractures or insulation failures.

    Sudden changes indicate potential lead problems requiring clinical attention.
    """

    FRACTURE_THRESHOLD = 500  # Ohms - sudden increase
    FAILURE_THRESHOLD = -300  # Ohms - sudden decrease

    @staticmethod
    def detect_anomalies(trend: LongitudinalTrend) -> List[Dict[str, Any]]:
        """
        Detect sudden changes in lead impedance.

        Args:
            trend: LongitudinalTrend for lead impedance

        Returns:
            List of detected anomalies with timestamps
        """
        if not trend.variable_name.startswith('lead_impedance'):
            raise ValueError("Trend must be for lead impedance")

        if len(trend.values) < 2:
            return []

        anomalies = []
        values = trend.values
        time_points = [datetime.fromisoformat(tp) for tp in trend.time_points]

        # Calculate differences between consecutive measurements
        for i in range(1, len(values)):
            delta = values[i] - values[i-1]

            if delta > LeadImpedanceTrendAnalyzer.FRACTURE_THRESHOLD:
                anomalies.append({
                    'type': 'possible_fracture',
                    'timestamp': time_points[i].isoformat(),
                    'previous_value': values[i-1],
                    'current_value': values[i],
                    'delta': delta,
                    'severity': 'critical',
                    'description': f"Sudden increase of {delta:.0f} Ohms suggests possible lead fracture"
                })

            elif delta < LeadImpedanceTrendAnalyzer.FAILURE_THRESHOLD:
                anomalies.append({
                    'type': 'possible_insulation_failure',
                    'timestamp': time_points[i].isoformat(),
                    'previous_value': values[i-1],
                    'current_value': values[i],
                    'delta': delta,
                    'severity': 'critical',
                    'description': f"Sudden decrease of {abs(delta):.0f} Ohms suggests possible insulation failure"
                })

        return anomalies

    @staticmethod
    def calculate_stability_score(trend: LongitudinalTrend) -> float:
        """
        Calculate lead stability score (0-100).

        Higher score = more stable impedance over time.

        Args:
            trend: LongitudinalTrend for lead impedance

        Returns:
            Stability score (0-100)
        """
        if len(trend.values) < 2:
            return 100.0

        # Calculate coefficient of variation
        mean_val = np.mean(trend.values)
        std_val = np.std(trend.values)

        if mean_val == 0:
            return 0.0

        cv = (std_val / mean_val) * 100

        # Convert CV to stability score (inverse relationship)
        # CV of 0% = 100 score, CV of 50% = 0 score
        stability_score = max(0, 100 - (cv * 2))

        return stability_score


class ArrhythmiaBurdenAnalyzer:
    """
    Analyzes arrhythmia burden trends over time.

    Identifies periods of high burden and calculates progression rates.
    """

    @staticmethod
    def calculate_burden_statistics(trend: LongitudinalTrend,
                                   window_days: int = 7) -> Dict[str, Any]:
        """
        Calculate rolling statistics for arrhythmia burden.

        Args:
            trend: LongitudinalTrend for afib_burden_percent
            window_days: Window size for rolling average

        Returns:
            Dictionary with burden statistics
        """
        if 'burden' not in trend.variable_name.lower():
            raise ValueError("Trend must be for arrhythmia burden")

        if len(trend.values) < 2:
            return {'error': 'Insufficient data'}

        time_points = [datetime.fromisoformat(tp) for tp in trend.time_points]
        values = np.array(trend.values)

        # Calculate rolling average (if enough points)
        rolling_avg = None
        if len(values) >= 7:
            rolling_avg = np.convolve(values, np.ones(min(7, len(values))) / min(7, len(values)), mode='valid')

        # Identify high burden episodes (>20%)
        high_burden_episodes = []
        for i, (tp, val) in enumerate(zip(time_points, values)):
            if val > 20:
                high_burden_episodes.append({
                    'timestamp': tp.isoformat(),
                    'burden_percent': val
                })

        # Calculate trend (increasing/decreasing)
        if len(values) >= 3:
            slope, _, r_value, _, _ = stats.linregress(
                range(len(values)),
                values
            )
            trend_direction = 'increasing' if slope > 0 else 'decreasing'
        else:
            slope = 0
            r_value = 0
            trend_direction = 'stable'

        return {
            'mean_burden': float(np.mean(values)),
            'max_burden': float(np.max(values)),
            'min_burden': float(np.min(values)),
            'current_burden': float(values[-1]),
            'rolling_average': rolling_avg.tolist() if rolling_avg is not None else None,
            'high_burden_episode_count': len(high_burden_episodes),
            'high_burden_episodes': high_burden_episodes,
            'trend_direction': trend_direction,
            'trend_slope': slope,
            'trend_r_squared': r_value ** 2 if len(values) >= 3 else 0,
        }
