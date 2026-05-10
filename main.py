"""
Swiss Chess Tournament Manager
Entry point
"""
import os
import sys

# PyInstaller path fix
if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
    if bundle_dir not in sys.path:
        sys.path.append(bundle_dir)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Elite Chess Tournament Manager")
    app.setOrganizationName("Elite Chess")
    app.setApplicationVersion("1.0.0")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
