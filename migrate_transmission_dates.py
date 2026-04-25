"""
Migration: Backfill Transmission.transmission_date from OBR-7
=============================================================

Transmissions imported before the parse_message fix had transmission_date
set from MSH-7. For some vendors (notably Boston Scientific LATITUDE) MSH-7
contains the export wall-clock — identical across every file in a single
export batch — rather than the actual transmission datetime. The actual
transmission datetime lives in OBR-7.

This script re-reads the original HL7 file for each transmission and, when
OBR-7 differs from the currently stored transmission_date, updates the row
to the OBR-7 value. The hl7_filename column (added in an earlier fix) tells
us where to find the original message.

Run once after deploying the fixed parser.py:

    python migrate_transmission_dates.py

Safe to re-run — only rows where OBR-7 differs from the current value are
touched. Transmissions with no stored hl7_filename are skipped (re-import
the original HL7 file to get a correct date).

After updating transmission dates, cached LongitudinalTrend records are
deleted so the timeline view recomputes them on next patient load (this
matters because the freshness check in load_patient_data compares trend
computed_at to Transmission.imported_at, not transmission_date — so cached
trends are NOT automatically invalidated by this migration).
"""

import sys
from datetime import datetime
from pathlib import Path

# Make sure the project root is on the path
sys.path.insert(0, str(Path(__file__).parent))

import hl7
from openpace.database.connection import get_session
from openpace.database.models import Transmission, LongitudinalTrend
from openpace.hl7.parser import HL7Parser


def main():
    session = get_session()
    parser = HL7Parser(session)

    transmissions = session.query(Transmission).all()
    print(f"Inspecting {len(transmissions)} transmissions...\n")

    updated = 0
    skipped_no_file = 0
    skipped_missing_obr = 0
    skipped_no_obr_date = 0
    failed = 0
    affected_patients: set = set()

    for tx in transmissions:
        if not tx.hl7_filename:
            skipped_no_file += 1
            continue

        path = Path(tx.hl7_filename)
        if not path.exists():
            skipped_no_file += 1
            continue

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                raw = fh.read()
            # Normalise line endings the same way HL7Parser does
            msg = hl7.parse(raw.replace("\n", "\r"))

            try:
                obr_segment = msg.segment("OBR")
            except KeyError:
                skipped_missing_obr += 1
                continue

            obr_dt_str = str(obr_segment[7]) if len(obr_segment) > 7 else ""
            new_date = parser._parse_hl7_datetime(obr_dt_str) if obr_dt_str else None

            if new_date is None:
                skipped_no_obr_date += 1
                continue

            if new_date == tx.transmission_date:
                continue  # already correct

            print(
                f"  tx_id={tx.transmission_id} ({path.name}): "
                f"{tx.transmission_date} -> {new_date}"
            )
            tx.transmission_date = new_date
            updated += 1
            affected_patients.add(tx.patient_id)
        except Exception as exc:
            failed += 1
            print(f"  [FAIL] tx_id={tx.transmission_id}: {type(exc).__name__}: {exc}")

    if updated:
        # Invalidate cached trends for affected patients so next patient load
        # recomputes them (load_patient_data uses imported_at not transmission_date
        # for staleness, so we must invalidate manually here).
        deleted = (
            session.query(LongitudinalTrend)
            .filter(LongitudinalTrend.patient_id.in_(affected_patients))
            .delete(synchronize_session=False)
        )
        session.commit()
        print(f"\nInvalidated {deleted} cached trend rows for "
              f"{len(affected_patients)} patient(s).")
    else:
        session.rollback()

    print()
    print(f"Updated:                  {updated}")
    print(f"Already correct:          {len(transmissions) - updated - skipped_no_file - skipped_missing_obr - skipped_no_obr_date - failed}")
    print(f"Skipped (no file/path):   {skipped_no_file}")
    print(f"Skipped (no OBR segment): {skipped_missing_obr}")
    print(f"Skipped (no OBR-7 date):  {skipped_no_obr_date}")
    print(f"Failed:                   {failed}")


if __name__ == "__main__":
    main()
