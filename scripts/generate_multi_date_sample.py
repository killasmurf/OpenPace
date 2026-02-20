#!/usr/bin/env python3
"""
Generate Multi-Date HL7 Sample Data

Creates an HL7 file with multiple transmission records across different dates,
useful for testing trend analysis and time-series visualization in OpenPace.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path


def format_hl7_timestamp(dt: datetime) -> str:
    """Format datetime as HL7 timestamp (YYYYMMDDHHMMSS)"""
    return dt.strftime("%Y%m%d%H%M%S")


def generate_transmission(transmission_num: int, base_date: datetime, days_offset: int) -> str:
    """
    Generate a single HL7 transmission with realistic parameter variation.

    Args:
        transmission_num: Sequential transmission number
        base_date: Starting date for transmissions
        days_offset: Number of days to offset from base_date

    Returns:
        HL7 message string
    """
    trans_date = base_date + timedelta(days=days_offset)
    timestamp = format_hl7_timestamp(trans_date)
    msg_id = f"MSG{transmission_num:05d}"

    # Simulate realistic parameter variation over time
    # Battery voltage decreases slowly over time
    battery = 2.80 - (days_offset * 0.001)

    # Impedances vary slightly
    atrial_imp = 625 + (days_offset % 50) - 25
    vent_imp = 485 + (days_offset % 40) - 20

    # AFib burden varies
    afib = max(0, min(100, 12.5 + (days_offset % 30) - 15))

    # Pacing percentages vary
    atrial_pace = max(0, min(100, 45 + (days_offset % 20) - 10))
    vent_pace = max(0, min(100, 78 + (days_offset % 15) - 7))

    # Heart rate parameters
    hr_avg = 72 + (days_offset % 10) - 5
    hr_max = 130 + (days_offset % 15) - 7
    hr_min = 58 + (days_offset % 8) - 4

    hl7_message = f"""MSH|^~\\&|Medtronic CareLink|Clinic123|OpenPace|Hospital||{timestamp}||ORU^R01|{msg_id}|P|2.5
PID|1||P123456^^^Clinic123||Doe^John||19800101|M|||123 Main St^^Anytown^CA^12345
OBR|1|||REMOTE_MONITOR|||{timestamp}
OBX|1|NM|73990-7^Battery Voltage^LN||{battery:.2f}|V|2.2-2.8|N|||F
OBX|2|NM|8889-8^Lead Impedance Atrial^LN||{atrial_imp}|Ohm|200-1500|N|||F
OBX|3|NM|8890-6^Lead Impedance Ventricular^LN||{vent_imp}|Ohm|200-1500|N|||F
OBX|4|NM|89269-2^AFib Burden^LN||{afib:.1f}|%|0-100|{"H" if afib > 20 else "N"}|||F
OBX|5|NM|MDC_PACE_PCT_A^Atrial Pacing Percent^MDC||{atrial_pace:.1f}|%|0-100|N|||F
OBX|6|NM|MDC_PACE_PCT_V^Ventricular Pacing Percent^MDC||{vent_pace:.1f}|%|0-100|N|||F
OBX|7|NM|8867-4^Heart Rate^LN||{hr_avg}|bpm|60-100|N|||F
OBX|8|NM|MDC_HR_MAX^Maximum Heart Rate^MDC||{hr_max}|bpm|||N|||F
OBX|9|NM|MDC_HR_MIN^Minimum Heart Rate^MDC||{hr_min}|bpm|||N|||F
OBX|10|ST|MDC_MODE^Pacing Mode^MDC||DDDR||||F
OBX|11|NM|MDC_RATE_LOWER^Lower Rate Limit^MDC||60|bpm|||N|||F
OBX|12|NM|MDC_RATE_UPPER^Upper Rate Limit^MDC||130|bpm|||N|||F
"""
    return hl7_message


def main():
    """Generate multi-date HL7 sample file"""
    # Configuration
    num_transmissions = 12  # One per month for a year
    days_between = 30       # Roughly monthly
    start_date = datetime(2024, 1, 15, 12, 0, 0)  # Jan 15, 2024 at noon

    # Output file
    output_file = Path(__file__).parent.parent / "tests" / "sample_data" / "multi_date_sample.hl7"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"Generating {num_transmissions} transmissions...")
    print(f"Date range: {start_date.strftime('%Y-%m-%d')} to "
          f"{(start_date + timedelta(days=days_between * (num_transmissions - 1))).strftime('%Y-%m-%d')}")
    print(f"Output file: {output_file}")
    print()

    # Generate transmissions
    with open(output_file, 'w') as f:
        for i in range(num_transmissions):
            transmission = generate_transmission(i + 1, start_date, i * days_between)
            f.write(transmission)

            # Add separator between transmissions (empty line)
            if i < num_transmissions - 1:
                f.write("\n")

            # Progress feedback
            trans_date = start_date + timedelta(days=i * days_between)
            print(f"  [{i+1:2d}/{num_transmissions}] {trans_date.strftime('%Y-%m-%d %H:%M:%S')}")

    print()
    print(f"✓ Successfully generated {output_file}")
    print()
    print("To import this file into OpenPace:")
    print("  1. Start OpenPace")
    print("  2. Click 'Import Data'")
    print(f"  3. Select: {output_file}")
    print()
    print("This file contains 12 monthly transmissions with realistic")
    print("parameter variations, perfect for testing trend analysis!")


if __name__ == "__main__":
    main()
