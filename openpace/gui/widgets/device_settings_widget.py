"""
Device Settings Widget

Displays pacemaker/ICD device settings organized into two clear categories:
- Fixed Settings: Device constants (model, serial, manufacturer, implant date)
- Operator-Defined Settings: Programmed parameters (mode, rates, sensitivities, therapies)
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QScrollArea, QGridLayout, QFrame,
    QSplitter, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class DeviceSettingsWidget(QWidget):
    """
    Widget displaying device settings separated into Fixed and Operator-Defined categories.

    Fixed Settings:
    - Device information (type, model, serial, manufacturer, implant date)
    - Lead information (model, serial, location)

    Operator-Defined Settings:
    - Bradycardia pacing (mode, rates, delays)
    - Tachycardia therapy (status, zones, ATP, shocks)
    - Lead channel sensing (sensitivity, polarity, adaptation)
    - Lead channel pacing (amplitude, pulse width, capture mode)

    Signals:
        settings_loaded: Emitted when settings are successfully loaded
    """

    settings_loaded = pyqtSignal()

    # Category display names
    CATEGORY_NAMES = {
        'device': 'Device Information',
        'lead_info': 'Lead Information',
        'brady': 'Bradycardia Pacing',
        'tachy': 'Tachycardia Therapy',
        'zone': 'Therapy Zones',
        'sensing': 'Sensing Configuration',
        'pacing': 'Pacing Configuration',
        'battery': 'Battery Status',
        'lead_msmt': 'Lead Measurements',
        'stats': 'Statistics',
        'episode': 'Episodes',
        'other': 'Other Settings',
    }

    # Human-readable labels for variable names
    VARIABLE_LABELS = {
        # Device info
        'device_type': 'Device Type',
        'device_model': 'Model',
        'device_serial': 'Serial Number',
        'device_manufacturer': 'Manufacturer',
        'device_implant_date': 'Implant Date',

        # Lead info
        'lead_model': 'Lead Model',
        'lead_serial': 'Lead Serial',
        'lead_manufacturer': 'Lead Manufacturer',
        'lead_implant_date': 'Lead Implant Date',
        'lead_polarity_type': 'Lead Polarity',
        'lead_location': 'Lead Location',

        # Brady settings
        'set_brady_mode': 'Pacing Mode',
        'set_brady_lowrate': 'Lower Rate Limit',
        'set_brady_max_tracking_rate': 'Max Tracking Rate',
        'set_brady_max_sensor_rate': 'Max Sensor Rate',
        'set_brady_sav_delay_high': 'SAV Delay (High)',
        'set_brady_sav_delay_low': 'SAV Delay (Low)',
        'set_brady_pav_delay_high': 'PAV Delay (High)',
        'set_brady_pav_delay_low': 'PAV Delay (Low)',
        'set_brady_sensor_type': 'Sensor Type',
        'set_brady_at_mode_switch_mode': 'AT Mode Switch Mode',
        'set_brady_at_mode_switch_rate': 'AT Mode Switch Rate',

        # Tachy settings
        'set_tachy_vstat': 'VT/VF Therapy Status',

        # Zone settings
        'set_zone_type': 'Zone Type',
        'set_zone_vendor_type': 'Zone Vendor Type',
        'set_zone_status': 'Zone Status',
        'set_zone_detection_interval': 'Detection Interval',
        'set_zone_atp_type_1': 'ATP Type 1',
        'set_zone_atp_type_2': 'ATP Type 2',
        'set_zone_num_atp_seqs_1': 'ATP Sequences 1',
        'set_zone_num_atp_seqs_2': 'ATP Sequences 2',
        'set_zone_shock_energy_1': 'Shock Energy 1',
        'set_zone_shock_energy_2': 'Shock Energy 2',
        'set_zone_shock_energy_3': 'Shock Energy 3',
        'set_zone_num_shocks_1': 'Num Shocks 1',
        'set_zone_num_shocks_2': 'Num Shocks 2',
        'set_zone_num_shocks_3': 'Num Shocks 3',

        # Sensing settings
        'set_leadchnl_ra_sensing_sensitivity': 'RA Sensitivity',
        'set_leadchnl_rv_sensing_sensitivity': 'RV Sensitivity',
        'set_leadchnl_ra_sensing_polarity': 'RA Sensing Polarity',
        'set_leadchnl_rv_sensing_polarity': 'RV Sensing Polarity',
        'set_leadchnl_ra_sensing_adaptation': 'RA Sensing Adaptation',
        'set_leadchnl_rv_sensing_adaptation': 'RV Sensing Adaptation',

        # Pacing settings
        'set_leadchnl_ra_pacing_amplitude': 'RA Pacing Amplitude',
        'set_leadchnl_rv_pacing_amplitude': 'RV Pacing Amplitude',
        'set_leadchnl_ra_pacing_pulsewidth': 'RA Pulse Width',
        'set_leadchnl_rv_pacing_pulsewidth': 'RV Pulse Width',
        'set_leadchnl_ra_pacing_polarity': 'RA Pacing Polarity',
        'set_leadchnl_rv_pacing_polarity': 'RV Pacing Polarity',
        'set_leadchnl_ra_pacing_capture_mode': 'RA Capture Mode',
        'set_leadchnl_rv_pacing_capture_mode': 'RV Capture Mode',

        # Battery measurements
        'msmt_battery_status': 'Battery Status',
        'msmt_battery_remaining_longevity': 'Remaining Longevity',
        'msmt_battery_remaining_percentage': 'Battery Percentage',
        'msmt_cap_charge_time': 'Capacitor Charge Time',

        # Lead measurements
        'msmt_leadchnl_ra_impedance': 'RA Lead Impedance',
        'msmt_leadchnl_rv_impedance': 'RV Lead Impedance',
        'msmt_leadchnl_ra_sensing_amplitude': 'RA Sensing Amplitude',
        'msmt_leadchnl_rv_sensing_amplitude': 'RV Sensing Amplitude',
        'msmt_leadchnl_ra_pacing_threshold_amplitude': 'RA Pacing Threshold',
        'msmt_leadchnl_rv_pacing_threshold_amplitude': 'RV Pacing Threshold',
        'msmt_leadhvchnl_impedance': 'HV Lead Impedance',

        # Statistics
        'stat_brady_ra_percent_paced': 'RA Pacing %',
        'stat_brady_rv_percent_paced': 'RV Pacing %',
        'stat_at_burden_percent': 'AT Burden',
        'stat_tachy_shocks_delivered_total': 'Total Shocks Delivered',
        'stat_tachy_atp_delivered_total': 'Total ATP Delivered',
    }

    # Value translations for coded values
    VALUE_TRANSLATIONS = {
        # Device types
        'MDC_IDC_ENUM_DEV_TYPE_ICD': 'ICD',
        'MDC_IDC_ENUM_DEV_TYPE_PM': 'Pacemaker',
        'MDC_IDC_ENUM_DEV_TYPE_CRT_D': 'CRT-D',
        'MDC_IDC_ENUM_DEV_TYPE_CRT_P': 'CRT-P',

        # Manufacturers
        'MDC_IDC_ENUM_MFG_BSX': 'Boston Scientific',
        'MDC_IDC_ENUM_MFG_MDT': 'Medtronic',
        'MDC_IDC_ENUM_MFG_ABT': 'Abbott',
        'MDC_IDC_ENUM_MFG_BTK': 'Biotronik',

        # Brady modes
        'MDC_IDC_ENUM_BRADY_MODE_DDD': 'DDD',
        'MDC_IDC_ENUM_BRADY_MODE_DDDR': 'DDDR',
        'MDC_IDC_ENUM_BRADY_MODE_VVI': 'VVI',
        'MDC_IDC_ENUM_BRADY_MODE_VVIR': 'VVIR',
        'MDC_IDC_ENUM_BRADY_MODE_AAI': 'AAI',
        'MDC_IDC_ENUM_BRADY_MODE_AAIR': 'AAIR',
        'MDC_IDC_ENUM_BRADY_MODE_DDI': 'DDI',
        'MDC_IDC_ENUM_BRADY_MODE_DDIR': 'DDIR',
        'MDC_IDC_ENUM_BRADY_MODE_VDD': 'VDD',
        'MDC_IDC_ENUM_BRADY_MODE_VOO': 'VOO',
        'MDC_IDC_ENUM_BRADY_MODE_DOO': 'DOO',

        # Therapy status
        'MDC_IDC_ENUM_THERAPY_STATUS_On': 'On',
        'MDC_IDC_ENUM_THERAPY_STATUS_Off': 'Off',
        'MDC_IDC_ENUM_THERAPY_STATUS_Monitor': 'Monitor Only',

        # Zone types
        'MDC_IDC_ENUM_ZONE_TYPE_Zone_VF': 'VF Zone',
        'MDC_IDC_ENUM_ZONE_TYPE_Zone_VT': 'VT Zone',
        'MDC_IDC_ENUM_ZONE_TYPE_Zone_VT1': 'VT-1 Zone',

        # Zone status
        'MDC_IDC_ENUM_ZONE_STATUS_Active': 'Active',
        'MDC_IDC_ENUM_ZONE_STATUS_Monitor': 'Monitor',
        'MDC_IDC_ENUM_ZONE_STATUS_Off': 'Off',

        # ATP types
        'MDC_IDC_ENUM_ATP_TYPE_Burst': 'Burst',
        'MDC_IDC_ENUM_ATP_TYPE_BurstScan': 'Burst+Scan',
        'MDC_IDC_ENUM_ATP_TYPE_Ramp': 'Ramp',
        'MDC_IDC_ENUM_ATP_TYPE_RampScan': 'Ramp+Scan',

        # Polarity
        'MDC_IDC_ENUM_POLARITY_BI': 'Bipolar',
        'MDC_IDC_ENUM_POLARITY_UNI': 'Unipolar',

        # Sensing adaptation
        'MDC_IDC_ENUM_SENSING_ADAPTATION_MODE_AdaptiveSensing': 'Adaptive',
        'MDC_IDC_ENUM_SENSING_ADAPTATION_MODE_Fixed': 'Fixed',

        # Capture mode
        'MDC_IDC_ENUM_PACING_CAPTURE_MODE_AdaptiveCapture': 'Adaptive',
        'MDC_IDC_ENUM_PACING_CAPTURE_MODE_Fixed': 'Fixed',

        # Battery status
        'MDC_IDC_ENUM_BATTERY_STATUS_BOS': 'Beginning of Service',
        'MDC_IDC_ENUM_BATTERY_STATUS_ERI': 'Elective Replacement',
        'MDC_IDC_ENUM_BATTERY_STATUS_EOL': 'End of Life',

        # Lead locations
        'MDC_IDC_ENUM_LEAD_LOCATION_CHAMBER_RA': 'Right Atrium',
        'MDC_IDC_ENUM_LEAD_LOCATION_CHAMBER_RV': 'Right Ventricle',
        'MDC_IDC_ENUM_LEAD_LOCATION_CHAMBER_LV': 'Left Ventricle',

        # Lead polarity
        'MDC_IDC_ENUM_LEAD_POLARITY_TYPE_BI': 'Bipolar',
        'MDC_IDC_ENUM_LEAD_POLARITY_TYPE_UNI': 'Unipolar',
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Device Settings")

        # Data storage
        self.transmission = None
        self.fixed_settings: Dict[str, Any] = {}
        self.operator_settings: Dict[str, Any] = {}
        self.zone_settings: Dict[int, Dict[str, Any]] = {}  # zone_id -> settings

        # Setup UI
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(main_layout)

        # Header
        header_layout = QVBoxLayout()

        self.title_label = QLabel("Device Settings")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        header_layout.addWidget(self.title_label)

        self.timestamp_label = QLabel("No data loaded")
        self.timestamp_label.setStyleSheet("color: gray; font-size: 11px;")
        header_layout.addWidget(self.timestamp_label)

        main_layout.addLayout(header_layout)

        # Scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(15)
        scroll_content.setLayout(self.content_layout)

        # Fixed Settings Section
        self.fixed_section = self._create_section("FIXED SETTINGS", "#2E7D32")
        self.content_layout.addWidget(self.fixed_section)

        # Fixed settings groups
        self.device_group = self._create_group("Device Information")
        self.lead_info_group = self._create_group("Lead Information")
        self.fixed_section.layout().addWidget(self.device_group)
        self.fixed_section.layout().addWidget(self.lead_info_group)

        # Operator-Defined Settings Section
        self.operator_section = self._create_section("OPERATOR-DEFINED SETTINGS", "#1565C0")
        self.content_layout.addWidget(self.operator_section)

        # Operator settings groups
        self.brady_group = self._create_group("Bradycardia Pacing")
        self.tachy_group = self._create_group("Tachycardia Therapy")
        self.zones_group = self._create_group("Therapy Zones")
        self.sensing_group = self._create_group("Sensing Configuration")
        self.pacing_group = self._create_group("Pacing Configuration")

        self.operator_section.layout().addWidget(self.brady_group)
        self.operator_section.layout().addWidget(self.tachy_group)
        self.operator_section.layout().addWidget(self.zones_group)
        self.operator_section.layout().addWidget(self.sensing_group)
        self.operator_section.layout().addWidget(self.pacing_group)

        # Measurements Section (separate from settings)
        self.measurements_section = self._create_section("MEASUREMENTS", "#6A1B9A")
        self.content_layout.addWidget(self.measurements_section)

        self.battery_group = self._create_group("Battery Status")
        self.lead_msmt_group = self._create_group("Lead Measurements")
        self.stats_group = self._create_group("Statistics")

        self.measurements_section.layout().addWidget(self.battery_group)
        self.measurements_section.layout().addWidget(self.lead_msmt_group)
        self.measurements_section.layout().addWidget(self.stats_group)

        self.content_layout.addStretch()

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        # Initially hide empty groups
        self._hide_empty_groups()

    def _create_section(self, title: str, color: str) -> QFrame:
        """
        Create a section frame with header.

        Args:
            title: Section title
            color: Header background color

        Returns:
            QFrame containing the section
        """
        section = QFrame()
        section.setFrameShape(QFrame.Shape.Box)
        section.setStyleSheet(f"""
            QFrame {{
                border: 1px solid #cccccc;
                border-radius: 5px;
                background-color: #fafafa;
            }}
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(10)
        section.setLayout(layout)

        # Section header
        header = QLabel(title)
        header.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: white;
                font-weight: bold;
                font-size: 12px;
                padding: 8px 12px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
        """)
        layout.addWidget(header)

        return section

    def _create_group(self, title: str) -> QGroupBox:
        """
        Create a settings group box.

        Args:
            title: Group title

        Returns:
            Configured QGroupBox
        """
        group = QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #dddddd;
                border-radius: 4px;
                margin-top: 8px;
                margin-left: 10px;
                margin-right: 10px;
                padding-top: 8px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #333333;
            }
        """)

        layout = QGridLayout()
        layout.setColumnStretch(1, 1)
        layout.setHorizontalSpacing(15)
        layout.setVerticalSpacing(6)
        group.setLayout(layout)

        # Store layout reference
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
        self.fixed_settings = {}
        self.operator_settings = {}
        self.zone_settings = {}

        # Update timestamp
        trans_date = transmission.transmission_date
        self.timestamp_label.setText(
            f"Settings from: {trans_date.strftime('%Y-%m-%d %H:%M')} | "
            f"Device: {transmission.device_manufacturer or 'Unknown'} {transmission.device_model or ''}"
        )

        # Categorize observations
        self._categorize_observations(transmission.observations)

        # Populate UI
        self._populate_fixed_settings()
        self._populate_operator_settings()
        self._populate_measurements()

        self._hide_empty_groups()
        self.settings_loaded.emit()

    def _categorize_observations(self, observations):
        """
        Categorize observations into fixed, operator, and measurement settings.

        Args:
            observations: List of Observation models
        """
        for obs in observations:
            var_name = obs.variable_name
            if not var_name:
                continue

            # Get value
            if obs.value_numeric is not None:
                value = obs.value_numeric
                unit = obs.unit or ''
            elif obs.value_text:
                value = self._translate_value(obs.value_text)
                unit = ''
            else:
                continue

            setting_data = {
                'value': value,
                'unit': unit,
                'vendor_code': obs.vendor_code,
                'raw_value': obs.value_text or obs.value_numeric,
            }

            # Categorize by variable name prefix
            if var_name.startswith('device_') or var_name.startswith('lead_'):
                self.fixed_settings[var_name] = setting_data
            elif var_name.startswith('set_zone_'):
                # Zone settings need sub-ID handling
                # For now, store by sequence number
                zone_id = obs.sequence_number or 1
                if zone_id not in self.zone_settings:
                    self.zone_settings[zone_id] = {}
                self.zone_settings[zone_id][var_name] = setting_data
            elif var_name.startswith('set_'):
                self.operator_settings[var_name] = setting_data
            elif var_name.startswith('msmt_') or var_name.startswith('stat_'):
                # Store measurements separately
                self.operator_settings[var_name] = setting_data

    def _translate_value(self, value: str) -> str:
        """
        Translate coded values to human-readable text.

        Args:
            value: Raw value string

        Returns:
            Translated value or original if no translation
        """
        # Check for direct translation
        if value in self.VALUE_TRANSLATIONS:
            return self.VALUE_TRANSLATIONS[value]

        # Try to extract enum value from full code
        # e.g., "754760^MDC_IDC_ENUM_BRADY_MODE_DDD^MDC" -> "DDD"
        if '^' in value:
            parts = value.split('^')
            for part in parts:
                if part in self.VALUE_TRANSLATIONS:
                    return self.VALUE_TRANSLATIONS[part]
                # Try to extract the last part after underscores
                if 'ENUM_' in part:
                    enum_parts = part.split('_')
                    # Get last meaningful part
                    last_part = enum_parts[-1]
                    if last_part:
                        return last_part

        return value

    def _populate_fixed_settings(self):
        """Populate fixed settings sections."""
        # Clear existing
        self._clear_group(self.device_group)
        self._clear_group(self.lead_info_group)

        # Add device info from transmission
        if self.transmission:
            if self.transmission.device_manufacturer:
                self._add_row(self.device_group, "Manufacturer",
                              self.transmission.device_manufacturer)
            if self.transmission.device_model:
                self._add_row(self.device_group, "Model",
                              self.transmission.device_model)
            if self.transmission.device_serial:
                self._add_row(self.device_group, "Serial Number",
                              self.transmission.device_serial)

        # Add from observations
        device_vars = ['device_type', 'device_implant_date']
        for var in device_vars:
            if var in self.fixed_settings:
                label = self.VARIABLE_LABELS.get(var, self._format_var_name(var))
                value = self._format_value(self.fixed_settings[var])
                self._add_row(self.device_group, label, value)

        # Lead info
        lead_vars = ['lead_model', 'lead_serial', 'lead_manufacturer',
                     'lead_implant_date', 'lead_polarity_type', 'lead_location']
        for var in lead_vars:
            if var in self.fixed_settings:
                label = self.VARIABLE_LABELS.get(var, self._format_var_name(var))
                value = self._format_value(self.fixed_settings[var])
                self._add_row(self.lead_info_group, label, value)

    def _populate_operator_settings(self):
        """Populate operator-defined settings sections."""
        # Clear existing
        self._clear_group(self.brady_group)
        self._clear_group(self.tachy_group)
        self._clear_group(self.zones_group)
        self._clear_group(self.sensing_group)
        self._clear_group(self.pacing_group)

        # Brady settings
        brady_vars = ['set_brady_mode', 'set_brady_lowrate', 'set_brady_max_tracking_rate',
                      'set_brady_max_sensor_rate', 'set_brady_sav_delay_high',
                      'set_brady_sav_delay_low', 'set_brady_pav_delay_high',
                      'set_brady_pav_delay_low', 'set_brady_sensor_type',
                      'set_brady_at_mode_switch_mode', 'set_brady_at_mode_switch_rate']
        for var in brady_vars:
            if var in self.operator_settings:
                label = self.VARIABLE_LABELS.get(var, self._format_var_name(var))
                value = self._format_value(self.operator_settings[var])
                self._add_row(self.brady_group, label, value)

        # Tachy settings
        if 'set_tachy_vstat' in self.operator_settings:
            label = self.VARIABLE_LABELS.get('set_tachy_vstat', 'VT/VF Status')
            value = self._format_value(self.operator_settings['set_tachy_vstat'])
            self._add_row(self.tachy_group, label, value)

        # Zone settings (grouped by zone)
        for zone_id in sorted(self.zone_settings.keys()):
            zone_data = self.zone_settings[zone_id]

            # Get zone type for header
            zone_type = "Zone"
            if 'set_zone_type' in zone_data:
                zone_type = self._format_value(zone_data['set_zone_type'])

            # Add zone header
            header_label = QLabel(f"  {zone_type}")
            header_label.setStyleSheet("font-weight: bold; color: #1565C0; margin-top: 5px;")
            self.zones_group.grid_layout.addWidget(
                header_label, self.zones_group.row_count, 0, 1, 2
            )
            self.zones_group.row_count += 1

            # Add zone settings
            zone_vars = ['set_zone_status', 'set_zone_detection_interval',
                         'set_zone_atp_type_1', 'set_zone_num_atp_seqs_1',
                         'set_zone_atp_type_2', 'set_zone_num_atp_seqs_2',
                         'set_zone_shock_energy_1', 'set_zone_num_shocks_1',
                         'set_zone_shock_energy_2', 'set_zone_num_shocks_2',
                         'set_zone_shock_energy_3', 'set_zone_num_shocks_3']
            for var in zone_vars:
                if var in zone_data:
                    label = self.VARIABLE_LABELS.get(var, self._format_var_name(var))
                    value = self._format_value(zone_data[var])
                    self._add_row(self.zones_group, f"    {label}", value)

        # Sensing settings
        sensing_vars = ['set_leadchnl_ra_sensing_sensitivity', 'set_leadchnl_rv_sensing_sensitivity',
                        'set_leadchnl_ra_sensing_polarity', 'set_leadchnl_rv_sensing_polarity',
                        'set_leadchnl_ra_sensing_adaptation', 'set_leadchnl_rv_sensing_adaptation']
        for var in sensing_vars:
            if var in self.operator_settings:
                label = self.VARIABLE_LABELS.get(var, self._format_var_name(var))
                value = self._format_value(self.operator_settings[var])
                self._add_row(self.sensing_group, label, value)

        # Pacing settings
        pacing_vars = ['set_leadchnl_ra_pacing_amplitude', 'set_leadchnl_rv_pacing_amplitude',
                       'set_leadchnl_ra_pacing_pulsewidth', 'set_leadchnl_rv_pacing_pulsewidth',
                       'set_leadchnl_ra_pacing_polarity', 'set_leadchnl_rv_pacing_polarity',
                       'set_leadchnl_ra_pacing_capture_mode', 'set_leadchnl_rv_pacing_capture_mode']
        for var in pacing_vars:
            if var in self.operator_settings:
                label = self.VARIABLE_LABELS.get(var, self._format_var_name(var))
                value = self._format_value(self.operator_settings[var])
                self._add_row(self.pacing_group, label, value)

    def _populate_measurements(self):
        """Populate measurement sections."""
        self._clear_group(self.battery_group)
        self._clear_group(self.lead_msmt_group)
        self._clear_group(self.stats_group)

        # Battery
        battery_vars = ['msmt_battery_status', 'msmt_battery_remaining_longevity',
                        'msmt_battery_remaining_percentage', 'msmt_cap_charge_time']
        for var in battery_vars:
            if var in self.operator_settings:
                label = self.VARIABLE_LABELS.get(var, self._format_var_name(var))
                value = self._format_value(self.operator_settings[var])
                self._add_row(self.battery_group, label, value)

        # Lead measurements
        lead_msmt_vars = ['msmt_leadchnl_ra_impedance', 'msmt_leadchnl_rv_impedance',
                          'msmt_leadchnl_ra_sensing_amplitude', 'msmt_leadchnl_rv_sensing_amplitude',
                          'msmt_leadchnl_ra_pacing_threshold_amplitude',
                          'msmt_leadchnl_rv_pacing_threshold_amplitude',
                          'msmt_leadhvchnl_impedance']
        for var in lead_msmt_vars:
            if var in self.operator_settings:
                label = self.VARIABLE_LABELS.get(var, self._format_var_name(var))
                value = self._format_value(self.operator_settings[var])
                self._add_row(self.lead_msmt_group, label, value)

        # Statistics
        stat_vars = ['stat_brady_ra_percent_paced', 'stat_brady_rv_percent_paced',
                     'stat_at_burden_percent', 'stat_tachy_shocks_delivered_total',
                     'stat_tachy_atp_delivered_total']
        for var in stat_vars:
            if var in self.operator_settings:
                label = self.VARIABLE_LABELS.get(var, self._format_var_name(var))
                value = self._format_value(self.operator_settings[var])
                self._add_row(self.stats_group, label, value)

    def _format_value(self, setting_data: Dict) -> str:
        """
        Format a setting value for display.

        Args:
            setting_data: Dictionary with value and unit

        Returns:
            Formatted string
        """
        value = setting_data['value']
        unit = setting_data.get('unit', '')

        # Handle numeric values
        if isinstance(value, float):
            # Format nicely
            if value == int(value):
                value_str = str(int(value))
            else:
                value_str = f"{value:.1f}"
        else:
            value_str = str(value)

        # Add unit if present
        if unit:
            # Clean up unit formatting
            unit = unit.replace('{beats}/min', 'bpm')
            unit = unit.replace('ohms', 'Ohm')
            return f"{value_str} {unit}"

        return value_str

    def _format_var_name(self, var_name: str) -> str:
        """
        Convert variable name to readable label.

        Args:
            var_name: Variable name like 'set_brady_lowrate'

        Returns:
            Formatted label like 'Brady Lowrate'
        """
        # Remove common prefixes
        for prefix in ['set_', 'msmt_', 'stat_', 'device_', 'lead_']:
            if var_name.startswith(prefix):
                var_name = var_name[len(prefix):]
                break

        # Replace underscores and title case
        return var_name.replace('_', ' ').title()

    def _add_row(self, group: QGroupBox, label: str, value: str):
        """
        Add a label-value row to a group.

        Args:
            group: Target group box
            label: Setting label
            value: Setting value
        """
        layout = group.grid_layout
        row = group.row_count

        label_widget = QLabel(f"{label}:")
        label_widget.setStyleSheet("font-weight: normal; color: #555555;")
        layout.addWidget(label_widget, row, 0,
                         Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        value_widget = QLabel(str(value))
        value_widget.setStyleSheet("font-weight: bold; color: #000000;")
        value_widget.setWordWrap(True)
        layout.addWidget(value_widget, row, 1,
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        group.row_count += 1

    def _clear_group(self, group: QGroupBox):
        """Clear all widgets from a group."""
        layout = group.grid_layout
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        group.row_count = 0

    def _hide_empty_groups(self):
        """Hide groups that have no data."""
        groups = [
            self.device_group, self.lead_info_group,
            self.brady_group, self.tachy_group, self.zones_group,
            self.sensing_group, self.pacing_group,
            self.battery_group, self.lead_msmt_group, self.stats_group
        ]

        for group in groups:
            group.setVisible(group.row_count > 0)

        # Hide sections if all their groups are hidden
        self.lead_info_group.setVisible(self.lead_info_group.row_count > 0)

        operator_visible = any(g.row_count > 0 for g in [
            self.brady_group, self.tachy_group, self.zones_group,
            self.sensing_group, self.pacing_group
        ])
        # Keep operator section visible even if some groups are empty

        measurement_visible = any(g.row_count > 0 for g in [
            self.battery_group, self.lead_msmt_group, self.stats_group
        ])
        self.measurements_section.setVisible(measurement_visible)

    def clear(self):
        """Clear all settings data."""
        self.transmission = None
        self.fixed_settings = {}
        self.operator_settings = {}
        self.zone_settings = {}

        self.timestamp_label.setText("No data loaded")

        # Clear all groups
        groups = [
            self.device_group, self.lead_info_group,
            self.brady_group, self.tachy_group, self.zones_group,
            self.sensing_group, self.pacing_group,
            self.battery_group, self.lead_msmt_group, self.stats_group
        ]
        for group in groups:
            self._clear_group(group)

        self._hide_empty_groups()
