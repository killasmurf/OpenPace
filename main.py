#!/usr/bin/env python3
"""
OpenPace - Pacemaker Data Analysis & Visualization Platform

Main entry point for the application.
"""

import sys
from PyQt6.QtWidgets import QApplication
from openpace.gui.main_window import MainWindow


def main():
    """
    Initialize and run the OpenPace application.
    """
    app = QApplication(sys.argv)
    app.setApplicationName("OpenPace")
    app.setOrganizationName("OpenPace")
    app.setApplicationVersion("0.1.0")

    # Create and show main window
    window = MainWindow()
    window.show()

    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
