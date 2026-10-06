"""
IntelliDesk AI Chat Page.
Provides an interactive text chat interface with Groq LLM:
- Non-blocking QThread execution for streaming / async responses
- Rich chat bubbles with syntax / formatted text support
- Action buttons: "Save to Notepad", "Clear Chat"
- MongoDB session memory integration
"""

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QScrollArea, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QFont

from gui.voice_page import ChatBubble


class _ChatWorker(QThread):
    """Background worker for querying LLM without freezing GUI."""

    response_ready = Signal(str, bool)  # text, is_success
    error = Signal(str)

    def __init__(self, prompt: str):
        super().__init__()
        self.prompt = prompt

    def run(self):
        try:
            from llm.ai_router import answer_general_question
            from memory.conversation_memory import save_qa_pair, save_command

            answer = answer_general_question(self.prompt)
            # Save to conversation memory
            save_qa_pair(self.prompt, answer)
            save_command(self.prompt, "general_question", True, answer[:300])

            self.response_ready.emit(answer, True)
        except Exception as e:
            self.error.emit(f"Error querying AI: {e}")


class ChatPage(QWidget):
    """Full-featured text-based AI Chat interface."""

    message_sent = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("chatPage")
        self._worker = None
        self._last_ai_answer = ""
        self._last_user_query = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)

        # ── Header ──────────────────────────────────────────
        header_row = QHBoxLayout()
        header_col = QVBoxLayout()
        hdr = QLabel("🤖  AI Chat")
        hdr.setObjectName("pageHeader")
        sub = QLabel("Ask questions, generate explanations, or brainstorm with Groq AI")
        sub.setObjectName("pageSubtitle")
        header_col.addWidget(hdr)
        header_col.addWidget(sub)
        header_row.addLayout(header_col)
        header_row.addStretch()

        # Clear button
        clear_btn = QPushButton("🗑  Clear")
        clear_btn.setStyleSheet("""
            QPushButton {
                background: #21262D;
                color: #8B949E;
                border: 1px solid #30363D;
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 12px;
            }
            QPushButton:hover { background: #30363D; color: #E6EDF3; }
        """)
        clear_btn.clicked.connect(self._clear_chat)
        header_row.addWidget(clear_btn)

        # Save to Notepad button
        self.notepad_btn = QPushButton("📝  Save to Notepad")
        self.notepad_btn.setStyleSheet("""
            QPushButton {
                background: #21262D;
                color: #8B949E;
                border: 1px solid #30363D;
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 12px;
            }
            QPushButton:hover { background: #1F6FEB; color: white; }
        """)
        self.notepad_btn.clicked.connect(self._save_to_notepad)
        header_row.addWidget(self.notepad_btn)

        root.addLayout(header_row)

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFrameShape(QFrame.HLine)
        root.addWidget(divider)

        # ── Chat Area ───────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._container = QWidget()
        self._chat_layout = QVBoxLayout(self._container)
        self._chat_layout.setSpacing(8)
        self._chat_layout.addStretch()
        scroll.setWidget(self._container)
        self._scroll = scroll
        root.addWidget(scroll, stretch=1)

        # ── Input Area ──────────────────────────────────────
        input_frame = QFrame()
        input_frame.setObjectName("sectionCard")
        input_frame.setStyleSheet("""
            QFrame#sectionCard {
                background: #161B22;
                border: 1px solid #30363D;
                border-radius: 12px;
                padding: 8px;
            }
        """)
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(8, 4, 8, 4)
        input_layout.setSpacing(10)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type a question or message and press Enter...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #E6EDF3;
                font-size: 14px;
                padding: 6px;
            }
        """)
        self.input_field.returnPressed.connect(self._send_message)
        input_layout.addWidget(self.input_field, stretch=1)

        self.send_btn = QPushButton("Send  ➤")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1F6FEB, stop:1 #388BFD);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 18px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background: #388BFD; }
            QPushButton:disabled { background: #21262D; color: #484F58; }
        """)
        self.send_btn.clicked.connect(self._send_message)
        input_layout.addWidget(self.send_btn)

        root.addWidget(input_frame)

        # Welcome message
        self._add_bubble("Hello! I'm your IntelliDesk AI Assistant. How can I help you today?", is_user=False)

    def _add_bubble(self, text: str, is_user: bool):
        bubble = ChatBubble(text, is_user=is_user)
        count = self._chat_layout.count()
        self._chat_layout.insertWidget(count - 1, bubble)
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        vbar = self._scroll.verticalScrollBar()
        vbar.setValue(vbar.maximum())

    def _send_message(self):
        text = self.input_field.text().strip()
        if not text or (self._worker and self._worker.isRunning()):
            return

        self._last_user_query = text
        self.input_field.clear()
        self._add_bubble(text, is_user=True)

        self.send_btn.setEnabled(False)
        self.input_field.setEnabled(False)

        # Show typing indicator bubble
        self._typing_bubble = ChatBubble("Thinking...", is_user=False)
        count = self._chat_layout.count()
        self._chat_layout.insertWidget(count - 1, self._typing_bubble)

        self._worker = _ChatWorker(text)
        self._worker.response_ready.connect(self._on_ai_response)
        self._worker.error.connect(self._on_ai_error)
        self._worker.start()

    def _on_ai_response(self, response: str, is_success: bool):
        # Remove typing bubble
        self._typing_bubble.deleteLater()
        self._last_ai_answer = response
        self._add_bubble(response, is_user=False)
        self._finish_send()

    def _on_ai_error(self, err_msg: str):
        self._typing_bubble.deleteLater()
        self._add_bubble(f"⚠ {err_msg}", is_user=False)
        self._finish_send()

    def _finish_send(self):
        self.send_btn.setEnabled(True)
        self.input_field.setEnabled(True)
        self.input_field.setFocus()

    def _clear_chat(self):
        # Remove all bubbles except stretch
        while self._chat_layout.count() > 1:
            item = self._chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._add_bubble("Chat cleared. How can I help you next?", is_user=False)

    def _save_to_notepad(self):
        if not self._last_ai_answer:
            return
        try:
            from mcp_layer.client import execute_mcp_tool
            execute_mcp_tool("save_to_notepad", {
                "text": self._last_ai_answer,
                "question": self._last_user_query
            })
            self._add_bubble("📝 Last answer has been saved to a new Notepad document.", is_user=False)
        except Exception as e:
            self._add_bubble(f"⚠ Could not save to Notepad: {e}", is_user=False)
