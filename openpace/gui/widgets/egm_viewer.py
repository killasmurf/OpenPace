"""
EGM (Electrogram) Viewer Widget

Interactive waveform visualization for pacemaker electrograms with:
- High-resolution signal display
- R-peak annotations
- RR interval overlay
- Measurement calipers
- Pan and zoom capabilities
- Export functionality
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QGroupBox, QSpinBox,
                             QCheckBox, QToolBar, QSplitter)
from PyQt6.QtCore import Qt, QPointF, pyqtSignal
from PyQt6.QtGui import QAction, QIcon
import pyqtgraph as pg
import numpy as np

from openpace.database.models import Observation
from openpace.processing.egm_decoder import EGMDecoder, EGMProcessor


class EGMViewerWidget(QWidget):
    """
    Interactive EGM waveform viewer with analysis tools.

    Features:
    - Waveform display with adjustable time scale
    - R-peak detection and marking
    - RR interval overlay
    - Heart rate statistics
    - Measurement calipers
    - Event annotations
    - Export capabilities
    """

    # Signals
    measurement_changed = pyqtSignal(float, float)  # Time1, Time2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("EGM Viewer")

        # Data
        self.egm_data = None
        self.observation = None
        self.caliper_lines = []
        self.annotations = []

        # Setup UI
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Toolbar
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        # Main splitter (waveform + controls)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Waveform display (left)
        waveform_widget = self._create_waveform_display()
        splitter.addWidget(waveform_widget)

        # Control panel (right)
        control_panel = self._create_control_panel()
        splitter.addWidget(control_panel)

        # Set splitter proportions (80% waveform, 20% controls)
        splitter.setSizes([800, 200])

        # Status bar
        self.status_label = QLabel("No EGM loaded")
        layout.addWidget(self.status_label)

    def _create_toolbar(self) -> QToolBar:
        """Create toolbar with actions."""
        toolbar = QToolBar()

        # Zoom actions
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.triggered.connect(self._zoom_in)
        toolbar.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.triggered.connect(self._zoom_out)
        toolbar.addAction(zoom_out_action)

        zoom_reset_action = QAction("Reset Zoom", self)
        zoom_reset_action.triggered.connect(self._zoom_reset)
        toolbar.addAction(zoom_reset_action)

        toolbar.addSeparator()

        # Measurement tools
        add_caliper_action = QAction("Add Caliper", self)
        add_caliper_action.triggered.connect(self._add_caliper)
        toolbar.addAction(add_caliper_action)

        clear_calipers_action = QAction("Clear Calipers", self)
        clear_calipers_action.triggered.connect(self._clear_calipers)
        toolbar.addAction(clear_calipers_action)

        toolbar.addSeparator()

        # Export
        export_action = QAction("Export Image", self)
        export_action.triggered.connect(self._export_image)
        toolbar.addAction(export_action)

        return toolbar

    def _create_waveform_display(self) -> QWidget:
        """Create waveform display area."""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)

        # EGM plot
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.setLabel('left', 'Amplitude', units='μV')
        self.plot_widget.setLabel('bottom', 'Time', units='s')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setTitle("Electrogram Waveform")

        # Enable crosshair cursor
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('gray', width=1, style=Qt.PenStyle.DashLine))
        self.hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('gray', width=1, style=Qt.PenStyle.DashLine))
        self.plot_widget.addItem(self.vLine, ignoreBounds=True)
        self.plot_widget.addItem(self.hLine, ignoreBounds=True)

        # Mouse move event for crosshair
        self.plot_widget.scene().sigMouseMoved.connect(self._mouse_moved)

        layout.addWidget(self.plot_widget)

        # RR interval plot
        self.rr_plot_widget = pg.PlotWidget()
        self.rr_plot_widget.setBackground('w')
        self.rr_plot_widget.setLabel('left', 'RR Interval', units='ms')
        self.rr_plot_widget.setLabel('bottom', 'Beat Number')
        self.rr_plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.rr_plot_widget.setTitle("RR Interval Tachogram")
        self.rr_plot_widget.setMaximumHeight(150)

        layout.addWidget(self.rr_plot_widget)

        return widget

    def _create_control_panel(self) -> QWidget:
        """Create control panel."""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)

        # Display options
        display_group = QGroupBox("Display Options")
        display_layout = QVBoxLayout()
        display_group.setLayout(display_layout)

        self.show_peaks_checkbox = QCheckBox("Show R-Peaks")
        self.show_peaks_checkbox.setChecked(True)
        self.show_peaks_checkbox.stateChanged.connect(self._update_display)
        display_layout.addWidget(self.show_peaks_checkbox)

        self.show_filtered_checkbox = QCheckBox("Show Filtered Signal")
        self.show_filtered_checkbox.setChecked(False)
        self.show_filtered_checkbox.stateChanged.connect(self._update_display)
        display_layout.addWidget(self.show_filtered_checkbox)

        self.show_rr_checkbox = QCheckBox("Show RR Intervals")
        self.show_rr_checkbox.setChecked(True)
        self.show_rr_checkbox.stateChanged.connect(self._update_display)
        display_layout.addWidget(self.show_rr_checkbox)

        layout.addWidget(display_group)

        # Statistics group
        stats_group = QGroupBox("Statistics")
        stats_layout = QVBoxLayout()
        stats_group.setLayout(stats_layout)

        self.hr_mean_label = QLabel("Mean HR: --")
        stats_layout.addWidget(self.hr_mean_label)

        self.hr_min_label = QLabel("Min HR: --")
        stats_layout.addWidget(self.hr_min_label)

        self.hr_max_label = QLabel("Max HR: --")
        stats_layout.addWidget(self.hr_max_label)

        self.peak_count_label = QLabel("Beats: --")
        stats_layout.addWidget(self.peak_count_label)

        self.duration_label = QLabel("Duration: --")
        stats_layout.addWidget(self.duration_label)

        layout.addWidget(stats_group)

        # Filter settings
        filter_group = QGroupBox("Filter Settings")
        filter_layout = QVBoxLayout()
        filter_group.setLayout(filter_layout)

        # Low cutoff
        low_layout = QHBoxLayout()
        low_layout.addWidget(QLabel("Low Cut (Hz):"))
        self.low_cutoff_spin = QSpinBox()
        self.low_cutoff_spin.setRange(0, 50)
        self.low_cutoff_spin.setValue(1)
        self.low_cutoff_spin.valueChanged.connect(self._refilter_signal)
        low_layout.addWidget(self.low_cutoff_spin)
        filter_layout.addLayout(low_layout)

        # High cutoff
        high_layout = QHBoxLayout()
        high_layout.addWidget(QLabel("High Cut (Hz):"))
        self.high_cutoff_spin = QSpinBox()
        self.high_cutoff_spin.setRange(10, 200)
        self.high_cutoff_spin.setValue(100)
        self.high_cutoff_spin.valueChanged.connect(self._refilter_signal)
        high_layout.addWidget(self.high_cutoff_spin)
        filter_layout.addLayout(high_layout)

        # Refilter button
        refilter_btn = QPushButton("Apply Filter")
        refilter_btn.clicked.connect(self._refilter_signal)
        filter_layout.addWidget(refilter_btn)

        layout.addWidget(filter_group)

        layout.addStretch()

        return widget

    def load_egm(self, observation: Observation):
        """
        Load and display EGM from observation.

        Args:
            observation: Observation object with EGM blob
        """
        self.observation = observation

        if not observation.value_blob:
            self.status_label.setText("No EGM data in observation")
            return

        # Decode EGM
        try:
            egm_data = EGMDecoder.decode_blob(observation.value_blob)

            if not egm_data or 'error' in egm_data:
                error_msg = egm_data.get('error', 'Unknown error') if egm_data else 'Decode failed'
                self.status_label.setText(f"Error decoding EGM: {error_msg}")
                return

            # Analyze EGM
            self.egm_data = EGMProcessor.analyze_egm(egm_data)

            # Update display
            self._update_display()
            self._update_statistics()

            self.status_label.setText(
                f"Loaded EGM: {len(self.egm_data['samples'])} samples @ "
                f"{self.egm_data['sample_rate']} Hz ({self.egm_data['duration_seconds']:.1f}s)"
            )

        except Exception as e:
            self.status_label.setText(f"Error loading EGM: {str(e)}")
            import traceback
            traceback.print_exc()

    def _update_display(self):
        """Update waveform display."""
        if not self.egm_data:
            return

        self.plot_widget.clear()

        # Determine which signal to show
        if self.show_filtered_checkbox.isChecked() and 'filtered_samples' in self.egm_data:
            samples = self.egm_data['filtered_samples']
            label = "Filtered EGM"
        else:
            samples = self.egm_data['samples']
            label = "Raw EGM"

        # Create time axis
        sample_rate = self.egm_data['sample_rate']
        time_axis = np.arange(len(samples)) / sample_rate

        # Plot waveform
        pen = pg.mkPen(color='b', width=1)
        self.plot_widget.plot(time_axis, samples, pen=pen, name=label)

        # Show R-peaks if enabled
        if self.show_peaks_checkbox.isChecked() and 'peaks' in self.egm_data:
            peaks = self.egm_data['peaks']
            peak_times = [time_axis[p] for p in peaks if p < len(time_axis)]
            peak_values = [samples[p] for p in peaks if p < len(samples)]

            # Plot peak markers
            self.plot_widget.plot(
                peak_times,
                peak_values,
                pen=None,
                symbol='o',
                symbolPen='r',
                symbolBrush='r',
                symbolSize=8,
                name='R-Peaks'
            )

        # Re-add crosshair
        self.plot_widget.addItem(self.vLine, ignoreBounds=True)
        self.plot_widget.addItem(self.hLine, ignoreBounds=True)

        # Update RR interval plot
        self._update_rr_plot()

    def _update_rr_plot(self):
        """Update RR interval tachogram."""
        if not self.show_rr_checkbox.isChecked():
            self.rr_plot_widget.hide()
            return

        self.rr_plot_widget.show()
        self.rr_plot_widget.clear()

        if not self.egm_data or 'rr_intervals' not in self.egm_data:
            return

        rr_intervals = self.egm_data['rr_intervals']
        if not rr_intervals:
            return

        # Plot RR intervals
        beat_numbers = list(range(1, len(rr_intervals) + 1))
        pen = pg.mkPen(color='g', width=2)
        self.rr_plot_widget.plot(
            beat_numbers,
            rr_intervals,
            pen=pen,
            symbol='o',
            symbolSize=5,
            symbolBrush='g'
        )

        # Add mean line
        mean_rr = np.mean(rr_intervals)
        mean_line = pg.InfiniteLine(
            pos=mean_rr,
            angle=0,
            pen=pg.mkPen('r', width=2, style=Qt.PenStyle.DashLine),
            label=f'Mean: {mean_rr:.0f}ms'
        )
        self.rr_plot_widget.addItem(mean_line)

    def _update_statistics(self):
        """Update statistics display."""
        if not self.egm_data:
            return

        hr_stats = self.egm_data.get('hr_statistics', {})

        if hr_stats:
            self.hr_mean_label.setText(f"Mean HR: {hr_stats['mean_hr']:.1f} bpm")
            self.hr_min_label.setText(f"Min HR: {hr_stats['min_hr']:.1f} bpm")
            self.hr_max_label.setText(f"Max HR: {hr_stats['max_hr']:.1f} bpm")
        else:
            self.hr_mean_label.setText("Mean HR: --")
            self.hr_min_label.setText("Min HR: --")
            self.hr_max_label.setText("Max HR: --")

        peak_count = self.egm_data.get('peak_count', 0)
        self.peak_count_label.setText(f"Beats: {peak_count}")

        duration = self.egm_data.get('duration_seconds', 0)
        self.duration_label.setText(f"Duration: {duration:.1f}s")

    def _refilter_signal(self):
        """Refilter signal with new parameters."""
        if not self.egm_data or 'samples' not in self.egm_data:
            return

        low_cut = self.low_cutoff_spin.value()
        high_cut = self.high_cutoff_spin.value()

        if low_cut >= high_cut:
            self.status_label.setText("Error: Low cutoff must be less than high cutoff")
            return

        try:
            # Refilter
            filtered = EGMProcessor.filter_signal(
                self.egm_data['samples'],
                self.egm_data['sample_rate'],
                lowcut=low_cut,
                highcut=high_cut
            )

            # Update filtered samples
            self.egm_data['filtered_samples'] = filtered.tolist()

            # Redetect peaks on filtered signal
            peaks = EGMProcessor.detect_peaks(
                filtered.tolist(),
                self.egm_data['sample_rate']
            )
            self.egm_data['peaks'] = peaks
            self.egm_data['peak_count'] = len(peaks)

            # Recalculate RR intervals
            rr_intervals = EGMProcessor.calculate_rr_intervals(
                peaks,
                self.egm_data['sample_rate']
            )
            self.egm_data['rr_intervals'] = rr_intervals

            # Recalculate HR stats
            hr_stats = EGMProcessor.calculate_heart_rate(rr_intervals)
            self.egm_data['hr_statistics'] = hr_stats

            # Update display
            self._update_display()
            self._update_statistics()

            self.status_label.setText(f"Refiltered: {low_cut}-{high_cut} Hz, {len(peaks)} peaks detected")

        except Exception as e:
            self.status_label.setText(f"Error refiltering: {str(e)}")

    def _mouse_moved(self, pos):
        """Handle mouse movement for crosshair."""
        if not self.egm_data:
            return

        if self.plot_widget.sceneBoundingRect().contains(pos):
            mousePoint = self.plot_widget.getPlotItem().vb.mapSceneToView(pos)
            self.vLine.setPos(mousePoint.x())
            self.hLine.setPos(mousePoint.y())

    def _zoom_in(self):
        """Zoom in on waveform."""
        self.plot_widget.getPlotItem().getViewBox().scaleBy((0.5, 1))

    def _zoom_out(self):
        """Zoom out on waveform."""
        self.plot_widget.getPlotItem().getViewBox().scaleBy((2, 1))

    def _zoom_reset(self):
        """Reset zoom to show all data."""
        self.plot_widget.autoRange()

    def _add_caliper(self):
        """Add measurement caliper."""
        if not self.egm_data:
            return

        # Add vertical line at current view center
        view_range = self.plot_widget.getPlotItem().getViewBox().viewRange()
        center_x = (view_range[0][0] + view_range[0][1]) / 2

        line = pg.InfiniteLine(
            pos=center_x,
            angle=90,
            movable=True,
            pen=pg.mkPen('m', width=2, style=Qt.PenStyle.DashLine),
            label=f'{center_x:.3f}s'
        )
        self.plot_widget.addItem(line)
        self.caliper_lines.append(line)

        # If we have 2+ calipers, calculate interval
        if len(self.caliper_lines) >= 2:
            pos1 = self.caliper_lines[-2].value()
            pos2 = self.caliper_lines[-1].value()
            interval = abs(pos2 - pos1)
            self.status_label.setText(f"Caliper interval: {interval*1000:.1f}ms ({60/interval:.1f} bpm)")

    def _clear_calipers(self):
        """Clear all calipers."""
        for line in self.caliper_lines:
            self.plot_widget.removeItem(line)
        self.caliper_lines.clear()

    def _export_image(self):
        """Export waveform as image."""
        from PyQt6.QtWidgets import QFileDialog

        if not self.egm_data:
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export EGM Image",
            "egm_waveform.png",
            "PNG Image (*.png);;JPEG Image (*.jpg)"
        )

        if filename:
            try:
                exporter = pg.exporters.ImageExporter(self.plot_widget.plotItem)
                exporter.export(filename)
                self.status_label.setText(f"Exported to {filename}")
            except Exception as e:
                self.status_label.setText(f"Export failed: {str(e)}")

    def clear(self):
        """Clear all data and reset view."""
        self.egm_data = None
        self.observation = None
        self.plot_widget.clear()
        self.rr_plot_widget.clear()
        self._clear_calipers()

        self.hr_mean_label.setText("Mean HR: --")
        self.hr_min_label.setText("Min HR: --")
        self.hr_max_label.setText("Max HR: --")
        self.peak_count_label.setText("Beats: --")
        self.duration_label.setText("Duration: --")
        self.status_label.setText("No EGM loaded")
