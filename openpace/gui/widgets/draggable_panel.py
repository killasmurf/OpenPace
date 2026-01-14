"""
Draggable Panel Widget

Extends CollapsiblePanel with drag-and-drop functionality for repositioning
panels within a grid layout.
"""

from typing import Optional
from PyQt6.QtWidgets import QWidget, QToolButton, QLabel, QMenu
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QSize, QRect
from PyQt6.QtGui import QMouseEvent, QPainter, QColor, QPen, QCursor, QResizeEvent, QAction

from .collapsible_panel import CollapsiblePanel
from .resize_handle import ResizeHandleManager


class DraggablePanel(CollapsiblePanel):
    """
    A collapsible panel that can be dragged and repositioned.

    Extends CollapsiblePanel with:
    - Drag-and-drop functionality for moving panels
    - Visual feedback during drag operations
    - Resize support through ResizeHandles
    - Panel locking capability
    - Context menu for panel options

    Signals:
        drag_started: Emitted when drag operation begins (panel_id, start_position)
        drag_moved: Emitted during drag (panel_id, current_position)
        drag_ended: Emitted when drag completes (panel_id, end_position)
        resize_grid_requested: Emitted when grid-based resize is requested (panel_id, delta_rows, delta_cols)
        panel_settings_requested: Emitted when user requests panel settings (panel_id)
    """

    drag_started = pyqtSignal(str, QPoint)  # panel_id, start_position
    drag_moved = pyqtSignal(str, QPoint)    # panel_id, current_position
    drag_ended = pyqtSignal(str, QPoint)    # panel_id, end_position
    resize_grid_requested = pyqtSignal(str, int, int)  # panel_id, delta_rows, delta_cols
    panel_settings_requested = pyqtSignal(str)  # panel_id

    def __init__(self, panel_id: str, title: str, content_widget: QWidget, parent=None):
        """
        Initialize draggable panel.

        Args:
            panel_id: Unique identifier for this panel
            title: Panel title text
            content_widget: The widget to display in the panel content area
            parent: Parent widget
        """
        super().__init__(title, content_widget, parent)

        self.panel_id = panel_id
        self.is_locked = False  # If True, prevent dragging
        self.is_dragging = False
        self.edit_mode = True  # Layout editing enabled by default
        self.drag_start_pos = QPoint()
        self.drag_start_global_pos = QPoint()

        # Grid position tracking
        self.grid_row = 0
        self.grid_col = 0
        self.grid_row_span = 1
        self.grid_col_span = 1

        # Add drag handle to header
        self._add_drag_handle()

        # Add resize handles
        self.resize_manager = ResizeHandleManager(self, corners=True, edges=True)
        self.resize_manager.resize_requested.connect(self._on_resize_requested)
        self.resize_manager.set_visible(True)

        # Set cursor for draggable area
        self.setMouseTracking(True)

        # Enable context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _add_drag_handle(self):
        """Add a visual drag handle to the panel header."""
        # Get the header layout (first widget in our layout)
        header = self.layout().itemAt(0).widget()
        header_layout = header.layout()

        # Create drag handle button (grippy icon)
        self.drag_handle = QToolButton()
        self.drag_handle.setText("⋮⋮")  # Vertical dots for drag
        self.drag_handle.setFixedSize(20, 20)
        self.drag_handle.setToolTip("Drag to move panel")
        self.drag_handle.setStyleSheet("""
            QToolButton {
                border: none;
                background: transparent;
                font-size: 12px;
                font-weight: bold;
                color: #888;
            }
            QToolButton:hover {
                color: #333;
                background-color: rgba(0, 0, 0, 0.1);
                border-radius: 3px;
            }
        """)
        self.drag_handle.setCursor(Qt.CursorShape.OpenHandCursor)

        # Insert at the beginning of the header (before collapse button)
        header_layout.insertWidget(0, self.drag_handle)

    def _show_context_menu(self, position: QPoint):
        """Show context menu for panel options."""
        menu = QMenu(self)

        # Panel size options
        size_menu = menu.addMenu("Resize Panel")

        increase_height = QAction("Increase Height", self)
        increase_height.triggered.connect(lambda: self._request_resize(1, 0))
        size_menu.addAction(increase_height)

        decrease_height = QAction("Decrease Height", self)
        decrease_height.triggered.connect(lambda: self._request_resize(-1, 0))
        size_menu.addAction(decrease_height)

        size_menu.addSeparator()

        increase_width = QAction("Increase Width", self)
        increase_width.triggered.connect(lambda: self._request_resize(0, 1))
        size_menu.addAction(increase_width)

        decrease_width = QAction("Decrease Width", self)
        decrease_width.triggered.connect(lambda: self._request_resize(0, -1))
        size_menu.addAction(decrease_width)

        menu.addSeparator()

        # Collapse/Expand
        if self.is_collapsed:
            expand_action = QAction("Expand Panel", self)
            expand_action.triggered.connect(self.toggle_collapse)
            menu.addAction(expand_action)
        else:
            collapse_action = QAction("Collapse Panel", self)
            collapse_action.triggered.connect(self.toggle_collapse)
            menu.addAction(collapse_action)

        # Hide panel
        hide_action = QAction("Hide Panel", self)
        hide_action.triggered.connect(self.hide_panel)
        menu.addAction(hide_action)

        menu.addSeparator()

        # Lock/Unlock
        if self.is_locked:
            unlock_action = QAction("Unlock Panel", self)
            unlock_action.triggered.connect(lambda: self.set_locked(False))
            menu.addAction(unlock_action)
        else:
            lock_action = QAction("Lock Panel Position", self)
            lock_action.triggered.connect(lambda: self.set_locked(True))
            menu.addAction(lock_action)

        menu.exec(self.mapToGlobal(position))

    def _request_resize(self, delta_rows: int, delta_cols: int):
        """Request a grid-based resize."""
        self.resize_grid_requested.emit(self.panel_id, delta_rows, delta_cols)

    def _on_resize_requested(self, delta_rows: int, delta_cols: int, handle_position: str):
        """Handle resize request from resize handles."""
        self.resize_grid_requested.emit(self.panel_id, delta_rows, delta_cols)

    def set_edit_mode(self, enabled: bool):
        """
        Enable or disable layout editing mode.

        Args:
            enabled: True to enable editing, False to disable
        """
        self.edit_mode = enabled
        self.drag_handle.setVisible(enabled)
        self.resize_manager.set_visible(enabled)

        if not enabled:
            self.is_locked = True
        else:
            self.is_locked = False

    def set_locked(self, locked: bool):
        """
        Lock or unlock the panel to prevent/allow dragging.

        Args:
            locked: True to lock panel, False to unlock
        """
        self.is_locked = locked

        if locked:
            self.drag_handle.setEnabled(False)
            self.drag_handle.setToolTip("Panel is locked")
            self.drag_handle.setCursor(Qt.CursorShape.ForbiddenCursor)
            self.resize_manager.set_enabled(False)
        else:
            self.drag_handle.setEnabled(True)
            self.drag_handle.setToolTip("Drag to move panel")
            self.drag_handle.setCursor(Qt.CursorShape.OpenHandCursor)
            self.resize_manager.set_enabled(True)

    def set_cell_size(self, cell_width: int, cell_height: int):
        """
        Update the grid cell size for resize calculations.

        Args:
            cell_width: Width of one grid cell in pixels
            cell_height: Height of one grid cell in pixels
        """
        self.resize_manager.set_cell_size(cell_width, cell_height)

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for drag start."""
        if event.button() == Qt.MouseButton.LeftButton and not self.is_locked and self.edit_mode:
            # Check if click is in the drag handle area or header
            header = self.layout().itemAt(0).widget()
            header_rect = header.geometry()

            if header_rect.contains(event.pos()):
                # Don't start drag if clicking on buttons
                clicked_widget = self.childAt(event.pos())
                if isinstance(clicked_widget, QToolButton) and clicked_widget != self.drag_handle:
                    super().mousePressEvent(event)
                    return

                # Start drag operation
                self.is_dragging = True
                self.drag_start_pos = event.pos()
                self.drag_start_global_pos = event.globalPosition().toPoint()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)

                # Emit drag started signal
                self.drag_started.emit(self.panel_id, self.mapToParent(event.pos()))

                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move during drag."""
        if self.is_dragging:
            # Calculate new position
            current_pos = self.mapToParent(event.pos())

            # Emit drag moved signal
            self.drag_moved.emit(self.panel_id, current_pos)

            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release for drag end."""
        if event.button() == Qt.MouseButton.LeftButton and self.is_dragging:
            self.is_dragging = False
            self.setCursor(Qt.CursorShape.ArrowCursor)

            # Emit drag ended signal
            end_pos = self.mapToParent(event.pos())
            self.drag_ended.emit(self.panel_id, end_pos)

            event.accept()
            return

        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        """Handle resize event to update resize handle positions."""
        super().resizeEvent(event)
        # Update resize handle positions when panel is resized
        if hasattr(self, 'resize_manager'):
            self.resize_manager.update_positions()

    def paintEvent(self, event):
        """Custom paint event to show drag state and edit mode."""
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw border when dragging
        if self.is_dragging:
            pen = QPen(QColor(0, 120, 215), 2)  # Blue border
            painter.setPen(pen)
            painter.drawRect(self.rect().adjusted(1, 1, -1, -1))

        # Draw subtle resize indicator in edit mode
        elif self.edit_mode and not self.is_locked:
            # Draw grip lines in bottom-right corner
            pen = QPen(QColor(180, 180, 180), 1)
            painter.setPen(pen)
            corner_size = 12
            margin = 4
            x = self.width() - margin
            y = self.height() - margin
            for i in range(3):
                offset = i * 4
                painter.drawLine(x - corner_size + offset, y, x, y - corner_size + offset)

    def get_panel_id(self) -> str:
        """Get the panel's unique identifier."""
        return self.panel_id

    def set_grid_position(self, row: int, col: int, row_span: int, col_span: int):
        """
        Set the panel's position in the grid layout.

        This is used by the GridLayoutManager to position the panel.

        Args:
            row: Starting row index
            col: Starting column index
            row_span: Number of rows to span
            col_span: Number of columns to span
        """
        self.grid_row = row
        self.grid_col = col
        self.grid_row_span = row_span
        self.grid_col_span = col_span

    def get_grid_position(self) -> tuple[int, int, int, int]:
        """
        Get the panel's current grid position.

        Returns:
            Tuple of (row, col, row_span, col_span)
        """
        return (
            self.grid_row,
            self.grid_col,
            self.grid_row_span,
            self.grid_col_span
        )
