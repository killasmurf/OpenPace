"""
Heart Rate Timeline Widget

Displays heart rate data over time with rate limits, alerts, and events.
Comprehensive timeline visualization for cardiac monitoring.
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox
from PyQt6.QtCore import Qt, pyqtSignal
import pyqtgraph as pg
import numpy as np

from openpace.gui.widgets.table_chart_mixin import TableChartMixin


class HeartRateTimelineWidget(QWidget, TableChartMixin):
    """
    Widget displaying heart rate timeline with limits and events.

    Features:
    - Heart rate plot (mean, max, min as shaded region)
    - Upper/lower rate limit lines
    - Alert markers (tachycardia, bradycardia, etc.)
    - Episode markers (AF, VT, SVT events)
    - Pacing percentage overlay
    - Color coding for out-of-range values
    """

    # Signals
    time_range_changed = pyqtSignal(float, float)  # start, end timestamps
    event_clicked = pyqtSignal(str, datetime)  # event_type, event_time

    # Default rate limits (can be overridden by device settings)
    DEFAULT_LOWER_RATE = 60  # bpm
    DEFAULT_UPPER_RATE = 130  # bpm

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Heart Rate Timeline")

        # Data storage
        self.time_points: List[datetime] = []
        self.heart_rates: List[float] = []
        self.heart_rates_max: List[float] = []
        self.heart_rates_min: List[float] = []

        # Rate limits
        self.lower_rate_limit: float = self.DEFAULT_LOWER_RATE
        self.upper_rate_limit: float = self.DEFAULT_UPPER_RATE

        # Events and alerts
        self.alerts: List[Dict[str, Any]] = []
        self.episodes: List[Dict[str, Any]] = []

        # Auto-detected alerts (from rate limit violations)
        self.auto_alerts: List[Dict[str, Any]] = []

        # Pacing data
        self.pacing_percent_atrial: List[float] = []
        self.pacing_percent_ventricular: List[float] = []

        # Setup UI
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        # Create main plot widget first
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # Axis labels
        self.plot_widget.setLabel('left', 'Heart Rate', units='bpm')
        self.plot_widget.setLabel('bottom', 'Date')

        # Enable mouse interaction
        self.plot_widget.setMouseEnabled(x=True, y=False)

        # Connect range change signal
        self.plot_widget.sigRangeChanged.connect(self._on_range_changed)

        # Legend
        self.legend = self.plot_widget.addLegend()

        # Initialize the table/chart toggle (from mixin)
        self.init_table_chart_toggle(
            title="Heart Rate Timeline",
            columns=["Date/Time", "HR Mean (bpm)", "HR Min", "HR Max", "Status"],
            chart_widget=self.plot_widget
        )

        # Add display toggles to the header (after title, before toggle switch)
        # Get the header layout (first item in main layout)
        main_layout = self.layout()
        header_layout = main_layout.itemAt(0).layout()

        # Insert checkboxes before the stretch (position 1) or find the stretch
        # The mixin creates: title_label, stretch, view_toggle
        # We want to insert our checkboxes before the view_toggle

        # Create checkboxes
        self.show_limits_cb = QCheckBox("Rate Limits")
        self.show_limits_cb.setChecked(True)
        self.show_limits_cb.toggled.connect(self._update_plot)

        self.show_range_cb = QCheckBox("Min/Max Range")
        self.show_range_cb.setChecked(True)
        self.show_range_cb.toggled.connect(self._update_plot)

        self.show_events_cb = QCheckBox("Events")
        self.show_events_cb.setChecked(True)
        self.show_events_cb.toggled.connect(self._update_plot)

        self.show_alerts_cb = QCheckBox("Alerts")
        self.show_alerts_cb.setChecked(True)
        self.show_alerts_cb.toggled.connect(self._update_plot)

        # Insert checkboxes before the toggle switch (which is at the end)
        # Position: title(0), stretch(1), toggle(2) -> insert at 2, 3, 4, 5
        header_layout.insertWidget(2, self.show_limits_cb)
        header_layout.insertWidget(3, self.show_range_cb)
        header_layout.insertWidget(4, self.show_events_cb)
        header_layout.insertWidget(5, self.show_alerts_cb)

        # Set reasonable Y range for heart rate
        self.plot_widget.setYRange(40, 180, padding=0.05)

    def set_heart_rate_data(self, time_points: List[datetime],
                            heart_rates: List[float],
                            heart_rates_max: Optional[List[float]] = None,
                            heart_rates_min: Optional[List[float]] = None):
        """
        Set heart rate data for plotting.

        Args:
            time_points: List of datetime objects
            heart_rates: List of mean heart rate values (bpm)
            heart_rates_max: Optional list of max heart rates
            heart_rates_min: Optional list of min heart rates
        """
        self.time_points = time_points
        self.heart_rates = heart_rates
        self.heart_rates_max = heart_rates_max or []
        self.heart_rates_min = heart_rates_min or []

        self._update_plot()

    def set_rate_limits(self, lower_rate: float, upper_rate: float):
        """
        Set the programmed rate limits.

        Args:
            lower_rate: Lower rate limit (bpm)
            upper_rate: Upper rate limit (bpm)
        """
        self.lower_rate_limit = lower_rate
        self.upper_rate_limit = upper_rate
        self._update_plot()

    def set_alerts(self, alerts: List[Dict[str, Any]]):
        """
        Set alert data for display.

        Args:
            alerts: List of alert dictionaries with keys:
                - time: datetime
                - type: str (e.g., 'tachycardia', 'bradycardia', 'pause')
                - value: float (heart rate or duration)
                - severity: str ('low', 'medium', 'high')
        """
        self.alerts = alerts
        self._update_plot()

    def set_episodes(self, episodes: List[Dict[str, Any]]):
        """
        Set episode/event data for display.

        Args:
            episodes: List of episode dictionaries with keys:
                - start_time: datetime
                - end_time: datetime (optional)
                - type: str (e.g., 'AF', 'VT', 'SVT', 'AT')
                - duration_seconds: float
                - max_rate: float (optional)
        """
        self.episodes = episodes
        self._update_plot()

    def set_pacing_data(self, time_points: List[datetime],
                        atrial_percent: List[float],
                        ventricular_percent: List[float]):
        """
        Set pacing percentage data.

        Args:
            time_points: List of datetime objects
            atrial_percent: Atrial pacing percentages
            ventricular_percent: Ventricular pacing percentages
        """
        # Store for potential overlay display
        self.pacing_percent_atrial = atrial_percent
        self.pacing_percent_ventricular = ventricular_percent

    def _detect_alerts(self):
        """
        Auto-detect alerts from heart rate data based on rate limits.

        Detects:
        - Bradycardia (HR below lower limit) - Yellow alert
        - Tachycardia (HR above upper limit) - Red alert
        - Severe bradycardia (HR < 50 bpm) - Red alert
        - Severe tachycardia (HR > 150 bpm) - Red alert
        """
        self.auto_alerts = []

        if not self.time_points or not self.heart_rates:
            return

        # Use max heart rates for tachycardia detection if available
        hr_max_data = self.heart_rates_max if self.heart_rates_max else self.heart_rates
        # Use min heart rates for bradycardia detection if available
        hr_min_data = self.heart_rates_min if self.heart_rates_min else self.heart_rates

        for i, dt in enumerate(self.time_points):
            hr_mean = self.heart_rates[i] if i < len(self.heart_rates) else 0
            hr_max = hr_max_data[i] if i < len(hr_max_data) else hr_mean
            hr_min = hr_min_data[i] if i < len(hr_min_data) else hr_mean

            # Check for tachycardia (using max HR if available)
            if hr_max > self.upper_rate_limit:
                # Determine severity
                if hr_max > 150:
                    severity = 'high'
                    alert_type = 'Severe Tachycardia'
                elif hr_max > self.upper_rate_limit + 20:
                    severity = 'medium'
                    alert_type = 'Tachycardia'
                else:
                    severity = 'low'
                    alert_type = 'High HR'

                self.auto_alerts.append({
                    'time': dt,
                    'type': alert_type,
                    'value': hr_max,
                    'severity': severity,
                    'direction': 'high'
                })

            # Check for bradycardia (using min HR if available)
            if hr_min < self.lower_rate_limit:
                # Determine severity
                if hr_min < 40:
                    severity = 'high'
                    alert_type = 'Severe Bradycardia'
                elif hr_min < 50:
                    severity = 'medium'
                    alert_type = 'Bradycardia'
                else:
                    severity = 'low'
                    alert_type = 'Low HR'

                self.auto_alerts.append({
                    'time': dt,
                    'type': alert_type,
                    'value': hr_min,
                    'severity': severity,
                    'direction': 'low'
                })

    def _plot_auto_alerts(self, timestamps: List[float]):
        """
        Plot auto-detected alerts as markers on the timeline.

        Uses different symbols and colors:
        - Red triangle (▲) for high severity
        - Orange diamond (◆) for medium severity
        - Yellow circle (●) for low severity
        """
        if not self.auto_alerts:
            return

        # Group alerts by severity for plotting
        high_alerts = []
        medium_alerts = []
        low_alerts = []

        for alert in self.auto_alerts:
            alert_time = alert['time']
            if isinstance(alert_time, str):
                alert_time = datetime.fromisoformat(alert_time)

            alert_ts = alert_time.timestamp()
            value = alert.get('value', 0)
            severity = alert.get('severity', 'low')

            if severity == 'high':
                high_alerts.append((alert_ts, value, alert))
            elif severity == 'medium':
                medium_alerts.append((alert_ts, value, alert))
            else:
                low_alerts.append((alert_ts, value, alert))

        # Plot high severity alerts (red triangles)
        if high_alerts:
            x = [a[0] for a in high_alerts]
            y = [a[1] for a in high_alerts]
            self.plot_widget.plot(
                x, y,
                pen=None,
                symbol='t',  # Triangle
                symbolSize=12,
                symbolBrush=(255, 0, 0),
                symbolPen=pg.mkPen((150, 0, 0), width=2),
                name='High Alert'
            )

            # Add vertical lines for high alerts
            for alert_ts, value, alert in high_alerts:
                line = pg.InfiniteLine(
                    pos=alert_ts,
                    angle=90,
                    pen=pg.mkPen(color=(255, 0, 0, 100), width=1, style=Qt.PenStyle.DotLine)
                )
                self.plot_widget.addItem(line)

        # Plot medium severity alerts (orange diamonds)
        if medium_alerts:
            x = [a[0] for a in medium_alerts]
            y = [a[1] for a in medium_alerts]
            self.plot_widget.plot(
                x, y,
                pen=None,
                symbol='d',  # Diamond
                symbolSize=10,
                symbolBrush=(255, 165, 0),
                symbolPen=pg.mkPen((200, 130, 0), width=2),
                name='Medium Alert'
            )

        # Plot low severity alerts (yellow circles)
        if low_alerts:
            x = [a[0] for a in low_alerts]
            y = [a[1] for a in low_alerts]
            self.plot_widget.plot(
                x, y,
                pen=None,
                symbol='o',  # Circle
                symbolSize=8,
                symbolBrush=(255, 255, 0),
                symbolPen=pg.mkPen((200, 200, 0), width=2),
                name='Low Alert'
            )

    def _update_plot(self):
        """Update the plot with current data and settings."""
        self.plot_widget.clear()

        if len(self.time_points) == 0:
            self.info_label.setText("No data")
            return

        # Convert datetimes to timestamps
        timestamps = [dt.timestamp() for dt in self.time_points]

        # Auto-detect alerts from heart rate data
        self._detect_alerts()

        # Plot min/max range if available and enabled
        if self.show_range_cb.isChecked() and self.heart_rates_max and self.heart_rates_min:
            self._plot_heart_rate_range(timestamps)

        # Plot mean heart rate line
        self._plot_heart_rate_line(timestamps)

        # Plot rate limits if enabled
        if self.show_limits_cb.isChecked():
            self._plot_rate_limits(timestamps)

        # Plot events/episodes if enabled
        if self.show_events_cb.isChecked():
            self._plot_episodes(timestamps)

        # Plot alerts (auto-detected and manual) if enabled
        if self.show_alerts_cb.isChecked():
            self._plot_alerts(timestamps)
            self._plot_auto_alerts(timestamps)

        # Configure time axis
        self._configure_time_axis()

        # Set time range with padding
        self._set_time_range_with_padding(timestamps)

        # Update statistics
        self._update_statistics()

    def _plot_heart_rate_line(self, timestamps: List[float]):
        """Plot the main heart rate line."""
        if not self.heart_rates:
            return

        # Color based on whether rates are within limits
        colors = []
        for hr in self.heart_rates:
            if hr < self.lower_rate_limit:
                colors.append((0, 100, 200))  # Blue for bradycardia
            elif hr > self.upper_rate_limit:
                colors.append((200, 0, 0))  # Red for tachycardia
            else:
                colors.append((0, 150, 0))  # Green for normal

        # Use most common color for line
        main_color = max(set(map(tuple, colors)), key=colors.count) if colors else (0, 150, 0)

        pen = pg.mkPen(color=main_color, width=2)
        self.plot_widget.plot(
            timestamps,
            self.heart_rates,
            pen=pen,
            symbol='o',
            symbolSize=5,
            symbolBrush=main_color,
            name='Heart Rate (Mean)'
        )

    def _plot_heart_rate_range(self, timestamps: List[float]):
        """Plot shaded region between min and max heart rates."""
        if not self.heart_rates_max or not self.heart_rates_min:
            return

        if len(self.heart_rates_max) != len(timestamps):
            return

        # Create fill between min and max
        fill = pg.FillBetweenItem(
            pg.PlotDataItem(timestamps, self.heart_rates_max),
            pg.PlotDataItem(timestamps, self.heart_rates_min),
            brush=pg.mkBrush(100, 100, 200, 50)
        )
        self.plot_widget.addItem(fill)

        # Plot max line (dashed)
        pen_max = pg.mkPen(color=(100, 100, 200, 150), width=1, style=Qt.PenStyle.DashLine)
        self.plot_widget.plot(timestamps, self.heart_rates_max, pen=pen_max, name='Max HR')

        # Plot min line (dashed)
        pen_min = pg.mkPen(color=(100, 100, 200, 150), width=1, style=Qt.PenStyle.DashLine)
        self.plot_widget.plot(timestamps, self.heart_rates_min, pen=pen_min, name='Min HR')

    def _plot_rate_limits(self, timestamps: List[float]):
        """Plot horizontal rate limit lines."""
        if len(timestamps) < 2:
            return

        min_t, max_t = min(timestamps), max(timestamps)
        padding = (max_t - min_t) * 0.1
        x_range = [min_t - padding, max_t + padding]

        # Lower rate limit (blue dashed)
        pen_lower = pg.mkPen(color=(0, 100, 200), width=2, style=Qt.PenStyle.DashLine)
        self.plot_widget.plot(
            x_range,
            [self.lower_rate_limit, self.lower_rate_limit],
            pen=pen_lower,
            name=f'Lower Limit ({self.lower_rate_limit:.0f} bpm)'
        )

        # Upper rate limit (red dashed)
        pen_upper = pg.mkPen(color=(200, 0, 0), width=2, style=Qt.PenStyle.DashLine)
        self.plot_widget.plot(
            x_range,
            [self.upper_rate_limit, self.upper_rate_limit],
            pen=pen_upper,
            name=f'Upper Limit ({self.upper_rate_limit:.0f} bpm)'
        )

    def _plot_alerts(self, timestamps: List[float]):
        """Plot alert markers on the timeline."""
        if not self.alerts:
            return

        for alert in self.alerts:
            try:
                alert_time = alert.get('time')
                if isinstance(alert_time, str):
                    alert_time = datetime.fromisoformat(alert_time)

                alert_ts = alert_time.timestamp()
                alert_type = alert.get('type', 'unknown')
                severity = alert.get('severity', 'low')
                value = alert.get('value', 0)

                # Color based on severity
                if severity == 'high':
                    color = (255, 0, 0)
                elif severity == 'medium':
                    color = (255, 165, 0)
                else:
                    color = (255, 255, 0)

                # Plot vertical line at alert time
                line = pg.InfiniteLine(
                    pos=alert_ts,
                    angle=90,
                    pen=pg.mkPen(color=color, width=2, style=Qt.PenStyle.DotLine),
                    label=f'{alert_type}: {value:.0f}',
                    labelOpts={'position': 0.9, 'color': color}
                )
                self.plot_widget.addItem(line)

            except Exception as e:
                print(f"Error plotting alert: {e}")

    def _plot_episodes(self, timestamps: List[float]):
        """Plot episode regions on the timeline."""
        if not self.episodes:
            return

        # Episode type colors
        episode_colors = {
            'AF': (255, 100, 100, 80),   # Red
            'VT': (255, 0, 0, 100),       # Dark red
            'SVT': (255, 165, 0, 80),     # Orange
            'AT': (255, 200, 100, 80),    # Light orange
            'pause': (100, 100, 255, 80), # Blue
        }

        for episode in self.episodes:
            try:
                start_time = episode.get('start_time')
                if isinstance(start_time, str):
                    start_time = datetime.fromisoformat(start_time)

                start_ts = start_time.timestamp()

                # Get end time or calculate from duration
                end_time = episode.get('end_time')
                if end_time:
                    if isinstance(end_time, str):
                        end_time = datetime.fromisoformat(end_time)
                    end_ts = end_time.timestamp()
                else:
                    duration = episode.get('duration_seconds', 60)
                    end_ts = start_ts + duration

                episode_type = episode.get('type', 'unknown')
                color = episode_colors.get(episode_type, (150, 150, 150, 80))

                # Create shaded region for episode
                region = pg.LinearRegionItem(
                    values=[start_ts, end_ts],
                    brush=pg.mkBrush(*color),
                    pen=pg.mkPen(color[:3], width=1),
                    movable=False
                )
                region.setZValue(-10)  # Behind other elements
                self.plot_widget.addItem(region)

                # Add label
                max_rate = episode.get('max_rate', '')
                label_text = f"{episode_type}"
                if max_rate:
                    label_text += f" ({max_rate:.0f}bpm)"

                # Add text label at top of region
                text = pg.TextItem(label_text, color=color[:3], anchor=(0.5, 1))
                text.setPos((start_ts + end_ts) / 2, self.upper_rate_limit + 10)
                self.plot_widget.addItem(text)

            except Exception as e:
                print(f"Error plotting episode: {e}")

    def _configure_time_axis(self):
        """Configure X-axis to display dates."""
        axis = pg.DateAxisItem(orientation='bottom')
        self.plot_widget.setAxisItems({'bottom': axis})

    def _set_time_range_with_padding(self, timestamps: List[float]):
        """Set X-axis range with padding."""
        if len(timestamps) == 0:
            return

        min_time = min(timestamps)
        max_time = max(timestamps)
        time_range = max_time - min_time

        padding = time_range * 0.10 if time_range > 0 else 86400
        self.plot_widget.setXRange(min_time - padding, max_time + padding, padding=0)

    def _update_statistics(self):
        """Update the statistics info label."""
        if not self.heart_rates:
            self.info_label.setText("No data")
            return

        mean_hr = np.mean(self.heart_rates)
        min_hr = np.min(self.heart_rates)
        max_hr = np.max(self.heart_rates)

        # Count out-of-range readings
        below_limit = sum(1 for hr in self.heart_rates if hr < self.lower_rate_limit)
        above_limit = sum(1 for hr in self.heart_rates if hr > self.upper_rate_limit)

        info_parts = [
            f"Mean: {mean_hr:.0f} bpm",
            f"Range: {min_hr:.0f}-{max_hr:.0f} bpm",
        ]

        if below_limit > 0:
            info_parts.append(f'<span style="color: #0064C8;">Below: {below_limit}</span>')
        if above_limit > 0:
            info_parts.append(f'<span style="color: #C80000;">Above: {above_limit}</span>')
        if self.episodes:
            info_parts.append(f"Episodes: {len(self.episodes)}")

        # Count alerts by severity
        total_alerts = len(self.alerts) + len(self.auto_alerts)
        if total_alerts > 0:
            high_count = sum(1 for a in self.alerts if a.get('severity') == 'high')
            high_count += sum(1 for a in self.auto_alerts if a.get('severity') == 'high')
            medium_count = sum(1 for a in self.alerts if a.get('severity') == 'medium')
            medium_count += sum(1 for a in self.auto_alerts if a.get('severity') == 'medium')
            low_count = total_alerts - high_count - medium_count

            alert_parts = []
            if high_count > 0:
                alert_parts.append(f'<span style="color: #FF0000;">{high_count} high</span>')
            if medium_count > 0:
                alert_parts.append(f'<span style="color: #FFA500;">{medium_count} med</span>')
            if low_count > 0:
                alert_parts.append(f'<span style="color: #FFD700;">{low_count} low</span>')

            info_parts.append(f"Alerts: {', '.join(alert_parts)}")

        self.info_label.setText("  |  ".join(info_parts))

    def _on_range_changed(self, view_box, ranges):
        """Handle plot range changes."""
        x_range = ranges[0]
        self.time_range_changed.emit(x_range[0], x_range[1])

    def clear(self):
        """Clear all data and plots."""
        self.time_points = []
        self.heart_rates = []
        self.heart_rates_max = []
        self.heart_rates_min = []
        self.alerts = []
        self.auto_alerts = []
        self.episodes = []
        self.pacing_percent_atrial = []
        self.pacing_percent_ventricular = []
        self.plot_widget.clear()
        self.info_label.setText("No data")

    def get_table_row_data(self) -> List[List[Any]]:
        """
        Get data rows for the table view.

        Returns:
            List of rows: [Date/Time, HR Mean (bpm), HR Min, HR Max, Status]
        """
        rows = []
        for i, dt in enumerate(self.time_points):
            # Format datetime
            date_str = dt.strftime("%Y-%m-%d %H:%M")

            # Heart rate values
            hr_mean = self.heart_rates[i] if i < len(self.heart_rates) else 0
            hr_min = self.heart_rates_min[i] if i < len(self.heart_rates_min) else ""
            hr_max = self.heart_rates_max[i] if i < len(self.heart_rates_max) else ""

            # Format values
            hr_mean_str = f"{hr_mean:.0f}"
            hr_min_str = f"{hr_min:.0f}" if hr_min else ""
            hr_max_str = f"{hr_max:.0f}" if hr_max else ""

            # Determine status based on rate limits
            if hr_mean < self.lower_rate_limit:
                status = "Below Limit"
            elif hr_mean > self.upper_rate_limit:
                status = "Above Limit"
            else:
                status = "Normal"

            rows.append([date_str, hr_mean_str, hr_min_str, hr_max_str, status])

        return rows
