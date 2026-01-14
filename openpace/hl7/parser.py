"""
HL7 ORU^R01 Parser

Parses HL7 observation result messages from pacemaker remote monitoring systems.

Message structure:
MSH → Message Header (device, facility)
PID → Patient Identification
OBR → Observation Request (context)
OBX → Observation Segment (actual data)
"""

import hl7
import re
import logging
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from openpace.database.models import Patient, Transmission, Observation
from openpace.hl7.translators.base_translator import get_translator
from openpace.exceptions import (
    HL7ValidationError,
    ValidationError,
    PatientIDValidationError,
    format_validation_error
)
from openpace.constants import FileLimits

# Configure logging
logger = logging.getLogger(__name__)


class DataSanitizer:
    """
    Data sanitization and validation utilities for HL7 data.

    Prevents injection attacks and ensures data integrity by:
    - Removing control characters
    - Validating format with regex patterns
    - Enforcing length limits
    - Sanitizing patient IDs and names
    """

    # Regex patterns for validation
    PATIENT_ID_PATTERN = re.compile(r'^[A-Za-z0-9\-_\.]{1,100}$')
    PATIENT_NAME_PATTERN = re.compile(r'^[A-Za-z0-9\s\'\-\.\,]{1,200}$')

    # Control characters to remove (C0 and C1 control codes except tab, newline, carriage return)
    CONTROL_CHARS_PATTERN = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]')

    @classmethod
    def sanitize_patient_id(cls, patient_id: str) -> str:
        """
        Sanitize and validate patient ID.

        Args:
            patient_id: Raw patient ID from HL7 message

        Returns:
            Sanitized patient ID

        Raises:
            PatientIDValidationError: If patient ID is invalid
        """
        if not patient_id:
            raise PatientIDValidationError("Patient ID cannot be empty")

        # Remove control characters
        sanitized = cls.CONTROL_CHARS_PATTERN.sub('', patient_id)

        # Enforce length limit
        if len(sanitized) > FileLimits.MAX_PATIENT_ID_LENGTH:
            raise PatientIDValidationError(
                format_validation_error(
                    "patient_id",
                    sanitized,
                    f"exceeds maximum length of {FileLimits.MAX_PATIENT_ID_LENGTH}"
                )
            )

        # Validate format (alphanumeric, hyphens, underscores, dots only)
        if not cls.PATIENT_ID_PATTERN.match(sanitized):
            raise PatientIDValidationError(
                format_validation_error(
                    "patient_id",
                    sanitized,
                    "contains invalid characters (allowed: A-Z, a-z, 0-9, -, _, .)"
                )
            )

        logger.debug(f"Sanitized patient ID: '{patient_id}' -> '{sanitized}'")
        return sanitized

    @classmethod
    def sanitize_patient_name(cls, patient_name: str) -> str:
        """
        Sanitize and validate patient name.

        Args:
            patient_name: Raw patient name from HL7 message

        Returns:
            Sanitized patient name

        Raises:
            ValidationError: If patient name is invalid
        """
        if not patient_name:
            return ""

        # Remove control characters
        sanitized = cls.CONTROL_CHARS_PATTERN.sub('', patient_name)

        # Enforce length limit
        if len(sanitized) > FileLimits.MAX_PATIENT_NAME_LENGTH:
            raise ValidationError(
                format_validation_error(
                    "patient_name",
                    sanitized,
                    f"exceeds maximum length of {FileLimits.MAX_PATIENT_NAME_LENGTH}"
                )
            )

        # Validate format (letters, numbers, spaces, apostrophes, hyphens, dots, commas)
        if sanitized and not cls.PATIENT_NAME_PATTERN.match(sanitized):
            raise ValidationError(
                format_validation_error(
                    "patient_name",
                    sanitized,
                    "contains invalid characters"
                )
            )

        logger.debug(f"Sanitized patient name: '{patient_name}' -> '{sanitized}'")
        return sanitized.strip()

    @classmethod
    def sanitize_text_field(cls, text: str, max_length: int = 500) -> str:
        """
        Sanitize general text fields.

        Args:
            text: Raw text from HL7 message
            max_length: Maximum allowed length

        Returns:
            Sanitized text

        Raises:
            ValidationError: If text exceeds length limit
        """
        if not text:
            return ""

        # Remove control characters
        sanitized = cls.CONTROL_CHARS_PATTERN.sub('', text)

        # Enforce length limit
        if len(sanitized) > max_length:
            raise ValidationError(
                format_validation_error(
                    "text_field",
                    sanitized,
                    f"exceeds maximum length of {max_length}"
                )
            )

        return sanitized.strip()


