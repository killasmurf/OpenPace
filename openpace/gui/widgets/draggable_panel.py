"""
Draggable Panel Widget

Extends CollapsiblePanel with drag-and-drop functionality for repositioning
panels within a grid layout.
"""

from typing import Optional
from PyQt6.QtWidgets import QWidget, QToolButton, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QSize, QRect
from PyQt6.QtGui import QMouseEvent, QPainter, QColor, QPen, QCursor

from .timeline_view import CollapsiblePanel


class DraggablePanel(CollapsiblePanel):
    """
    A collapsible panel that can be dragged and repositioned.

    Extends CollapsiblePanel with:
    - Drag-and-drop functionality for moving panels
    - Visual feedback during drag operations
    - Resize support through ResizeHandles
    - Panel locking capability

    Signals:
        drag_started: Emitted when drag operation begins (panel_id, start_position)
        drag_moved: Emitted during drag (panel_id, current_position)
        drag_ended: Emitted when drag completes (panel_id, end_position)
        resize_requested: Emitted when panel resize is requested (panel_id, new_size)
    """

    drag_started = pyqtSignal(str, QPoint)  # panel_id, start_position
    drag_moved = pyqtSignal(str, QPoint)    # panel_id, current_position
    drag_ended = pyqtSignal(str, QPoint)    # panel_id, end_position
    resize_requested = pyqtSignal(str, QSize)  # panel_id, new_size

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
        self.drag_start_pos = QPoint()
        self.drag_start_global_pos = QPoint()

        # Add drag handle to header
        self._add_drag_handle()

        # Set cursor for draggable area
        self.setMouseTracking(True)

    def _add_drag_handle(self):
        """Add a visual drag handle to the panel header."""
        # Get the header layout (first widget in our layout)
        header = self.layout().itemAt(0).widget()
        header_layout = header.layout()

        # Create drag handle button (grippy icon)
        self.drag_handle = QToolButton()
        self.drag_handle.setText("⣿")  # Grippy icon
        self.drag_handle.setFixedSize(20, 20)
        self.drag_handle.setToolTip("Drag to move panel")
        self.drag_handle.setStyleSheet("""
            QToolButton {
                border: none;
                background: transparent;
                font-size: 10px;
                color: #666;
            }
            QToolButton:hover {
                color: #000;
            }
        """)
        self.drag_handle.setCursor(Qt.CursorShape.OpenHandCursor)

        # Insert at the beginning of the header (before collapse button)
        header_layout.insertWidget(0, self.drag_handle)

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
        else:
            self.drag_handle.setEnabled(True)
            self.drag_handle.setToolTip("Drag to move panel")
            self.drag_handle.setCursor(Qt.CursorShape.OpenHandCursor)

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for drag start."""
        if event.button() == Qt.MouseButton.LeftButton and not self.is_locked:
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

    def paintEvent(self, event):
        """Custom paint event to show drag state."""
        super().paintEvent(event)

        # Draw border when dragging
        if self.is_dragging:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Draw highlighted border
            pen = QPen(QColor(0, 120, 215), 2)  # Blue border
            painter.setPen(pen)
            painter.drawRect(self.rect().adjusted(1, 1, -1, -1))

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
            getattr(self, 'grid_row', 0),
            getattr(self, 'grid_col', 0),
            getattr(self, 'grid_row_span', 1),
            getattr(self, 'grid_col_span', 1)
        )
