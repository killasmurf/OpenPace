#!/usr/bin/env python3
"""
Test runner script for OpenPace.

This script provides convenient commands for running tests with different
configurations and generating coverage reports.

Usage:
    python run_tests.py [options]

Options:
    --all           Run all tests
    --unit          Run only unit tests
    --integration   Run only integration tests
    --database      Run only database tests
    --gui           Run only GUI tests
    --hl7           Run only HL7 parser tests
    --smoke         Run only smoke tests
    --coverage      Generate coverage report (HTML)
    --no-cov        Run tests without coverage
    --verbose       Verbose output
    --markers       List all available test markers
    --failed        Re-run only failed tests from last run
"""

import sys
import subprocess
from pathlib import Path


def run_command(cmd):
    """Execute a shell command and return the result."""
    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    return result.returncode


def main():
    """Main test runner function."""
    args = sys.argv[1:]

    # Base pytest command
    base_cmd = ["pytest"]

    # Handle special commands
    if "--markers" in args:
        return run_command(base_cmd + ["--markers"])

    if "--failed" in args:
        return run_command(base_cmd + ["--lf"])

    # Build command based on arguments
    if "--all" in args or len(args) == 0:
        cmd = base_cmd + ["tests/"]
    elif "--unit" in args:
        cmd = base_cmd + ["-m", "unit", "tests/"]
    elif "--integration" in args:
        cmd = base_cmd + ["-m", "integration", "tests/"]
    elif "--database" in args:
        cmd = base_cmd + ["tests/test_database/"]
    elif "--gui" in args:
        cmd = base_cmd + ["tests/test_gui/"]
    elif "--hl7" in args:
        cmd = base_cmd + ["tests/test_hl7/"]
    elif "--smoke" in args:
        cmd = base_cmd + ["-m", "smoke", "tests/"]
    else:
        # Default to all tests
        cmd = base_cmd + ["tests/"]

    # Add coverage options
    if "--no-cov" in args:
        cmd.append("--no-cov")
    elif "--coverage" in args:
        cmd.extend(["--cov=openpace", "--cov-report=html", "--cov-report=term"])

    # Add verbosity
    if "--verbose" in args:
        cmd.append("-vv")

    return run_command(cmd)


if __name__ == "__main__":
    sys.exit(main())
