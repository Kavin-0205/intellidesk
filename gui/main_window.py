"""
IntelliDesk Main Window.
Coordinates sidebar navigation, stacked pages, and cross-component signal wiring.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QLabel, QListWidget, QListWidgetItem, QStatusBar, QFrame
)
from PySide6.QtGui import QFont

from gui.dashboard import DashboardPage
from gui.voice_page import VoiceAssistantPage
from gui.chat import ChatPage
from gui.screen_page import ScreenReaderPage
from gui.code_page import CodingAssistantPage
from gui.files_page import FileManagerPage
from gui.history_page import HistoryPage
from gui.settings import SettingsPage


class MainWindow(QMainWindow):
    """Primary application window for IntelliDesk."""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("IntelliDesk — AI Desktop Assistant")
        self.resize(1360, 820)
        self.setMinimumSize(1024, 680)

        # ── Central Widget & Layout ──────────────────────────
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Sidebar ──────────────────────────────────────────
        sidebar_frame = QWidget()
        sidebar_frame.setObjectName("sidebar")
        sidebar_frame.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(sidebar_frame)
        sidebar_layout.setContentsMargins(14, 20, 14, 16)
        sidebar_layout.setSpacing(12)

        # App Brand Title
        brand_row = QHBoxLayout()
        brand_icon = QLabel("⚡")
        brand_icon.setStyleSheet("font-size: 24px;")
        brand_title = QLabel("IntelliDesk")
        brand_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #58A6FF;")
        brand_row.addWidget(brand_icon)
        brand_row.addWidget(brand_title)
        brand_row.addStretch()
        sidebar_layout.addLayout(brand_row)

        subtitle = QLabel("AI Desktop Assistant")
        subtitle.setStyleSheet("color: #8B949E; font-size: 11px; margin-left: 2px;")
        sidebar_layout.addWidget(subtitle)

        # Divider
        div = QFrame()
        div.setObjectName("divider")
        div.setFrameShape(QFrame.HLine)
        sidebar_layout.addWidget(div)

        # Sidebar List
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebarList")
        self.sidebar.setFont(QFont("Segoe UI", 11))
        self.sidebar.setSpacing(4)
        self.sidebar.setStyleSheet("""
            QListWidget#sidebarList {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget#sidebarList::item {
                padding: 11px 14px;
                border-radius: 8px;
                color: #8B949E;
                font-weight: 500;
            }
            QListWidget#sidebarList::item:hover {
                background: #21262D;
                color: #E6EDF3;
            }
            QListWidget#sidebarList::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1F6FEB, stop:1 #388BFD);
                color: white;
                font-weight: bold;
            }
        """)

        nav_items = [
            ("🖥  Dashboard", "Live system stats and AI health"),
            ("🎙  Voice Assistant", "Voice control with real-time mic"),
            ("🤖  AI Chat", "Natural language text chat with Groq"),
            ("📄  Screen Reader", "Screen OCR & AI error analysis"),
            ("💻  Coding Assistant", "Code explanation, debugging & Git"),
            ("📁  File Manager", "Workspace file exploration"),
            ("📋  History & Memory", "Recent commands, Q&A and top apps"),
            ("⚙  Settings", "API keys, DB, voice and diagnostics"),
        ]

        for text, tooltip in nav_items:
            item = QListWidgetItem(text)
            item.setToolTip(tooltip)
            self.sidebar.addItem(item)

        sidebar_layout.addWidget(self.sidebar, stretch=1)

        # Bottom status pill
        status_pill = QFrame()
        status_pill.setStyleSheet("""
            background: #21262D;
            border-radius: 8px;
            padding: 8px 12px;
        """)
        pill_layout = QHBoxLayout(status_pill)
        pill_layout.setContentsMargins(6, 4, 6, 4)
        pill_dot = QLabel("🟢")
        pill_dot.setStyleSheet("font-size: 10px;")
        pill_text = QLabel("System Online")
        pill_text.setStyleSheet("color: #E6EDF3; font-size: 11px; font-weight: bold;")
        pill_layout.addWidget(pill_dot)
        pill_layout.addWidget(pill_text)
        pill_layout.addStretch()
        sidebar_layout.addWidget(status_pill)

        main_layout.addWidget(sidebar_frame)

        # ── Stacked Pages ────────────────────────────────────
        self.pages = QStackedWidget()

        self.dashboard_page = DashboardPage()
        self.voice_page     = VoiceAssistantPage()
        self.chat_page      = ChatPage()
        self.screen_page    = ScreenReaderPage()
        self.code_page      = CodingAssistantPage()
        self.files_page     = FileManagerPage()
        self.history_page   = HistoryPage()
        self.settings_page  = SettingsPage()

        self.pages.addWidget(self.dashboard_page)   # Index 0
        self.pages.addWidget(self.voice_page)       # Index 1
        self.pages.addWidget(self.chat_page)        # Index 2
        self.pages.addWidget(self.screen_page)      # Index 3
        self.pages.addWidget(self.code_page)        # Index 4
        self.pages.addWidget(self.files_page)       # Index 5
        self.pages.addWidget(self.history_page)     # Index 6
        self.pages.addWidget(self.settings_page)    # Index 7

        main_layout.addWidget(self.pages, stretch=1)

        # ── Cross-Page Wiring ────────────────────────────────
        self.sidebar.currentRowChanged.connect(self.pages.setCurrentIndex)

        # When voice command completes, update Dashboard and History
        self.voice_page.command_completed.connect(self._on_command_completed)

        # Start on Voice Assistant or Dashboard (Dashboard as default 0)
        self.sidebar.setCurrentRow(0)

        # ── Status Bar ───────────────────────────────────────
        self.status = QStatusBar()
        self.status.setStyleSheet("""
            QStatusBar {
                background-color: #161B22;
                color: #8B949E;
                border-top: 1px solid #30363D;
                font-size: 11px;
                padding: 4px 12px;
            }
        """)
        self.status.showMessage("IntelliDesk Active — Ready for voice or text commands")
        self.setStatusBar(self.status)

    def _on_command_completed(self, is_qa: bool):
        if is_qa:
            self.dashboard_page.increment_qa()
        else:
            self.dashboard_page.increment_command()
        # Refresh history
        self.history_page.refresh()