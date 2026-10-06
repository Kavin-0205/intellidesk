"""
IntelliDesk Dashboard Cards — premium dark theme.
"""

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QHBoxLayout, QProgressBar
from PySide6.QtCore import Qt


class DashboardCard(QFrame):
    """
    Premium metric card with icon + title + big value + optional progress bar.
    """

    def __init__(self, icon: str, title: str, value: str = "—",
                 subtitle: str = "", show_bar: bool = False):
        super().__init__()
        self.setObjectName("dashCard")
        self.setMinimumHeight(110)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(4)

        # Icon + title row
        top = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setObjectName("cardIcon")

        title_lbl = QLabel(title)
        title_lbl.setObjectName("cardTitle")

        top.addWidget(icon_lbl)
        top.addSpacing(6)
        top.addWidget(title_lbl)
        top.addStretch()
        layout.addLayout(top)

        # Big value
        self.value_lbl = QLabel(value)
        self.value_lbl.setObjectName("cardValue")
        layout.addWidget(self.value_lbl)

        # Optional progress bar
        if show_bar:
            self.bar = QProgressBar()
            self.bar.setRange(0, 100)
            self.bar.setValue(0)
            self.bar.setTextVisible(False)
            self.bar.setFixedHeight(6)
            layout.addWidget(self.bar)
        else:
            self.bar = None

        # Subtitle
        if subtitle:
            self.sub_lbl = QLabel(subtitle)
            self.sub_lbl.setObjectName("cardSub")
            layout.addWidget(self.sub_lbl)
        else:
            self.sub_lbl = None

    def update_value(self, value: str, bar_pct: int = -1, subtitle: str = ""):
        self.value_lbl.setText(value)
        if self.bar is not None and bar_pct >= 0:
            self.bar.setValue(min(100, max(0, bar_pct)))
        if self.sub_lbl and subtitle:
            self.sub_lbl.setText(subtitle)