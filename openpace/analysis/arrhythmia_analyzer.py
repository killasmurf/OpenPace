"""
Arrhythmia Burden Analyzer

Analyzes arrhythmia burden trends over time, identifies high burden episodes,
and calculates progression rates for atrial fibrillation and other arrhythmias.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import numpy as np
from scipy import stats

from openpace.database.models import LongitudinalTrend


class ArrhythmiaAnalyzer:
    """
    Analyzes arrhythmia burden trends over time.

    Identifies periods of high burden and calculates progression rates.
    """

    # Burden thresholds (percentages)
    LOW_BURDEN = 10.0
    MODERATE_BURDEN = 20.0
    HIGH_BURDEN = 40.0

    # Clinical significance thresholds
    MINIMAL_BURDEN = 1.0  # Below this is minimal/none
    PAROXYSMAL_THRESHOLD = 7.0  # < 7 days = paroxysmal
    PERSISTENT_THRESHOLD = 30.0  # > 30% = persistent

    @staticmethod
    def calculate_burden_statistics(trend: LongitudinalTrend,
                                   window_days: int = 7) -> Dict[str, Any]:
        """
        Calculate comprehensive statistics for arrhythmia burden.

        Args:
            trend: LongitudinalTrend for afib_burden_percent or similar
            window_days: Window size for rolling average (default 7 days)

        Returns:
            Dictionary with burden statistics and clinical classification
        """
        if 'burden' not in trend.variable_name.lower() and 'afib' not in trend.variable_name.lower():
            raise ValueError("Trend must be for arrhythmia burden")

        if len(trend.values) < 2:
            return {
                'error': 'Insufficient data',
                'min_points_required': 2,
                'current_points': len(trend.values)
            }

        time_points = [datetime.fromisoformat(tp) for tp in trend.time_points]
        values = np.array(trend.values)

        # Calculate rolling average (if enough points)
        rolling_avg = None
        if len(values) >= 3:
            window = min(window_days, len(values))
            rolling_avg = np.convolve(
                values,
                np.ones(window) / window,
                mode='valid'
            )

        # Identify burden episodes by level
        episodes = ArrhythmiaAnalyzer._categorize_episodes(time_points, values)

        # Calculate trend (increasing/decreasing/stable)
        trend_analysis = ArrhythmiaAnalyzer._calculate_trend(values)

        # Determine clinical classification
        classification = ArrhythmiaAnalyzer._classify_burden(
            values,
            time_points
        )

        # Calculate time metrics
        time_metrics = ArrhythmiaAnalyzer._calculate_time_metrics(
            time_points,
            values
        )

        return {
            'mean_burden': float(np.mean(values)),
            'median_burden': float(np.median(values)),
            'max_burden': float(np.max(values)),
            'min_burden': float(np.min(values)),
            'current_burden': float(values[-1]),
            'std_deviation': float(np.std(values)),
            'rolling_average': rolling_avg.tolist() if rolling_avg is not None else None,
            'episodes': episodes,
            'trend': trend_analysis,
            'classification': classification,
            'time_metrics': time_metrics,
            'data_points': len(values),
            'observation_period': {
                'start': time_points[0].isoformat(),
                'end': time_points[-1].isoformat(),
                'days': (time_points[-1] - time_points[0]).days
            }
        }

    @staticmethod
    def _categorize_episodes(time_points: List[datetime],
                            values: np.ndarray) -> Dict[str, Any]:
        """Categorize burden episodes by severity level."""
        minimal_episodes = []
        low_episodes = []
        moderate_episodes = []
        high_episodes = []

        for i, (tp, val) in enumerate(zip(time_points, values)):
            episode = {
                'timestamp': tp.isoformat(),
                'burden_percent': float(val)
            }

            if val < ArrhythmiaAnalyzer.MINIMAL_BURDEN:
                minimal_episodes.append(episode)
            elif val < ArrhythmiaAnalyzer.LOW_BURDEN:
                low_episodes.append(episode)
            elif val < ArrhythmiaAnalyzer.MODERATE_BURDEN:
                moderate_episodes.append(episode)
            elif val < ArrhythmiaAnalyzer.HIGH_BURDEN:
                moderate_episodes.append(episode)
            else:
                high_episodes.append(episode)

        return {
            'minimal': {
                'count': len(minimal_episodes),
                'threshold': f'< {ArrhythmiaAnalyzer.MINIMAL_BURDEN}%',
                'episodes': minimal_episodes
            },
            'low': {
                'count': len(low_episodes),
                'threshold': f'{ArrhythmiaAnalyzer.MINIMAL_BURDEN}-{ArrhythmiaAnalyzer.LOW_BURDEN}%',
                'episodes': low_episodes
            },
            'moderate': {
                'count': len(moderate_episodes),
                'threshold': f'{ArrhythmiaAnalyzer.LOW_BURDEN}-{ArrhythmiaAnalyzer.HIGH_BURDEN}%',
                'episodes': moderate_episodes
            },
            'high': {
                'count': len(high_episodes),
                'threshold': f'> {ArrhythmiaAnalyzer.HIGH_BURDEN}%',
                'episodes': high_episodes
            }
        }

    @staticmethod
    def _calculate_trend(values: np.ndarray) -> Dict[str, Any]:
        """Calculate burden trend direction and rate."""
        if len(values) < 3:
            return {
                'direction': 'unknown',
                'slope': 0,
                'r_squared': 0,
                'confidence': 'insufficient_data'
            }

        # Linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            range(len(values)),
            values
        )

        # Determine direction
        if abs(slope) < 0.5:  # Less than 0.5% change per observation
            direction = 'stable'
        elif slope > 0:
            direction = 'increasing'
        else:
            direction = 'decreasing'

        # Determine confidence
        if r_value ** 2 > 0.8 and p_value < 0.05:
            confidence = 'high'
        elif r_value ** 2 > 0.5 and p_value < 0.1:
            confidence = 'medium'
        else:
            confidence = 'low'

        return {
            'direction': direction,
            'slope': float(slope),
            'slope_percent_per_observation': float(slope),
            'r_squared': float(r_value ** 2),
            'p_value': float(p_value),
            'confidence': confidence
        }

    @staticmethod
    def _classify_burden(values: np.ndarray,
                        time_points: List[datetime]) -> Dict[str, Any]:
        """Classify burden pattern clinically."""
        mean_burden = np.mean(values)
        max_burden = np.max(values)
        current_burden = values[-1]

        # Determine classification type
        if mean_burden < ArrhythmiaAnalyzer.MINIMAL_BURDEN:
            classification_type = 'minimal'
            severity = 'none'
        elif mean_burden < ArrhythmiaAnalyzer.LOW_BURDEN:
            classification_type = 'paroxysmal'
            severity = 'low'
        elif mean_burden < ArrhythmiaAnalyzer.MODERATE_BURDEN:
            classification_type = 'persistent'
            severity = 'moderate'
        else:
            classification_type = 'chronic'
            severity = 'high'

        # Calculate burden variability
        variability = np.std(values) / mean_burden * 100 if mean_burden > 0 else 0

        return {
            'type': classification_type,
            'severity': severity,
            'variability_cv': float(variability),
            'description': ArrhythmiaAnalyzer._get_classification_description(
                classification_type,
                mean_burden
            )
        }

    @staticmethod
    def _calculate_time_metrics(time_points: List[datetime],
                               values: np.ndarray) -> Dict[str, Any]:
        """Calculate time-based metrics."""
        # Count days above thresholds
        days_above_low = int(np.sum(values >= ArrhythmiaAnalyzer.LOW_BURDEN))
        days_above_moderate = int(np.sum(values >= ArrhythmiaAnalyzer.MODERATE_BURDEN))
        days_above_high = int(np.sum(values >= ArrhythmiaAnalyzer.HIGH_BURDEN))

        total_observations = len(values)

        return {
            'observations_above_low_burden': days_above_low,
            'observations_above_moderate_burden': days_above_moderate,
            'observations_above_high_burden': days_above_high,
            'percent_above_low_burden': float(days_above_low / total_observations * 100),
            'percent_above_moderate_burden': float(days_above_moderate / total_observations * 100),
            'percent_above_high_burden': float(days_above_high / total_observations * 100),
        }

    @staticmethod
    def _get_classification_description(classification_type: str,
                                       mean_burden: float) -> str:
        """Get clinical description of burden classification."""
        descriptions = {
            'minimal': f"Minimal burden ({mean_burden:.1f}%). No significant arrhythmia detected.",
            'paroxysmal': f"Paroxysmal pattern ({mean_burden:.1f}%). Intermittent episodes.",
            'persistent': f"Persistent pattern ({mean_burden:.1f}%). Regular sustained episodes.",
            'chronic': f"Chronic pattern ({mean_burden:.1f}%). High continuous burden."
        }
        return descriptions.get(classification_type, "Unknown pattern")

    @staticmethod
    def get_recommendation(analysis: Dict[str, Any]) -> str:
        """
        Get clinical recommendation based on burden analysis.

        Args:
            analysis: Analysis results from calculate_burden_statistics()

        Returns:
            Clinical recommendation text
        """
        if 'error' in analysis:
            return "Insufficient data for recommendation. Collect more transmissions."

        current_burden = analysis['current_burden']
        classification = analysis['classification']['severity']
        trend_direction = analysis['trend']['direction']

        if current_burden >= ArrhythmiaAnalyzer.HIGH_BURDEN:
            return "HIGH BURDEN: Consider rhythm control strategy and anticoagulation review."
        elif current_burden >= ArrhythmiaAnalyzer.MODERATE_BURDEN:
            if trend_direction == 'increasing':
                return "MODERATE BURDEN (Increasing): Monitor closely. Consider intervention."
            else:
                return "MODERATE BURDEN: Continue monitoring and current treatment."
        elif current_burden >= ArrhythmiaAnalyzer.LOW_BURDEN:
            if trend_direction == 'increasing':
                return "LOW BURDEN (Increasing trend): Monitor for progression."
            else:
                return "LOW BURDEN: Continue routine monitoring."
        else:
            return "MINIMAL BURDEN: Continue routine device monitoring."
