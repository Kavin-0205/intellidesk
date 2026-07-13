from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QGridLayout
)

from PySide6.QtCore import Qt, QTimer
import psutil
from datetime import datetime

from gui.cards import DashboardCard


class DashboardPage(QWidget):

    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout(self)

        # Welcome Label
        welcome = QLabel("Welcome to IntelliDesk 👋")
        welcome.setAlignment(Qt.AlignCenter)
        welcome.setStyleSheet("""
            font-size:24px;
            font-weight:bold;
        """)

        main_layout.addWidget(welcome)

        # Grid Layout
        grid = QGridLayout()

        # Dashboard Cards
        self.cpu_card = DashboardCard("CPU Usage", "0%")
        self.ram_card = DashboardCard("RAM Usage", "0%")
        self.ai_card = DashboardCard("AI Status", "Offline")
        self.time_card = DashboardCard("Time", "--:--")

        grid.addWidget(self.cpu_card, 0, 0)
        grid.addWidget(self.ram_card, 0, 1)
        grid.addWidget(self.ai_card, 1, 0)
        grid.addWidget(self.time_card, 1, 1)

        main_layout.addLayout(grid)

        # Live Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_dashboard)
        self.timer.start(1000)

        self.update_dashboard()

    def update_dashboard(self):

        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        current_time = datetime.now().strftime("%I:%M:%S %p")

        self.cpu_card.update_value(f"{cpu}%")
        self.ram_card.update_value(f"{ram}%")
        self.ai_card.update_value("🟢 Ready")
        self.time_card.update_value(current_time)