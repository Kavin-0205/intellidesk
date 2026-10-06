"""
IntelliDesk Application Entry Point.
Launches the PySide6 Desktop GUI with Dark Theme styling.
"""

import sys
from PySide6.QtWidgets import QApplication
from gui.styles import DARK_THEME
from gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("IntelliDesk")
    app.setStyleSheet(DARK_THEME)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()