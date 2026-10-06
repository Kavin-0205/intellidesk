"""
IntelliDesk Screen Reader & OCR Page.
Provides visual GUI tools for Phase 8 Screen Intelligence:
- One-click screen capture & OCR text extraction
- Screen error explanation using Groq LLM
- Screen summarization
- Text view with copy and save capabilities
"""

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QFrame, QScrollArea, QProgressBar
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont


class _ScreenWorker(QThread):
    """Background worker for OCR / AI screen operations."""

    finished = Signal(str, str)  # (title, result_text)
    error = Signal(str)

    def __init__(self, action: str):
        super().__init__()
        self.action = action

    def run(self):
        try:
            if self.action == "read":
                from screen.ocr import extract_text_from_screen
                text = extract_text_from_screen()
                self.finished.emit("OCR Screen Text", text if text.strip() else "No readable text detected on screen.")
            elif self.action == "explain_error":
                from screen.screen_analyzer import explain_error_on_screen
                res = explain_error_on_screen()
                explanation = res.get("explanation", res.get("error", "No explanation generated."))
                self.finished.emit("Error Analysis", explanation)
            elif self.action == "summarize":
                from screen.screen_analyzer import analyze_screen
                res = analyze_screen(task="summarize")
                summary = res.get("analysis", res.get("error", "No summary generated."))
                self.finished.emit("Screen Summary", summary)
            else:
                self.error.emit(f"Unknown action: {self.action}")
        except Exception as e:
            self.error.emit(str(e))


class ScreenReaderPage(QWidget):
    """Visual page for screen OCR extraction and AI error analysis."""

    def __init__(self):
        super().__init__()
        self.setObjectName("screenPage")
        self._worker = None

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        # ── Header ──────────────────────────────────────────
        hdr = QLabel("📄  Screen Reader & Vision")
        hdr.setObjectName("pageHeader")
        sub = QLabel("Extract text and analyze visible windows, code, or error dialogues on your screen")
        sub.setObjectName("pageSubtitle")
        root.addWidget(hdr)
        root.addWidget(sub)

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFrameShape(QFrame.HLine)
        root.addWidget(divider)

        # ── Action Buttons Row ──────────────────────────────
        btn_card = QFrame()
        btn_card.setObjectName("sectionCard")
        btn_layout = QHBoxLayout(btn_card)
        btn_layout.setSpacing(12)

        self.btn_read = QPushButton("📸  Read Screen Text")
        self.btn_read.setStyleSheet(self._btn_style("#1F6FEB", "#388BFD"))
        self.btn_read.clicked.connect(lambda: self._start_task("read"))
        btn_layout.addWidget(self.btn_read)

        self.btn_error = QPushButton("⚠  Explain Error on Screen")
        self.btn_error.setStyleSheet(self._btn_style("#D97706", "#F59E0B"))
        self.btn_error.clicked.connect(lambda: self._start_task("explain_error"))
        btn_layout.addWidget(self.btn_error)

        self.btn_summary = QPushButton("📊  Summarize Screen")
        self.btn_summary.setStyleSheet(self._btn_style("#059669", "#10B981"))
        self.btn_summary.clicked.connect(lambda: self._start_task("summarize"))
        btn_layout.addWidget(self.btn_summary)

        root.addWidget(btn_card)

        # ── Status / Progress ───────────────────────────────
        self.status_lbl = QLabel("Ready — choose an action above to analyze your desktop screen")
        self.status_lbl.setStyleSheet("color:#8B949E; font-size:13px;")
        root.addWidget(self.status_lbl)

        # ── Output Area ─────────────────────────────────────
        self.result_title = QLabel("Result")
        self.result_title.setStyleSheet("color:#E6EDF3; font-weight:bold; font-size:15px;")
        root.addWidget(self.result_title)

        self.output_box = QTextEdit()
        self.output_box.setReadOnly(True)
        self.output_box.setFont(QFont("Consolas", 11))
        self.output_box.setStyleSheet("""
            QTextEdit {
                background-color: #161B22;
                color: #E6EDF3;
                border: 1px solid #30363D;
                border-radius: 12px;
                padding: 14px;
                line-height: 1.5;
            }
        """)
        self.output_box.setPlaceholderText("Extracted text or AI analysis will appear here...")
        root.addWidget(self.output_box, stretch=1)

        # ── Bottom Action Bar ───────────────────────────────
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()

        copy_btn = QPushButton("📋  Copy Text")
        copy_btn.setStyleSheet("""
            QPushButton {
                background: #21262D; color: #8B949E;
                border: 1px solid #30363D; border-radius: 8px;
                padding: 6px 16px; font-size: 12px;
            }
            QPushButton:hover { background: #30363D; color: #E6EDF3; }
        """)
        copy_btn.clicked.connect(self._copy_text)
        bottom_row.addWidget(copy_btn)

        save_btn = QPushButton("📝  Save to Notepad")
        save_btn.setStyleSheet("""
            QPushButton {
                background: #21262D; color: #8B949E;
                border: 1px solid #30363D; border-radius: 8px;
                padding: 6px 16px; font-size: 12px;
            }
            QPushButton:hover { background: #1F6FEB; color: white; }
        """)
        save_btn.clicked.connect(self._save_to_notepad)
        bottom_row.addWidget(save_btn)

        root.addLayout(bottom_row)

    def _btn_style(self, c1: str, c2: str) -> str:
        return f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {c1}, stop:1 {c2});
                color: white;
                border: none;
                border-radius: 10px;
                padding: 12px 18px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {c2}; }}
            QPushButton:disabled {{ background: #21262D; color: #484F58; }}
        """

    def _set_buttons_enabled(self, enabled: bool):
        self.btn_read.setEnabled(enabled)
        self.btn_error.setEnabled(enabled)
        self.btn_summary.setEnabled(enabled)

    def _start_task(self, action: str):
        if self._worker and self._worker.isRunning():
            return
        self._set_buttons_enabled(False)
        self.status_lbl.setText("⏳  Analyzing screen, please wait...")
        self.output_box.clear()

        self._worker = _ScreenWorker(action)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_finished(self, title: str, text: str):
        self._set_buttons_enabled(True)
        self.status_lbl.setText("✅  Done")
        self.result_title.setText(f"Result — {title}")
        self.output_box.setPlainText(text)

    def _on_error(self, err: str):
        self._set_buttons_enabled(True)
        self.status_lbl.setText(f"⚠  Error: {err}")
        self.output_box.setPlainText(f"Error executing screen analysis:\n{err}")

    def _copy_text(self):
        text = self.output_box.toPlainText()
        if text:
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(text)
            self.status_lbl.setText("📋  Copied to clipboard!")

    def _save_to_notepad(self):
        text = self.output_box.toPlainText()
        if text:
            try:
                from mcp_layer.client import execute_mcp_tool
                execute_mcp_tool("save_to_notepad", {
                    "text": text,
                    "question": self.result_title.text()
                })
                self.status_lbl.setText("📝  Saved to Notepad!")
            except Exception as e:
                self.status_lbl.setText(f"⚠  Failed to save: {e}")
