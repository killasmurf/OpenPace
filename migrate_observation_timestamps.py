"""
Migration: Backfill observation_time from HL7 source data
==========================================================

Every observation imported before this fix was stamped with datetime.utcnow()
at import time instead of the actual clinical timestamp from the HL7 message.

This script re-reads the raw HL7 from each transmission and updates
observation_time using the same three-tier fallback as the fixed parser:

  1. OBX-14  per-observation datetime  (most accurate)
  2. OBR-7   observation group datetime
  3. MSH-7   transmission datetime

Run once after deploying the fixed parser.py:

    python migrate_observation_timestamps.py

Safe to re-run — it only touches rows where observation_time is within
1 minute of the transmission's imported_at (the import wall-clock stamp).
"""

import hl7
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Make sure the project root is on the path
sys.path.insert(0, str(Path(__file__).parent))

from openpace.database.connection import init_database, get_db_session
from openpace.database.models import Transmission, Observation


def _parse_hl7_datetime(s: str):
    if not s or not s.strip():
        return None
    s = s.strip()
    try:
        if len(s) >= 14:
            return datetime.strptime(s[:14], '%Y%m%d%H%M%S')
        if len(s) >= 8:
            return datetime.strptime(s[:8], '%Y%m%d')
    except ValueError:
        pass
    return None


def _resolve_from_hl7(obx_segment, obr_datetime, transmission_date):
    """Three-tier fallback — mirrors the fixed parser logic."""
    # 1. OBX-14
    try:
        if len(obx_segment) > 14:
            ts = _parse_hl7_datetime(str(obx_segment[14]))
            if ts:
                return ts, 'OBX-14'
    except Exception:
        pass
    # 2. OBR-7
    if obr_datetime:
        return obr_datetime, 'OBR-7'
    # 3. MSH-7
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
        if not tx.raw_hl7:
            print(f"  [TX {tx.transmission_id}] No raw_hl7 stored — skipping "
                  f"(re-import the file to get corrected timestamps).")
            continue

        # Parse the stored raw HL7
        raw = tx.raw_hl7.replace('\r\n', '\r').replace('\n', '\r')
        try:
            msg = hl7.parse(raw)
        except Exception as e:
            print(f"  [TX {tx.transmission_id}] Could not re-parse HL7: {e}")
            continue

        # Extract OBR-7 datetime
        obr_datetime = None
        try:
            obr = msg.segment('OBR')
            obr_datetime = _parse_hl7_datetime(str(obr[7])) if len(obr) > 7 else None
        except KeyError:
            pass

        # Index OBX segments by sequence number (OBX-1)
        obx_by_seq = {}
        for seg in msg.segments('OBX'):
            try:
                seq = int(str(seg[1]))
                obx_by_seq[seq] = seg
            except (ValueError, IndexError):
                pass

        # Identify the import wall-clock stamp for this transmission
        # Rows are "bad" when observation_time ≈ imported_at (within 60s)
        imported_at = tx.imported_at
        cutoff = timedelta(seconds=60)

        observations = session.query(Observation).filter_by(
            transmission_id=tx.transmission_id
        ).all()

        tx_updated = 0
        tx_skipped = 0

        for obs in observations:
            # Only touch rows that look like they got the wall-clock stamp
            if abs(obs.observation_time - imported_at) > cutoff:
                tx_skipped += 1
                continue

            seg = obx_by_seq.get(obs.sequence_number)
            if seg is None:
                tx_skipped += 1
                continue

            new_time, source = _resolve_from_hl7(seg, obr_datetime, tx.transmission_date)
            if new_time is None:
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

    print(f"\nMigration complete.")
    print(f"  Total rows updated : {total_updated}")
    print(f"  Total rows skipped : {total_skipped}")
    print()
    if total_updated == 0:
        print("NOTE: Zero rows updated.")
        print("  If the database stores raw_hl7 in the Transmission model, ensure the")
        print("  column is populated. If raw HL7 is not stored, re-import your files")
        print("  with the fixed parser.py to obtain correct timestamps.")


if __name__ == '__main__':
    migrate()
