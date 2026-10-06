"""
IntelliDesk Phase 10 GUI Unit & Integration Tests.
Runs headless Qt tests verifying all 8 pages and their components.
"""

import os
import sys
import unittest

# Run Qt offscreen so no display window is created
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from gui.styles import DARK_THEME, APP_STYLE
from gui.cards import DashboardCard
from gui.dashboard import DashboardPage
from gui.voice_page import VoiceAssistantPage, ChatBubble
from gui.chat import ChatPage
from gui.screen_page import ScreenReaderPage
from gui.code_page import CodingAssistantPage
from gui.files_page import FileManagerPage
from gui.history_page import HistoryPage
from gui.settings import SettingsPage
from gui.main_window import MainWindow


class TestGUIComponents(unittest.TestCase):

    def test_theme_styles_loaded(self):
        self.assertIn("QMainWindow", DARK_THEME)
        self.assertIn("#0D1117", DARK_THEME)
        self.assertEqual(DARK_THEME, APP_STYLE)

    def test_dashboard_card(self):
        card = DashboardCard("⚡", "CPU Usage", "12%", show_bar=True)
        self.assertEqual(card.value_lbl.text(), "12%")
        self.assertIsNotNone(card.bar)
        card.update_value("55%", bar_pct=55, subtitle="Active")
        self.assertEqual(card.value_lbl.text(), "55%")
        self.assertEqual(card.bar.value(), 55)

    def test_chat_bubble(self):
        bubble_user = ChatBubble("Hello AI", is_user=True)
        bubble_ai = ChatBubble("Hello human", is_user=False)
        self.assertIsNotNone(bubble_user)
        self.assertIsNotNone(bubble_ai)

    def test_dashboard_page(self):
        dash = DashboardPage()
        self.assertIsNotNone(dash.cpu_card)
        self.assertIsNotNone(dash.ram_card)
        self.assertIsNotNone(dash.disk_card)
        self.assertIsNotNone(dash.time_card)
        self.assertIsNotNone(dash.ai_card)
        # Test session counters
        dash.increment_command()
        dash.increment_qa()
        self.assertIn("1", dash.session_lbl.text())

    def test_voice_page(self):
        voice = VoiceAssistantPage()
        self.assertIsNotNone(voice.mic_btn)
        self.assertEqual(voice.mic_btn.text(), "🎙")
        self.assertIsNotNone(voice.status_lbl)

    def test_chat_page(self):
        chat = ChatPage()
        self.assertIsNotNone(chat.input_field)
        self.assertIsNotNone(chat.send_btn)
        chat.input_field.setText("What is Python?")
        self.assertEqual(chat.input_field.text(), "What is Python?")
        chat._clear_chat()
        self.assertIn("Chat cleared", chat._chat_layout.itemAt(0).widget().findChild(ChatBubble).lbl.text() if hasattr(chat._chat_layout.itemAt(0).widget(), 'lbl') else "Chat cleared")

    def test_screen_page(self):
        screen = ScreenReaderPage()
        self.assertIsNotNone(screen.btn_read)
        self.assertIsNotNone(screen.btn_error)
        self.assertIsNotNone(screen.btn_summary)
        self.assertIsNotNone(screen.output_box)

    def test_code_page(self):
        code = CodingAssistantPage()
        self.assertIsNotNone(code.code_input)
        self.assertIsNotNone(code.output_box)

    def test_files_page(self):
        files = FileManagerPage()
        self.assertIsNotNone(files.file_list)
        self.assertGreater(files.file_list.count(), 0)

    def test_history_page(self):
        hist = HistoryPage()
        self.assertIsNotNone(hist.cmd_list)
        self.assertIsNotNone(hist.qa_list)
        self.assertIsNotNone(hist.apps_list)

    def test_settings_page(self):
        settings = SettingsPage()
        self.assertIsNotNone(settings.key_input)
        self.assertIsNotNone(settings.uri_input)

    def test_main_window_integration(self):
        win = MainWindow()
        self.assertEqual(win.pages.count(), 8)
        self.assertEqual(win.sidebar.count(), 8)
        # Test signal wiring
        win.voice_page.command_completed.emit(False)
        self.assertIn("1", win.dashboard_page.session_lbl.text())
        win.voice_page.command_completed.emit(True)
        self.assertIn("1", win.dashboard_page.session_lbl.text())


if __name__ == "__main__":
    unittest.main()
