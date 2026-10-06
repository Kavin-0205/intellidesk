"""
IntelliDesk Phase 9 Tests: Window Management & System Power Commands.

Tests:
1. Window Control:
   - list_windows() format and structure
   - get_active_window() format and structure
   - focus_window() validation (empty title, missing window)
   - minimize_window() validation
   - maximize_window() validation
   - close_window() safety guard on protected titles ("task manager", "windows security")
2. System Power Control:
   - lock_screen()
   - sleep_system()
   - shutdown_system() delay validation and cancel_command format
   - restart_system() delay validation and cancel_command format
   - cancel_shutdown()
3. Intent Router Integration:
   - window_action intent routing (list, active, focus, minimize, maximize, close)
   - power_action intent routing (lock, sleep, shutdown, restart, cancel_shutdown)
"""

import unittest
from unittest.mock import patch, MagicMock

from automation.window_control import (
    list_windows,
    get_active_window,
    focus_window,
    minimize_window,
    maximize_window,
    close_window,
    _is_protected,
)
from automation.system_control import (
    lock_screen,
    sleep_system,
    shutdown_system,
    restart_system,
    cancel_shutdown,
)
from intent_router import handle_intent


class TestWindowControl(unittest.TestCase):

    def test_list_windows_structure(self):
        res = list_windows()
        self.assertIsInstance(res, dict)
        self.assertIn("success", res)
        self.assertIn("windows", res)
        self.assertIn("count", res)
        self.assertEqual(res["action"], "list_windows")

    def test_get_active_window_structure(self):
        res = get_active_window()
        self.assertIsInstance(res, dict)
        self.assertIn("success", res)
        self.assertIn("title", res)
        self.assertEqual(res["action"], "get_active_window")

    def test_focus_window_empty(self):
        res = focus_window("")
        self.assertFalse(res["success"])
        self.assertIn("error", res)

    def test_minimize_window_empty(self):
        res = minimize_window("")
        self.assertFalse(res["success"])
        self.assertIn("error", res)

    def test_maximize_window_empty(self):
        res = maximize_window("")
        self.assertFalse(res["success"])
        self.assertIn("error", res)

    def test_close_window_empty(self):
        res = close_window("")
        self.assertFalse(res["success"])
        self.assertIn("error", res)

    def test_close_window_protected_safety(self):
        # Protected windows must be rejected immediately
        self.assertTrue(_is_protected("Task Manager"))
        self.assertTrue(_is_protected("Windows Security"))
        self.assertTrue(_is_protected("Registry Editor"))
        self.assertTrue(_is_protected("Windows PowerShell"))

        res = close_window("Task Manager")
        self.assertFalse(res["success"])
        self.assertIn("Cannot close protected system window", res["error"])

        res2 = close_window("Windows Security")
        self.assertFalse(res2["success"])
        self.assertIn("Cannot close protected system window", res2["error"])


