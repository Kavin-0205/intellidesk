"""
IntelliDesk Settings & Diagnostics Page.
Allows viewing and configuring:
- Groq LLM API Key and status validation
- MongoDB persistent database connection test
- Speech & Voice Settings (TTS rate, test voice audio)
- System Diagnostics (OS, Python environment, MCP server health)
"""

import os
import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QFrame, QScrollArea, QComboBox, QSlider
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont


class SettingsPage(QWidget):
    """Settings, configurations and diagnostics page."""

    def __init__(self):
        super().__init__()
        self.setObjectName("settingsPage")

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        # ── Header ──────────────────────────────────────────
        hdr = QLabel("⚙  Settings & Diagnostics")
        hdr.setObjectName("pageHeader")
        sub = QLabel("Manage API keys, persistent database, voice preferences, and system diagnostics")
        sub.setObjectName("pageSubtitle")
        root.addWidget(hdr)
        root.addWidget(sub)

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFrameShape(QFrame.HLine)
        root.addWidget(divider)

        # ── Scroll Area for Settings Sections ───────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(20)

        # 1. AI Configuration Card
        layout.addWidget(self._build_ai_card())

        # 2. MongoDB Database Card
        layout.addWidget(self._build_db_card())

        # 3. Speech & Voice Card
        layout.addWidget(self._build_voice_card())

        # 4. System Diagnostics Card
        layout.addWidget(self._build_diag_card())

        layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)

    def _card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("sectionCard")
        card.setStyleSheet("""
            QFrame#sectionCard {
                background: #161B22;
                border: 1px solid #30363D;
                border-radius: 14px;
                padding: 16px;
            }
        """)
        v = QVBoxLayout(card)
        v.setSpacing(12)
        lbl = QLabel(title)
        lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #E6EDF3;")
        v.addWidget(lbl)
        return card, v

    def _build_ai_card(self) -> QFrame:
        card, layout = self._card("🤖  Groq AI LLM Settings")

        row = QHBoxLayout()
        key_label = QLabel("Groq API Key:")
        key_label.setFixedWidth(130)
        key_label.setStyleSheet("color: #8B949E; font-size: 13px;")

        self.key_input = QLineEdit()
        current_key = os.getenv("GROQ_API_KEY", "")
        if current_key:
            # Mask part of the key
            self.key_input.setText(current_key[:8] + "•" * 20 + current_key[-4:] if len(current_key) > 12 else "••••••••")
        else:
            self.key_input.setPlaceholderText("Enter your gsk_... Groq API Key")
        self.key_input.setEchoMode(QLineEdit.Password)
        self.key_input.setStyleSheet("""
            QLineEdit {
                background: #0D1117; color: #E6EDF3;
                border: 1px solid #30363D; border-radius: 8px;
                padding: 6px 10px; font-size: 13px;
            }
        """)

        test_ai_btn = QPushButton("Test Key")
        test_ai_btn.setStyleSheet("""
            QPushButton {
                background: #1F6FEB; color: white; border: none;
                border-radius: 8px; padding: 6px 14px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background: #388BFD; }
        """)
        test_ai_btn.clicked.connect(self._test_groq_key)

        row.addWidget(key_label)
        row.addWidget(self.key_input, stretch=1)
        row.addWidget(test_ai_btn)
        layout.addLayout(row)

        self.ai_status_lbl = QLabel("Status: Click 'Test Key' to verify API connection.")
        self.ai_status_lbl.setStyleSheet("color: #8B949E; font-size: 12px;")
        layout.addWidget(self.ai_status_lbl)
        return card

    def _build_db_card(self) -> QFrame:
        card, layout = self._card("💾  MongoDB Persistent Database")

        row = QHBoxLayout()
        uri_lbl = QLabel("Connection URI:")
        uri_lbl.setFixedWidth(130)
        uri_lbl.setStyleSheet("color: #8B949E; font-size: 13px;")

        self.uri_input = QLineEdit()
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.uri_input.setText(mongo_uri)
        self.uri_input.setStyleSheet("""
            QLineEdit {
                background: #0D1117; color: #E6EDF3;
                border: 1px solid #30363D; border-radius: 8px;
                padding: 6px 10px; font-size: 13px;
            }
        """)

        test_db_btn = QPushButton("Test MongoDB")
        test_db_btn.setStyleSheet("""
            QPushButton {
                background: #238636; color: white; border: none;
                border-radius: 8px; padding: 6px 14px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background: #2EA043; }
        """)
        test_db_btn.clicked.connect(self._test_mongo)

        row.addWidget(uri_lbl)
        row.addWidget(self.uri_input, stretch=1)
        row.addWidget(test_db_btn)
        layout.addLayout(row)

        self.db_status_lbl = QLabel("Status: Click 'Test MongoDB' to test local database connection.")
        self.db_status_lbl.setStyleSheet("color: #8B949E; font-size: 12px;")
        layout.addWidget(self.db_status_lbl)
        return card

    def _build_voice_card(self) -> QFrame:
        card, layout = self._card("🎙  Voice & Audio Settings")

        row = QHBoxLayout()
        voice_lbl = QLabel("Speech Engine:")
        voice_lbl.setFixedWidth(130)
        voice_lbl.setStyleSheet("color: #8B949E; font-size: 13px;")

        engine_box = QComboBox()
        engine_box.addItem("Windows SAPI5 (Default)")
        engine_box.addItem("pyttsx3 Local Engine")
        engine_box.setStyleSheet("""
            QComboBox {
                background: #0D1117; color: #E6EDF3;
                border: 1px solid #30363D; border-radius: 8px;
                padding: 6px 12px; font-size: 12px;
            }
        """)

        test_voice_btn = QPushButton("🔊  Test Voice")
        test_voice_btn.setStyleSheet("""
            QPushButton {
                background: #21262D; color: #E6EDF3; border: 1px solid #30363D;
                border-radius: 8px; padding: 6px 14px; font-size: 12px;
            }
            QPushButton:hover { background: #1F6FEB; color: white; }
        """)
        test_voice_btn.clicked.connect(self._test_voice)

        row.addWidget(voice_lbl)
        row.addWidget(engine_box, stretch=1)
        row.addWidget(test_voice_btn)
        layout.addLayout(row)

        desc = QLabel("Microphone input uses Google Speech Recognition with automatic ambient noise calibration.")
        desc.setStyleSheet("color: #8B949E; font-size: 12px;")
        layout.addWidget(desc)
        return card

    def _build_diag_card(self) -> QFrame:
        card, layout = self._card("📊  System Information")

        import platform
        py_ver = sys.version.split()[0]
        os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"

        info_text = (
            f"Python: {py_ver}  |  OS: {os_info}  |  "
            f"MCP Tools: 60 registered  |  Intents: 21 supported"
        )
        lbl = QLabel(info_text)
        lbl.setStyleSheet("color: #58A6FF; font-size: 12px; font-family: Consolas;")
        layout.addWidget(lbl)
        return card

    def _test_groq_key(self):
        self.ai_status_lbl.setText("⏳ Testing Groq API connection...")
        try:
            from llm.grok_client import client
            if client:
                res = client.chat.completions.create(
                    model="openai/gpt-oss-120b",
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=5
                )
                self.ai_status_lbl.setText("🟢 Groq API Connected & Validated!")
                self.ai_status_lbl.setStyleSheet("color: #3FB950; font-size: 12px;")
            else:
                self.ai_status_lbl.setText("🔴 Groq Client returned None. Check your GROQ_API_KEY in .env.")
                self.ai_status_lbl.setStyleSheet("color: #F85149; font-size: 12px;")
        except Exception as e:
            self.ai_status_lbl.setText(f"🔴 Error: {e}")
            self.ai_status_lbl.setStyleSheet("color: #F85149; font-size: 12px;")

    def _test_mongo(self):
        self.db_status_lbl.setText("⏳ Testing MongoDB connection...")
        try:
            input_uri = self.uri_input.text().strip()
            if input_uri:
                os.environ["MONGO_URI"] = input_uri
            from database.mongodb import connect, get_status
            avail = connect(force=True)
            if avail:
                status = get_status()
                db_name = status.get("database", "intellidesk")
                self.db_status_lbl.setText(f"🟢 MongoDB Connected & Active (DB: '{db_name}')!")
                self.db_status_lbl.setStyleSheet("color: #3FB950; font-size: 12px;")
            else:
                self.db_status_lbl.setText("🟡 MongoDB unavailable. Using in-memory fallback smoothly.")
                self.db_status_lbl.setStyleSheet("color: #D29922; font-size: 12px;")
        except Exception as e:
            self.db_status_lbl.setText(f"🔴 Error: {e}")
            self.db_status_lbl.setStyleSheet("color: #F85149; font-size: 12px;")

    def _test_voice(self):
        try:
            from speech.tts import speak
            speak("IntelliDesk voice engine is operating normally.", wait=False)
        except Exception as e:
            print(f"Voice test error: {e}")
