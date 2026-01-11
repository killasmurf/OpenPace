"""
AFib Burden Bar Chart Widget

Displays arrhythmia burden over time as bar chart with trend indicators.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
import pyqtgraph as pg
import numpy as np


class BurdenWidget(QWidget):
    """
    Widget displaying arrhythmia burden as bar chart.

    Features:
    - Bar chart of burden percentage over time
    - Color coding (green → yellow → red for increasing burden)
    - High burden threshold line (20%)
    - Trend arrow (increasing/decreasing)
    - Mean burden display
    """

    HIGH_BURDEN_THRESHOLD = 20.0  # Percent

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Arrhythmia Burden")

        # Data
        self.time_points = []
        self.burden_values = []
        self.arrhythmia_type = "AFib"

        # Setup UI
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Title
        self.title_label = QLabel("AFib Burden")
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.title_label)

        # Info label (mean, trend)
        self.info_label = QLabel("No data")
        self.info_label.setStyleSheet("font-size: 11px; color: gray;")
        layout.addWidget(self.info_label)

        # Plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.showGrid(x=False, y=True, alpha=0.3)

        # Axis labels
        self.plot_widget.setLabel('left', 'Burden', units='%')
        self.plot_widget.setLabel('bottom', 'Date')

        # Y-axis range (0-100%)
        self.plot_widget.setYRange(0, 100)

        # Enable mouse interaction
        self.plot_widget.setMouseEnabled(x=True, y=False)

        layout.addWidget(self.plot_widget)

        # Legend
        self.plot_widget.addLegend()

    def set_data(self, arrhythmia_type: str, time_points: List[datetime], burden_values: List[float]):
        """
        Set arrhythmia burden data.

        Args:
            arrhythmia_type: Type of arrhythmia (e.g., "AFib", "VT", "SVT")
            time_points: List of datetime objects
            burden_values: List of burden percentages
        """
        self.arrhythmia_type = arrhythmia_type
        self.time_points = time_points
        self.burden_values = burden_values

        # Update title
        self.title_label.setText(f"{arrhythmia_type} Burden")

        # Convert datetimes to timestamps
        timestamps = [dt.timestamp() for dt in time_points]

        # Clear previous plots
        self.plot_widget.clear()

        if len(timestamps) == 0:
            self.info_label.setText("No data")
            return

        # Plot high burden threshold line
        self._plot_threshold_line(timestamps)

        # Plot burden bars
        self._plot_burden_bars(timestamps, burden_values)

        # Calculate and display statistics
        self._calculate_statistics(burden_values)

        # Configure time axis
        self._configure_time_axis(timestamps)

        # Set X-axis range with 10% extension on either side
        self._set_time_range_with_padding(timestamps)

        # Fixed Y-axis range
        self.plot_widget.setYRange(0, max(100, max(burden_values) * 1.1))

    def _plot_threshold_line(self, timestamps: List[float]):
        """
        Plot high burden threshold line.

        Args:
            timestamps: X-axis values for line extent
        """
        if len(timestamps) < 2:
            return

        pen = pg.mkPen(color=(200, 100, 0), width=2, style=Qt.PenStyle.DashLine)
        self.plot_widget.plot(
            [timestamps[0], timestamps[-1]],
            [self.HIGH_BURDEN_THRESHOLD, self.HIGH_BURDEN_THRESHOLD],
            pen=pen,
            name='High Burden (20%)'
        )

    def _plot_burden_bars(self, timestamps: List[float], burden_values: List[float]):
        """
        Plot burden as bar chart with color coding.

        Args:
            timestamps: X-axis timestamps
            burden_values: Burden percentages
        """
        if len(timestamps) == 0:
            return

        # Calculate bar width (days between points or fixed)
        if len(timestamps) > 1:
            # Use average spacing
            spacings = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
            avg_spacing = np.mean(spacings)
            bar_width = avg_spacing * 0.8  # 80% of spacing
        else:
            bar_width = 86400  # 1 day in seconds

        # Create bar chart
        colors = []
        for value in burden_values:
            if value < 10:
                color = (0, 200, 0, 150)  # Green
            elif value < 20:
                color = (200, 150, 0, 150)  # Yellow
            else:
                color = (200, 0, 0, 150)  # Red
            colors.append(color)

        # Plot bars
        bargraph = pg.BarGraphItem(
            x=timestamps,
            height=burden_values,
            width=bar_width,
            brushes=colors,
            pen=pg.mkPen(color=(100, 100, 100), width=1)
        )
        self.plot_widget.addItem(bargraph)

    def _calculate_statistics(self, burden_values: List[float]):
        """
        Calculate and display burden statistics.

        Args:
            burden_values: Burden percentages
        """
        if len(burden_values) == 0:
            self.info_label.setText("No data")
            return

        mean_burden = np.mean(burden_values)
        max_burden = np.max(burden_values)
        current_burden = burden_values[-1]

        # Determine trend
        if len(burden_values) >= 3:
            recent_mean = np.mean(burden_values[-3:])
            earlier_mean = np.mean(burden_values[:3]) if len(burden_values) >= 6 else np.mean(burden_values[:len(burden_values)//2])

            if recent_mean > earlier_mean * 1.2:
                trend = "↑ Increasing"
                trend_color = "red"
            elif recent_mean < earlier_mean * 0.8:
                trend = "↓ Decreasing"
                trend_color = "green"
            else:
                trend = "→ Stable"
                trend_color = "gray"
        else:
            trend = ""
            trend_color = "gray"

        # Build info text
        info_parts = [
            f"Current: {current_burden:.1f}%",
            f"Mean: {mean_burden:.1f}%",
            f"Max: {max_burden:.1f}%"
        ]

        if trend:
            info_parts.append(f'<span style="color: {trend_color};">{trend}</span>')

        self.info_label.setText("  |  ".join(info_parts))

    def _configure_time_axis(self, timestamps: List[float]):
        """
        Configure X-axis to display dates properly.

        Args:
            timestamps: Unix timestamps
        """
        axis = pg.DateAxisItem(orientation='bottom')
        self.plot_widget.setAxisItems({'bottom': axis})

    def _set_time_range_with_padding(self, timestamps: List[float]):
        """
        Set X-axis range with 10% padding on either side.

        Args:
            timestamps: Unix timestamps
        """
        if len(timestamps) == 0:
            return

        min_time = min(timestamps)
        max_time = max(timestamps)
        time_range = max_time - min_time

        # Add 10% padding on each side
        padding = time_range * 0.10 if time_range > 0 else 86400  # 1 day if single point

        self.plot_widget.setXRange(min_time - padding, max_time + padding, padding=0)

    def clear(self):
        """Clear all data and plots."""
        self.time_points = []
        self.burden_values = []
        self.plot_widget.clear()
        self.info_label.setText("No data")
