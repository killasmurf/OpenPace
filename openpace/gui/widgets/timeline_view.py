"""
Timeline View - OSCAR-Style Layout

Combines all trend widgets into a cohesive timeline visualization.
Displays battery, impedance, and burden trends in synchronized view.
Supports collapsible panels and size adjustment.
"""

from typing import Optional, Dict, List
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QScrollArea, QGroupBox,
    QSplitter, QToolButton, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint, QTimer, QRect
from PyQt6.QtGui import QIcon, QPainter, QColor, QPen
from sqlalchemy.orm import Session, joinedload

from openpace.database.models import Patient, Transmission, LongitudinalTrend
from openpace.processing.trend_calculator import TrendCalculator
from openpace.gui.layouts import GridLayoutManager, LayoutMode, LayoutSerializer
from openpace.config import get_config
from .battery_widget import BatteryTrendWidget
from .impedance_widget import ImpedanceTrendWidget
from .burden_widget import BurdenWidget
from .settings_panel import SettingsPanel
from .device_settings_widget import DeviceSettingsWidget
from .heart_rate_widget import HeartRateTimelineWidget
from .collapsible_panel import CollapsiblePanel
from .draggable_panel import DraggablePanel
from .resize_handle import ResizeHandleManager


class PatientSelectorWidget(QWidget):
    """
    Patient and date range selector widget.

    Signals:
        patient_selected: Emitted when patient selection changes
    """

    patient_selected = pyqtSignal(str)  # patient_id

    def __init__(self, db_session: Session, parent=None):
        super().__init__(parent)
        self.session = db_session
        self.current_patient_id = None

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QHBoxLayout()
        self.setLayout(layout)

        # Patient selector
        layout.addWidget(QLabel("Patient:"))

        self.patient_combo = QComboBox()
        self.patient_combo.currentIndexChanged.connect(self._on_patient_changed)
        layout.addWidget(self.patient_combo)

        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_patients)
        layout.addWidget(self.refresh_btn)

        layout.addStretch()

        # Load initial patient list
        self.load_patients()

    def load_patients(self):
        """Load patient list from database."""
        self.patient_combo.clear()

        try:
            patients = self.session.query(Patient).all()

            for patient in patients:
                display_name = patient.anonymized_id if patient.anonymized else patient.patient_name
                self.patient_combo.addItem(display_name, patient.patient_id)

            if patients:
                self.patient_combo.setCurrentIndex(0)

        except Exception as e:
            print(f"Error loading patients: {e}")

    def _on_patient_changed(self, index: int):
        """Handle patient selection change."""
        if index >= 0:
            patient_id = self.patient_combo.itemData(index)
            if patient_id:
                self.current_patient_id = patient_id
                self.patient_selected.emit(patient_id)

    def get_current_patient_id(self) -> Optional[str]:
        """Get currently selected patient ID."""
        return self.current_patient_id


