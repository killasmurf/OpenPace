#!/usr/bin/env python3
"""Test Boston Scientific settings display."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from openpace.database.connection import init_database, get_db_session
from openpace.hl7.parser import HL7Parser

# Initialize database
init_database(':memory:', echo=False)
session = get_db_session()

# Load and parse Boston Scientific file
data_file = Path('tests/sample_data/csc.1002050604.1.dat')
print(f"Loading: {data_file}")
print()

with open(data_file, 'r', encoding='utf-8', errors='ignore') as f:
    hl7_content = f.read()

parser = HL7Parser(session, anonymize=False)
transmission = parser.parse_message(hl7_content, filename=str(data_file))

# Extract ALL observations into settings data format
settings_data = {}
for obs in transmission.observations:
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

    settings_data[var_name] = {
        'value': obs.value_numeric if obs.value_numeric is not None else obs.value_text,
        'value_str': value_str,
        'unit': obs.unit,
        'vendor_code': obs.vendor_code
    }

print(f"Total observations extracted: {len(settings_data)}")
print()

# Show first 50 observations
print("First 50 observations:")
for i, (var_name, info) in enumerate(sorted(settings_data.items())):
    if i >= 50:
        break
    print(f"  {var_name}: {info['value_str']}")

print()
print(f"... and {max(0, len(settings_data) - 50)} more observations")