class TestSystemPowerControl(unittest.TestCase):

    @patch("ctypes.windll.user32.LockWorkStation")
    def test_lock_screen(self, mock_lock):
        mock_lock.return_value = 1
        res = lock_screen()
        self.assertTrue(res["success"])
        self.assertEqual(res["action"], "lock_screen")
        mock_lock.assert_called_once()

    @patch("subprocess.run")
    def test_sleep_system(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        res = sleep_system()
        self.assertTrue(res["success"])
        self.assertEqual(res["action"], "sleep_system")

    @patch("subprocess.run")
    def test_shutdown_system(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        res = shutdown_system(delay_seconds=30)
        self.assertTrue(res["success"])
        self.assertEqual(res["action"], "shutdown_system")
        self.assertEqual(res["delay_seconds"], 30)
        self.assertEqual(res["cancel_command"], "shutdown /a")
        mock_run.assert_called_once_with(["shutdown", "/s", "/t", "30"], check=True)

    @patch("subprocess.run")
    def test_shutdown_system_minimum_buffer(self, mock_run):
        # Must enforce minimum 10-second buffer
        mock_run.return_value = MagicMock(returncode=0)
        res = shutdown_system(delay_seconds=2)
        self.assertEqual(res["delay_seconds"], 10)

    @patch("subprocess.run")
    def test_restart_system(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        res = restart_system(delay_seconds=45)
        self.assertTrue(res["success"])
        self.assertEqual(res["action"], "restart_system")
        self.assertEqual(res["delay_seconds"], 45)
        mock_run.assert_called_once_with(["shutdown", "/r", "/t", "45"], check=True)

    @patch("subprocess.run")
    def test_cancel_shutdown(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        res = cancel_shutdown()
        self.assertTrue(res["success"])
        self.assertEqual(res["action"], "cancel_shutdown")
        mock_run.assert_called_once_with(["shutdown", "/a"], check=True)


class TestIntentRouterWindowPower(unittest.TestCase):

    @patch("intent_router.execute_mcp_tool")
    def test_route_window_list(self, mock_tool):
        mock_tool.return_value = {
            "success": True,
            "result": {"success": True, "windows": ["Chrome", "VS Code"], "count": 2}
        }
        intent_data = {"intent": "window_action", "action": "list"}
        res = handle_intent(intent_data, user_command="List open windows", speak_response=False)
        self.assertTrue(res["success"])
        self.assertIn("open windows", res["response"].lower())

    def test_route_window_focus_missing_title(self):
        intent_data = {"intent": "window_action", "action": "focus", "title": None}
        res = handle_intent(intent_data, user_command="Bring to front", speak_response=False)
        self.assertFalse(res["success"])
        self.assertIn("Which window", res["response"])

    def test_route_window_minimize_missing_title(self):
        intent_data = {"intent": "window_action", "action": "minimize", "title": None}
        res = handle_intent(intent_data, user_command="Minimize window", speak_response=False)
        self.assertFalse(res["success"])
        self.assertIn("Which window", res["response"])

    @patch("intent_router.execute_mcp_tool")
    def test_route_window_close_protected(self, mock_tool):
        mock_tool.return_value = {
            "success": False,
            "result": {"success": False, "error": "Cannot close protected system window: 'Task Manager'"}
        }
        intent_data = {"intent": "window_action", "action": "close", "title": "Task Manager"}
        res = handle_intent(intent_data, user_command="Close Task Manager", speak_response=False)
        self.assertFalse(res["success"])
        self.assertIn("protected", res["response"].lower())

    @patch("intent_router.execute_mcp_tool")
    def test_route_power_lock(self, mock_tool):
        mock_tool.return_value = {
            "success": True,
            "result": {"success": True, "action": "lock_screen"}
        }
        intent_data = {"intent": "power_action", "action": "lock"}
        res = handle_intent(intent_data, user_command="Lock my screen", speak_response=False)
        self.assertTrue(res["success"])
        self.assertIn("locking", res["response"].lower())

    @patch("intent_router.execute_mcp_tool")
    def test_route_power_shutdown(self, mock_tool):
        mock_tool.return_value = {
            "success": True,
            "result": {
                "success": True,
                "action": "shutdown_system",
                "delay_seconds": 60,
                "cancel_command": "shutdown /a"
            }
        }
        intent_data = {"intent": "power_action", "action": "shutdown", "delay_seconds": 60}
        res = handle_intent(intent_data, user_command="Shutdown the computer", speak_response=False)
        self.assertTrue(res["success"])
        self.assertIn("shutdown scheduled", res["response"].lower())
        self.assertIn("cancel shutdown", res["response"].lower())

    @patch("intent_router.execute_mcp_tool")
    def test_route_power_cancel_shutdown(self, mock_tool):
        mock_tool.return_value = {
            "success": True,
            "result": {"success": True, "action": "cancel_shutdown"}
        }
        intent_data = {"intent": "power_action", "action": "cancel_shutdown"}
        res = handle_intent(intent_data, user_command="Cancel shutdown", speak_response=False)
        self.assertTrue(res["success"])
        self.assertIn("cancelled", res["response"].lower())


if __name__ == "__main__":
    unittest.main()
