# OpenPace

**Pacemaker Data Analysis & Visualization Platform**

OpenPace is a desktop application for analyzing and displaying interactive graphs of pacemaker data, inspired by the OSCAR CPAP analysis tool. It provides comprehensive time-series visualization, event detection, statistical analysis, and comparison capabilities for cardiac device data.

## Overview

OpenPace processes HL7 ORU^R01 messages from pacemaker remote monitoring systems and in-clinic interrogations, providing clinicians and researchers with powerful tools to:

- Visualize longitudinal trends (battery depletion, lead impedance)
- Analyze discrete episodic events (arrhythmias, mode switches)
- Review high-resolution EGM (Electrogram) strips
- Compare sessions across time
- Generate clinical reports

## Key Features

### Data Processing
- **HL7 ORU^R01 Parser**: Extracts data from MSH, PID, OBR, and OBX segments
- **Multi-Vendor Support**: Translators for Medtronic, Boston Scientific, Abbott, Biotronik
- **LOINC Mapping**: Standardizes observations to universal variables
- **EGM Decoding**: Processes base64-encoded electrogram waveforms

### Visualization (OSCAR-Style)
- **Timeline View (Macro)**: Years of trends at a glance
  - Battery voltage trends with ERI prediction
  - Lead impedance monitoring with fracture detection
  - Arrhythmia burden (daily/weekly percentages)
  - Pacing percentage vs. activity level overlay

- **Episode Viewer (Micro)**: Millisecond-resolution EGM strips
  - Interactive waveform display
  - RR interval calculation and HR derivation
  - Measurement tools (calipers)
  - Event annotations

### Analysis Engine
- **Longitudinal Trend Analysis**: Battery depletion rates, ERI date prediction
- **Lead Monitoring**: Fracture detection (sudden impedance spikes), insulation failure (drops)
- **Arrhythmia Analysis**: AFib/AFL burden calculation, episode frequency
- **Rate Response Assessment**: Pacing percentage vs. activity correlation

### Privacy & Security
- **Anonymization Toggle**: OSCAR-style "Public Mode" for sharing screenshots
- **Local-Only Storage**: SQLite database, no cloud transmission
- **PII Stripping**: Removes names, DOB, MRN before export
- **Educational Use Focus**: Designed for learning and non-clinical research

## Technology Stack

- **Language**: Python 3.11+
- **GUI Framework**: PyQt6
- **HL7 Processing**: python-hl7, hl7apy
- **Data Analysis**: pandas, numpy, scipy
- **Visualization**: pyqtgraph (high-performance), matplotlib
- **Database**: SQLite with SQLAlchemy ORM
- **Signal Processing**: scipy (EGM filtering and analysis)

## Project Structure

```
OpenPace/
├── openpace/               # Main application package
│   ├── gui/               # PyQt6 user interface
│   ├── hl7/               # HL7 parsing and vendor translators
│   ├── processing/        # Data normalization and EGM decoding
│   ├── analysis/          # Analysis algorithms
│   ├── database/          # SQLAlchemy models and migrations
│   ├── export/            # Report generation and data export
│   ├── privacy/           # Anonymization and encryption
│   └── utils/             # Utilities and configuration
├── tests/                 # Unit tests and sample data
├── docs/                  # Documentation
└── resources/             # Icons, stylesheets, samples
```

## Data Sources

OpenPace supports HL7 ORU^R01 messages from:

- **Remote Monitoring Systems**
  - Medtronic CareLink
  - Boston Scientific LATITUDE
  - Abbott Merlin.net
  - Biotronik Home Monitoring

- **In-Clinic Interrogation Devices**
  - Programmer exports in HL7 format

## Key Observations Supported

| Feature | HL7 Source | Analysis |
|---------|-----------|----------|
| Battery Status | OBX (Voltage/ERI) | Trend battery depletion over years |
| Lead Impedance | OBX (Ohms) | Monitor for fractures or insulation failure |
| Arrhythmia Burden | OBX (AFib/AFL %) | Calculate daily/weekly burden percentages |
| EGM Strips | OBX-5 (Encapsulated Data) | Render visual waveforms of cardiac episodes |
| Pacing Histograms | OBX (Rate distributions) | Analyze pacing burden and rate response |

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/OpenPace.git
cd OpenPace

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## Development Status

**Current Phase**: Foundation & Core HL7 Ingestion

- [x] Project structure initialized
- [x] Git repository created
- [ ] Database schema implementation
- [ ] Basic HL7 parser
- [ ] Medtronic translator
- [ ] PyQt6 main window
- [ ] Timeline view
- [ ] Battery trend visualization

See [docs/architecture.md](docs/architecture.md) for detailed implementation roadmap.

## Use Case

**Target Audience**: Educational/personal use, suitable for:
- Learning about pacemaker data analysis
- Research projects requiring device data visualization
- Understanding cardiac device programming and performance
- Developing analysis algorithms for cardiac rhythms

**Not Intended For**: Clinical decision-making or patient care without appropriate validation and regulatory approval.

## Privacy Notice

OpenPace is designed with privacy in mind:
- All data stays local on your machine
- Anonymization features for sharing screenshots
- No telemetry or external data transmission
- Compliant with best practices for handling medical device data

**Important**: When working with real patient data, always follow your institution's data governance policies and applicable regulations (HIPAA, GDPR, etc.).

## Contributing

This is an educational project. Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT License](LICENSE) - See LICENSE file for details.

## Acknowledgments

Inspired by [OSCAR](https://www.sleepfiles.com/OSCAR/) - the incredible CPAP data analysis tool that empowers patients and clinicians worldwide.

## Contact

For questions, issues, or collaboration opportunities, please open an issue on GitHub.

---

**Disclaimer**: OpenPace is an educational tool and is not intended for clinical use. Always consult qualified healthcare professionals for medical device programming and patient care decisions.
