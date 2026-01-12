"""
Pacemaker Settings Panel Widget

Displays device programming parameters in an organized, medical-record style format.
Shows bradycardia pacing, tachycardia therapy, sensing, and lead configuration settings.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QGroupBox, QScrollArea, QGridLayout, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class SettingsPanel(QWidget):
    """
    Widget displaying pacemaker device settings in a medical-record format.

    Organizes settings into logical groups:
    - Device Information
    - Bradycardia Pacing Settings
    - Tachycardia Therapy Settings (ICD only)
    - Sensing Configuration
    - Lead Channel Configuration
    - Advanced Features

    Signals:
        settings_changed: Emitted when new settings are loaded
    """

    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Device Settings")

        # Data
        self.transmission = None
        self.settings_data = {}

        # Setup UI
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Title
        self.title_label = QLabel("Device Programming Settings")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        main_layout.addWidget(self.title_label)

        # Timestamp label
        self.timestamp_label = QLabel("No data loaded")
        self.timestamp_label.setStyleSheet("color: gray; font-size: 11px;")
        main_layout.addWidget(self.timestamp_label)

        # Scroll area for settings groups
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout()
        self.scroll_layout.setSpacing(15)
        scroll_content.setLayout(self.scroll_layout)

        # Create settings group boxes
        self.device_group = self._create_settings_group("Device Information")
        self.brady_group = self._create_settings_group("Bradycardia Pacing")
        self.tachy_group = self._create_settings_group("Tachycardia Therapy")
        self.sensing_group = self._create_settings_group("Sensing Configuration")
        self.lead_group = self._create_settings_group("Lead Channels")
        self.advanced_group = self._create_settings_group("Advanced Features")

        self.scroll_layout.addWidget(self.device_group)
        self.scroll_layout.addWidget(self.brady_group)
        self.scroll_layout.addWidget(self.tachy_group)
        self.scroll_layout.addWidget(self.sensing_group)
        self.scroll_layout.addWidget(self.lead_group)
        self.scroll_layout.addWidget(self.advanced_group)
        self.scroll_layout.addStretch()

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        # Initially hide empty groups
        self.tachy_group.setVisible(False)
        self.sensing_group.setVisible(False)
        self.lead_group.setVisible(False)
        self.advanced_group.setVisible(False)

    def _create_settings_group(self, title: str) -> QGroupBox:
        """
        Create a settings group box with grid layout.

        Args:
            title: Group box title

        Returns:
            Configured QGroupBox
        """
        group = QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)

        layout = QGridLayout()
        layout.setColumnStretch(1, 1)  # Value column stretches
        layout.setHorizontalSpacing(15)
        layout.setVerticalSpacing(8)
        group.setLayout(layout)

        # Store layout reference for dynamic population
        group.grid_layout = layout
        group.row_count = 0

        return group

    def load_transmission(self, transmission):
        """
        Load settings from a transmission.

        Args:
            transmission: Transmission model with observations
        """
        self.transmission = transmission
        self.settings_data = {}

        # Update timestamp
        trans_date = transmission.transmission_date
        self.timestamp_label.setText(
            f"Settings from transmission on {trans_date.strftime('%Y-%m-%d %H:%M')}"
        )

        # Extract settings from observations
        self._extract_settings_from_observations(transmission.observations)

        # Populate UI groups
        self._populate_device_info()
        self._populate_brady_settings()
        self._populate_tachy_settings()
        self._populate_sensing_settings()
        self._populate_lead_settings()
        self._populate_advanced_settings()

        self.settings_changed.emit()

    def _extract_settings_from_observations(self, observations):
        """
        Extract settings from observation list.

        Args:
            observations: List of Observation models
        """
        for obs in observations:
            var_name = obs.variable_name

            # Get value (numeric or text)
            if obs.value_numeric is not None:
                value = obs.value_numeric
                if obs.unit:
                    value_str = f"{value} {obs.unit}"
                else:
                    value_str = str(value)
            elif obs.value_text:
                value_str = obs.value_text
            else:
                continue

            # Categorize setting
            self.settings_data[var_name] = {
                'value': obs.value_numeric if obs.value_numeric is not None else obs.value_text,
                'value_str': value_str,
                'unit': obs.unit,
                'vendor_code': obs.vendor_code
            }

    def _populate_device_info(self):
        """Populate device information group."""
        self._clear_group(self.device_group)

        if self.transmission:
            self._add_setting_row(
                self.device_group,
                "Manufacturer",
                self.transmission.device_manufacturer or "Unknown"
            )
            self._add_setting_row(
                self.device_group,
                "Model",
                self.transmission.device_model or "Not specified"
            )
            self._add_setting_row(
                self.device_group,
                "Serial Number",
                self.transmission.device_serial or "Not specified"
            )
            if self.transmission.device_firmware:
                self._add_setting_row(
                    self.device_group,
                    "Firmware",
                    self.transmission.device_firmware
                )

    def _populate_brady_settings(self):
        """Populate bradycardia pacing settings."""
        self._clear_group(self.brady_group)

        # Find all settings with brady-related keywords
        brady_keywords = ['brady', 'pacing', 'mode', 'rate', 'delay', 'av', 'sav', 'pav',
                          'pvarp', 'sensor', 'switch', 'lowrate', 'tracking']

        found_any = False
        for var_name, setting_info in sorted(self.settings_data.items()):
            # Check if this is a brady-related setting
            var_lower = var_name.lower()
            is_brady = any(keyword in var_lower for keyword in brady_keywords)

            # Also check if it's a SET_BRADY code
            if 'set_brady' in var_lower or 'mdc_idc_set_brady' in var_lower:
                is_brady = True

            if is_brady:
                # Create readable display name from variable name
                display_name = self._format_variable_name(var_name)
                self._add_setting_row(
                    self.brady_group,
                    display_name,
                    setting_info['value_str']
                )
                found_any = True

        if not found_any:
            self._add_no_data_label(self.brady_group)

    def _populate_tachy_settings(self):
        """Populate tachycardia therapy settings (ICD only)."""
        self._clear_group(self.tachy_group)

        # Find all settings with tachy-related keywords
        tachy_keywords = ['tachy', 'zone', 'vt', 'vf', 'atp', 'shock', 'therapy',
                          'detection', 'energy', 'vstat']

        found_any = False
        for var_name, setting_info in sorted(self.settings_data.items()):
            # Check if this is a tachy-related setting
            var_lower = var_name.lower()
            is_tachy = any(keyword in var_lower for keyword in tachy_keywords)

            # Also check for SET_TACHYTHERAPY or SET_ZONE codes
            if 'set_tachytherapy' in var_lower or 'set_zone' in var_lower:
                is_tachy = True

            if is_tachy:
                # Create readable display name from variable name
                display_name = self._format_variable_name(var_name)
                self._add_setting_row(
                    self.tachy_group,
                    display_name,
                    setting_info['value_str']
                )
                found_any = True

        # Show/hide group based on whether we have tachy settings
        self.tachy_group.setVisible(found_any)

    def _populate_sensing_settings(self):
        """Populate sensing configuration."""
        self._clear_group(self.sensing_group)

        # Find all settings with sensing-related keywords
        sensing_keywords = ['sensing', 'sensitivity', 'blanking', 'adaptation',
                            'leadchnl', 'intr', 'ampl']

        found_any = False
        for var_name, setting_info in sorted(self.settings_data.items()):
            # Check if this is a sensing-related setting
            var_lower = var_name.lower()
            is_sensing = any(keyword in var_lower for keyword in sensing_keywords)

            # Also check for SET_LEADCHNL_SENSING codes
            if 'set_leadchnl' in var_lower and 'sensing' in var_lower:
                is_sensing = True

            # Exclude pacing settings (they go in lead channels)
            if 'pacing' in var_lower or 'amplitude' in var_lower or 'pulsewidth' in var_lower:
                is_sensing = False

            if is_sensing:
                # Create readable display name from variable name
                display_name = self._format_variable_name(var_name)
                self._add_setting_row(
                    self.sensing_group,
                    display_name,
                    setting_info['value_str']
                )
                found_any = True

        self.sensing_group.setVisible(found_any)

    def _populate_lead_settings(self):
        """Populate lead channel configuration."""
        self._clear_group(self.lead_group)

        # Find all settings with lead/pacing-related keywords
        lead_keywords = ['pacing', 'amplitude', 'pulsewidth', 'pulse_width', 'polarity',
                         'leadchnl', 'capture', 'threshold']

        found_any = False
        for var_name, setting_info in sorted(self.settings_data.items()):
            # Check if this is a lead-related setting
            var_lower = var_name.lower()
            is_lead = any(keyword in var_lower for keyword in lead_keywords)

            # Also check for SET_LEADCHNL_PACING codes
            if 'set_leadchnl' in var_lower and 'pacing' in var_lower:
                is_lead = True

            # Exclude brady mode/rate settings (they go in brady section)
            if any(kw in var_lower for kw in ['mode', 'lowrate', 'tracking', 'sensor_rate']):
                is_lead = False

            if is_lead:
                # Create readable display name from variable name
                display_name = self._format_variable_name(var_name)
                self._add_setting_row(
                    self.lead_group,
                    display_name,
                    setting_info['value_str']
                )
                found_any = True

        self.lead_group.setVisible(found_any)

    def _populate_advanced_settings(self):
        """Populate advanced features and uncategorized settings."""
        self._clear_group(self.advanced_group)

        # Keywords that indicate this setting has already been categorized
        categorized_keywords = [
            'brady', 'pacing', 'mode', 'rate', 'delay', 'av', 'sav', 'pav',
            'tachy', 'zone', 'vt', 'vf', 'atp', 'shock', 'therapy', 'detection',
            'sensing', 'sensitivity', 'blanking', 'adaptation',
            'amplitude', 'pulsewidth', 'pulse_width', 'polarity', 'capture', 'threshold',
            'battery', 'impedance', 'longevity', 'voltage', 'burden', 'afib'
        ]

        found_any = False
        for var_name, setting_info in sorted(self.settings_data.items()):
            # Check if this setting hasn't been categorized yet
            var_lower = var_name.lower()
            is_categorized = any(keyword in var_lower for keyword in categorized_keywords)

            # Show uncategorized settings here
            if not is_categorized:
                # Create readable display name from variable name
                display_name = self._format_variable_name(var_name)
                self._add_setting_row(
                    self.advanced_group,
                    display_name,
                    setting_info['value_str']
                )
                found_any = True

        self.advanced_group.setVisible(found_any)

    def _format_variable_name(self, var_name: str) -> str:
        """
        Convert a variable name into a readable display name.

        Args:
            var_name: Variable name (e.g., 'set_brady_lowrate', 'atrial_amplitude')

        Returns:
            Formatted display name (e.g., 'Brady Lowrate', 'Atrial Amplitude')
        """
        # Remove common prefixes
        name = var_name
        for prefix in ['mdc_idc_', 'set_', 'msmt_']:
            if name.lower().startswith(prefix):
                name = name[len(prefix):]

        # Replace underscores with spaces
        name = name.replace('_', ' ')

        # Title case each word
        name = ' '.join(word.capitalize() for word in name.split())

        return name

    def _add_setting_row(self, group: QGroupBox, label: str, value: str):
        """
        Add a setting row to a group.

        Args:
            group: Group box to add to
            label: Setting label
            value: Setting value
        """
        layout = group.grid_layout
        row = group.row_count

        # Label
        label_widget = QLabel(f"{label}:")
        label_widget.setStyleSheet("font-weight: normal; color: #333333;")
        layout.addWidget(label_widget, row, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        # Value
        value_widget = QLabel(str(value))
        value_widget.setStyleSheet("font-weight: bold; color: #000000;")
        value_widget.setWordWrap(True)
        layout.addWidget(value_widget, row, 1, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        group.row_count += 1

    def _add_no_data_label(self, group: QGroupBox):
        """
        Add 'No data' label to empty group.

        Args:
            group: Group box to add to
        """
        layout = group.grid_layout
        label = QLabel("No settings data available")
        label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(label, 0, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
        group.row_count = 1

    def _clear_group(self, group: QGroupBox):
        """
        Clear all widgets from a group.

        Args:
            group: Group box to clear
        """
        layout = group.grid_layout

        # Remove all widgets
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        group.row_count = 0

    def clear(self):
        """Clear all settings data."""
        self.transmission = None
        self.settings_data = {}
        self.timestamp_label.setText("No data loaded")

        # Clear all groups
        self._clear_group(self.device_group)
        self._clear_group(self.brady_group)
        self._clear_group(self.tachy_group)
        self._clear_group(self.sensing_group)
        self._clear_group(self.lead_group)
        self._clear_group(self.advanced_group)

        # Add no data labels
        self._add_no_data_label(self.device_group)
        self._add_no_data_label(self.brady_group)

        # Hide optional groups
        self.tachy_group.setVisible(False)
        self.sensing_group.setVisible(False)
        self.lead_group.setVisible(False)
        self.advanced_group.setVisible(False)

    def export_settings_text(self) -> str:
        """
        Export settings as formatted text.

        Returns:
            Text representation of settings
        """
        if not self.transmission:
            return "No settings loaded"

        lines = []
        lines.append("=" * 60)
        lines.append("PACEMAKER DEVICE SETTINGS")
        lines.append("=" * 60)
        lines.append("")

        trans_date = self.transmission.transmission_date
        lines.append(f"Transmission Date: {trans_date.strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"Manufacturer: {self.transmission.device_manufacturer or 'Unknown'}")
        lines.append(f"Model: {self.transmission.device_model or 'Not specified'}")
        lines.append(f"Serial: {self.transmission.device_serial or 'Not specified'}")
        lines.append("")

        # Add each category
        for group_title, var_mapping in [
            ("BRADYCARDIA PACING", {
                'pacing_mode': 'Pacing Mode',
                'base_rate': 'Base Rate',
                'lower_rate': 'Lower Rate',
                'max_tracking_rate': 'Max Tracking Rate'
            }),
            ("SENSING", {
                'atrial_sensitivity': 'Atrial Sensitivity',
                'ventricular_sensitivity': 'Ventricular Sensitivity'
            }),
            ("LEAD CHANNELS", {
                'atrial_amplitude': 'Atrial Amplitude',
                'ventricular_amplitude': 'Ventricular Amplitude'
            })
        ]:
            found_any = False
            group_lines = [f"{group_title}:", "-" * len(group_title)]

            for var_name, display_name in var_mapping.items():
                if var_name in self.settings_data:
                    value = self.settings_data[var_name]['value_str']
                    group_lines.append(f"  {display_name}: {value}")
                    found_any = True

            if found_any:
                lines.extend(group_lines)
                lines.append("")

        return "\n".join(lines)
