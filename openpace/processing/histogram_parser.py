"""
Histogram Parser

Parses rate histograms, activity histograms, and time-in-zone data from HL7 messages.
These histograms show distribution of heart rates, pacing rates, and patient activity levels.
"""

from typing import Dict, List, Optional, Tuple, Any
import json
import logging

logger = logging.getLogger(__name__)


class HistogramParser:
    """
    Parses histogram data from pacemaker transmissions.

    Histograms typically come in these formats:
    1. Text format: "zone1:10%|zone2:45%|zone3:30%|zone4:15%"
    2. JSON format: {"bins": [60, 70, 80, 90], "counts": [10, 45, 30, 15]}
    3. Encoded binary format (vendor-specific)
    """

    @staticmethod
    def parse_rate_histogram(histogram_data: str) -> Optional[Dict[str, Any]]:
        """
        Parse heart rate histogram.

        Typical format shows percentage of time in different rate zones.

        Args:
            histogram_data: Raw histogram string or JSON

        Returns:
            Dictionary with:
                - bins: List of rate ranges [(min, max), ...]
                - percentages: List of percentages for each bin
                - total_time: Total monitoring time if available
        """
        if not histogram_data:
            return None

        # Try JSON format first
        try:
            data = json.loads(histogram_data)
            return HistogramParser._parse_json_histogram(data, 'rate')
        except (json.JSONDecodeError, TypeError):
            pass

        # Try pipe-delimited format: "60-70:10%|70-80:45%|80-90:30%"
        if '|' in histogram_data:
            return HistogramParser._parse_piped_histogram(histogram_data)

        # Try comma-separated format: "60-70:10,70-80:45,80-90:30"
        if ',' in histogram_data and ':' in histogram_data:
            return HistogramParser._parse_csv_histogram(histogram_data)

        logger.warning(f"Could not parse rate histogram: {histogram_data[:100]}")
        return None

    @staticmethod
    def parse_activity_histogram(histogram_data: str) -> Optional[Dict[str, Any]]:
        """
        Parse patient activity histogram.

        Shows distribution of activity levels (sedentary, light, moderate, vigorous).

        Args:
            histogram_data: Raw histogram string

        Returns:
            Dictionary with activity levels and percentages
        """
        if not histogram_data:
            return None

        # Activity histograms often use labels
        # Format: "rest:40%|light:30%|moderate:20%|vigorous:10%"

        try:
            data = json.loads(histogram_data)
            return HistogramParser._parse_json_histogram(data, 'activity')
        except (json.JSONDecodeError, TypeError):
            pass

        if '|' in histogram_data:
            result = HistogramParser._parse_piped_histogram(histogram_data)
            if result:
                # Convert to activity-specific format
                return {
                    'activity_levels': result['bins'],
                    'percentages': result['percentages'],
                    'type': 'activity'
                }

        return None

    @staticmethod
    def parse_pacing_histogram(histogram_data: str) -> Optional[Dict[str, Any]]:
        """
        Parse pacing percentage histogram.

        Shows how often the pacemaker paced vs. intrinsic rhythm.

        Args:
            histogram_data: Raw histogram string

        Returns:
            Dictionary with pacing distribution
        """
        if not histogram_data:
            return None

        try:
            data = json.loads(histogram_data)
            return HistogramParser._parse_json_histogram(data, 'pacing')
        except (json.JSONDecodeError, TypeError):
            pass

        # Pacing histograms might show: "intrinsic:25%|paced:75%"
        if '|' in histogram_data or ',' in histogram_data:
            result = HistogramParser._parse_piped_histogram(histogram_data)
            if result:
                return {
                    **result,
                    'type': 'pacing'
                }

        return None

    @staticmethod
    def _parse_piped_histogram(data: str) -> Optional[Dict[str, Any]]:
        """
        Parse pipe-delimited histogram format.

        Format: "60-70:10%|70-80:45%|80-90:30%|90-100:15%"

        Args:
            data: Pipe-delimited string

        Returns:
            Parsed histogram dictionary
        """
        bins = []
        percentages = []

        parts = data.split('|')
        for part in parts:
            if ':' not in part:
                continue

            range_part, pct_part = part.split(':', 1)

            # Parse percentage
            pct_str = pct_part.replace('%', '').strip()
            try:
                pct = float(pct_str)
            except ValueError:
                continue

            # Parse range
            if '-' in range_part:
                # Numeric range: "60-70"
                try:
                    min_val, max_val = range_part.split('-')
                    bins.append((float(min_val.strip()), float(max_val.strip())))
                except ValueError:
                    # Label range: "rest", "light", etc.
                    bins.append(range_part.strip())
            else:
                # Single value or label
                bins.append(range_part.strip())

            percentages.append(pct)

        if not bins:
            return None

        return {
            'bins': bins,
            'percentages': percentages,
            'bin_count': len(bins),
        }

    @staticmethod
    def _parse_csv_histogram(data: str) -> Optional[Dict[str, Any]]:
        """
        Parse comma-separated histogram format.

        Format: "60-70:10,70-80:45,80-90:30"

        Args:
            data: Comma-separated string

        Returns:
            Parsed histogram dictionary
        """
        # Convert to pipe format and reuse parser
        piped_data = data.replace(',', '|')
        return HistogramParser._parse_piped_histogram(piped_data)

    @staticmethod
    def _parse_json_histogram(data: Dict, histogram_type: str) -> Dict[str, Any]:
        """
        Parse JSON histogram format.

        Format: {
            "bins": [60, 70, 80, 90, 100],
            "counts": [10, 45, 30, 15],
            "unit": "bpm"
        }

        Args:
            data: JSON dictionary
            histogram_type: Type of histogram ('rate', 'activity', 'pacing')

        Returns:
            Normalized histogram dictionary
        """
        bins = data.get('bins', [])
        counts = data.get('counts', [])
        percentages = data.get('percentages', [])

        # If counts but no percentages, calculate percentages
        if counts and not percentages:
            total = sum(counts)
            if total > 0:
                percentages = [(count / total) * 100 for count in counts]

        # Convert bins to ranges
        bin_ranges = []
        for i in range(len(bins) - 1):
            bin_ranges.append((bins[i], bins[i + 1]))

        return {
            'bins': bin_ranges if bin_ranges else bins,
            'percentages': percentages,
            'counts': counts,
            'type': histogram_type,
            'unit': data.get('unit', ''),
        }

    @staticmethod
    def calculate_statistics(histogram: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate summary statistics from histogram.

        Args:
            histogram: Parsed histogram dictionary

        Returns:
            Dictionary with statistical measures:
                - weighted_mean: Weighted average
                - mode_bin: Most frequent bin
                - percentile_50: Median bin
        """
        if not histogram or 'bins' not in histogram or 'percentages' not in histogram:
            return {}

        bins = histogram['bins']
        percentages = histogram['percentages']

        if len(bins) != len(percentages):
            return {}

        # Calculate weighted mean (for numeric bins)
        weighted_mean = None
        numeric_bins = []

        for bin_val, pct in zip(bins, percentages):
            if isinstance(bin_val, tuple):
                # Range: use midpoint
                mid = (bin_val[0] + bin_val[1]) / 2
                numeric_bins.append(mid)
            elif isinstance(bin_val, (int, float)):
                numeric_bins.append(float(bin_val))

        if numeric_bins:
            weighted_sum = sum(val * (pct / 100) for val, pct in zip(numeric_bins, percentages))
            weighted_mean = weighted_sum

        # Find mode (bin with highest percentage)
        max_pct_idx = percentages.index(max(percentages))
        mode_bin = bins[max_pct_idx]

        # Find median bin (50th percentile)
        cumulative = 0
        median_bin = bins[0]
        for bin_val, pct in zip(bins, percentages):
            cumulative += pct
            if cumulative >= 50:
                median_bin = bin_val
                break

        return {
            'weighted_mean': weighted_mean,
            'mode_bin': mode_bin,
            'median_bin': median_bin,
            'max_percentage': max(percentages),
        }


class TimeInZoneCalculator:
    """
    Calculates time spent in different heart rate or pacing zones.

    Used for assessing rate response, exercise capacity, and arrhythmia burden.
    """

    # Standard heart rate zones (as percentage of max HR or absolute bpm)
    STANDARD_HR_ZONES = {
        'bradycardia': (0, 60),
        'normal_rest': (60, 100),
        'elevated': (100, 120),
        'tachycardia': (120, 200),
        'extreme': (200, 300),
    }

    @staticmethod
    def calculate_time_in_zones(histogram: Dict[str, Any],
                                zone_definitions: Dict[str, Tuple[float, float]] = None) -> Dict[str, float]:
        """
        Calculate percentage of time in predefined zones.

        Args:
            histogram: Parsed histogram with bins and percentages
            zone_definitions: Custom zone ranges (optional)

        Returns:
            Dictionary mapping zone names to percentages
        """
        if not zone_definitions:
            zone_definitions = TimeInZoneCalculator.STANDARD_HR_ZONES

        bins = histogram.get('bins', [])
        percentages = histogram.get('percentages', [])

        zone_times = {zone: 0.0 for zone in zone_definitions.keys()}

        for bin_val, pct in zip(bins, percentages):
            # Determine bin range
            if isinstance(bin_val, tuple):
                bin_min, bin_max = bin_val
            elif isinstance(bin_val, (int, float)):
                # Single value - treat as point
                bin_min = bin_max = float(bin_val)
            else:
                # Non-numeric bin, skip
                continue

            # Check which zones this bin overlaps
            bin_mid = (bin_min + bin_max) / 2

            for zone_name, (zone_min, zone_max) in zone_definitions.items():
                if zone_min <= bin_mid < zone_max:
                    zone_times[zone_name] += pct
                    break

        return zone_times
