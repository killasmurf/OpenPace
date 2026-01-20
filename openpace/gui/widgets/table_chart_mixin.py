"""
Table/Chart Toggle Mixin

Provides functionality to switch between chart (graph) and table (data) views
in trend visualization widgets.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QStackedWidget, QMenu,
    QFileDialog, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QColor
import csv
import json


class ToggleSwitch(QWidget):
    """
    Custom toggle switch widget for Chart/Table selection.

    Styled as a slider-style toggle with labels on each side.
    """

    toggled = pyqtSignal(bool)  # True = Table, False = Chart

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_table_mode = False
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        self.setLayout(layout)

        # Chart label
        self.chart_label = QLabel("Chart")
        self.chart_label.setStyleSheet("font-size: 11px; font-weight: bold;")
        layout.addWidget(self.chart_label)

        # Toggle indicator
        self.toggle_indicator = QLabel()
        self.toggle_indicator.setFixedSize(40, 20)
        self.toggle_indicator.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_indicator_style()
        layout.addWidget(self.toggle_indicator)

        # Table label
        self.table_label = QLabel("Table")
        self.table_label.setStyleSheet("font-size: 11px; color: gray;")
        layout.addWidget(self.table_label)

    def _update_indicator_style(self):
        """Update toggle indicator appearance based on current state."""
        if self._is_table_mode:
            # Table mode - indicator on right
            self.toggle_indicator.setStyleSheet("""
                QLabel {
                    background-color: #4CAF50;
                    border-radius: 10px;
                    border: 2px solid #388E3C;
                }
            """)
            self.chart_label.setStyleSheet("font-size: 11px; color: gray;")
            self.table_label.setStyleSheet("font-size: 11px; font-weight: bold;")
        else:
            # Chart mode - indicator on left
            self.toggle_indicator.setStyleSheet("""
                QLabel {
                    background-color: #2196F3;
                    border-radius: 10px;
                    border: 2px solid #1976D2;
                }
            """)
            self.chart_label.setStyleSheet("font-size: 11px; font-weight: bold;")
            self.table_label.setStyleSheet("font-size: 11px; color: gray;")

    def mousePressEvent(self, event):
        """Handle click on toggle switch."""
        self._is_table_mode = not self._is_table_mode
        self._update_indicator_style()
        self.toggled.emit(self._is_table_mode)

    def is_table_mode(self) -> bool:
        """Return current mode."""
        return self._is_table_mode

    def set_table_mode(self, is_table: bool):
        """Set the toggle state."""
        if self._is_table_mode != is_table:
            self._is_table_mode = is_table
            self._update_indicator_style()


class TableChartMixin:
    """
    Mixin class to add table/chart toggle functionality to widgets.

    Usage:
        class MyWidget(QWidget, TableChartMixin):
            def __init__(self):
                super().__init__()
                self._init_ui()

            def _init_ui(self):
                # Create your layout...
                self.init_table_chart_toggle(
                    title="My Widget",
                    columns=["Date/Time", "Value", "Status"]
                )

    The mixin expects the widget to have:
        - self.time_points: List[datetime]
        - A method to get values for table population
    """

    # View mode constants
    VIEW_CHART = 0
    VIEW_TABLE = 1

    def init_table_chart_toggle(self, title: str, columns: List[str],
                                 chart_widget: QWidget = None):
        """
        Initialize the table/chart toggle functionality.

        Args:
            title: Widget title to display
            columns: Column headers for the table view
            chart_widget: Existing chart widget (PlotWidget) to use
        """
        self._table_columns = columns
        self._view_mode = self.VIEW_CHART

        # Create main layout if not exists
        if not self.layout():
            main_layout = QVBoxLayout()
            main_layout.setContentsMargins(5, 5, 5, 5)
            self.setLayout(main_layout)

        main_layout = self.layout()

        # Clear existing layout
        while main_layout.count():
            item = main_layout.takeAt(0)
            # Don't delete the chart widget if passed
            if item.widget() and item.widget() != chart_widget:
                item.widget().setParent(None)

        # Header with title and toggle
        header_layout = QHBoxLayout()

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        # Toggle switch
        self.view_toggle = ToggleSwitch()
        self.view_toggle.toggled.connect(self._on_view_toggle)
        header_layout.addWidget(self.view_toggle)

        main_layout.addLayout(header_layout)

        # Info label (for statistics)
        self.info_label = QLabel("No data")
        self.info_label.setStyleSheet("font-size: 11px; color: gray;")
        main_layout.addWidget(self.info_label)

        # Stacked widget for chart/table views
        self.stacked_widget = QStackedWidget()

        # Chart view (page 0)
        if chart_widget:
            self.chart_widget = chart_widget
        else:
            # Create placeholder if no chart provided
            self.chart_widget = QWidget()
        self.stacked_widget.addWidget(self.chart_widget)

        # Table view (page 1)
        self.table_widget = self._create_table_widget()
        self.stacked_widget.addWidget(self.table_widget)

        main_layout.addWidget(self.stacked_widget, stretch=1)

        # Start in chart view
        self.stacked_widget.setCurrentIndex(self.VIEW_CHART)

    def _create_table_widget(self) -> QTableWidget:
        """Create and configure the table widget."""
        table = QTableWidget()
        table.setColumnCount(len(self._table_columns))
        table.setHorizontalHeaderLabels(self._table_columns)

        # Configure table appearance
        table.setAlternatingRowColors(True)
        table.setStyleSheet("""
            QTableWidget {
                alternate-background-color: #f5f5f5;
                gridline-color: #ddd;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #e0e0e0;
                padding: 5px;
                border: 1px solid #ccc;
                font-weight: bold;
            }
        """)

        # Enable sorting
        table.setSortingEnabled(True)

        # Stretch columns to fit
        header = table.horizontalHeader()
        header.setStretchLastSection(True)
        for i in range(len(self._table_columns)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        # Enable selection
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)

        # Context menu for export
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(self._show_table_context_menu)

        return table

    def _on_view_toggle(self, is_table_mode: bool):
        """Handle view toggle switch."""
        if is_table_mode:
            self._populate_table()
            self.stacked_widget.setCurrentIndex(self.VIEW_TABLE)
        else:
            self.stacked_widget.setCurrentIndex(self.VIEW_CHART)

        self._view_mode = self.VIEW_TABLE if is_table_mode else self.VIEW_CHART

    def _populate_table(self):
        """
        Populate the table with data.

        Override this method in subclasses to customize table data.
        Default implementation uses self.time_points and expects
        get_table_row_data() to be implemented.
        """
        self.table_widget.setRowCount(0)

        if not hasattr(self, 'time_points') or not self.time_points:
            return

        rows = self.get_table_row_data()
        self.table_widget.setRowCount(len(rows))

        for row_idx, row_data in enumerate(rows):
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                # Apply color if it's a status column
                if col_idx == len(row_data) - 1:  # Assume last column is status
                    color = self._get_status_color(str(value))
                    if color:
                        item.setForeground(color)

                self.table_widget.setItem(row_idx, col_idx, item)

    def get_table_row_data(self) -> List[List[Any]]:
        """
        Get data rows for the table.

        Override this method in subclasses to provide widget-specific data.

        Returns:
            List of rows, where each row is a list of column values
        """
        # Default implementation - override in subclasses
        return []

    def _get_status_color(self, status: str) -> Optional[QColor]:
        """Get color for status value."""
        status_lower = status.lower()
        if status_lower in ('good', 'normal', 'low'):
            return QColor(0, 150, 0)  # Green
        elif status_lower in ('monitor', 'moderate', 'warning'):
            return QColor(200, 150, 0)  # Yellow/Orange
        elif status_lower in ('replace soon', 'high', 'critical', 'anomaly', 'above limit', 'below limit'):
            return QColor(200, 0, 0)  # Red
        return None

    def _show_table_context_menu(self, position):
        """Show context menu for table export options."""
        menu = QMenu(self.table_widget)

        # Copy selected rows
        copy_action = QAction("Copy Selected", self.table_widget)
        copy_action.triggered.connect(self._copy_selected_rows)
        menu.addAction(copy_action)

        # Copy all
        copy_all_action = QAction("Copy All", self.table_widget)
        copy_all_action.triggered.connect(self._copy_all_rows)
        menu.addAction(copy_all_action)

        menu.addSeparator()

        # Export to CSV
        export_csv_action = QAction("Export to CSV...", self.table_widget)
        export_csv_action.triggered.connect(self._export_to_csv)
        menu.addAction(export_csv_action)

        # Export to JSON
        export_json_action = QAction("Export to JSON...", self.table_widget)
        export_json_action.triggered.connect(self._export_to_json)
        menu.addAction(export_json_action)

        menu.exec(self.table_widget.mapToGlobal(position))

    def _copy_selected_rows(self):
        """Copy selected rows to clipboard."""
        selected_rows = set(item.row() for item in self.table_widget.selectedItems())
        if not selected_rows:
            return

        lines = []
        # Add header
        headers = [self.table_widget.horizontalHeaderItem(i).text()
                   for i in range(self.table_widget.columnCount())]
        lines.append('\t'.join(headers))

        # Add selected rows
        for row in sorted(selected_rows):
            row_data = []
            for col in range(self.table_widget.columnCount()):
                item = self.table_widget.item(row, col)
                row_data.append(item.text() if item else '')
            lines.append('\t'.join(row_data))

        clipboard = QApplication.clipboard()
        clipboard.setText('\n'.join(lines))

    def _copy_all_rows(self):
        """Copy all rows to clipboard."""
        lines = []
        # Add header
        headers = [self.table_widget.horizontalHeaderItem(i).text()
                   for i in range(self.table_widget.columnCount())]
        lines.append('\t'.join(headers))

        # Add all rows
        for row in range(self.table_widget.rowCount()):
            row_data = []
            for col in range(self.table_widget.columnCount()):
                item = self.table_widget.item(row, col)
                row_data.append(item.text() if item else '')
            lines.append('\t'.join(row_data))

        clipboard = QApplication.clipboard()
        clipboard.setText('\n'.join(lines))

    def _export_to_csv(self):
        """Export table data to CSV file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self.table_widget,
            "Export to CSV",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )

        if not file_path:
            return

        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Write header
            headers = [self.table_widget.horizontalHeaderItem(i).text()
                       for i in range(self.table_widget.columnCount())]
            writer.writerow(headers)

            # Write rows
            for row in range(self.table_widget.rowCount()):
                row_data = []
                for col in range(self.table_widget.columnCount()):
                    item = self.table_widget.item(row, col)
                    row_data.append(item.text() if item else '')
                writer.writerow(row_data)

    def _export_to_json(self):
        """Export table data to JSON file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self.table_widget,
            "Export to JSON",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            return

        headers = [self.table_widget.horizontalHeaderItem(i).text()
                   for i in range(self.table_widget.columnCount())]

        data = []
        for row in range(self.table_widget.rowCount()):
            row_dict = {}
            for col, header in enumerate(headers):
                item = self.table_widget.item(row, col)
                row_dict[header] = item.text() if item else ''
            data.append(row_dict)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def set_view_mode(self, mode: int):
        """
        Set the current view mode.

        Args:
            mode: VIEW_CHART (0) or VIEW_TABLE (1)
        """
        if mode == self.VIEW_TABLE:
            self.view_toggle.set_table_mode(True)
            self._populate_table()
            self.stacked_widget.setCurrentIndex(self.VIEW_TABLE)
        else:
            self.view_toggle.set_table_mode(False)
            self.stacked_widget.setCurrentIndex(self.VIEW_CHART)

        self._view_mode = mode

    def get_view_mode(self) -> int:
        """Get the current view mode."""
        return self._view_mode