class HL7Parser:
    """
    Main HL7 message parser for pacemaker data.

    Extracts data from HL7 ORU^R01 messages and stores in database.
    """

    def __init__(self, db_session: Session, anonymize: bool = False):
        """
        Initialize HL7 parser.

        Args:
            db_session: SQLAlchemy database session
            anonymize: If True, strip PII from patient data
        """
        self.session = db_session
        self.anonymize = anonymize

    def validate_hl7_message(self, hl7_message_text: str) -> None:
        """
        Validate HL7 message before parsing.

        Prevents DoS attacks through:
        - Size limit validation (MAX 50MB)
        - Format validation (must start with MSH)
        - Basic structure validation

        Args:
            hl7_message_text: Raw HL7 message string

        Raises:
            HL7ValidationError: If message fails validation
        """
        if not hl7_message_text:
            raise HL7ValidationError("HL7 message cannot be empty")

        # Check message size to prevent DoS through memory exhaustion
        message_size = len(hl7_message_text.encode('utf-8'))
        if message_size < FileLimits.MIN_HL7_MESSAGE_SIZE:
            raise HL7ValidationError(
                f"HL7 message too small ({message_size} bytes). "
                f"Minimum size: {FileLimits.MIN_HL7_MESSAGE_SIZE} bytes"
            )

        if message_size > FileLimits.MAX_HL7_MESSAGE_SIZE:
            raise HL7ValidationError(
                f"HL7 message too large ({message_size} bytes). "
                f"Maximum allowed: {FileLimits.MAX_HL7_MESSAGE_SIZE} bytes (50 MB)"
            )

        # Validate message format - must start with MSH segment
        normalized = hl7_message_text.replace('\r\n', '\r').replace('\n', '\r')
        if not normalized.startswith('MSH'):
            raise HL7ValidationError(
                "Invalid HL7 message format: must start with 'MSH' segment"
            )

        # Check for minimum required segments (MSH and PID)
        if 'PID' not in normalized:
            raise HL7ValidationError(
                "Invalid HL7 message: missing required PID (Patient Identification) segment"
            )

        logger.info(f"HL7 message validation passed: {message_size} bytes")

    def parse_message(self, hl7_message_text: str, filename: str = None) -> Transmission:
        """
        Parse a complete HL7 ORU^R01 message.

        Args:
            hl7_message_text: Raw HL7 message string
            filename: Optional source filename

        Returns:
            Transmission object representing the parsed message

        Raises:
            HL7ValidationError: If message fails validation
            ValueError: If message is not valid HL7 ORU^R01
        """
        # Validate message before parsing (security check)
        self.validate_hl7_message(hl7_message_text)

        # Parse HL7 message
        # python-hl7 expects segments separated by \r, normalize line endings
        hl7_message_normalized = hl7_message_text.replace('\r\n', '\r').replace('\n', '\r')

        try:
            msg = hl7.parse(hl7_message_normalized)
        except Exception as e:
            logger.error(f"HL7 parsing failed: {e}")
            raise ValueError(f"Failed to parse HL7 message: {e}")

        # Verify message type
        msh = msg.segment('MSH')
        # MSH-9 in HL7 spec (Message Type), but python-hl7 uses 1-based indexing
        # and includes separator field, so it's at index 9 (actually shows as index 10 due to encoding)
        # Try both indexes to be safe
        message_type_field = msh[9] if len(msh) > 9 else None
        if not message_type_field or not str(message_type_field).strip():
            message_type_field = msh[10] if len(msh) > 10 else None

        # python-hl7 parses compound fields into nested lists: [[['ORU'], ['R01']]]
        if isinstance(message_type_field, list):
            # Flatten nested lists
            def flatten(lst):
                result = []
                for item in lst:
                    if isinstance(item, list):
                        result.extend(flatten(item))
                    else:
                        result.append(str(item))
                return result
            parts = flatten(message_type_field)
            message_type = '^'.join(parts)
        else:
            message_type = str(message_type_field) if message_type_field else ''

        if 'ORU' not in message_type or 'R01' not in message_type:
            raise ValueError(f"Expected ORU^R01 message, got: {message_type}")

        # Extract segments
        msh_data = self.parse_msh(msh)
        pid_data = self.parse_pid(msg.segment('PID'))

        # OBR may not always be present, handle gracefully
        try:
            obr_data = self.parse_obr(msg.segment('OBR'))
        except KeyError:
            obr_data = {}

        # Get or create patient
        patient = self._get_or_create_patient(pid_data)

        # Create transmission record
        transmission = Transmission(
            patient_id=patient.patient_id,
            transmission_date=msh_data['message_datetime'],
            transmission_type=obr_data.get('observation_type', 'unknown'),
            message_control_id=msh_data.get('message_control_id'),
            sending_application=msh_data.get('sending_application'),
            sending_facility=msh_data.get('sending_facility'),
            device_manufacturer=self._extract_manufacturer(msh_data),
            device_model=pid_data.get('device_model'),
            device_serial=pid_data.get('device_serial'),
            hl7_filename=filename,
        )
        self.session.add(transmission)
        self.session.flush()  # Get transmission_id

        # Get appropriate translator based on manufacturer
        translator = get_translator(transmission.device_manufacturer or 'Generic')

        # Parse all OBX segments
        obx_count = 0
        for obx_segment in msg.segments('OBX'):
            observation = self.parse_obx(
                obx_segment,
                transmission.transmission_id,
                translator,
                transmission.transmission_date
            )
            if observation:
                self.session.add(observation)
                obx_count += 1

        self.session.commit()

        print(f"[OK] Parsed transmission {transmission.transmission_id}: {obx_count} observations")
        return transmission

    def parse_msh(self, msh_segment) -> Dict:
        """
        Parse MSH (Message Header) segment.

        MSH|^~\\&|SENDING_APP|SENDING_FACILITY|RECEIVING_APP|RECEIVING_FACILITY|DATETIME||ORU^R01|MSG_ID|P|2.5

        Args:
            msh_segment: MSH segment from hl7 message

        Returns:
            Dictionary with message header data
        """
        # python-hl7 indexing: MSH|^~\&|3|4|5|6|7|8|9|10|11|12|13
        # Note: Field 0=MSH, 1=separator field, 2=^~\&, then actual data starts at 3

        # Parse datetime - try field 8 first (Medtronic), then field 7 (Boston Scientific)
        datetime_str = str(msh_segment[8][0]) if isinstance(msh_segment[8], list) else str(msh_segment[8])
        if not datetime_str or datetime_str in ('', 'None'):
            # Try field 7 as fallback (Boston Scientific uses this)
            datetime_str = str(msh_segment[7][0]) if isinstance(msh_segment[7], list) else str(msh_segment[7])

        return {
            'sending_application': str(msh_segment[3][0]) if isinstance(msh_segment[3], list) else str(msh_segment[3]),
            'sending_facility': str(msh_segment[4][0]) if isinstance(msh_segment[4], list) else str(msh_segment[4]),
            'receiving_application': str(msh_segment[5][0]) if isinstance(msh_segment[5], list) else str(msh_segment[5]),
            'receiving_facility': str(msh_segment[6][0]) if isinstance(msh_segment[6], list) else str(msh_segment[6]),
            'message_datetime': self._parse_hl7_datetime(datetime_str),
            'message_type': 'ORU^R01',  # Already validated
            'message_control_id': str(msh_segment[11][0]) if isinstance(msh_segment[11], list) else str(msh_segment[11]),
            'version': str(msh_segment[13][0]) if len(msh_segment) > 13 else '2.5',
        }

    def parse_pid(self, pid_segment) -> Dict:
        """
        Parse PID (Patient Identification) segment with input validation.

        PID|1||PATIENT_ID^^^FACILITY||LAST^FIRST||DOB|GENDER|||...

        Boston Scientific LATITUDE format embeds device info in PID-3:
        model:D433/serial:677770^^BSX^U~7767669^^The Alfred Hospital^U

        Args:
            pid_segment: PID segment from hl7 message

        Returns:
            Dictionary with sanitized patient data including device info

        Raises:
            PatientIDValidationError: If patient ID is invalid
            ValidationError: If patient name is invalid
        """
        # Extract patient ID (PID-3)
        patient_id_field = str(pid_segment[3])

        # Initialize device info
        device_model = None
        device_serial = None

        # Check for Boston Scientific LATITUDE format with embedded device info
        # Format: model:D433/serial:677770^^BSX^U~7767669^^The Alfred Hospital^U
        if 'model:' in patient_id_field or 'serial:' in patient_id_field:
            # Parse device info from the field
            device_model, device_serial, raw_patient_id = self._extract_device_info_from_pid(patient_id_field)
        else:
            # Handle complex ID format: ID^^^FACILITY
            raw_patient_id = patient_id_field.split('^')[0] if '^' in patient_id_field else patient_id_field

        # Sanitize patient ID (critical for SQL injection prevention)
        patient_id = DataSanitizer.sanitize_patient_id(raw_patient_id)

        # Extract patient name (PID-5)
        patient_name = None
        if not self.anonymize:
            name_field = str(pid_segment[5])
            if '^' in name_field:
                # Format: LAST^FIRST^MIDDLE
                parts = name_field.split('^')
                last = parts[0] if len(parts) > 0 else ''
                first = parts[1] if len(parts) > 1 else ''
                raw_name = f"{first} {last}".strip()
            else:
                raw_name = name_field

            # Sanitize patient name
            if raw_name and raw_name not in ('', 'None'):
                patient_name = DataSanitizer.sanitize_patient_name(raw_name)

        # Extract date of birth (PID-7)
        dob = None
        if not self.anonymize:
            dob_str = str(pid_segment[7])
            dob = self._parse_hl7_date(dob_str)

        # Extract gender (PID-8) - validate single character
        gender_raw = str(pid_segment[8]) if len(pid_segment) > 8 else None
        gender = None
        if gender_raw and gender_raw in ('M', 'F', 'O', 'U', 'm', 'f', 'o', 'u'):
            gender = gender_raw.upper()

        return {
            'patient_id': patient_id,
            'patient_name': patient_name,
            'date_of_birth': dob,
            'gender': gender,
            'device_model': device_model,
            'device_serial': device_serial,
        }

    def parse_obr(self, obr_segment) -> Dict:
        """
        Parse OBR (Observation Request) segment.

        OBR|1|ORDER_ID|FILLER_ID|OBSERVATION_TYPE|||DATETIME|...

        Args:
            obr_segment: OBR segment from hl7 message

        Returns:
            Dictionary with observation request data
        """
        # OBR-4: Universal Service Identifier
        observation_type_field = str(obr_segment[4])
        observation_type = observation_type_field.split('^')[0] if '^' in observation_type_field else observation_type_field

        # Determine if remote or in-clinic based on observation type
        transmission_type = 'remote' if 'REMOTE' in observation_type.upper() else 'in_clinic'

        return {
            'observation_type': transmission_type,
            'order_id': str(obr_segment[2]) if len(obr_segment) > 2 else None,
            'observation_datetime': self._parse_hl7_datetime(str(obr_segment[7])) if len(obr_segment) > 7 else None,
        }

    def parse_obx(self, obx_segment, transmission_id: int, translator,
                  observation_time: datetime) -> Optional[Observation]:
        """
        Parse OBX (Observation) segment - the core pacemaker data.

        OBX|SEQ|TYPE|OBSERVATION_ID^TEXT^CODING_SYSTEM|SUB_ID|VALUE|UNITS|RANGE|FLAGS|...

        Examples:
        - OBX|1|NM|73990-7^Battery Voltage^LN||2.65|V|2.2-2.8|N|||F
        - OBX|2|NM|8889-8^Lead Impedance Atrial^LN||625|Ohm|200-1500|N|||F
        - OBX|3|ED|11524-6^EGM Strip^LN||^Base64^SGVsbG8=^Base64|||F

        Args:
            obx_segment: OBX segment from hl7 message
            transmission_id: ID of parent transmission
            translator: Vendor-specific translator
            observation_time: Timestamp for the observation (from transmission)

        Returns:
            Observation object or None if observation is unknown
        """
        # OBX-2: Value type (NM=numeric, ST=string, ED=encapsulated data)
        value_type = str(obx_segment[2])

        # OBX-3: Observation identifier (LOINC code or vendor-specific)
        observation_id_field = str(obx_segment[3])
        parts = observation_id_field.split('^')
        observation_id = parts[0]

        # Sanitize observation text to prevent injection
        raw_observation_text = parts[1] if len(parts) > 1 else ''
        observation_text = DataSanitizer.sanitize_text_field(
            raw_observation_text,
            max_length=FileLimits.MAX_OBSERVATION_TEXT_LENGTH
        )

        coding_system = parts[2] if len(parts) > 2 else ''

        # OBX-5: Observation value
        value = str(obx_segment[5])

        # OBX-6: Units
        unit = str(obx_segment[6]) if len(obx_segment) > 6 else None

        # OBX-7: Reference range
        reference_range = str(obx_segment[7]) if len(obx_segment) > 7 else None

        # OBX-8: Abnormal flags (N=normal, H=high, L=low, etc.)
        abnormal_flag = str(obx_segment[8]) if len(obx_segment) > 8 else None

        # OBX-11: Observation result status (F=final, P=preliminary)
        obs_status = str(obx_segment[11]) if len(obx_segment) > 11 else 'F'

        # OBX-1: Sequence number
        sequence = int(str(obx_segment[1])) if len(obx_segment) > 1 else None

        # Map vendor code to universal variable
        universal_var = translator.map_observation_id(observation_id, observation_text)

        if not universal_var:
            # Unknown observation, skip or log
            print(f"  [WARN] Unknown observation: {observation_id} ({observation_text})")
            return None

        # Determine if LOINC code
        loinc_code = observation_id if coding_system == 'LN' else None

        # Create observation object
        observation = Observation(
            transmission_id=transmission_id,
            observation_time=observation_time,
            sequence_number=sequence,
            variable_name=universal_var,
            loinc_code=loinc_code,
            vendor_code=observation_id,
            unit=unit,
            reference_range=reference_range,
            abnormal_flag=abnormal_flag,
            observation_status=obs_status,
        )

        # Parse value based on type
        if value_type == 'NM':  # Numeric
            try:
                observation.value_numeric = float(value)
            except ValueError:
                print(f"  [WARN] Invalid numeric value: {value}")
                return None

        elif value_type == 'ST':  # String/Text
            # Try to convert to numeric if it looks like a number
            # Many devices send numeric data as ST type
            try:
                # Remove common non-numeric characters and try conversion
                cleaned_value = value.strip().replace(',', '.')
                observation.value_numeric = float(cleaned_value)
            except (ValueError, AttributeError):
                # Not a number, store as text
                observation.value_text = value

        elif value_type == 'ED':  # Encapsulated Data (base64 blob)
            blob_data = self._extract_base64_from_ed(value)
            observation.value_blob = blob_data

        return observation

    def _get_or_create_patient(self, pid_data: Dict) -> Patient:
        """
        Get existing patient or create new one.

        Args:
            pid_data: Patient data dictionary from PID segment

        Returns:
            Patient object
        """
        patient_id = pid_data['patient_id']
        patient = self.session.query(Patient).filter_by(patient_id=patient_id).first()

        if not patient:
            # Create new patient
            patient = Patient(
                patient_id=patient_id,
                anonymized=self.anonymize,
                patient_name=pid_data['patient_name'],
                date_of_birth=pid_data['date_of_birth'],
                gender=pid_data['gender'],
            )

            # If anonymizing, create anonymized ID
            if self.anonymize:
                # Use last 3 digits of patient ID for anonymized display
                patient.anonymized_id = f"Patient_{patient_id[-3:]}"

            self.session.add(patient)
            self.session.flush()
            print(f"[OK] Created new patient: {patient.anonymized_id if self.anonymize else patient.patient_name}")

        return patient

    def _extract_manufacturer(self, msh_data: Dict) -> str:
        """
        Extract manufacturer from MSH data.

        Args:
            msh_data: MSH segment data

        Returns:
            Manufacturer name
        """
        app = msh_data.get('sending_application', '').upper()

        if 'MEDTRONIC' in app or 'CARELINK' in app:
            return 'Medtronic'
        elif 'BOSTON' in app or 'BSC' in app or 'LATITUDE' in app:
            return 'Boston Scientific'
        elif 'ABBOTT' in app or 'MERLIN' in app or 'SJM' in app:
            return 'Abbott'
        elif 'BIOTRONIK' in app:
            return 'Biotronik'
        else:
            return 'Generic'

    def _extract_device_info_from_pid(self, patient_id_field: str) -> tuple:
        """
        Extract device model and serial from Boston Scientific LATITUDE PID-3 format.

        Format: model:D433/serial:677770^^BSX^U~7767669^^The Alfred Hospital^U

        The field may contain multiple repetitions separated by '~':
        - First repetition: device info (model:XXX/serial:YYY)
        - Second repetition: actual patient ID

        Args:
            patient_id_field: Raw PID-3 field value

        Returns:
            Tuple of (device_model, device_serial, patient_id)
        """
        device_model = None
        device_serial = None
        patient_id = None

        # Split by repetition separator '~'
        repetitions = patient_id_field.split('~')

        for rep in repetitions:
            # Get first component (before any '^')
            first_component = rep.split('^')[0] if '^' in rep else rep

            # Check if this repetition contains device info
            if 'model:' in first_component or 'serial:' in first_component:
                # Parse device info: model:D433/serial:677770
                parts = first_component.split('/')
                for part in parts:
                    if part.startswith('model:'):
                        device_model = part[6:].strip()  # Remove 'model:' prefix
                    elif part.startswith('serial:'):
                        device_serial = part[7:].strip()  # Remove 'serial:' prefix
            else:
                # This might be the patient ID
                if first_component and first_component.strip():
                    # Use first non-device-info value as patient ID
                    if patient_id is None:
                        patient_id = first_component.strip()

        # If no separate patient ID found, generate one from device serial
        if patient_id is None and device_serial:
            patient_id = f"DEV-{device_serial}"

        logger.info(f"Extracted device info - Model: {device_model}, Serial: {device_serial}, Patient ID: {patient_id}")

        return device_model, device_serial, patient_id

    def _parse_hl7_datetime(self, hl7_datetime: str) -> Optional[datetime]:
        """
        Convert HL7 datetime (YYYYMMDDHHmmss) to Python datetime.

        Handles formats like:
        - YYYYMMDDHHmmss
        - YYYYMMDDHHmmss+0000 (with timezone)
        - YYYYMMDD (date only)

        Args:
            hl7_datetime: HL7 datetime string

        Returns:
            Python datetime object or None if invalid
        """
        if not hl7_datetime or hl7_datetime == '' or hl7_datetime == 'None':
            return None

        try:
            # HL7 datetime: YYYYMMDDHHmmss (can be truncated, may have timezone)
            hl7_datetime = hl7_datetime.strip()

            # Remove timezone if present (+0000, -0500, etc.)
            if '+' in hl7_datetime or '-' in hl7_datetime:
                # Find the timezone separator
                for sep in ['+', '-']:
                    if sep in hl7_datetime and hl7_datetime.index(sep) >= 8:
                        hl7_datetime = hl7_datetime[:hl7_datetime.index(sep)]
                        break

            if len(hl7_datetime) >= 14:
                return datetime.strptime(hl7_datetime[:14], '%Y%m%d%H%M%S')
            elif len(hl7_datetime) >= 12:
                # YYYYMMDDHHmm (no seconds)
                return datetime.strptime(hl7_datetime[:12], '%Y%m%d%H%M')
            elif len(hl7_datetime) >= 8:
                # Date only
                return datetime.strptime(hl7_datetime[:8], '%Y%m%d')
        except ValueError as e:
            logger.warning(f"Failed to parse HL7 datetime '{hl7_datetime}': {e}")

        return None

    def _parse_hl7_date(self, hl7_date: str):
        """
        Convert HL7 date (YYYYMMDD) to Python date.

        Args:
            hl7_date: HL7 date string

        Returns:
            Python date object or None if invalid
        """
        if not hl7_date or hl7_date == '':
            return None

        try:
            if len(hl7_date) >= 8:
                return datetime.strptime(hl7_date[:8], '%Y%m%d').date()
        except ValueError:
            pass

        return None

    def _extract_base64_from_ed(self, ed_value: str) -> Optional[bytes]:
        """
        Extract base64 data from HL7 Encapsulated Data format.

        Format: ^SourceApp^Base64Data^Encoding

        Args:
            ed_value: HL7 ED field value

        Returns:
            Decoded bytes or None if invalid
        """
        import base64

        parts = ed_value.split('^')
        if len(parts) >= 3:
            try:
                return base64.b64decode(parts[2])
            except Exception as e:
                print(f"  [WARN] Failed to decode base64: {e}")
                return None

        return None
