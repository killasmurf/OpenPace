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
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint, QTimer
from PyQt6.QtGui import QIcon, QPainter, QColor, QPen
from sqlalchemy.orm import Session

from openpace.database.models import Patient, Transmission, LongitudinalTrend
from openpace.processing.trend_calculator import TrendCalculator
from openpace.gui.layouts import GridLayoutManager, LayoutMode, LayoutSerializer
from openpace.config import get_config
from .battery_widget import BatteryTrendWidget
from .impedance_widget import ImpedanceTrendWidget
from .burden_widget import BurdenWidget
from .settings_panel import SettingsPanel
from .draggable_panel import DraggablePanel
from .resize_handle import ResizeHandleManager


class CollapsiblePanel(QWidget):
    """
    A collapsible panel that can be expanded/collapsed.

    Signals:
        visibility_changed: Emitted when panel is shown/hidden
    """

    visibility_changed = pyqtSignal(bool)  # True if visible

    def __init__(self, title: str, content_widget: QWidget, parent=None):
        super().__init__(parent)
        self.title = title
        self.content_widget = content_widget
        self.is_collapsed = False

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        # Header with collapse button
        header = QWidget()
        header.setStyleSheet("""
            QWidget {
                background-color: #e0e0e0;
                border: 1px solid #cccccc;
                border-radius: 3px;
            }
        """)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(5, 5, 5, 5)
        header.setLayout(header_layout)

        # Collapse/expand button
        self.collapse_btn = QToolButton()
        self.collapse_btn.setText("▼")
        self.collapse_btn.setCheckable(True)
        self.collapse_btn.setChecked(False)
        self.collapse_btn.clicked.connect(self.toggle_collapse)
        self.collapse_btn.setFixedSize(20, 20)
        header_layout.addWidget(self.collapse_btn)

        # Title label
        title_label = QLabel(self.title)
        title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Close button
        self.close_btn = QToolButton()
        self.close_btn.setText("✕")
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.clicked.connect(self.hide_panel)
        header_layout.addWidget(self.close_btn)

        layout.addWidget(header)

        # Content container
        self.content_container = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(5, 5, 5, 5)
        self.content_container.setLayout(content_layout)
        content_layout.addWidget(self.content_widget)

        layout.addWidget(self.content_container)

    def toggle_collapse(self):
        """Toggle the collapsed state."""
        self.is_collapsed = self.collapse_btn.isChecked()

        if self.is_collapsed:
            self.content_container.hide()
            self.collapse_btn.setText("▶")
        else:
            self.content_container.show()
            self.collapse_btn.setText("▼")

    def hide_panel(self):
        """Hide the entire panel."""
        self.hide()
        self.visibility_changed.emit(False)

    def show_panel(self):
        """Show the panel."""
        self.show()
        self.visibility_changed.emit(True)

    def set_collapsed(self, collapsed: bool):
        """Set the collapsed state programmatically."""
        if collapsed != self.is_collapsed:
            self.collapse_btn.setChecked(collapsed)
            self.toggle_collapse()


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
    settings_visibility_changed = pyqtSignal(bool)

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
        self.settings_panel = SettingsPanel()

        if self.use_grid_layout:
            # Use new grid layout system
            self._init_grid_layout(layout)
        else:
            # Use legacy QSplitter layout
            self._init_splitter_layout(layout)

    def _init_grid_layout(self, parent_layout: QVBoxLayout):
        """Initialize grid-based layout system."""
        # Create container for grid
        grid_container = QWidget()
        grid_container.setMinimumSize(800, 600)

        # Create grid layout manager
        self.grid_manager = GridLayoutManager(grid_container, rows=12, cols=12)
        self.grid_manager.layout_changed.connect(self._on_layout_changed)

        # Create draggable panels
        self.battery_panel = DraggablePanel("battery", "Battery Voltage", self.battery_widget)
        self.battery_panel.visibility_changed.connect(self.battery_visibility_changed.emit)
        self.battery_panel.drag_started.connect(self._on_drag_started)
        self.battery_panel.drag_moved.connect(self._on_drag_moved)
        self.battery_panel.drag_ended.connect(self._on_drag_ended)
        self.panels['battery'] = self.battery_panel

        self.atrial_panel = DraggablePanel("atrial_impedance", "Atrial Lead Impedance",
                                          self.atrial_impedance_widget)
        self.atrial_panel.visibility_changed.connect(self.atrial_impedance_visibility_changed.emit)
        self.atrial_panel.drag_started.connect(self._on_drag_started)
        self.atrial_panel.drag_moved.connect(self._on_drag_moved)
        self.atrial_panel.drag_ended.connect(self._on_drag_ended)
        self.panels['atrial_impedance'] = self.atrial_panel

        self.vent_panel = DraggablePanel("vent_impedance", "Ventricular Lead Impedance",
                                        self.vent_impedance_widget)
        self.vent_panel.visibility_changed.connect(self.vent_impedance_visibility_changed.emit)
        self.vent_panel.drag_started.connect(self._on_drag_started)
        self.vent_panel.drag_moved.connect(self._on_drag_moved)
        self.vent_panel.drag_ended.connect(self._on_drag_ended)
        self.panels['vent_impedance'] = self.vent_panel

        self.burden_panel = DraggablePanel("burden", "Arrhythmia Burden", self.burden_widget)
        self.burden_panel.visibility_changed.connect(self.burden_visibility_changed.emit)
        self.burden_panel.drag_started.connect(self._on_drag_started)
        self.burden_panel.drag_moved.connect(self._on_drag_moved)
        self.burden_panel.drag_ended.connect(self._on_drag_ended)
        self.panels['burden'] = self.burden_panel

        self.settings_panel_widget = DraggablePanel("settings", "Device Settings", self.settings_panel)
        self.settings_panel_widget.visibility_changed.connect(self.settings_visibility_changed.emit)
        self.settings_panel_widget.drag_started.connect(self._on_drag_started)
        self.settings_panel_widget.drag_moved.connect(self._on_drag_moved)
        self.settings_panel_widget.drag_ended.connect(self._on_drag_ended)
        self.panels['settings'] = self.settings_panel_widget

        # Set default vertical layout
        self._set_default_vertical_layout()

        # Load saved layout if available (do this after panels are added)
        self._load_layout_from_file()

        parent_layout.addWidget(grid_container)

    def _init_splitter_layout(self, parent_layout: QVBoxLayout):
        """Initialize legacy QSplitter layout."""
        # Splitter for resizable panels
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setHandleWidth(4)
        self.splitter.setChildrenCollapsible(False)

        # Create collapsible panels
        self.battery_panel = CollapsiblePanel("Battery Voltage", self.battery_widget)
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
        """Set default vertical (stacked) layout."""
        if not self.grid_manager:
            return

        # All panels full width, stacked vertically
        # Each panel gets 2-3 rows, total 12 rows
        self.grid_manager.add_panel("battery", self.battery_panel, row=0, col=0, row_span=2, col_span=12)
        self.grid_manager.add_panel("atrial_impedance", self.atrial_panel, row=2, col=0,
                                   row_span=2, col_span=12)
        self.grid_manager.add_panel("vent_impedance", self.vent_panel, row=4, col=0,
                                   row_span=2, col_span=12)
        self.grid_manager.add_panel("burden", self.burden_panel, row=6, col=0, row_span=3, col_span=12)
        self.grid_manager.add_panel("settings", self.settings_panel_widget, row=9, col=0,
                                   row_span=3, col_span=12)

    def _set_default_horizontal_layout(self):
        """Set default horizontal (side-by-side) layout."""
        if not self.grid_manager:
            return

        # Battery panel full width at top
        self.grid_manager.add_panel("battery", self.battery_panel, row=0, col=0, row_span=3, col_span=12)

        # Four panels below in 2x2 grid
        self.grid_manager.add_panel("atrial_impedance", self.atrial_panel, row=3, col=0,
                                   row_span=4, col_span=6)
        self.grid_manager.add_panel("vent_impedance", self.vent_panel, row=3, col=6,
                                   row_span=4, col_span=6)
        self.grid_manager.add_panel("burden", self.burden_panel, row=7, col=0, row_span=5, col_span=6)
        self.grid_manager.add_panel("settings", self.settings_panel_widget, row=7, col=6,
                                   row_span=5, col_span=6)

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

            # Load battery trend
            if 'battery_voltage' in trends_by_var:
                trend = trends_by_var['battery_voltage']
                time_points = [datetime.fromisoformat(tp) for tp in trend.time_points]
                self.battery_widget.set_data(time_points, trend.values)

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

            # Load device settings from most recent transmission
            most_recent_transmission = self.session.query(Transmission).filter_by(
                patient_id=patient_id
            ).order_by(Transmission.transmission_date.desc()).first()

            if most_recent_transmission:
                self.settings_panel.load_transmission(most_recent_transmission)
            else:
                self.settings_panel.clear()

        except Exception as e:
            print(f"Error loading patient data: {e}")
            import traceback
            traceback.print_exc()

    def clear_all(self):
        """Clear all chart data."""
        self.battery_widget.clear()
        self.atrial_impedance_widget.clear()
        self.vent_impedance_widget.clear()
        self.burden_widget.clear()
        self.settings_panel.clear()
