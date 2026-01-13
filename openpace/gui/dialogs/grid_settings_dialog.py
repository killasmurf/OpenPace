"""
Grid Settings Dialog

Provides a dialog for configuring grid layout settings.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QSpinBox, QCheckBox, QPushButton,
    QGroupBox, QDialogButtonBox
)
from PyQt6.QtCore import Qt

from openpace.config import get_config


class GridSettingsDialog(QDialog):
    """
    Dialog for configuring grid layout settings.

    Allows users to configure:
    - Grid dimensions (rows and columns)
    - Panel minimum sizes
    - Snap-to-grid behavior
    - Auto-save settings
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Grid Settings")
        self.setModal(True)
        self.resize(400, 300)

        # Load current config
        self.config = get_config()

        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Grid dimensions group
        grid_group = QGroupBox("Grid Dimensions")
        grid_layout = QFormLayout()
        grid_group.setLayout(grid_layout)

        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(6, 24)
        self.rows_spin.setValue(12)
        self.rows_spin.setToolTip("Number of rows in the grid (6-24)")
        grid_layout.addRow("Rows:", self.rows_spin)

        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(6, 24)
        self.cols_spin.setValue(12)
        self.cols_spin.setToolTip("Number of columns in the grid (6-24)")
        grid_layout.addRow("Columns:", self.cols_spin)

        layout.addWidget(grid_group)

        # Panel size group
        size_group = QGroupBox("Panel Minimum Sizes")
        size_layout = QFormLayout()
        size_group.setLayout(size_layout)

        self.min_width_spin = QSpinBox()
        self.min_width_spin.setRange(100, 500)
        self.min_width_spin.setValue(200)
        self.min_width_spin.setSuffix(" px")
        self.min_width_spin.setToolTip("Minimum panel width in pixels")
        size_layout.addRow("Minimum Width:", self.min_width_spin)

        self.min_height_spin = QSpinBox()
        self.min_height_spin.setRange(100, 500)
        self.min_height_spin.setValue(150)
        self.min_height_spin.setSuffix(" px")
        self.min_height_spin.setToolTip("Minimum panel height in pixels")
        size_layout.addRow("Minimum Height:", self.min_height_spin)

        layout.addWidget(size_group)

        # Behavior group
        behavior_group = QGroupBox("Behavior")
        behavior_layout = QVBoxLayout()
        behavior_group.setLayout(behavior_layout)

        self.snap_to_grid_check = QCheckBox("Snap panels to grid when dragging")
        self.snap_to_grid_check.setToolTip(
            "When enabled, panels will snap to grid cells during drag operations"
        )
        behavior_layout.addWidget(self.snap_to_grid_check)

        self.auto_save_check = QCheckBox("Automatically save layout changes")
        self.auto_save_check.setToolTip(
            "When enabled, layout changes will be saved automatically"
        )
        behavior_layout.addWidget(self.auto_save_check)

        self.use_grid_check = QCheckBox("Use grid layout system (requires restart)")
        self.use_grid_check.setToolTip(
            "Enable the new grid layout system. Changes require application restart."
        )
        behavior_layout.addWidget(self.use_grid_check)

        layout.addWidget(behavior_group)

        # Add stretch to push buttons to bottom
        layout.addStretch()

        # Default layout selection
        default_layout_group = QGroupBox("Default Layout Mode")
        default_layout_layout = QFormLayout()
        default_layout_group.setLayout(default_layout_layout)

        from PyQt6.QtWidgets import QComboBox
        self.default_layout_combo = QComboBox()
        self.default_layout_combo.addItems(["Vertical", "Horizontal", "Free Grid"])
        self.default_layout_combo.setToolTip("Default layout mode when application starts")
        default_layout_layout.addRow("Default Mode:", self.default_layout_combo)

        layout.addWidget(default_layout_group)

        # Add stretch
        layout.addStretch()

        # Button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.RestoreDefaults
        )
        button_box.accepted.connect(self._save_and_accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(
            self._restore_defaults
        )

        layout.addWidget(button_box)

    def _load_settings(self):
        """Load current settings from config."""
        ui_config = self.config.ui

        # Load grid settings
        self.rows_spin.setValue(ui_config.grid_rows)
        self.cols_spin.setValue(ui_config.grid_cols)

        # Load panel sizes
        self.min_width_spin.setValue(ui_config.panel_min_width)
        self.min_height_spin.setValue(ui_config.panel_min_height)

        # Load behavior settings
        self.snap_to_grid_check.setChecked(ui_config.snap_to_grid)
        self.auto_save_check.setChecked(ui_config.save_panel_layouts)
        self.use_grid_check.setChecked(ui_config.use_grid_layout)

        # Load default layout mode
        mode_map = {
            "vertical": 0,
            "horizontal": 1,
            "free_grid": 2
        }
        index = mode_map.get(ui_config.default_layout_mode, 0)
        self.default_layout_combo.setCurrentIndex(index)

    def _save_and_accept(self):
        """Save settings and close dialog."""
        ui_config = self.config.ui

        # Save grid settings
        ui_config.grid_rows = self.rows_spin.value()
        ui_config.grid_cols = self.cols_spin.value()

        # Save panel sizes
        ui_config.panel_min_width = self.min_width_spin.value()
        ui_config.panel_min_height = self.min_height_spin.value()

        # Save behavior settings
        ui_config.snap_to_grid = self.snap_to_grid_check.isChecked()
        ui_config.save_panel_layouts = self.auto_save_check.isChecked()
        ui_config.use_grid_layout = self.use_grid_check.isChecked()

        # Save default layout mode
        mode_map = ["vertical", "horizontal", "free_grid"]
        ui_config.default_layout_mode = mode_map[self.default_layout_combo.currentIndex()]

        # Save config to file
        try:
            self.config.save_to_file()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Save Failed",
                f"Failed to save settings: {e}"
            )
            return

        self.accept()

    def _restore_defaults(self):
        """Restore default settings."""
        from openpace.config import UIConfig

        # Create default config
        defaults = UIConfig()

        # Restore defaults
        self.rows_spin.setValue(defaults.grid_rows)
        self.cols_spin.setValue(defaults.grid_cols)
        self.min_width_spin.setValue(defaults.panel_min_width)
        self.min_height_spin.setValue(defaults.panel_min_height)
        self.snap_to_grid_check.setChecked(defaults.snap_to_grid)
        self.auto_save_check.setChecked(defaults.save_panel_layouts)
        self.use_grid_check.setChecked(defaults.use_grid_layout)

        mode_map = {
            "vertical": 0,
            "horizontal": 1,
            "free_grid": 2
        }
        index = mode_map.get(defaults.default_layout_mode, 0)
        self.default_layout_combo.setCurrentIndex(index)
