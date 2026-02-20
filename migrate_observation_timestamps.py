"""
Migration: Backfill observation_time from HL7 source data
==========================================================

Observations imported before the timestamp fixes were stamped with an
incorrect datetime — either datetime.utcnow() (very old imports) or the
HL7 MSH-7 / OBR-7 session date instead of the per-observation clinical
date.

This script re-reads the original HL7 file for each transmission and
updates observation_time using the same four-tier fallback as the fixed
parser:

  1. OBX-14  per-observation datetime            (most accurate)
  2. Vendor datetime OBX value for sub_id group  (e.g. BSC msmt_battery_datetime)
  3. OBR-7   observation group datetime
  4. MSH-7   transmission datetime

The original HL7 file path is taken from Transmission.hl7_filename.
Transmissions with no stored filename cannot be fixed here — re-import
the original HL7 file with the fixed parser to get correct timestamps.

After updating observation timestamps, cached LongitudinalTrend records
are deleted so they are recalculated correctly on next patient load.

Run once after deploying the fixed parser.py:

    python migrate_observation_timestamps.py

Safe to re-run — it only updates rows where the resolved timestamp
actually differs from the currently stored value.
"""

import hl7
import sys
from datetime import datetime
from pathlib import Path

# Make sure the project root is on the path
sys.path.insert(0, str(Path(__file__).parent))

from openpace.database.connection import init_database, get_db_session
from openpace.database.models import Transmission, Observation


def _parse_hl7_datetime(s: str):
    if not s or not s.strip():
        return None
    s = s.strip()
    # Strip timezone suffix (+HH, -HH, +HHMM, -HHMM) at position >= 8
    for sep in ('+', '-'):
        idx = s.find(sep)
        if idx >= 8:
            s = s[:idx]
            break
    try:
        if len(s) >= 14:
            return datetime.strptime(s[:14], '%Y%m%d%H%M%S')
        if len(s) >= 12:
            return datetime.strptime(s[:12], '%Y%m%d%H%M')
        if len(s) >= 8:
            return datetime.strptime(s[:8], '%Y%m%d')
    except ValueError:
        pass
    return None


def _resolve_from_hl7(obx_segment, sub_id, obr_datetime,
                      transmission_date, datetime_by_sub_id):
    """
    Four-tier fallback — mirrors the fixed parser logic.

    Returns (datetime, source_label) or (None, None).
    """
    # Tier 1: OBX-14
    try:
        if len(obx_segment) > 14:
            ts = _parse_hl7_datetime(str(obx_segment[14]))
            if ts:
                return ts, 'OBX-14'
    except Exception:
        pass

    # Tier 2: vendor measurement datetime from a preceding datetime OBX in same sub-group
    if sub_id and sub_id in datetime_by_sub_id:
        return datetime_by_sub_id[sub_id], 'vendor-datetime-OBX'

    # Tier 3: OBR-7
    if obr_datetime:
        return obr_datetime, 'OBR-7'

    # Tier 4: MSH-7
    if transmission_date:
        return transmission_date, 'MSH-7'

    return None, None


def migrate():
    init_database()
    session = get_db_session()

    transmissions = session.query(Transmission).all()
    print(f"Found {len(transmissions)} transmission(s) to inspect.\n")

    total_updated = 0
    total_skipped = 0

    for tx in transmissions:
        filename = tx.hl7_filename
        if not filename:
            print(f"  [TX {tx.transmission_id}] No hl7_filename stored — skipping "
                  f"(re-import the file to get corrected timestamps).")
            total_skipped += 1
            continue

        filepath = Path(filename)
        if not filepath.exists():
            print(f"  [TX {tx.transmission_id}] HL7 file not found at {filename!r} — skipping.")
            total_skipped += 1
            continue

        # Re-read and parse the original HL7 file
        try:
            raw = filepath.read_text(encoding='utf-8', errors='replace')
            raw = raw.replace('\r\n', '\r').replace('\n', '\r')
            msg = hl7.parse(raw)
        except Exception as e:
            print(f"  [TX {tx.transmission_id}] Could not parse HL7 file: {e}")
            total_skipped += 1
            continue

        # Extract OBR-7 datetime (first OBR)
        obr_datetime = None
        try:
            obr = msg.segment('OBR')
            obr_datetime = _parse_hl7_datetime(str(obr[7])) if len(obr) > 7 else None
        except (KeyError, Exception):
            pass

        # Index OBX segments by sequence number (OBX-1)
        obx_by_seq = {}
        for seg in msg.segments('OBX'):
            try:
                seq = int(str(seg[1]))
                obx_by_seq[seq] = seg
            except (ValueError, IndexError):
                pass

        # Build vendor datetime lookup (BSC msmt_*_datetime pattern):
        # Walk OBX segments in sequence order, looking for TS/DT-typed observations
        # whose observation text contains "datetime".  Map them by OBX-4 sub_id so
        # subsequent OBX rows in the same group inherit the correct clinical date.
        datetime_by_sub_id: dict = {}
        for seq_key in sorted(obx_by_seq.keys()):
            seg = obx_by_seq[seq_key]
            try:
                value_type = str(seg[2]).strip()
                obs_id_raw = str(seg[3])
                obs_text = obs_id_raw.split('^')[1] if '^' in obs_id_raw else ''
                sub_id = str(seg[4]).strip() if len(seg) > 4 else ''
                value = str(seg[5]).strip() if len(seg) > 5 else ''

                if (value_type in ('TS', 'DT', 'DTM') and
                        'datetime' in obs_text.lower() and value):
                    parsed_dt = _parse_hl7_datetime(value)
                    if parsed_dt and sub_id:
                        datetime_by_sub_id[sub_id] = parsed_dt
            except Exception:
                pass

        # Fetch all observations for this transmission, ordered by sequence
        observations = session.query(Observation).filter_by(
            transmission_id=tx.transmission_id
        ).order_by(Observation.sequence_number).all()

        tx_updated = 0
        tx_skipped = 0

        for obs in observations:
            seg = obx_by_seq.get(obs.sequence_number)
            if seg is None:
                tx_skipped += 1
                continue

            sub_id = str(seg[4]).strip() if len(seg) > 4 else ''
            new_time, source = _resolve_from_hl7(
                seg, sub_id, obr_datetime, tx.transmission_date, datetime_by_sub_id
            )

            if new_time is None or new_time == obs.observation_time:
                tx_skipped += 1
                continue

            obs.observation_time = new_time
            tx_updated += 1

        session.commit()

        print(f"  [TX {tx.transmission_id}]  "
              f"updated={tx_updated}  skipped={tx_skipped}  "
              f"(OBR datetime: {obr_datetime})")

        total_updated += tx_updated
        total_skipped += tx_skipped

    # After fixing observation timestamps, delete stale pre-computed trend records.
    # They will be recalculated correctly on next patient load.
    if total_updated > 0:
        from openpace.database.models import LongitudinalTrend
        deleted = session.query(LongitudinalTrend).delete()
        session.commit()
        print(f"\nInvalidated {deleted} cached trend record(s) "
              f"(will be recalculated on next patient load).")

    print(f"\nMigration complete.")
    print(f"  Total rows updated : {total_updated}")
    print(f"  Total rows skipped : {total_skipped}")
    if total_updated == 0:
        print()
        print("NOTE: Zero rows updated.")
        print("  Ensure Transmission.hl7_filename points to accessible files.")
        print("  If the original HL7 files are no longer available, re-import")
        print("  them with the fixed parser.py to obtain correct timestamps.")


if __name__ == '__main__':
    migrate()
