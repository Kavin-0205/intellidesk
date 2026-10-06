"""
IntelliDesk File Manager Page.
Provides file exploration, search, and file manipulation.
"""

from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QListWidget, QListWidgetItem, QFrame, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class FileManagerPage(QWidget):
    """Visual file management and exploration interface."""

    def __init__(self):
        super().__init__()
        self.setObjectName("filesPage")
        self.current_dir = Path.cwd()

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)

        # ── Header ──────────────────────────────────────────
        hdr = QLabel("📁  File Manager")
        hdr.setObjectName("pageHeader")
        sub = QLabel("Browse workspace files, search, and manage directories")
        sub.setObjectName("pageSubtitle")
        root.addWidget(hdr)
        root.addWidget(sub)

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFrameShape(QFrame.HLine)
        root.addWidget(divider)

        # ── Navigation & Path Bar ───────────────────────────
        nav_bar = QHBoxLayout()
        nav_bar.setSpacing(8)

        up_btn = QPushButton("⬆ Up")
        up_btn.setStyleSheet("""
            QPushButton {
                background: #21262D; color: #8B949E; border: 1px solid #30363D;
                border-radius: 8px; padding: 6px 12px; font-size: 12px;
            }
            QPushButton:hover { background: #30363D; color: #E6EDF3; }
        """)
        up_btn.clicked.connect(self._go_up)
        nav_bar.addWidget(up_btn)

        self.path_input = QLineEdit(str(self.current_dir))
        self.path_input.setStyleSheet("""
            QLineEdit {
                background: #161B22; color: #E6EDF3; border: 1px solid #30363D;
                border-radius: 8px; padding: 6px 10px; font-size: 13px; font-family: Consolas;
            }
        """)
        self.path_input.returnPressed.connect(self._on_path_entered)
        nav_bar.addWidget(self.path_input, stretch=1)

        open_exp_btn = QPushButton("📂  Open in Explorer")
        open_exp_btn.setStyleSheet("""
            QPushButton {
                background: #1F6FEB; color: white; border: none;
                border-radius: 8px; padding: 6px 14px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background: #388BFD; }
        """)
        open_exp_btn.clicked.connect(self._open_in_explorer)
        nav_bar.addWidget(open_exp_btn)

        root.addLayout(nav_bar)

        # ── File List ───────────────────────────────────────
        self.file_list = QListWidget()
        self.file_list.setFont(QFont("Segoe UI", 11))
        self.file_list.setStyleSheet("""
            QListWidget {
                background: #161B22; border: 1px solid #30363D;
                border-radius: 12px; padding: 8px; color: #E6EDF3;
            }
            QListWidget::item { padding: 8px 12px; border-radius: 6px; }
            QListWidget::item:hover { background: #21262D; }
            QListWidget::item:selected { background: #1F6FEB; color: white; }
        """)
        self.file_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        root.addWidget(self.file_list, stretch=1)

        # ── Footer / Quick Actions ──────────────────────────
        footer = QHBoxLayout()
        self.count_lbl = QLabel("Loading...")
        self.count_lbl.setStyleSheet("color:#8B949E; font-size:12px;")
        footer.addWidget(self.count_lbl)
        footer.addStretch()

        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #21262D; color: #8B949E; border: 1px solid #30363D;
                border-radius: 8px; padding: 4px 12px; font-size: 12px;
            }
            QPushButton:hover { background: #30363D; color: #E6EDF3; }
        """)
        refresh_btn.clicked.connect(self._refresh)
        footer.addWidget(refresh_btn)

        root.addLayout(footer)

        self._refresh()

    def _refresh(self):
        self.file_list.clear()
        try:
            entries = sorted(list(self.current_dir.iterdir()), key=lambda e: (not e.is_dir(), e.name.lower()))
            for entry in entries:
                if entry.name.startswith("."):
                    continue
                icon = "📁 " if entry.is_dir() else "📄 "
                size_str = ""
                if entry.is_file():
                    try:
                        size = entry.stat().st_size
                        if size < 1024:
                            size_str = f"  ({size} B)"
                        elif size < 1024 * 1024:
                            size_str = f"  ({size // 1024} KB)"
                        else:
                            size_str = f"  ({size / (1024 * 1024):.1f} MB)"
                    except Exception:
                        pass
                item = QListWidgetItem(f"{icon} {entry.name}{size_str}")
                item.setData(Qt.UserRole, str(entry))
                self.file_list.addItem(item)
            self.count_lbl.setText(f"{len(entries)} items in {self.current_dir.name or self.current_dir}")
        except Exception as e:
            self.count_lbl.setText(f"Error reading directory: {e}")

    def _go_up(self):
        parent = self.current_dir.parent
        if parent != self.current_dir:
            self.current_dir = parent
            self.path_input.setText(str(self.current_dir))
            self._refresh()

    def _on_path_entered(self):
        new_path = Path(self.path_input.text().strip())
        if new_path.is_dir():
            self.current_dir = new_path
            self._refresh()
        else:
            self.path_input.setText(str(self.current_dir))

    def _on_item_double_clicked(self, item: QListWidgetItem):
        path_str = item.data(Qt.UserRole)
        if not path_str:
            return
        p = Path(path_str)
        if p.is_dir():
            self.current_dir = p
            self.path_input.setText(str(self.current_dir))
            self._refresh()
        else:
            # Try opening file
            import os
            try:
                os.startfile(str(p))
            except Exception as e:
                print(f"Error opening file: {e}")

    def _open_in_explorer(self):
        import subprocess
        try:
            subprocess.run(["explorer", str(self.current_dir)])
        except Exception as e:
            print(f"Error opening explorer: {e}")
