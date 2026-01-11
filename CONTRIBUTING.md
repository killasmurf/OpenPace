# Contributing to OpenPace

Thank you for your interest in contributing to OpenPace! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/OpenPace.git`
3. Create a virtual environment: `python -m venv venv`
4. Activate the virtual environment:
   - Linux/Mac: `source venv/bin/activate`
   - Windows: `venv\Scripts\activate`
5. Install dependencies: `pip install -r requirements.txt`

## Development Workflow

1. Create a new branch for your feature: `git checkout -b feature/your-feature-name`
2. Make your changes
3. Run tests: `pytest tests/`
4. Format code: `black openpace/ tests/`
5. Check code quality: `flake8 openpace/ tests/`
6. Commit your changes: `git commit -m "Description of changes"`
7. Push to your fork: `git push origin feature/your-feature-name`
8. Create a Pull Request

## Code Style

- Follow PEP 8 guidelines
- Use `black` for code formatting (line length: 100)
- Use type hints where possible
- Write docstrings for all public functions and classes
- Keep functions focused and modular

## Testing

- Write unit tests for new functionality
- Ensure all tests pass before submitting PR
- Aim for good test coverage (use `pytest-cov`)
- Place test files in `tests/` directory mirroring the source structure

## Documentation

- Update README.md if adding new features
- Add docstrings to new functions/classes
- Update relevant documentation in `docs/`

## Privacy & Security

- Never commit real patient data
- Ensure sample data is fully anonymized
- Follow best practices for handling medical device data
- Report security issues privately to maintainers

## Areas for Contribution

- **HL7 Parsers**: Additional vendor translators
- **Analysis Algorithms**: New detection algorithms, statistical methods
- **Visualization**: Enhanced charts, new view types
- **Testing**: Expand test coverage, create sample datasets
- **Documentation**: User guides, tutorials, API docs
- **Performance**: Optimization for large datasets

## Questions?

Open an issue with the `question` label or reach out to maintainers.

Thank you for contributing to OpenPace!
