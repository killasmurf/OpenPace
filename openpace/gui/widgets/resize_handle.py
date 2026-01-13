"""
Resize Handle Widget

Provides visual handles for resizing panels. Handles can be placed at corners
or edges of a panel to allow the user to resize by dragging.
"""

from enum import Enum
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QSize, QRect
from PyQt6.QtGui import QMouseEvent, QPainter, QColor, QCursor


class HandlePosition(Enum):
    """Position of resize handle."""
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"


class ResizeHandle(QWidget):
    """
    A resize handle widget for panel resizing.

    Provides visual feedback and emits signals during resize operations.
    Handles can be positioned at corners or edges of a parent widget.

    Signals:
        resize_started: Emitted when resize begins (start_position)
        resize_moved: Emitted during resize (delta_x, delta_y)
        resize_ended: Emitted when resize completes (final_size)
    """

    resize_started = pyqtSignal(QPoint)  # start_position
    resize_moved = pyqtSignal(int, int)  # delta_x, delta_y
    resize_ended = pyqtSignal(QSize)     # final_size

    def __init__(self, position: HandlePosition, parent: QWidget = None):
        """
        Initialize resize handle.

        Args:
            position: Position of the handle (corner or edge)
            parent: Parent widget to resize
        """
        super().__init__(parent)

        self.position = position
        self.is_resizing = False
        self.resize_start_pos = QPoint()
        self.parent_start_size = QSize()

        # Handle appearance
        self.handle_size = 8  # Size of the handle in pixels
        self.setFixedSize(self.handle_size, self.handle_size)

        # Set cursor based on position
        self._set_cursor()

        # Enable mouse tracking
        self.setMouseTracking(True)

        # Style
        self.setStyleSheet("""
            ResizeHandle {
                background-color: rgba(0, 120, 215, 128);
                border-radius: 2px;
            }
            ResizeHandle:hover {
                background-color: rgba(0, 120, 215, 192);
            }
        """)

    def _set_cursor(self):
        """Set appropriate cursor based on handle position."""
        cursor_map = {
            HandlePosition.TOP_LEFT: Qt.CursorShape.SizeFDiagCursor,
            HandlePosition.TOP_RIGHT: Qt.CursorShape.SizeBDiagCursor,
            HandlePosition.BOTTOM_LEFT: Qt.CursorShape.SizeBDiagCursor,
            HandlePosition.BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
            HandlePosition.TOP: Qt.CursorShape.SizeVerCursor,
            HandlePosition.BOTTOM: Qt.CursorShape.SizeVerCursor,
            HandlePosition.LEFT: Qt.CursorShape.SizeHorCursor,
            HandlePosition.RIGHT: Qt.CursorShape.SizeHorCursor,
        }
        self.setCursor(cursor_map.get(self.position, Qt.CursorShape.ArrowCursor))

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press to start resize."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_resizing = True
            self.resize_start_pos = event.globalPosition().toPoint()

            if self.parent():
                self.parent_start_size = self.parent().size()

            # Emit resize started
            self.resize_started.emit(self.resize_start_pos)
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move during resize."""
        if self.is_resizing and self.parent():
            # Calculate delta
            current_pos = event.globalPosition().toPoint()
            delta = current_pos - self.resize_start_pos

            # Calculate new size based on handle position
            delta_x = 0
            delta_y = 0

            if self.position in [HandlePosition.TOP_LEFT, HandlePosition.LEFT, HandlePosition.BOTTOM_LEFT]:
                delta_x = -delta.x()  # Left side moves inversely
            elif self.position in [HandlePosition.TOP_RIGHT, HandlePosition.RIGHT, HandlePosition.BOTTOM_RIGHT]:
                delta_x = delta.x()

            if self.position in [HandlePosition.TOP_LEFT, HandlePosition.TOP, HandlePosition.TOP_RIGHT]:
                delta_y = -delta.y()  # Top side moves inversely
            elif self.position in [HandlePosition.BOTTOM_LEFT, HandlePosition.BOTTOM, HandlePosition.BOTTOM_RIGHT]:
                delta_y = delta.y()

            # Emit resize moved
            self.resize_moved.emit(delta_x, delta_y)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release to end resize."""
        if event.button() == Qt.MouseButton.LeftButton and self.is_resizing:
            self.is_resizing = False

            if self.parent():
                # Emit final size
                final_size = self.parent().size()
                self.resize_ended.emit(final_size)

            event.accept()

    def update_position(self):
        """Update handle position based on parent size."""
        if not self.parent():
            return

        parent_rect = self.parent().rect()
        margin = 2  # Margin from edge

        # Position based on handle type
        if self.position == HandlePosition.TOP_LEFT:
            self.move(margin, margin)
        elif self.position == HandlePosition.TOP_RIGHT:
            self.move(parent_rect.width() - self.handle_size - margin, margin)
        elif self.position == HandlePosition.BOTTOM_LEFT:
            self.move(margin, parent_rect.height() - self.handle_size - margin)
        elif self.position == HandlePosition.BOTTOM_RIGHT:
            self.move(
                parent_rect.width() - self.handle_size - margin,
                parent_rect.height() - self.handle_size - margin
            )
        elif self.position == HandlePosition.TOP:
            self.move(parent_rect.width() // 2 - self.handle_size // 2, margin)
        elif self.position == HandlePosition.BOTTOM:
            self.move(
                parent_rect.width() // 2 - self.handle_size // 2,
                parent_rect.height() - self.handle_size - margin
            )
        elif self.position == HandlePosition.LEFT:
            self.move(margin, parent_rect.height() // 2 - self.handle_size // 2)
        elif self.position == HandlePosition.RIGHT:
            self.move(
                parent_rect.width() - self.handle_size - margin,
                parent_rect.height() // 2 - self.handle_size // 2
            )

        # Bring to front
        self.raise_()


class ResizeHandleManager:
    """
    Manages multiple resize handles for a widget.

    Creates and positions handles at corners and/or edges of a widget.
    """

    def __init__(self, widget: QWidget, corners: bool = True, edges: bool = False):
        """
        Initialize resize handle manager.

        Args:
            widget: Widget to add resize handles to
            corners: Add corner handles
            edges: Add edge handles
        """
        self.widget = widget
        self.handles = []

        # Create corner handles
        if corners:
            self.handles.append(ResizeHandle(HandlePosition.TOP_LEFT, widget))
            self.handles.append(ResizeHandle(HandlePosition.TOP_RIGHT, widget))
            self.handles.append(ResizeHandle(HandlePosition.BOTTOM_LEFT, widget))
            self.handles.append(ResizeHandle(HandlePosition.BOTTOM_RIGHT, widget))

        # Create edge handles
        if edges:
            self.handles.append(ResizeHandle(HandlePosition.TOP, widget))
            self.handles.append(ResizeHandle(HandlePosition.BOTTOM, widget))
            self.handles.append(ResizeHandle(HandlePosition.LEFT, widget))
            self.handles.append(ResizeHandle(HandlePosition.RIGHT, widget))

        # Connect signals from all handles
        for handle in self.handles:
            handle.resize_started.connect(self._on_resize_started)
            handle.resize_moved.connect(self._on_resize_moved)
            handle.resize_ended.connect(self._on_resize_ended)

        # Initially hide handles
        self.set_visible(False)

    def _on_resize_started(self, position: QPoint):
        """Handle resize start from any handle."""
        # Store initial size
        self.initial_size = self.widget.size()
        self.initial_pos = self.widget.pos()

    def _on_resize_moved(self, delta_x: int, delta_y: int):
        """Handle resize movement from any handle."""
        # Calculate new size
        new_width = max(100, self.initial_size.width() + delta_x)  # Min width 100
        new_height = max(100, self.initial_size.height() + delta_y)  # Min height 100

        # Resize widget
        self.widget.resize(new_width, new_height)

        # Update handle positions
        self.update_positions()

    def _on_resize_ended(self, final_size: QSize):
        """Handle resize end from any handle."""
        # Final update
        self.update_positions()

    def update_positions(self):
        """Update positions of all handles."""
        for handle in self.handles:
            handle.update_position()

    def set_visible(self, visible: bool):
        """Show or hide all handles."""
        for handle in self.handles:
            handle.setVisible(visible)

    def set_enabled(self, enabled: bool):
        """Enable or disable all handles."""
        for handle in self.handles:
            handle.setEnabled(enabled)
