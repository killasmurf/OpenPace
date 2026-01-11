# OpenPace Architecture

This document describes the system architecture of OpenPace, a pacemaker data analysis platform inspired by OSCAR.

## Overview

OpenPace follows a modular architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────┐
│              PyQt6 GUI Layer                        │
│  (Timeline View, Episode Viewer, Controls)          │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│           Analysis Engine                           │
│  (Battery, Impedance, Arrhythmia, EGM)             │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│         Processing Engine                           │
│  (Normalization, EGM Decoding, LOINC Mapping)      │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│            HL7 Parser Layer                         │
│  (MSH/PID/OBR/OBX + Vendor Translators)            │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│          Database Layer (SQLite)                    │
│  (Patients, Transmissions, Observations, Trends)    │
└─────────────────────────────────────────────────────┘
```

## Component Details

### 1. HL7 Parser Layer (`openpace/hl7/`)

**Responsibility**: Parse HL7 ORU^R01 messages and extract pacemaker data.

**Key Files**:
- `parser.py`: Main HL7 message parser
- `segments/`: MSH, PID, OBR, OBX segment parsers
- `translators/`: Vendor-specific code mappers

**Vendor Translators**:
- `medtronic.py`: Medtronic CareLink codes
- `boston_scientific.py`: LATITUDE codes
- `abbott.py`: Merlin.net codes
- `biotronik.py`: Home Monitoring codes

### 2. Processing Engine (`openpace/processing/`)

**Responsibility**: Normalize vendor-specific data to universal format.

**Key Files**:
- `normalizer.py`: Convert to standard schema
- `egm_decoder.py`: Decode base64 EGM blobs
- `histogram_parser.py`: Parse rate/activity histograms
- `loinc_mapper.py`: Map LOINC codes to variables

### 3. Analysis Engine (`openpace/analysis/`)

**Responsibility**: Perform clinical analysis on normalized data.

**Key Files**:
- `battery_analyzer.py`: Trend analysis, ERI prediction
- `impedance_analyzer.py`: Fracture/failure detection
- `arrhythmia_analyzer.py`: Burden calculation
- `egm_analyzer.py`: Waveform analysis, RR intervals
- `rate_response.py`: Pacing vs. activity correlation

### 4. GUI Layer (`openpace/gui/`)

**Responsibility**: Provide OSCAR-style user interface.

**Key Files**:
- `main_window.py`: Application main window
- `timeline_view.py`: Macro view (months/years)
- `episode_viewer.py`: Micro view (EGM strips)
- `patient_selector.py`: Patient/date selection
- `widgets/`: Custom plot widgets

### 5. Database Layer (`openpace/database/`)

**Responsibility**: Persist data in SQLite database.

**Key Files**:
- `models.py`: SQLAlchemy ORM models
- `connection.py`: Database connection management
- `migrations/`: Schema version control (Alembic)

## Data Flow

1. **Import**: User selects HL7 file
2. **Parse**: HL7 parser extracts segments (MSH→PID→OBR→OBX)
3. **Translate**: Vendor translator maps codes to universal variables
4. **Normalize**: Processing engine standardizes data
5. **Store**: Database layer persists observations
6. **Analyze**: Analysis engine computes trends/events
7. **Visualize**: GUI renders timeline and EGM views
8. **Export**: Reports generated with anonymization option

## Key Design Patterns

- **Factory Pattern**: Vendor translator selection
- **Strategy Pattern**: Different EGM decoding strategies per vendor
- **Observer Pattern**: GUI updates on data changes
- **Repository Pattern**: Database access abstraction

## Privacy Architecture

- **Anonymization Manager**: Strips PII before display/export
- **Encryption Support**: Optional database encryption
- **Local-Only**: No network communication
- **Audit Trail**: Track data access (future)

## Performance Considerations

- **Lazy Loading**: Load EGM blobs on-demand
- **Pre-computed Trends**: Cache longitudinal calculations
- **PyQtGraph**: High-performance plotting for large datasets
- **Indexed Database**: Optimize queries on timestamp columns

## Testing Strategy

- **Unit Tests**: Each module independently tested
- **Integration Tests**: HL7 parsing → database → analysis
- **Sample Data**: Vendor-specific test messages
- **GUI Tests**: pytest-qt for UI components

See implementation roadmap in [README.md](../README.md).
