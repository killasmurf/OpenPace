"""
Battery Depletion Analyzer

Analyzes battery voltage trends and predicts ERI (Elective Replacement Indicator) date.
Uses linear regression to estimate when battery will reach critical threshold.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from scipy import stats

from openpace.database.models import LongitudinalTrend


class BatteryAnalyzer:
    """
    Analyzes battery depletion trends and predicts ERI date.

    Uses linear regression to estimate when battery will reach
    Elective Replacement Indicator (ERI) threshold.
    """

    ERI_THRESHOLD = 2.2  # Volts
    EOL_THRESHOLD = 2.0  # End of Life threshold

    @staticmethod
    def analyze_depletion(trend: LongitudinalTrend) -> Dict[str, Any]:
        """
        Analyze battery voltage trend and predict ERI date.

        Args:
            trend: LongitudinalTrend for battery_voltage

        Returns:
            Dictionary with analysis results including:
            - current_voltage: Latest voltage reading
            - depletion_rate_v_per_year: Annual voltage loss
            - predicted_eri_date: When ERI threshold will be reached
            - years_to_eri: Years remaining until ERI
            - r_squared: Quality of fit (0-1)
            - confidence: Analysis confidence level
        """
        if trend.variable_name != 'battery_voltage':
            raise ValueError("Trend must be for battery_voltage")

        if len(trend.values) < 3:
            return {
                'error': 'Insufficient data points for analysis',
                'min_points_required': 3,
                'current_points': len(trend.values)
            }

        # Convert time points to days since first observation
        time_points = [datetime.fromisoformat(tp) for tp in trend.time_points]
        start_time = time_points[0]
        days = [(tp - start_time).total_seconds() / 86400 for tp in time_points]

        # Linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(days, trend.values)

        # Predict ERI date
        eri_date = None
        eol_date = None
        days_to_eri = None
        days_to_eol = None

        if slope < 0:  # Battery is depleting
            # Calculate when voltage reaches ERI threshold
            days_to_eri = (BatteryAnalyzer.ERI_THRESHOLD - intercept) / slope
            days_to_eol = (BatteryAnalyzer.EOL_THRESHOLD - intercept) / slope

            if days_to_eri > 0:
                eri_date = start_time + timedelta(days=days_to_eri)

            if days_to_eol > 0:
                eol_date = start_time + timedelta(days=days_to_eol)

        # Calculate depletion rate (V/year)
        depletion_rate_per_year = slope * 365.25

        # Determine confidence level
        confidence = BatteryAnalyzer._calculate_confidence(
            r_value ** 2,
            len(trend.values),
            p_value
        )

        # Calculate remaining capacity percentage
        current_voltage = trend.values[-1]
        nominal_voltage = 2.8  # Typical new pacemaker battery
        remaining_capacity = max(0, min(100,
            ((current_voltage - BatteryAnalyzer.ERI_THRESHOLD) /
             (nominal_voltage - BatteryAnalyzer.ERI_THRESHOLD)) * 100
        ))

        return {
            'current_voltage': current_voltage,
            'depletion_rate_v_per_year': depletion_rate_per_year,
            'slope': slope,
            'intercept': intercept,
            'r_squared': r_value ** 2,
            'p_value': p_value,
            'std_err': std_err,
            'eri_threshold': BatteryAnalyzer.ERI_THRESHOLD,
            'eol_threshold': BatteryAnalyzer.EOL_THRESHOLD,
            'predicted_eri_date': eri_date.isoformat() if eri_date else None,
            'predicted_eol_date': eol_date.isoformat() if eol_date else None,
            'days_to_eri': days_to_eri,
            'days_to_eol': days_to_eol,
            'years_to_eri': days_to_eri / 365.25 if days_to_eri else None,
            'years_to_eol': days_to_eol / 365.25 if days_to_eol else None,
            'remaining_capacity_percent': remaining_capacity,
            'confidence': confidence,
            'data_points': len(trend.values),
            'observation_period_days': max(days),
        }

    @staticmethod
    def _calculate_confidence(r_squared: float, n_points: int, p_value: float) -> str:
        """
        Calculate confidence level in the prediction.

        Args:
            r_squared: R-squared value from regression
            n_points: Number of data points
            p_value: Statistical significance

        Returns:
            Confidence level: 'high', 'medium', or 'low'
        """
        if r_squared > 0.9 and n_points >= 5 and p_value < 0.05:
            return 'high'
        elif r_squared > 0.7 and n_points >= 3 and p_value < 0.1:
            return 'medium'
        else:
            return 'low'

    @staticmethod
    def get_status_color(voltage: float) -> str:
        """
        Get color code for voltage level.

        Args:
            voltage: Current battery voltage

        Returns:
            Color code: 'green', 'yellow', or 'red'
        """
        if voltage >= 2.5:
            return 'green'
        elif voltage >= 2.3:
            return 'yellow'
        else:
            return 'red'

    @staticmethod
    def get_recommendation(analysis: Dict[str, Any]) -> str:
        """
        Get clinical recommendation based on analysis.

        Args:
            analysis: Analysis results from analyze_depletion()

        Returns:
            Recommendation text
        """
        if 'error' in analysis:
            return "Insufficient data for recommendation. Collect more transmissions."

        voltage = analysis['current_voltage']
        years_to_eri = analysis.get('years_to_eri')

        if voltage < BatteryAnalyzer.ERI_THRESHOLD:
            return "URGENT: Battery at ERI. Schedule device replacement immediately."
        elif voltage < 2.3:
            return "WARNING: Battery approaching ERI. Plan replacement soon."
        elif years_to_eri and years_to_eri < 0.5:
            return "CAUTION: Battery may reach ERI within 6 months. Monitor closely."
        elif years_to_eri and years_to_eri < 1:
            return "Battery expected to reach ERI within 1 year. Continue monitoring."
        else:
            return "Battery status normal. Continue routine monitoring."
