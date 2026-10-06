"""
IntelliDesk Coding Assistant Page.
Provides AI code analysis, error explanation, and Git automation controls.
"""

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QFrame, QComboBox, QLineEdit
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont


class _CodeWorker(QThread):
    finished = Signal(str, str)
    error = Signal(str)

    def __init__(self, action: str, code_snippet: str, extra: str = ""):
        super().__init__()
        self.action = action
        self.code_snippet = code_snippet
        self.extra = extra

    def run(self):
        try:
            from llm.ai_router import answer_general_question

            if self.action == "explain":
                prompt = (
                    f"Explain this code concisely, highlighting key logic and flow:\n\n"
                    f"```\n{self.code_snippet}\n```"
                )
                res = answer_general_question(prompt)
                self.finished.emit("Code Explanation", res)

            elif self.action == "debug":
                prompt = (
                    f"Analyze this code for potential bugs, edge cases, or security issues, "
                    f"and provide recommended fixes:\n\n"
                    f"```\n{self.code_snippet}\n```"
                )
                res = answer_general_question(prompt)
                self.finished.emit("Bug Analysis & Fixes", res)

            elif self.action == "git_status":
                from automation.git_control import git_status
                status_res = git_status()
                if status_res.get("success"):
                    msg = (
                        f"Branch: {status_res.get('branch', 'unknown')}\n"
                        f"Status: {'Clean' if status_res.get('is_clean') else 'Modified files present'}\n"
                        f"Untracked: {status_res.get('untracked', [])}\n"
                        f"Modified: {status_res.get('modified', [])}"
                    )
                else:
                    msg = f"Git status failed: {status_res.get('error', 'unknown error')}"
                self.finished.emit("Git Repository Status", msg)

            elif self.action == "git_commit_push":
                from automation.git_control import git_commit_and_push
                commit_msg = self.extra or "Update from IntelliDesk Coding Assistant"
                res = git_commit_and_push(message=commit_msg)
                if res.get("success"):
                    msg = f"Successfully committed & pushed!\nCommit: {res.get('commit_hash', '')}\nBranch: {res.get('branch', '')}"
                else:
                    msg = f"Failed to commit & push: {res.get('error', res.get('push_error', 'unknown'))}"
                self.finished.emit("Git Commit & Push", msg)

            else:
                self.error.emit(f"Unknown action: {self.action}")

        except Exception as e:
            self.error.emit(str(e))


class CodingAssistantPage(QWidget):
    """Visual Coding Assistant with AI analysis and Git operations."""

    def __init__(self):
        super().__init__()
        self.setObjectName("codePage")
        self._worker = None

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)

        # ── Header ──────────────────────────────────────────
        hdr = QLabel("💻  Coding Assistant & Git")
        hdr.setObjectName("pageHeader")
        sub = QLabel("Analyze code, find bugs, scan for security issues, and manage Git repositories")
        sub.setObjectName("pageSubtitle")
        root.addWidget(hdr)
        root.addWidget(sub)

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFrameShape(QFrame.HLine)
        root.addWidget(divider)

        # ── Code Input Box ──────────────────────────────────
        code_lbl = QLabel("Code Snippet / Input:")
        code_lbl.setStyleSheet("color:#8B949E; font-size:13px; font-weight:bold;")
        root.addWidget(code_lbl)

        self.code_input = QTextEdit()
        self.code_input.setFont(QFont("Consolas", 11))
        self.code_input.setPlaceholderText("Paste or write code here to analyze or debug...")
        self.code_input.setStyleSheet("""
            QTextEdit {
                background: #161B22; color: #E6EDF3;
                border: 1px solid #30363D; border-radius: 10px;
                padding: 10px;
            }
        """)
        self.code_input.setFixedHeight(160)
        root.addWidget(self.code_input)

        # ── Action Buttons Row ──────────────────────────────
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        explain_btn = QPushButton("🧠  Explain Code")
        explain_btn.setStyleSheet(self._btn_style("#1F6FEB", "#388BFD"))
        explain_btn.clicked.connect(lambda: self._start_action("explain"))
        btn_bar.addWidget(explain_btn)

        debug_btn = QPushButton("🐛  Find Bugs & Fix")
        debug_btn.setStyleSheet(self._btn_style("#B45309", "#D97706"))
        debug_btn.clicked.connect(lambda: self._start_action("debug"))
        btn_bar.addWidget(debug_btn)

        git_btn = QPushButton("🌿  Git Status")
        git_btn.setStyleSheet(self._btn_style("#238636", "#2EA043"))
        git_btn.clicked.connect(lambda: self._start_action("git_status"))
        btn_bar.addWidget(git_btn)

        self.commit_msg_input = QLineEdit()
        self.commit_msg_input.setPlaceholderText("Commit message...")
        self.commit_msg_input.setStyleSheet("""
            QLineEdit {
                background: #161B22; color: #E6EDF3;
                border: 1px solid #30363D; border-radius: 8px;
                padding: 6px 10px; font-size: 12px;
            }
        """)
        btn_bar.addWidget(self.commit_msg_input)

        push_btn = QPushButton("🚀  Commit & Push")
        push_btn.setStyleSheet(self._btn_style("#7C3AED", "#8B5CF6"))
        push_btn.clicked.connect(lambda: self._start_action("git_commit_push"))
        btn_bar.addWidget(push_btn)

        root.addLayout(btn_bar)

        # ── Output Area ─────────────────────────────────────
        self.res_title = QLabel("AI Analysis Output")
        self.res_title.setStyleSheet("color:#E6EDF3; font-weight:bold; font-size:14px;")
        root.addWidget(self.res_title)

        self.output_box = QTextEdit()
        self.output_box.setReadOnly(True)
        self.output_box.setFont(QFont("Segoe UI", 11))
        self.output_box.setStyleSheet("""
            QTextEdit {
                background: #161B22; color: #E6EDF3;
                border: 1px solid #30363D; border-radius: 10px;
                padding: 12px; line-height: 1.5;
            }
        """)
        self.output_box.setPlaceholderText("Analysis results or Git output will appear here...")
        root.addWidget(self.output_box, stretch=1)

    def _btn_style(self, c1: str, c2: str) -> str:
        return f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {c1}, stop:1 {c2});
                color: white; border: none; border-radius: 8px;
                padding: 8px 14px; font-size: 12px; font-weight: bold;
            }}
            QPushButton:hover {{ background: {c2}; }}
        """

    def _start_action(self, action: str):
        if self._worker and self._worker.isRunning():
            return
        code = self.code_input.toPlainText().strip()
        extra = self.commit_msg_input.text().strip()

        if action in ("explain", "debug") and not code:
            self.output_box.setPlainText("Please paste some code into the snippet box first.")
            return

        self.output_box.setPlainText("⏳ Processing request with Groq AI / Git engine...")
        self._worker = _CodeWorker(action, code, extra)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_finished(self, title: str, text: str):
        self.res_title.setText(f"Output — {title}")
        self.output_box.setPlainText(text)

    def _on_error(self, err: str):
        self.res_title.setText("Error")
        self.output_box.setPlainText(f"Error:\n{err}")
