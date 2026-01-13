"""
Grid Layout Manager

Manages panel positioning in a flexible grid system. Provides functionality
for adding, moving, and resizing panels within a grid, calculating drop zones,
and handling layout serialization.
"""

from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from PyQt6.QtWidgets import QWidget, QGridLayout
from PyQt6.QtCore import Qt, QPoint, QRect, QSize, pyqtSignal, QObject
from PyQt6.QtGui import QPainter, QColor, QPen


class LayoutMode(Enum):
    """Layout mode enumeration."""
    FREE_GRID = "free_grid"        # Panels can be positioned anywhere
    VERTICAL = "vertical"          # Panels snap to full-width rows
    HORIZONTAL = "horizontal"      # Panels snap to columns


class PanelInfo:
    """Information about a panel's position and size in the grid."""

    def __init__(self, widget: QWidget, row: int, col: int, row_span: int, col_span: int):
        """
        Initialize panel info.

        Args:
            widget: The panel widget
            row: Starting row index
            col: Starting column index
            row_span: Number of rows to span
            col_span: Number of columns to span
        """
        self.widget = widget
        self.row = row
        self.col = col
        self.row_span = row_span
        self.col_span = col_span
        self.visible = True
        self.collapsed = False

    def get_rect(self) -> QRect:
        """Get the rectangle occupied by this panel in grid coordinates."""
        return QRect(self.col, self.row, self.col_span, self.row_span)

    def overlaps_with(self, other: 'PanelInfo') -> bool:
        """Check if this panel overlaps with another."""
        return self.get_rect().intersects(other.get_rect())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'row': self.row,
            'col': self.col,
            'row_span': self.row_span,
            'col_span': self.col_span,
            'visible': self.visible,
            'collapsed': self.collapsed
        }

    @classmethod
    def from_dict(cls, widget: QWidget, data: Dict[str, Any]) -> 'PanelInfo':
        """Create from dictionary."""
        info = cls(
            widget=widget,
            row=data['row'],
            col=data['col'],
            row_span=data['row_span'],
            col_span=data['col_span']
        )
        info.visible = data.get('visible', True)
        info.collapsed = data.get('collapsed', False)
        return info


