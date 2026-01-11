"""
Lead Impedance Analyzer

Analyzes lead impedance trends to detect fractures, insulation failures,
and other lead integrity issues requiring clinical attention.
"""

from typing import List, Dict, Any
from datetime import datetime
import numpy as np

from openpace.database.models import LongitudinalTrend


class ImpedanceAnalyzer:
    """
    Analyzes lead impedance trends to detect fractures or insulation failures.

    Sudden changes indicate potential lead problems requiring clinical attention.
    """

    # Anomaly detection thresholds
    FRACTURE_THRESHOLD = 500  # Ohms - sudden increase
    FAILURE_THRESHOLD = -300  # Ohms - sudden decrease

    # Normal range
    NORMAL_RANGE_MIN = 200  # Ohms
    NORMAL_RANGE_MAX = 1500  # Ohms

    # Stability thresholds
    EXCELLENT_STABILITY = 95  # Score > 95
    GOOD_STABILITY = 85  # Score 85-95
    FAIR_STABILITY = 70  # Score 70-85
    # Score < 70 = Poor stability

    @staticmethod
    def detect_anomalies(trend: LongitudinalTrend) -> List[Dict[str, Any]]:
        """
        Detect sudden changes in lead impedance.

        Args:
            trend: LongitudinalTrend for lead impedance

        Returns:
            List of detected anomalies with timestamps and severity
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
            current_value = values[i]

            # Check for fracture (sudden increase)
            if delta > ImpedanceAnalyzer.FRACTURE_THRESHOLD:
                severity = ImpedanceAnalyzer._determine_severity(
                    delta,
                    current_value,
                    'fracture'
                )
                anomalies.append({
                    'type': 'possible_fracture',
                    'timestamp': time_points[i].isoformat(),
                    'previous_value': values[i-1],
                    'current_value': current_value,
                    'delta': delta,
                    'severity': severity,
                    'description': f"Sudden increase of {delta:.0f} Ohms suggests possible lead fracture",
                    'recommendation': ImpedanceAnalyzer._get_fracture_recommendation(severity)
                })

            # Check for insulation failure (sudden decrease)
            elif delta < ImpedanceAnalyzer.FAILURE_THRESHOLD:
                severity = ImpedanceAnalyzer._determine_severity(
                    abs(delta),
                    current_value,
                    'failure'
                )
                anomalies.append({
                    'type': 'possible_insulation_failure',
                    'timestamp': time_points[i].isoformat(),
                    'previous_value': values[i-1],
                    'current_value': current_value,
                    'delta': delta,
                    'severity': severity,
                    'description': f"Sudden decrease of {abs(delta):.0f} Ohms suggests possible insulation failure",
                    'recommendation': ImpedanceAnalyzer._get_failure_recommendation(severity)
                })

            # Check for out-of-range values
            if current_value < ImpedanceAnalyzer.NORMAL_RANGE_MIN:
                anomalies.append({
                    'type': 'below_normal_range',
                    'timestamp': time_points[i].isoformat(),
                    'previous_value': values[i-1],
                    'current_value': current_value,
                    'delta': delta,
                    'severity': 'warning',
                    'description': f"Impedance {current_value:.0f} Ohms below normal range",
                    'recommendation': "Monitor for potential lead insulation compromise"
                })

            elif current_value > ImpedanceAnalyzer.NORMAL_RANGE_MAX:
                anomalies.append({
                    'type': 'above_normal_range',
                    'timestamp': time_points[i].isoformat(),
                    'previous_value': values[i-1],
                    'current_value': current_value,
                    'delta': delta,
                    'severity': 'warning',
                    'description': f"Impedance {current_value:.0f} Ohms above normal range",
                    'recommendation': "Monitor for potential lead conductor issues"
                })

        return anomalies

    @staticmethod
    def calculate_stability_score(trend: LongitudinalTrend) -> Dict[str, Any]:
        """
        Calculate lead stability score (0-100).

        Higher score = more stable impedance over time.

        Args:
            trend: LongitudinalTrend for lead impedance

        Returns:
            Dictionary with stability metrics
        """
        if len(trend.values) < 2:
            return {
                'score': 100.0,
                'rating': 'excellent',
                'confidence': 'low'
            }

        values = np.array(trend.values)

        # Calculate coefficient of variation
        mean_val = np.mean(values)
        std_val = np.std(values)

        if mean_val == 0:
            return {
                'score': 0.0,
                'rating': 'invalid',
                'confidence': 'none'
            }

        cv = (std_val / mean_val) * 100

        # Convert CV to stability score (inverse relationship)
        # CV of 0% = 100 score, CV of 50% = 0 score
        stability_score = max(0, 100 - (cv * 2))

        # Determine rating
        if stability_score >= ImpedanceAnalyzer.EXCELLENT_STABILITY:
            rating = 'excellent'
        elif stability_score >= ImpedanceAnalyzer.GOOD_STABILITY:
            rating = 'good'
        elif stability_score >= ImpedanceAnalyzer.FAIR_STABILITY:
            rating = 'fair'
        else:
            rating = 'poor'

        # Confidence based on number of data points
        if len(values) >= 10:
            confidence = 'high'
        elif len(values) >= 5:
            confidence = 'medium'
        else:
            confidence = 'low'

        return {
            'score': round(stability_score, 1),
            'rating': rating,
            'coefficient_of_variation': round(cv, 2),
            'mean_impedance': round(mean_val, 1),
            'std_deviation': round(std_val, 1),
            'confidence': confidence,
            'data_points': len(values)
        }

    @staticmethod
    def analyze_trend(trend: LongitudinalTrend) -> Dict[str, Any]:
        """
        Comprehensive analysis of lead impedance trend.

        Args:
            trend: LongitudinalTrend for lead impedance

        Returns:
            Complete analysis including anomalies, stability, and statistics
        """
        if not trend.variable_name.startswith('lead_impedance'):
            raise ValueError("Trend must be for lead impedance")

        # Detect anomalies
        anomalies = ImpedanceAnalyzer.detect_anomalies(trend)

        # Calculate stability
        stability = ImpedanceAnalyzer.calculate_stability_score(trend)

        # Basic statistics
        values = np.array(trend.values)
        time_points = [datetime.fromisoformat(tp) for tp in trend.time_points]

        # Calculate trend direction
        if len(values) >= 3:
            from scipy import stats as scipy_stats
            slope, intercept, r_value, p_value, std_err = scipy_stats.linregress(
                range(len(values)),
                values
            )
            trend_direction = 'increasing' if slope > 5 else ('decreasing' if slope < -5 else 'stable')
        else:
            slope = 0
            trend_direction = 'stable'

        # Overall assessment
        critical_anomalies = [a for a in anomalies if a['severity'] == 'critical']
        warning_anomalies = [a for a in anomalies if a['severity'] == 'warning']

        if critical_anomalies:
            overall_status = 'critical'
            recommendation = "URGENT: Critical lead issue detected. Review immediately."
        elif warning_anomalies:
            overall_status = 'warning'
            recommendation = "CAUTION: Lead anomaly detected. Monitor closely."
        elif stability['rating'] in ['poor', 'fair']:
            overall_status = 'monitor'
            recommendation = "Lead stability below optimal. Continue monitoring."
        else:
            overall_status = 'normal'
            recommendation = "Lead functioning normally."

        return {
            'lead_name': trend.variable_name.replace('lead_impedance_', '').title(),
            'current_impedance': values[-1],
            'mean_impedance': float(np.mean(values)),
            'min_impedance': float(np.min(values)),
            'max_impedance': float(np.max(values)),
            'impedance_range': float(np.max(values) - np.min(values)),
            'trend_direction': trend_direction,
            'trend_slope': slope,
            'stability': stability,
            'anomalies': anomalies,
            'anomaly_count': len(anomalies),
            'critical_anomaly_count': len(critical_anomalies),
            'warning_anomaly_count': len(warning_anomalies),
            'overall_status': overall_status,
            'recommendation': recommendation,
            'data_points': len(values),
            'observation_period': {
                'start': time_points[0].isoformat(),
                'end': time_points[-1].isoformat(),
                'days': (time_points[-1] - time_points[0]).days
            }
        }

    @staticmethod
    def _determine_severity(delta: float, current_value: float, anomaly_type: str) -> str:
        """Determine severity of anomaly."""
        if anomaly_type == 'fracture':
            if delta > 1000 or current_value > 2000:
                return 'critical'
            elif delta > 700 or current_value > 1800:
                return 'warning'
            else:
                return 'info'
        else:  # failure
            if delta > 500 or current_value < 100:
                return 'critical'
            elif delta > 400 or current_value < 150:
                return 'warning'
            else:
                return 'info'

    @staticmethod
    def _get_fracture_recommendation(severity: str) -> str:
        """Get recommendation for fracture."""
        if severity == 'critical':
            return "Immediate lead evaluation required. Consider lead replacement."
        elif severity == 'warning':
            return "Close monitoring required. Schedule follow-up interrogation."
        else:
            return "Monitor trend. Consider follow-up if pattern continues."

    @staticmethod
    def _get_failure_recommendation(severity: str) -> str:
        """Get recommendation for insulation failure."""
        if severity == 'critical':
            return "Immediate evaluation required. Possible insulation breach."
        elif severity == 'warning':
            return "Monitor closely for progressive insulation compromise."
        else:
            return "Continue monitoring. Verify with additional interrogations."
