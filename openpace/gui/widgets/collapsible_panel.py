"""
Collapsible Panel Widget

A panel that can be expanded/collapsed with a header containing
title, collapse button, and close button.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton
)
from PyQt6.QtCore import pyqtSignal


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
