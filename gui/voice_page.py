"""
IntelliDesk Voice Assistant Page.

Central voice interaction page with:
- Animated mic button (pulsing while listening)
- Real-time transcript display
- Response bubble with last AI reply
- Session command counter
- Non-blocking voice loop using QThread
"""

import threading
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QFrame, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont


class _VoiceWorker(QThread):
    """Worker thread for one voice-to-response cycle (non-blocking)."""

    transcript_ready = Signal(str)    # emits STT text
    response_ready   = Signal(str, bool)  # (response text, success)
    error            = Signal(str)
    finished_cycle   = Signal()

    def __init__(self):
        super().__init__()
        self._stop = False

    def run(self):
        try:
            from speech.stt import listen_once
            from llm.ai_router import classify_intent
            from intent_router import handle_intent
            from context.context_manager import context

            # STT
            transcript = listen_once()
            if not transcript:
                self.error.emit("I didn't catch that. Please try again.")
                self.finished_cycle.emit()
                return

            self.transcript_ready.emit(transcript)

            # Intent + route
            session_ctx = context.get_session_summary()
            intent_data = classify_intent(transcript, session_context=session_ctx)
            result = handle_intent(intent_data, user_command=transcript, speak_response=True)

            response = result.get("response", "Done.")
            success = result.get("success", False)
            self.response_ready.emit(response, success)

        except Exception as e:
            self.error.emit(f"Error: {e}")
        finally:
            self.finished_cycle.emit()


class ChatBubble(QFrame):
    """Single chat bubble — user or assistant."""

    def __init__(self, text: str, is_user: bool = False):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)

        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setMaximumWidth(480)
        lbl.setFont(QFont("Segoe UI", 12))

        if is_user:
            lbl.setStyleSheet("""
                background: #1F6FEB;
                color: white;
                border-radius: 14px;
                padding: 10px 16px;
                font-size: 13px;
            """)
            layout.addStretch()
            layout.addWidget(lbl)
        else:
            lbl.setStyleSheet("""
                background: #21262D;
                color: #C9D1D9;
                border-radius: 14px;
                border: 1px solid #30363D;
                padding: 10px 16px;
                font-size: 13px;
            """)
            layout.addWidget(lbl)
            layout.addStretch()


class VoiceAssistantPage(QWidget):

    # Signal to notify dashboard of new commands
    command_completed = Signal(bool)  # True = Q&A, False = action

    def __init__(self):
        super().__init__()
        self.setObjectName("voicePage")
        self._worker = None
        self._listening = False
        self._pulse_timer = QTimer()
        self._pulse_timer.timeout.connect(self._pulse_step)
        self._pulse_alpha = 255
        self._pulse_dir = -1

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 24, 32, 24)
        root.setSpacing(16)

        # ── Header ──────────────────────────────────────────
        hdr = QLabel("🎙  Voice Assistant")
        hdr.setObjectName("pageHeader")
        sub = QLabel("Press the microphone and speak a command")
        sub.setObjectName("pageSubtitle")
        root.addWidget(hdr)
        root.addWidget(sub)

        # ── Chat Bubble Scroll Area ─────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._chat_container = QWidget()
        self._chat_layout = QVBoxLayout(self._chat_container)
        self._chat_layout.setSpacing(4)
        self._chat_layout.addStretch()
        scroll.setWidget(self._chat_container)
        self._scroll = scroll
        root.addWidget(scroll, stretch=1)

        # ── Status label ────────────────────────────────────
        self.status_lbl = QLabel("Ready — press the mic to speak")
        self.status_lbl.setObjectName("statusLabel")
        self.status_lbl.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status_lbl)

        # ── Mic Button ──────────────────────────────────────
        mic_row = QHBoxLayout()
        mic_row.addStretch()

        self.mic_btn = QPushButton("🎙")
        self.mic_btn.setObjectName("micBtn")
        self.mic_btn.setToolTip("Click to speak a voice command")
        self.mic_btn.clicked.connect(self._on_mic_clicked)

        mic_row.addWidget(self.mic_btn)
        mic_row.addStretch()
        root.addLayout(mic_row)

        # ── Greeting bubble ─────────────────────────────────
        self._add_bubble("Hello! I'm IntelliDesk. How can I help you today?", is_user=False)

    # ── Private helpers ──────────────────────────────────────

    def _add_bubble(self, text: str, is_user: bool):
        bubble = ChatBubble(text, is_user=is_user)
        # Insert before the trailing stretch
        count = self._chat_layout.count()
        self._chat_layout.insertWidget(count - 1, bubble)
        # Auto-scroll to bottom
        QTimer.singleShot(50, self._scroll_bottom)

    def _scroll_bottom(self):
        vbar = self._scroll.verticalScrollBar()
        vbar.setValue(vbar.maximum())

    def _set_listening(self, value: bool):
        self._listening = value
        if value:
            self.mic_btn.setText("⏹")
            self.mic_btn.setStyleSheet("""
                QPushButton#micBtn {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                        stop:0 #B91C1C, stop:1 #EF4444);
                    color: white;
                    border: none;
                    border-radius: 32px;
                    font-size: 22px;
                    min-width: 64px; max-width: 64px;
                    min-height: 64px; max-height: 64px;
                }
            """)
            self.status_lbl.setText("🔴  Listening…")
            self._pulse_timer.start(40)
        else:
            self.mic_btn.setText("🎙")
            self.mic_btn.setStyleSheet("")  # revert to stylesheet default
            self._pulse_timer.stop()

    def _pulse_step(self):
        """Subtle pulsing animation on status label opacity."""
        self._pulse_alpha += self._pulse_dir * 8
        if self._pulse_alpha <= 100:
            self._pulse_dir = 1
        elif self._pulse_alpha >= 255:
            self._pulse_dir = -1
        self._pulse_alpha = max(100, min(255, self._pulse_alpha))
        alpha = self._pulse_alpha
        self.status_lbl.setStyleSheet(
            f"color: rgba(239,68,68,{alpha}); font-size:16px; font-weight:bold;"
        )

    # ── Voice Cycle ──────────────────────────────────────────

    def _on_mic_clicked(self):
        if self._listening:
            return  # one command at a time
        self._set_listening(True)
        self.mic_btn.setEnabled(False)

        self._worker = _VoiceWorker()
        self._worker.transcript_ready.connect(self._on_transcript)
        self._worker.response_ready.connect(self._on_response)
        self._worker.error.connect(self._on_error)
        self._worker.finished_cycle.connect(self._on_finished)
        self._worker.start()

    def _on_transcript(self, text: str):
        self._add_bubble(text, is_user=True)
        self.status_lbl.setText("🤔  Processing…")

    def _on_response(self, text: str, success: bool):
        self._add_bubble(text, is_user=False)
        intent_was_qa = any(w in text.lower() for w in ["is", "are", "was", "have", "does"])
        self.command_completed.emit(intent_was_qa)

    def _on_error(self, msg: str):
        self.status_lbl.setText(f"⚠  {msg}")
        self._add_bubble(f"⚠  {msg}", is_user=False)

    def _on_finished(self):
        self._set_listening(False)
        self.mic_btn.setEnabled(True)
        self.status_lbl.setStyleSheet("")
        self.status_lbl.setText("Ready — press the mic to speak")
