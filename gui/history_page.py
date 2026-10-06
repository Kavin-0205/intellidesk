"""
IntelliDesk History Page.
Shows recent command and Q&A history with timestamps.
"""

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QFrame, QTabWidget
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
import json
from pathlib import Path
from datetime import datetime


def _divider():
    d = QFrame()
    d.setObjectName("divider")
    d.setFrameShape(QFrame.HLine)
    return d


class HistoryPage(QWidget):

    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        # ── Header ──────────────────────────────────────────
        hdr = QLabel("📋  Command History")
        hdr.setObjectName("pageHeader")
        sub = QLabel("Recent voice commands and Q&A pairs from this session")
        sub.setObjectName("pageSubtitle")
        root.addWidget(hdr)
        root.addWidget(sub)
        root.addWidget(_divider())

        # ── Tabs ─────────────────────────────────────────────
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                background: #161B22;
                border: 1px solid #30363D;
                border-radius: 12px;
            }
            QTabBar::tab {
                background: #21262D;
                color: #8B949E;
                padding: 8px 20px;
                border-radius: 8px;
                margin-right: 4px;
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background: #1F6FEB;
                color: white;
            }
        """)

        # Commands tab
        self.cmd_list = QListWidget()
        self.cmd_list.setFont(QFont("Segoe UI", 12))
        tabs.addTab(self.cmd_list, "🎙 Commands")

        # Q&A tab
        self.qa_list = QListWidget()
        self.qa_list.setFont(QFont("Segoe UI", 12))
        tabs.addTab(self.qa_list, "💬 Q&A")

        # Top Apps tab
        self.apps_list = QListWidget()
        self.apps_list.setFont(QFont("Segoe UI", 12))
        tabs.addTab(self.apps_list, "📊 Top Apps")

        root.addWidget(tabs, stretch=1)

        # ── Refresh button row ──────────────────────────────
        from PySide6.QtWidgets import QPushButton
        refresh_btn = QPushButton("↻  Refresh")
        refresh_btn.setFixedWidth(120)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #21262D;
                color: #8B949E;
                border: 1px solid #30363D;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover { background: #1F6FEB; color: white; }
        """)
        refresh_btn.clicked.connect(self.refresh)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(refresh_btn)
        root.addLayout(btn_row)

        # Initial placeholders
        self._add_placeholder(self.cmd_list, "Loading command history...")
        self._add_placeholder(self.qa_list, "Loading Q&A history...")
        self._add_placeholder(self.apps_list, "Loading top apps...")

        # Defer initial load so window opens immediately
        QTimer.singleShot(200, self.refresh)
        # Auto-refresh every 30 seconds
        t = QTimer(self)
        t.timeout.connect(self.refresh)
        t.start(30_000)

    def refresh(self):
        """Fetch history in background thread so the GUI never freezes."""
        import threading

        def worker():
            cmd_data = []
            qa_data = []
            app_data = []
            try:
                from memory.conversation_memory import get_recent_commands
                cmd_data = get_recent_commands(limit=30)
            except Exception as e:
                print(f"[HistoryPage] Error fetching commands: {e}")
            try:
                from memory.conversation_memory import get_recent_qa
                qa_data = get_recent_qa(limit=20)
            except Exception as e:
                print(f"[HistoryPage] Error fetching QA: {e}")
            try:
                from memory.app_history import get_top_apps_combined
                app_data = get_top_apps_combined(limit=10)
            except Exception as e:
                print(f"[HistoryPage] Error fetching apps: {e}")

            QTimer.singleShot(0, lambda: self._apply_data(cmd_data, qa_data, app_data))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_data(self, commands, qa_pairs, top_apps):
        self._render_commands(commands)
        self._render_qa(qa_pairs)
        self._render_top_apps(top_apps)

    def _render_commands(self, commands):
        self.cmd_list.clear()
        if commands:
            for c in reversed(commands):
                ts = c.get("timestamp", "")
                cmd = c.get("command", "Unknown command")
                intent = c.get("intent", "")
                ok = "✅" if c.get("success") else "❌"
                item = QListWidgetItem(f"{ok}  {cmd}   [{intent}]   {ts[:16]}")
                self.cmd_list.addItem(item)
        else:
            self._add_placeholder(self.cmd_list, "No command history yet.")

    def _render_qa(self, pairs):
        self.qa_list.clear()
        if pairs:
            for pair in reversed(pairs):
                q = pair.get("question", "?")[:80]
                a = pair.get("answer", "—")[:80]
                item = QListWidgetItem(f"Q: {q}\n   A: {a}")
                item.setFont(QFont("Segoe UI", 11))
                self.qa_list.addItem(item)
        else:
            self._add_placeholder(self.qa_list, "No Q&A history yet.")

    def _render_top_apps(self, apps):
        self.apps_list.clear()
        if apps:
            for i, app in enumerate(apps, 1):
                name = app.get("application", app.get("name", "Unknown"))
                count = app.get("count", 0)
                item = QListWidgetItem(f"#{i}  {name.title()}  —  {count} launches")
                self.apps_list.addItem(item)
        else:
            self._add_placeholder(self.apps_list, "No app usage history yet.")

    def _add_placeholder(self, list_widget: QListWidget, text: str):
        item = QListWidgetItem(text)
        item.setForeground(Qt.gray)
        item.setFlags(Qt.NoItemFlags)
        list_widget.addItem(item)

    def add_command(self, command: str, intent: str, success: bool):
        """Live update — adds a new command to the top of the list without a full refresh."""
        ok = "✅" if success else "❌"
        ts = datetime.now().strftime("%H:%M:%S")
        item = QListWidgetItem(f"{ok}  {command}   [{intent}]   {ts}")
        self.cmd_list.insertItem(0, item)

    def add_qa(self, question: str, answer: str):
        """Live update — adds a new Q&A pair."""
        q = question[:80]
        a = answer[:80]
        item = QListWidgetItem(f"Q: {q}\n   A: {a}")
        item.setFont(QFont("Segoe UI", 11))
        self.qa_list.insertItem(0, item)
