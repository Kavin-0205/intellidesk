from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout
)
from PySide6.QtCore import Qt


class DashboardCard(QFrame):
    """
    Reusable dashboard card.
    Example:
        CPU Usage
        25%
    """

    def __init__(self, title: str, value: str):
        super().__init__()

        self.setObjectName("dashboardCard")

        layout = QVBoxLayout(self)

        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setObjectName("cardTitle")

        self.value_label = QLabel(value)
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setObjectName("cardValue")

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

    def update_value(self, value: str):
        """Update the displayed value."""
        self.value_label.setText(value)