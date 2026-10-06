"""
IntelliDesk Premium Dashboard Page.
Shows live CPU, RAM, disk, and AI status cards, updated every second.
"""

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame
)
from PySide6.QtCore import Qt, QTimer
import psutil
from datetime import datetime

from gui.cards import DashboardCard


def _divider():
    d = QFrame()
    d.setObjectName("divider")
    d.setFrameShape(QFrame.HLine)
    return d


class DashboardPage(QWidget):

    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(20)

        # ── Header ──────────────────────────────────────────
        header = QLabel("🖥  Dashboard")
        header.setObjectName("pageHeader")
        subtitle = QLabel("Live system metrics and AI status")
        subtitle.setObjectName("pageSubtitle")
        root.addWidget(header)
        root.addWidget(subtitle)
        root.addWidget(_divider())

        # ── Metric Cards ─────────────────────────────────────
        grid = QGridLayout()
        grid.setSpacing(16)

        self.cpu_card  = DashboardCard("⚡", "CPU Usage",  "0%",  show_bar=True)
        self.ram_card  = DashboardCard("🧠", "RAM Usage",  "0%",  show_bar=True)
        self.disk_card = DashboardCard("💾", "Disk Usage", "0%",  show_bar=True)
        self.time_card = DashboardCard("🕐", "Current Time", "--:--")
        self.ai_card   = DashboardCard("🤖", "AI Status",  "Loading…")
        self.voice_card = DashboardCard("🎙", "Voice Engine", "Ready")

        grid.addWidget(self.cpu_card,   0, 0)
        grid.addWidget(self.ram_card,   0, 1)
        grid.addWidget(self.disk_card,  0, 2)
        grid.addWidget(self.time_card,  1, 0)
        grid.addWidget(self.ai_card,    1, 1)
        grid.addWidget(self.voice_card, 1, 2)

        root.addLayout(grid)

        # ── Session Stats ────────────────────────────────────
        stats_frame = QFrame()
        stats_frame.setObjectName("sectionCard")
        stats_layout = QVBoxLayout(stats_frame)
        stats_layout.setSpacing(8)

        stats_hdr = QLabel("📊  Session Stats")
        stats_hdr.setStyleSheet("font-size:15px; font-weight:bold; color:#E6EDF3;")
        stats_layout.addWidget(stats_hdr)

        self.session_lbl = QLabel("Commands this session: 0  |  Questions answered: 0")
        self.session_lbl.setStyleSheet("color:#8B949E; font-size:12px;")
        stats_layout.addWidget(self.session_lbl)

        root.addWidget(stats_frame)
        root.addStretch()

        # ── Timer ────────────────────────────────────────────
        self._cmd_count = 0
        self._qa_count = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self._update)
        self.timer.start(1000)
        self._update()

        # Check AI status asynchronously
        QTimer.singleShot(500, self._check_ai_status)

    def _update(self):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
        now = datetime.now().strftime("%I:%M:%S %p")
        date = datetime.now().strftime("%b %d, %Y")

        self.cpu_card.update_value(f"{cpu:.0f}%", int(cpu))
        self.ram_card.update_value(f"{ram:.0f}%", int(ram))
        self.disk_card.update_value(f"{disk:.0f}%", int(disk))
        self.time_card.update_value(now, subtitle=date)

    def _check_ai_status(self):
        try:
            import os
            api_key = os.getenv("GROQ_API_KEY", "")
            if api_key and len(api_key) > 10:
                self.ai_card.update_value("🟢 Online")
            else:
                self.ai_card.update_value("🔴 No API Key")
        except Exception:
            self.ai_card.update_value("⚠ Unknown")

    def increment_command(self):
        self._cmd_count += 1
        self._refresh_session()

    def increment_qa(self):
        self._qa_count += 1
        self._refresh_session()

    def _refresh_session(self):
        self.session_lbl.setText(
            f"Commands this session: {self._cmd_count}  |  "
            f"Questions answered: {self._qa_count}"
        )