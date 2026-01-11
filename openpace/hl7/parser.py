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
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from openpace.database.models import Patient, Transmission, Observation
from openpace.hl7.translators.base_translator import get_translator


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

    def parse_message(self, hl7_message_text: str, filename: str = None) -> Transmission:
        """
        Parse a complete HL7 ORU^R01 message.

        Args:
            hl7_message_text: Raw HL7 message string
            filename: Optional source filename

        Returns:
            Transmission object representing the parsed message

        Raises:
            ValueError: If message is not valid HL7 ORU^R01
        """
        # Parse HL7 message
        # python-hl7 expects segments separated by \r, normalize line endings
        hl7_message_normalized = hl7_message_text.replace('\r\n', '\r').replace('\n', '\r')

        try:
            msg = hl7.parse(hl7_message_normalized)
        except Exception as e:
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
        return {
            'sending_application': str(msh_segment[3][0]) if isinstance(msh_segment[3], list) else str(msh_segment[3]),
            'sending_facility': str(msh_segment[4][0]) if isinstance(msh_segment[4], list) else str(msh_segment[4]),
            'receiving_application': str(msh_segment[5][0]) if isinstance(msh_segment[5], list) else str(msh_segment[5]),
            'receiving_facility': str(msh_segment[6][0]) if isinstance(msh_segment[6], list) else str(msh_segment[6]),
            'message_datetime': self._parse_hl7_datetime(str(msh_segment[8][0]) if isinstance(msh_segment[8], list) else str(msh_segment[8])),
            'message_type': 'ORU^R01',  # Already validated
            'message_control_id': str(msh_segment[11][0]) if isinstance(msh_segment[11], list) else str(msh_segment[11]),
            'version': str(msh_segment[13][0]) if len(msh_segment) > 13 else '2.5',
        }

    def parse_pid(self, pid_segment) -> Dict:
        """
        Parse PID (Patient Identification) segment.

        PID|1||PATIENT_ID^^^FACILITY||LAST^FIRST||DOB|GENDER|||...

        Args:
            pid_segment: PID segment from hl7 message

        Returns:
            Dictionary with patient data
        """
        # Extract patient ID (PID-3)
        patient_id_field = str(pid_segment[3])
        # Handle complex ID format: ID^^^FACILITY
        patient_id = patient_id_field.split('^')[0] if '^' in patient_id_field else patient_id_field

        # Extract patient name (PID-5)
        patient_name = None
        if not self.anonymize:
            name_field = str(pid_segment[5])
            if '^' in name_field:
                # Format: LAST^FIRST^MIDDLE
                parts = name_field.split('^')
                last = parts[0] if len(parts) > 0 else ''
                first = parts[1] if len(parts) > 1 else ''
                patient_name = f"{first} {last}".strip()
            else:
                patient_name = name_field

        # Extract date of birth (PID-7)
        dob = None
        if not self.anonymize:
            dob_str = str(pid_segment[7])
            dob = self._parse_hl7_date(dob_str)

        # Extract gender (PID-8)
        gender = str(pid_segment[8]) if len(pid_segment) > 8 else None

        return {
            'patient_id': patient_id,
            'patient_name': patient_name,
            'date_of_birth': dob,
            'gender': gender,
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
        observation_text = parts[1] if len(parts) > 1 else ''
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

    def _parse_hl7_datetime(self, hl7_datetime: str) -> Optional[datetime]:
        """
        Convert HL7 datetime (YYYYMMDDHHmmss) to Python datetime.

        Args:
            hl7_datetime: HL7 datetime string

        Returns:
            Python datetime object or None if invalid
        """
        if not hl7_datetime or hl7_datetime == '':
            return None

        try:
            # HL7 datetime: YYYYMMDDHHmmss (can be truncated)
            hl7_datetime = hl7_datetime.strip()
            if len(hl7_datetime) >= 14:
                return datetime.strptime(hl7_datetime[:14], '%Y%m%d%H%M%S')
            elif len(hl7_datetime) >= 8:
                # Date only
                return datetime.strptime(hl7_datetime[:8], '%Y%m%d')
        except ValueError:
            pass

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
