from gui.dashboard import DashboardPage
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QStackedWidget,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QStatusBar
)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        # Window Title
        self.setWindowTitle("IntelliDesk")

        # Window Size
        self.resize(1400, 800)

        # -----------------------
        # Central Widget
        # -----------------------
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main Layout
        main_layout = QHBoxLayout(central_widget)

        # -----------------------
        # Sidebar
        # -----------------------
        self.sidebar = QListWidget()

        self.sidebar.setFixedWidth(230)

        pages = [
            "🏠 Home",
            "🤖 AI Chat",
            "🎤 Voice Assistant",
            "📁 File Manager",
            "💻 Coding Assistant",
            "📄 Screen Reader",
            "📊 Dashboard",
            "⚙ Settings"
        ]

        for page in pages:
            item = QListWidgetItem(page)
            self.sidebar.addItem(item)

        # -----------------------
        # Page Area
        # -----------------------
        self.pages = QStackedWidget()

        self.pages.addWidget(self.create_page(
            "🏠 Home",
            "Welcome to IntelliDesk"
        ))

        self.pages.addWidget(self.create_page(
            "🤖 AI Chat",
            "Chat with Grok AI"
        ))

        self.pages.addWidget(self.create_page(
            "🎤 Voice Assistant",
            "Control your PC using voice."
        ))

        self.pages.addWidget(self.create_page(
            "📁 File Manager",
            "Manage your files."
        ))

        self.pages.addWidget(self.create_page(
            "💻 Coding Assistant",
            "Analyze and explain code."
        ))

        self.pages.addWidget(self.create_page(
            "📄 Screen Reader",
            "Read and summarize the screen."
        ))

        self.pages.addWidget(DashboardPage())

        self.pages.addWidget(self.create_page(
            "⚙ Settings",
            "Configure IntelliDesk."
        ))

        # -----------------------
        # Connect Sidebar
        # -----------------------
        self.sidebar.currentRowChanged.connect(
            self.pages.setCurrentIndex
        )

        # Default Page
        self.sidebar.setCurrentRow(0)

        # Add Widgets
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.pages)

        # -----------------------
        # Status Bar
        # -----------------------
        status = QStatusBar()
        status.showMessage("IntelliDesk Ready")
        self.setStatusBar(status)

    def create_page(self, title, description):

        page = QWidget()

        layout = QHBoxLayout(page)

        label = QLabel(
            f"""
            <h1>{title}</h1>

            <br>

            <h3>{description}</h3>
            """
        )

        label.setAlignment(Qt.AlignCenter)

        layout.addWidget(label)

        return page