class TimelineView(QWidget):
    """
    Main timeline view widget.

    OSCAR-style layout with collapsible, draggable, resizable trend panels.
    Uses GridLayoutManager for flexible panel positioning.
    """

    # Signals for panel visibility changes (for menu synchronization)
    battery_visibility_changed = pyqtSignal(bool)
    atrial_impedance_visibility_changed = pyqtSignal(bool)
    vent_impedance_visibility_changed = pyqtSignal(bool)
    burden_visibility_changed = pyqtSignal(bool)
    heart_rate_visibility_changed = pyqtSignal(bool)
    settings_visibility_changed = pyqtSignal(bool)
    device_settings_visibility_changed = pyqtSignal(bool)

    # Signal for layout changes
    layout_mode_changed = pyqtSignal(LayoutMode)

    def __init__(self, db_session: Session, parent=None, use_grid_layout: bool = True):
        super().__init__(parent)
        self.session = db_session
        self.current_patient_id = None

        # Feature flag for new grid layout
        self.use_grid_layout = use_grid_layout

        # Dictionary to track panels by panel_id
        self.panels = {}

        # Current orientation (for legacy QSplitter mode)
        self.current_orientation = Qt.Orientation.Vertical

        # Grid layout manager
        self.grid_manager = None

        # Drop zone visualization
        self.drop_zone_rect = None
        self.dragging_panel_id = None

        # Debounce timer for layout saves
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(1000)  # 1 second debounce
        self.save_timer.timeout.connect(self._save_layout_to_file)

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(layout)

        # Patient selector at top
        self.patient_selector = PatientSelectorWidget(self.session)
        self.patient_selector.patient_selected.connect(self.load_patient_data)
        layout.addWidget(self.patient_selector)

        # Create trend widgets
        self.battery_widget = BatteryTrendWidget()
        self.atrial_impedance_widget = ImpedanceTrendWidget()
        self.vent_impedance_widget = ImpedanceTrendWidget()
        self.burden_widget = BurdenWidget()
        self.heart_rate_widget = HeartRateTimelineWidget()
        self.settings_panel = SettingsPanel()
        self.device_settings_widget = DeviceSettingsWidget()

        if self.use_grid_layout:
            # Use new grid layout system
            self._init_grid_layout(layout)
        else:
            # Use legacy QSplitter layout
            self._init_splitter_layout(layout)

    def _init_grid_layout(self, parent_layout: QVBoxLayout):
        """Initialize grid-based layout system."""
        # Create container for grid
        self.grid_container = QWidget()
        self.grid_container.setMinimumSize(800, 600)

        # Create grid layout manager
        self.grid_manager = GridLayoutManager(self.grid_container, rows=12, cols=12)
        self.grid_manager.layout_changed.connect(self._on_layout_changed)

        # Layout editing mode (enabled by default)
        self.layout_edit_mode = True

        # Helper function to connect all panel signals
        def setup_panel(panel: DraggablePanel, visibility_signal):
            panel.visibility_changed.connect(visibility_signal.emit)
            panel.drag_started.connect(self._on_drag_started)
            panel.drag_moved.connect(self._on_drag_moved)
            panel.drag_ended.connect(self._on_drag_ended)
            panel.resize_grid_requested.connect(self._on_panel_resize_requested)

        # Create draggable panels
        self.battery_panel = DraggablePanel("battery", "Battery Status", self.battery_widget)
        setup_panel(self.battery_panel, self.battery_visibility_changed)
        self.panels['battery'] = self.battery_panel

        self.atrial_panel = DraggablePanel("atrial_impedance", "Atrial Lead Impedance",
                                          self.atrial_impedance_widget)
        setup_panel(self.atrial_panel, self.atrial_impedance_visibility_changed)
        self.panels['atrial_impedance'] = self.atrial_panel

        self.vent_panel = DraggablePanel("vent_impedance", "Ventricular Lead Impedance",
                                        self.vent_impedance_widget)
        setup_panel(self.vent_panel, self.vent_impedance_visibility_changed)
        self.panels['vent_impedance'] = self.vent_panel

        self.burden_panel = DraggablePanel("burden", "Arrhythmia Burden", self.burden_widget)
        setup_panel(self.burden_panel, self.burden_visibility_changed)
        self.panels['burden'] = self.burden_panel

        self.settings_panel_widget = DraggablePanel("settings", "Device Settings", self.settings_panel)
        setup_panel(self.settings_panel_widget, self.settings_visibility_changed)
        self.panels['settings'] = self.settings_panel_widget

        self.device_settings_panel = DraggablePanel("device_settings", "Device Settings (Fixed/Operator)",
                                                     self.device_settings_widget)
        setup_panel(self.device_settings_panel, self.device_settings_visibility_changed)
        self.panels['device_settings'] = self.device_settings_panel

        self.heart_rate_panel = DraggablePanel("heart_rate", "Heart Rate Timeline",
                                               self.heart_rate_widget)
        setup_panel(self.heart_rate_panel, self.heart_rate_visibility_changed)
        self.panels['heart_rate'] = self.heart_rate_panel

        # Set default vertical layout
        self._set_default_vertical_layout()

        # Load saved layout if available (do this after panels are added)
        self._load_layout_from_file()

        parent_layout.addWidget(self.grid_container)

        # Initialize cell sizes after layout is set up (delayed to ensure widget is sized)
        QTimer.singleShot(200, self._update_panel_cell_sizes)

    def _init_splitter_layout(self, parent_layout: QVBoxLayout):
        """Initialize legacy QSplitter layout."""
        # Splitter for resizable panels
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setHandleWidth(4)
        self.splitter.setChildrenCollapsible(False)

        # Create collapsible panels
        self.battery_panel = CollapsiblePanel("Battery Status", self.battery_widget)
        self.battery_panel.visibility_changed.connect(self.battery_visibility_changed.emit)
        self.panels['battery'] = self.battery_panel
        self.splitter.addWidget(self.battery_panel)

        self.atrial_panel = CollapsiblePanel("Atrial Lead Impedance", self.atrial_impedance_widget)
        self.atrial_panel.visibility_changed.connect(self.atrial_impedance_visibility_changed.emit)
        self.panels['atrial_impedance'] = self.atrial_panel
        self.splitter.addWidget(self.atrial_panel)

        self.vent_panel = CollapsiblePanel("Ventricular Lead Impedance", self.vent_impedance_widget)
        self.vent_panel.visibility_changed.connect(self.vent_impedance_visibility_changed.emit)
        self.panels['vent_impedance'] = self.vent_panel
        self.splitter.addWidget(self.vent_panel)

        self.burden_panel = CollapsiblePanel("Arrhythmia Burden", self.burden_widget)
        self.burden_panel.visibility_changed.connect(self.burden_visibility_changed.emit)
        self.panels['burden'] = self.burden_panel
        self.splitter.addWidget(self.burden_panel)

        self.settings_panel_widget = CollapsiblePanel("Device Settings", self.settings_panel)
        self.settings_panel_widget.visibility_changed.connect(self.settings_visibility_changed.emit)
        self.panels['settings'] = self.settings_panel_widget
        self.splitter.addWidget(self.settings_panel_widget)

        # Set initial sizes (equal distribution)
        sizes = [200] * 5
        self.splitter.setSizes(sizes)

        parent_layout.addWidget(self.splitter)

    def _set_default_vertical_layout(self):
        """Set default grid layout for panels with heart rate timeline at bottom."""
        if not self.grid_manager:
            return

        # Grid layout with heart rate timeline spanning full width at bottom
        # Row 1 (rows 0-4): Battery, Atrial Impedance, Ventricular Impedance
        self.grid_manager.add_panel("battery", self.battery_panel,
                                   row=0, col=0, row_span=4, col_span=4)
        self.grid_manager.add_panel("atrial_impedance", self.atrial_panel,
                                   row=0, col=4, row_span=4, col_span=4)
        self.grid_manager.add_panel("vent_impedance", self.vent_panel,
                                   row=0, col=8, row_span=4, col_span=4)
        # Row 2 (rows 4-8): Burden, Settings, Device Settings
        self.grid_manager.add_panel("burden", self.burden_panel,
                                   row=4, col=0, row_span=4, col_span=4)
        self.grid_manager.add_panel("settings", self.settings_panel_widget,
                                   row=4, col=4, row_span=4, col_span=4)
        self.grid_manager.add_panel("device_settings", self.device_settings_panel,
                                   row=4, col=8, row_span=4, col_span=4)
        # Row 3 (rows 8-12): Heart Rate Timeline (full width)
        self.grid_manager.add_panel("heart_rate", self.heart_rate_panel,
                                   row=8, col=0, row_span=4, col_span=12)

    def _set_default_horizontal_layout(self):
        """Set default horizontal (side-by-side) layout."""
        if not self.grid_manager:
            return

        # Battery panel full width at top
        self.grid_manager.add_panel("battery", self.battery_panel, row=0, col=0, row_span=2, col_span=12)

        # Impedance panels side-by-side
        self.grid_manager.add_panel("atrial_impedance", self.atrial_panel, row=2, col=0,
                                   row_span=2, col_span=6)
        self.grid_manager.add_panel("vent_impedance", self.vent_panel, row=2, col=6,
                                   row_span=2, col_span=6)
        # Burden and settings side-by-side
        self.grid_manager.add_panel("burden", self.burden_panel, row=4, col=0, row_span=2, col_span=6)
        self.grid_manager.add_panel("settings", self.settings_panel_widget, row=4, col=6,
                                   row_span=2, col_span=6)
        # Device settings half width
        self.grid_manager.add_panel("device_settings", self.device_settings_panel, row=6, col=0,
                                   row_span=2, col_span=6)
        # Heart rate timeline (spans remaining space)
        self.grid_manager.add_panel("heart_rate", self.heart_rate_panel, row=6, col=6,
                                   row_span=6, col_span=6)

    def _on_drag_started(self, panel_id: str, start_position: QPoint):
        """Handle drag start event."""
        self.dragging_panel_id = panel_id
        # Enable drop zone visualization
        self.setMouseTracking(True)

    def _on_drag_moved(self, panel_id: str, current_position: QPoint):
        """Handle drag move event."""
        if not self.grid_manager:
            return

        # Calculate drop zone
        drop_zone = self.grid_manager.get_drop_zone(current_position)

        if drop_zone:
            row, col = drop_zone
            # Update drop zone visualization
            self.drop_zone_rect = (row, col)
            self.update()  # Trigger repaint

    def _on_drag_ended(self, panel_id: str, end_position: QPoint):
        """Handle drag end event."""
        if not self.grid_manager:
            return

        # Calculate final drop zone
        drop_zone = self.grid_manager.get_drop_zone(end_position)

        if drop_zone:
            row, col = drop_zone
            # Move panel to new position
            self.grid_manager.move_panel(panel_id, row, col)

        # Clear drop zone visualization
        self.drop_zone_rect = None
        self.dragging_panel_id = None
        self.setMouseTracking(False)
        self.update()

        # Schedule layout save
        self._schedule_layout_save()

    def _on_layout_changed(self):
        """Handle layout change event."""
        # Schedule layout save
        self._schedule_layout_save()
        # Update cell sizes for resize handles
        self._update_panel_cell_sizes()

    def _on_panel_resize_requested(self, panel_id: str, delta_rows: int, delta_cols: int):
        """
        Handle panel resize request from drag handles or context menu.

        Args:
            panel_id: ID of the panel to resize
            delta_rows: Number of rows to add (positive) or remove (negative)
            delta_cols: Number of columns to add (positive) or remove (negative)
        """
        if not self.grid_manager:
            return

        panel_info = self.grid_manager.get_panel_info(panel_id)
        if not panel_info:
            return

        # Calculate new dimensions
        new_row_span = max(1, panel_info.row_span + delta_rows)
        new_col_span = max(1, panel_info.col_span + delta_cols)

        # Ensure we don't exceed grid bounds
        max_row_span = self.grid_manager.rows - panel_info.row
        max_col_span = self.grid_manager.cols - panel_info.col
        new_row_span = min(new_row_span, max_row_span)
        new_col_span = min(new_col_span, max_col_span)

        # Apply resize
        self.grid_manager.resize_panel(panel_id, new_row_span, new_col_span)

        # Schedule layout save
        self._schedule_layout_save()

    def _update_panel_cell_sizes(self):
        """Update cell sizes for all panels based on current grid container size."""
        if not self.grid_manager or not hasattr(self, 'grid_container'):
            return

        # Calculate cell dimensions
        container_size = self.grid_container.size()
        cell_width = max(1, container_size.width() // self.grid_manager.cols)
        cell_height = max(1, container_size.height() // self.grid_manager.rows)

        # Update all draggable panels
        for panel_id, panel in self.panels.items():
            if hasattr(panel, 'set_cell_size'):
                panel.set_cell_size(cell_width, cell_height)

    def set_edit_mode(self, enabled: bool):
        """
        Enable or disable layout editing mode.

        When disabled, panels cannot be dragged or resized.

        Args:
            enabled: True to enable editing, False to disable
        """
        self.layout_edit_mode = enabled

        # Update all draggable panels
        for panel_id, panel in self.panels.items():
            if hasattr(panel, 'set_edit_mode'):
                panel.set_edit_mode(enabled)

    def is_edit_mode(self) -> bool:
        """Check if layout editing is enabled."""
        return getattr(self, 'layout_edit_mode', True)

    def resizeEvent(self, event):
        """Handle resize to update cell sizes."""
        super().resizeEvent(event)
        # Update cell sizes when the widget is resized
        QTimer.singleShot(100, self._update_panel_cell_sizes)

    def _schedule_layout_save(self):
        """Schedule a debounced layout save."""
        if self.save_timer:
            self.save_timer.start()

    def _save_layout_to_file(self):
        """Save current layout to file."""
        if not self.grid_manager:
            return

        try:
            # Get config
            config = get_config()

            # Check if saving is enabled
            if not config.ui.save_panel_layouts:
                return

            # Serialize layout
            layout_data = LayoutSerializer.serialize(self.grid_manager)

            # Save to default location
            layout_path = LayoutSerializer.get_default_layout_path()
            LayoutSerializer.save_to_file(layout_data, layout_path)

            # Also save to config
            config.ui.panel_layouts['default'] = layout_data
            config.save_to_file()

        except Exception as e:
            print(f"Failed to save layout: {e}")

    def _load_layout_from_file(self):
        """Load layout from file if available."""
        if not self.grid_manager:
            return

        try:
            # Get config
            config = get_config()

            # Check if saved layouts exist
            if not config.ui.save_panel_layouts:
                return

            # Try to load from file first
            layout_path = LayoutSerializer.get_default_layout_path()
            layout_data = LayoutSerializer.load_from_file(layout_path)

            # If no file, try config
            if not layout_data:
                layout_data = config.ui.panel_layouts.get('default')

            # If we have layout data, restore it
            if layout_data and LayoutSerializer.validate_layout(layout_data):
                LayoutSerializer.deserialize(layout_data, self.grid_manager)
            else:
                # No saved layout, use default based on config
                default_mode = config.ui.default_layout_mode
                if default_mode == "horizontal":
                    self._set_default_horizontal_layout()
                else:
                    self._set_default_vertical_layout()

        except Exception as e:
            print(f"Failed to load layout: {e}")
            # Fall back to default vertical layout
            self._set_default_vertical_layout()

    def set_layout_mode(self, mode: LayoutMode):
        """
        Set the layout mode.

        Args:
            mode: The layout mode (FREE_GRID, VERTICAL, or HORIZONTAL)
        """
        if not self.grid_manager:
            return

        self.grid_manager.set_mode(mode)
        self.layout_mode_changed.emit(mode)

    def get_layout_mode(self) -> Optional[LayoutMode]:
        """Get current layout mode."""
        if self.grid_manager:
            return self.grid_manager.mode
        return None

    def save_layout(self) -> Dict:
        """
        Serialize current panel layout.

        Returns:
            Dictionary containing layout data
        """
        if self.grid_manager:
            return self.grid_manager.serialize_layout()
        return {}

    def restore_layout(self, layout_data: Dict):
        """
        Restore panel layout from saved state.

        Args:
            layout_data: Dictionary containing layout data
        """
        if self.grid_manager:
            self.grid_manager.restore_layout(layout_data)

    def paintEvent(self, event):
        """Custom paint event to show drop zones."""
        super().paintEvent(event)

        if self.drop_zone_rect and self.grid_manager:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Calculate drop zone rectangle
            row, col = self.drop_zone_rect
            cell_width = self.grid_manager.cell_width
            cell_height = self.grid_manager.cell_height

            # Get panel info to determine size
            if self.dragging_panel_id:
                panel_info = self.grid_manager.get_panel_info(self.dragging_panel_id)
                if panel_info:
                    rect = QRect(
                        int(col * cell_width),
                        int(row * cell_height),
                        int(panel_info.col_span * cell_width),
                        int(panel_info.row_span * cell_height)
                    )

                    # Draw drop zone indicator
                    pen = QPen(QColor(0, 120, 215), 2)  # Blue border
                    painter.setPen(pen)
                    painter.setBrush(QColor(0, 120, 215, 30))  # Semi-transparent fill
                    painter.drawRect(rect)

    def show_panel(self, panel_name: str):
        """Show a specific panel by name."""
        if panel_name in self.panels:
            self.panels[panel_name].show_panel()

            # If using grid layout, show in grid manager
            if self.grid_manager:
                self.grid_manager.show_panel(panel_name)

    def hide_panel(self, panel_name: str):
        """Hide a specific panel by name."""
        if panel_name in self.panels:
            self.panels[panel_name].hide_panel()

            # If using grid layout, hide in grid manager
            if self.grid_manager:
                self.grid_manager.hide_panel(panel_name)

    def toggle_panel(self, panel_name: str, visible: bool):
        """Toggle panel visibility."""
        if visible:
            self.show_panel(panel_name)
        else:
            self.hide_panel(panel_name)

    def set_orientation(self, orientation: Qt.Orientation):
        """
        Change the orientation of the panel layout.

        Args:
            orientation: Qt.Orientation.Vertical or Qt.Orientation.Horizontal
        """
        if self.use_grid_layout:
            # Map Qt orientation to LayoutMode
            if orientation == Qt.Orientation.Vertical:
                self.set_layout_mode(LayoutMode.VERTICAL)
            else:
                self.set_layout_mode(LayoutMode.HORIZONTAL)
        else:
            # Legacy QSplitter mode
            if orientation == self.current_orientation:
                return

            self.current_orientation = orientation

            # Get current panel sizes before changing orientation
            current_sizes = self.splitter.sizes()

            # Change splitter orientation
            self.splitter.setOrientation(orientation)

            # Restore sizes (they'll be applied to the new orientation)
            if len(current_sizes) == 5:
                self.splitter.setSizes(current_sizes)

    def load_patient_data(self, patient_id: str):
        """
        Load and display data for selected patient.

        Args:
            patient_id: Patient identifier
        """
        self.current_patient_id = patient_id

        try:
            # Query trends for this patient
            trends = self.session.query(LongitudinalTrend).filter_by(
                patient_id=patient_id
            ).all()

            # If no trends, calculate them
            if not trends:
                print(f"No pre-computed trends found, calculating...")
                calculator = TrendCalculator(self.session)
                trends = calculator.calculate_all_trends(patient_id)

            # Organize trends by variable
            trends_by_var = {t.variable_name: t for t in trends}

            # Debug: print available variables
            print(f"[DEBUG] Available trend variables: {list(trends_by_var.keys())}")

            # If still no trends (single transmission), load raw observations
            if not trends_by_var:
                print(f"[DEBUG] No trends available, loading raw observations...")
                self._load_raw_observations(patient_id)
                return

            # Load battery trend - try multiple variable names
            battery_var = None
            for var in ['battery_longevity', 'battery_percentage', 'battery_voltage']:
                if var in trends_by_var:
                    battery_var = var
                    break

            if battery_var:
                trend = trends_by_var[battery_var]
                time_points = [datetime.fromisoformat(tp) for tp in trend.time_points]
                # Determine measurement type from variable name
                if battery_var == 'battery_longevity':
                    measurement_type = 'longevity'
                elif battery_var == 'battery_percentage':
                    measurement_type = 'percentage'
                else:
                    measurement_type = 'voltage'
                self.battery_widget.set_data(time_points, trend.values, measurement_type)
            else:
                print(f"[DEBUG] No battery data found")

            # Load atrial impedance
            if 'lead_impedance_atrial' in trends_by_var:
                trend = trends_by_var['lead_impedance_atrial']
                time_points = [datetime.fromisoformat(tp) for tp in trend.time_points]
                self.atrial_impedance_widget.set_data("Atrial", time_points, trend.values)

            # Load ventricular impedance
            if 'lead_impedance_ventricular' in trends_by_var:
                trend = trends_by_var['lead_impedance_ventricular']
                time_points = [datetime.fromisoformat(tp) for tp in trend.time_points]
                self.vent_impedance_widget.set_data("Ventricular", time_points, trend.values)

            # Load AFib burden
            if 'afib_burden_percent' in trends_by_var:
                trend = trends_by_var['afib_burden_percent']
                time_points = [datetime.fromisoformat(tp) for tp in trend.time_points]
                self.burden_widget.set_data("AFib", time_points, trend.values)

            # Load heart rate data
            hr_time_points = None
            hr_values = None
            hr_max_values = None
            hr_min_values = None

            # Try heart_rate_mean first, fall back to heart_rate
            hr_var = 'heart_rate_mean' if 'heart_rate_mean' in trends_by_var else 'heart_rate'
            if hr_var in trends_by_var:
                trend = trends_by_var[hr_var]
                hr_time_points = [datetime.fromisoformat(tp) for tp in trend.time_points]
                hr_values = trend.values

            if 'heart_rate_max' in trends_by_var:
                trend = trends_by_var['heart_rate_max']
                hr_max_values = trend.values

            if 'heart_rate_min' in trends_by_var:
                trend = trends_by_var['heart_rate_min']
                hr_min_values = trend.values

            # Set heart rate data if available
            if hr_time_points and hr_values:
                self.heart_rate_widget.set_heart_rate_data(
                    hr_time_points, hr_values, hr_max_values, hr_min_values
                )

            # Try to load rate limits from trends (check multiple variable names)
            lower_rate = self.heart_rate_widget.DEFAULT_LOWER_RATE
            upper_rate = self.heart_rate_widget.DEFAULT_UPPER_RATE

            # Check for lower rate limit
            for var in ['lower_rate_limit', 'set_brady_lowrate']:
                if var in trends_by_var:
                    trend = trends_by_var[var]
                    if trend.values:
                        lower_rate = trend.values[-1]  # Use most recent value
                        break

            # Check for upper rate limit (use max tracking rate or max sensor rate)
            for var in ['upper_rate_limit', 'set_brady_max_tracking_rate', 'set_brady_max_sensor_rate']:
                if var in trends_by_var:
                    trend = trends_by_var[var]
                    if trend.values:
                        upper_rate = trend.values[-1]  # Use most recent value
                        break

            self.heart_rate_widget.set_rate_limits(lower_rate, upper_rate)

            # Load episodes for heart rate widget
            self._load_episodes(patient_id)

            # Load device settings from most recent transmission
            # Use joinedload to eagerly load observations
            most_recent_transmission = self.session.query(Transmission).options(
                joinedload(Transmission.observations)
            ).filter_by(
                patient_id=patient_id
            ).order_by(Transmission.transmission_date.desc()).first()

            if most_recent_transmission:
                print(f"[DEBUG] Loading settings from transmission {most_recent_transmission.transmission_id} with {len(most_recent_transmission.observations)} observations")
                self.settings_panel.load_transmission(most_recent_transmission)
                self.device_settings_widget.load_transmission(most_recent_transmission)
            else:
                self.settings_panel.clear()
                self.device_settings_widget.clear()

        except Exception as e:
            print(f"Error loading patient data: {e}")
            import traceback
            traceback.print_exc()

    def _load_raw_observations(self, patient_id: str):
        """
        Load raw observations directly when trend data is insufficient.

        Used when there's only a single transmission (not enough data for trends).

        Args:
            patient_id: Patient identifier
        """
        from openpace.database.models import Observation

        # Query all numeric observations for this patient
        observations = self.session.query(Observation).join(
            Observation.transmission
        ).filter(
            Observation.transmission.has(patient_id=patient_id),
            Observation.value_numeric.isnot(None)
        ).all()

        # Group observations by variable name
        obs_by_var = {}
        for obs in observations:
            if obs.variable_name not in obs_by_var:
                obs_by_var[obs.variable_name] = []
            obs_by_var[obs.variable_name].append(obs)

        print(f"[DEBUG] Raw observation variables: {list(obs_by_var.keys())}")

        # Load battery data - try multiple variable names (prefer longevity/percentage over voltage)
        for var in ['battery_longevity', 'battery_percentage', 'battery_voltage']:
            if var in obs_by_var:
                obs_list = obs_by_var[var]
                time_points = [obs.observation_time for obs in obs_list]
                values = [obs.value_numeric for obs in obs_list]
                # Determine measurement type from variable name
                if var == 'battery_longevity':
                    measurement_type = 'longevity'
                elif var == 'battery_percentage':
                    measurement_type = 'percentage'
                else:
                    measurement_type = 'voltage'
                self.battery_widget.set_data(time_points, values, measurement_type)
                print(f"[DEBUG] Loaded battery data ({var}): {len(values)} points")
                break

        # Load atrial impedance
        if 'lead_impedance_atrial' in obs_by_var:
            obs_list = obs_by_var['lead_impedance_atrial']
            time_points = [obs.observation_time for obs in obs_list]
            values = [obs.value_numeric for obs in obs_list]
            self.atrial_impedance_widget.set_data("Atrial", time_points, values)
            print(f"[DEBUG] Loaded atrial impedance: {len(values)} points")

        # Load ventricular impedance
        if 'lead_impedance_ventricular' in obs_by_var:
            obs_list = obs_by_var['lead_impedance_ventricular']
            time_points = [obs.observation_time for obs in obs_list]
            values = [obs.value_numeric for obs in obs_list]
            self.vent_impedance_widget.set_data("Ventricular", time_points, values)
            print(f"[DEBUG] Loaded ventricular impedance: {len(values)} points")

        # Load AFib burden
        if 'afib_burden_percent' in obs_by_var:
            obs_list = obs_by_var['afib_burden_percent']
            time_points = [obs.observation_time for obs in obs_list]
            values = [obs.value_numeric for obs in obs_list]
            self.burden_widget.set_data("AFib", time_points, values)
            print(f"[DEBUG] Loaded AFib burden: {len(values)} points")

        # Load heart rate data
        hr_var = 'heart_rate_mean' if 'heart_rate_mean' in obs_by_var else 'heart_rate'
        if hr_var in obs_by_var:
            obs_list = obs_by_var[hr_var]
            time_points = [obs.observation_time for obs in obs_list]
            values = [obs.value_numeric for obs in obs_list]
            hr_max = [obs.value_numeric for obs in obs_by_var.get('heart_rate_max', [])] or None
            hr_min = [obs.value_numeric for obs in obs_by_var.get('heart_rate_min', [])] or None
            self.heart_rate_widget.set_heart_rate_data(time_points, values, hr_max, hr_min)
            print(f"[DEBUG] Loaded heart rate: {len(values)} points")

        # Load rate limits from observations (check multiple variable names)
        lower_rate = self.heart_rate_widget.DEFAULT_LOWER_RATE
        upper_rate = self.heart_rate_widget.DEFAULT_UPPER_RATE

        for var in ['lower_rate_limit', 'set_brady_lowrate']:
            if var in obs_by_var:
                obs_list = obs_by_var[var]
                if obs_list and obs_list[-1].value_numeric:
                    lower_rate = obs_list[-1].value_numeric
                    break

        for var in ['upper_rate_limit', 'set_brady_max_tracking_rate', 'set_brady_max_sensor_rate']:
            if var in obs_by_var:
                obs_list = obs_by_var[var]
                if obs_list and obs_list[-1].value_numeric:
                    upper_rate = obs_list[-1].value_numeric
                    break

        self.heart_rate_widget.set_rate_limits(lower_rate, upper_rate)
        print(f"[DEBUG] Rate limits: {lower_rate} - {upper_rate} bpm")

        # Load device settings from most recent transmission
        # Use joinedload to eagerly load observations
        most_recent_transmission = self.session.query(Transmission).options(
            joinedload(Transmission.observations)
        ).filter_by(
            patient_id=patient_id
        ).order_by(Transmission.transmission_date.desc()).first()

        if most_recent_transmission:
            print(f"[DEBUG] Loading settings from transmission {most_recent_transmission.transmission_id} with {len(most_recent_transmission.observations)} observations")
            self.settings_panel.load_transmission(most_recent_transmission)
            self.device_settings_widget.load_transmission(most_recent_transmission)

        # Load episodes for heart rate widget
        self._load_episodes(patient_id)

    def _load_episodes(self, patient_id: str):
        """
        Load episodes from observations and display in heart rate widget.

        Args:
            patient_id: Patient identifier
        """
        from openpace.database.models import Observation

        # Query episode-related observations
        episode_obs = self.session.query(Observation).join(
            Observation.transmission
        ).filter(
            Observation.transmission.has(patient_id=patient_id),
            Observation.variable_name.like('episode_%')
        ).all()

        if not episode_obs:
            print(f"[DEBUG] No episode observations found")
            return

        # Group observations by sub_id (which identifies each episode)
        episodes_by_sub_id = {}
        for obs in episode_obs:
            sub_id = obs.sub_id or '1'
            if sub_id not in episodes_by_sub_id:
                episodes_by_sub_id[sub_id] = {}
            episodes_by_sub_id[sub_id][obs.variable_name] = obs

        # Build episode list for the widget
        episodes = []
        for sub_id, obs_dict in episodes_by_sub_id.items():
            episode = {}

            # Get episode datetime
            if 'episode_datetime' in obs_dict:
                episode['start_time'] = obs_dict['episode_datetime'].observation_time
            elif 'episode_id' in obs_dict:
                episode['start_time'] = obs_dict['episode_id'].observation_time
            else:
                continue  # Skip if no time available

            # Get episode type
            if 'episode_type' in obs_dict:
                episode['type'] = obs_dict['episode_type'].value_text or 'Unknown'
                # Extract short type from MDC codes like "MDC_IDC_ENUM_EPISODE_TYPE_Epis_PeriodicEGM"
                if 'Epis_' in episode['type']:
                    episode['type'] = episode['type'].split('Epis_')[-1]
                elif '_' in episode['type']:
                    episode['type'] = episode['type'].split('_')[-1]
            else:
                episode['type'] = 'Unknown'

            # Get duration if available
            if 'episode_duration' in obs_dict and obs_dict['episode_duration'].value_numeric:
                duration = obs_dict['episode_duration'].value_numeric
                episode['duration_seconds'] = duration
                # Calculate end time
                from datetime import timedelta
                episode['end_time'] = episode['start_time'] + timedelta(seconds=duration)

            # Get episode ID for reference
            if 'episode_id' in obs_dict:
                episode['episode_id'] = obs_dict['episode_id'].value_text

            episodes.append(episode)

        if episodes:
            print(f"[DEBUG] Loaded {len(episodes)} episodes")
            self.heart_rate_widget.set_episodes(episodes)
        else:
            print(f"[DEBUG] No valid episodes found")

    def clear_all(self):
        """Clear all chart data."""
        self.battery_widget.clear()
        self.atrial_impedance_widget.clear()
        self.vent_impedance_widget.clear()
        self.burden_widget.clear()
        self.heart_rate_widget.clear()
        self.settings_panel.clear()
        self.device_settings_widget.clear()