class GridLayoutManager(QObject):
    """
    Manages panel positioning in a flexible grid layout.

    Provides:
    - Grid-based panel positioning
    - Drop zone calculation for drag-and-drop
    - Overlap detection and resolution
    - Layout serialization/deserialization
    - Support for different layout modes
    """

    layout_changed = pyqtSignal()  # Emitted when layout changes

    def __init__(self, container: QWidget, rows: int = 12, cols: int = 12):
        """
        Initialize grid layout manager.

        Args:
            container: The container widget to manage
            rows: Number of grid rows
            cols: Number of grid columns
        """
        super().__init__()
        self.container = container
        self.rows = rows
        self.cols = cols
        self.mode = LayoutMode.VERTICAL

        # Track panels by panel_id
        self.panels: Dict[str, PanelInfo] = {}

        # Create the grid layout
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(5)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.container.setLayout(self.grid_layout)

        # Cell size tracking (updated on resize)
        self.cell_width = 0
        self.cell_height = 0

    def set_mode(self, mode: LayoutMode):
        """
        Set the layout mode.

        Args:
            mode: The layout mode to use
        """
        if self.mode == mode:
            return

        self.mode = mode
        self._apply_mode_constraints()
        self.layout_changed.emit()

    def _apply_mode_constraints(self):
        """Apply constraints based on current layout mode."""
        if self.mode == LayoutMode.VERTICAL:
            # Make all panels full width, stacked vertically
            row = 0
            for panel_id, info in self.panels.items():
                if info.visible:
                    info.col = 0
                    info.col_span = self.cols
                    info.row = row
                    row += info.row_span
            self._rebuild_layout()

        elif self.mode == LayoutMode.HORIZONTAL:
            # Arrange panels in columns
            # For simplicity, use equal-width columns
            num_visible = sum(1 for info in self.panels.values() if info.visible)
            if num_visible == 0:
                return

            col_width = self.cols // num_visible
            col = 0
            for panel_id, info in self.panels.items():
                if info.visible:
                    info.row = 0
                    info.col = col
                    info.row_span = self.rows
                    info.col_span = col_width
                    col += col_width
            self._rebuild_layout()

    def add_panel(self, panel_id: str, widget: QWidget,
                  row: int, col: int, row_span: int, col_span: int):
        """
        Add a panel to the grid.

        Args:
            panel_id: Unique identifier for the panel
            widget: The panel widget
            row: Starting row index
            col: Starting column index
            row_span: Number of rows to span
            col_span: Number of columns to span
        """
        # Validate coordinates
        if not self._is_valid_position(row, col, row_span, col_span):
            raise ValueError(f"Invalid grid position: ({row}, {col}) with span ({row_span}, {col_span})")

        # Check for overlaps
        new_info = PanelInfo(widget, row, col, row_span, col_span)
        for existing_id, existing_info in self.panels.items():
            if existing_info.visible and new_info.overlaps_with(existing_info):
                # Auto-resolve overlap by shifting new panel
                row = existing_info.row + existing_info.row_span
                new_info.row = row

        # Store panel info
        self.panels[panel_id] = new_info

        # Add to grid layout
        self.grid_layout.addWidget(widget, row, col, row_span, col_span)

        # Update cell sizes
        self._update_cell_sizes()

        self.layout_changed.emit()

    def move_panel(self, panel_id: str, new_row: int, new_col: int):
        """
        Move a panel to a new position.

        Args:
            panel_id: Panel identifier
            new_row: New row index
            new_col: New column index
        """
        if panel_id not in self.panels:
            return

        info = self.panels[panel_id]

        # Validate new position
        if not self._is_valid_position(new_row, new_col, info.row_span, info.col_span):
            return

        # Apply mode constraints
        if self.mode == LayoutMode.VERTICAL:
            # Force full width
            new_col = 0
            info.col_span = self.cols
        elif self.mode == LayoutMode.HORIZONTAL:
            # Keep in current column span area
            pass

        # Update position
        info.row = new_row
        info.col = new_col

        # Rebuild layout
        self._rebuild_layout()

        self.layout_changed.emit()

    def resize_panel(self, panel_id: str, new_row_span: int, new_col_span: int):
        """
        Resize a panel.

        Args:
            panel_id: Panel identifier
            new_row_span: New row span
            new_col_span: New column span
        """
        if panel_id not in self.panels:
            return

        info = self.panels[panel_id]

        # Validate new size
        if not self._is_valid_position(info.row, info.col, new_row_span, new_col_span):
            return

        # Apply mode constraints
        if self.mode == LayoutMode.VERTICAL:
            new_col_span = self.cols  # Force full width
        elif self.mode == LayoutMode.HORIZONTAL:
            new_row_span = self.rows  # Force full height

        # Update size
        info.row_span = new_row_span
        info.col_span = new_col_span

        # Rebuild layout
        self._rebuild_layout()

        self.layout_changed.emit()

    def remove_panel(self, panel_id: str):
        """
        Remove a panel from the grid.

        Args:
            panel_id: Panel identifier
        """
        if panel_id not in self.panels:
            return

        info = self.panels[panel_id]
        self.grid_layout.removeWidget(info.widget)
        del self.panels[panel_id]

        self.layout_changed.emit()

    def hide_panel(self, panel_id: str):
        """Hide a panel without removing it."""
        if panel_id not in self.panels:
            return

        info = self.panels[panel_id]
        info.visible = False
        info.widget.hide()

        self._rebuild_layout()
        self.layout_changed.emit()

    def show_panel(self, panel_id: str):
        """Show a previously hidden panel."""
        if panel_id not in self.panels:
            return

        info = self.panels[panel_id]
        info.visible = True
        info.widget.show()

        self._rebuild_layout()
        self.layout_changed.emit()

    def get_drop_zone(self, position: QPoint) -> Optional[Tuple[int, int]]:
        """
        Calculate the grid cell for a given position.

        Args:
            position: Position in container coordinates

        Returns:
            Tuple of (row, col) or None if invalid
        """
        if self.cell_width == 0 or self.cell_height == 0:
            return None

        col = int(position.x() / self.cell_width)
        row = int(position.y() / self.cell_height)

        if 0 <= row < self.rows and 0 <= col < self.cols:
            return (row, col)

        return None

    def _is_valid_position(self, row: int, col: int, row_span: int, col_span: int) -> bool:
        """Check if a position and span are valid within the grid."""
        return (
            0 <= row < self.rows and
            0 <= col < self.cols and
            row + row_span <= self.rows and
            col + col_span <= self.cols and
            row_span > 0 and
            col_span > 0
        )

    def _rebuild_layout(self):
        """Rebuild the grid layout with current panel positions."""
        # Remove all widgets from layout
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        # Re-add visible panels
        for panel_id, info in self.panels.items():
            if info.visible:
                self.grid_layout.addWidget(
                    info.widget,
                    info.row,
                    info.col,
                    info.row_span,
                    info.col_span
                )

    def _update_cell_sizes(self):
        """Update calculated cell sizes based on container size."""
        container_size = self.container.size()
        self.cell_width = container_size.width() / self.cols
        self.cell_height = container_size.height() / self.rows

    def serialize_layout(self) -> Dict[str, Any]:
        """
        Serialize the current layout to a dictionary.

        Returns:
            Dictionary containing layout data
        """
        return {
            'layout_mode': self.mode.value,
            'grid_rows': self.rows,
            'grid_cols': self.cols,
            'panels': {
                panel_id: info.to_dict()
                for panel_id, info in self.panels.items()
            }
        }

    def restore_layout(self, layout_data: Dict[str, Any]):
        """
        Restore layout from serialized data.

        Args:
            layout_data: Dictionary containing layout data
        """
        # Restore mode
        mode_str = layout_data.get('layout_mode', 'vertical')
        try:
            self.mode = LayoutMode(mode_str)
        except ValueError:
            self.mode = LayoutMode.VERTICAL

        # Restore grid size
        self.rows = layout_data.get('grid_rows', 12)
        self.cols = layout_data.get('grid_cols', 12)

        # Restore panel positions
        panels_data = layout_data.get('panels', {})
        for panel_id, panel_data in panels_data.items():
            if panel_id in self.panels:
                info = self.panels[panel_id]
                info.row = panel_data.get('row', 0)
                info.col = panel_data.get('col', 0)
                info.row_span = panel_data.get('row_span', 1)
                info.col_span = panel_data.get('col_span', 1)
                info.visible = panel_data.get('visible', True)
                info.collapsed = panel_data.get('collapsed', False)

                if info.visible:
                    info.widget.show()
                else:
                    info.widget.hide()

        # Rebuild layout
        self._rebuild_layout()
        self.layout_changed.emit()

    def get_panel_info(self, panel_id: str) -> Optional[PanelInfo]:
        """Get info for a specific panel."""
        return self.panels.get(panel_id)

    def get_all_panels(self) -> Dict[str, PanelInfo]:
        """Get all panel info."""
        return self.panels.copy()
