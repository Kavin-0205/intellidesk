"""
IntelliDesk Regression & Robustness Test Suite.

Validates fixes for:
1. Context resolution (Chrome, Notepad, Calculator, pronouns, query preservation)
2. Ambiguous destructive language handling
3. Window target resolution and alias mapping
4. Argument validation and missing parameter recovery
5. File operation preconditions (directory exists, destination conflict)
6. Git operation preconditions (branch already exists)
7. Clipboard reliability and write-back verification
8. Bounded network timeout, connection reset, and HTTP 429 quota handling
9. Destructive safety gating preservation
10. OCR multi-target extraction
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from context.context_manager import ContextManager, context
from llm.ai_router import (
    classify_intent,
    deterministic_fallback_predict,
    validate_and_normalize_intent,
)
from llm.grok_client import (
    execute_llm_request,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMConnectionError,
)
from intent_router import handle_intent
from automation import file_control as file_ctl
from automation import git_control as git_ctl
from automation import keyboard_control as kbd_ctl
from automation import window_control as win_ctl
from screen.ocr import extract_text_from_image, _get_reader


class TestContextResolution(unittest.TestCase):
    """Tests 1-8: Context follow-ups, pronoun resolution, and ambiguity handling."""

    def setUp(self):
        context._init_state()

    @patch("llm.ai_router.execute_llm_request")
    def test_01_open_chrome_close_it(self, mock_llm):
        mock_llm.return_value = json.dumps({"intent": "close_application", "application": "it"})
        context.set_current_app("chrome")
        resolved = context.resolve_reference("Close it")
        self.assertEqual(resolved, "close chrome")

        intent = classify_intent("Close it", session_context=context.get_context_summary())
        self.assertEqual(intent.get("intent"), "close_application")
        self.assertEqual(intent.get("application"), "chrome")

    @patch("llm.ai_router.execute_llm_request")
    def test_02_open_notepad_close_it(self, mock_llm):
        mock_llm.return_value = json.dumps({"intent": "close_application", "application": "it"})
        context.set_current_app("notepad")
        resolved = context.resolve_reference("Close it")
        self.assertEqual(resolved, "close notepad")

        intent = classify_intent("Close it", session_context=context.get_context_summary())
        self.assertEqual(intent.get("intent"), "close_application")
        self.assertEqual(intent.get("application"), "notepad")

    @patch("llm.ai_router.execute_llm_request")
    def test_03_open_chrome_open_notepad_close_it(self, mock_llm):
        mock_llm.return_value = json.dumps({"intent": "close_application", "application": "it"})
        context.set_current_app("chrome")
        context.set_current_app("notepad")
        self.assertEqual(context.current_application, "notepad")

        resolved = context.resolve_reference("Close it")
        self.assertEqual(resolved, "close notepad")

        intent = classify_intent("Close it", session_context=context.get_context_summary())
        self.assertEqual(intent.get("intent"), "close_application")
        self.assertEqual(intent.get("application"), "notepad")

    @patch("llm.ai_router.execute_llm_request")
    def test_04_open_chrome_minimize_it(self, mock_llm):
        mock_llm.return_value = json.dumps({"intent": "window_action", "action": "minimize", "title": "it"})
        context.set_current_app("chrome")
        resolved = context.resolve_reference("Minimize it")
        self.assertEqual(resolved, "minimize chrome")

        intent = classify_intent("Minimize it", session_context=context.get_context_summary())
        self.assertEqual(intent.get("intent"), "window_action")
        self.assertEqual(intent.get("action"), "minimize")
        self.assertEqual(intent.get("title"), "chrome")

    @patch("llm.ai_router.execute_llm_request")
    def test_05_open_chrome_focus_it(self, mock_llm):
        mock_llm.return_value = json.dumps({"intent": "window_action", "action": "focus", "title": "it"})
        context.set_current_app("chrome")
        resolved = context.resolve_reference("Focus it")
        self.assertEqual(resolved, "focus chrome")

        intent = classify_intent("Focus it", session_context=context.get_context_summary())
        self.assertEqual(intent.get("intent"), "window_action")
        self.assertEqual(intent.get("action"), "focus")
        self.assertEqual(intent.get("title"), "chrome")

    @patch("llm.ai_router.execute_llm_request")
    def test_06_open_calc_minimize_it(self, mock_llm):
        mock_llm.return_value = json.dumps({"intent": "window_action", "action": "minimize", "title": "it"})
        context.set_current_app("calculator")
        resolved = context.resolve_reference("minimize it")
        self.assertEqual(resolved, "minimize calculator")

        intent = classify_intent("minimize it", session_context=context.get_context_summary())
        self.assertEqual(intent.get("intent"), "window_action")
        self.assertEqual(intent.get("action"), "minimize")
        self.assertEqual(intent.get("title"), "calculator")

    def test_07_ambiguous_shut_it_down(self):
        context.set_current_app("notepad")
        self.assertTrue(context.is_ambiguous_destructive("shut it down"))

        # ai_router must detect ambiguity and request clarification without cloud LLM call
        res = classify_intent("shut it down", session_context=context.get_context_summary())
        self.assertEqual(res.get("intent"), "clarification_needed")
        self.assertIn("close the current application or shut down Windows", res.get("message", ""))

        # handle_intent must NOT execute any shutdown or close
        routed = handle_intent(res, user_command="shut it down", speak_response=False)
        self.assertFalse(routed.get("success"))
        self.assertTrue(routed.get("clarification_needed"))

    def test_08_context_query_not_window_action(self):
        context.set_current_app("notepad")

        queries = [
            "What application am I using?",
            "What is my active application?",
            "What am I working on?",
            "What is open?",
            "What app is open?",
            "What app is currently open?",
            "What application is open?",
            "What program is open?",
            "Which application is open?",
            "What is currently open?",
            "What am I currently using?",
        ]
        for q in queries:
            # resolve_reference must NOT corrupt the query
            resolved = context.resolve_reference(q)
            self.assertEqual(resolved, q)

            # fallback / classifier must route to context_query, never window_action
            pred = deterministic_fallback_predict(q, session_context=context.get_context_summary())
            self.assertEqual(pred.get("intent"), "context_query", f"Query '{q}' failed to route to context_query")


class TestFilePreconditions(unittest.TestCase):
    """Tests 9-11: File & directory preconditions and conflict prevention."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_09_create_existing_folder(self):
        folder_path = os.path.join(self.test_dir, "existing_folder")
        # First creation succeeds
        res1 = file_ctl.create_folder(folder_path)
        self.assertTrue(res1.get("success"))

        # Second creation detects existing directory
        res2 = file_ctl.create_folder(folder_path)
        self.assertFalse(res2.get("success"))
        self.assertTrue(res2.get("already_exists"))
        self.assertIn("already exists", res2.get("error", ""))

    def test_10_rename_file_destination_exists(self):
        src = os.path.join(self.test_dir, "src.txt")
        dst = os.path.join(self.test_dir, "dst.txt")
        Path(src).write_text("source content", encoding="utf-8")
        Path(dst).write_text("destination content", encoding="utf-8")

        # Rename with overwrite=False must reject conflict
        res = file_ctl.rename_file(src, dst, overwrite=False)
        self.assertFalse(res.get("success"))
        self.assertTrue(res.get("destination_exists"))
        self.assertIn("already exists", res.get("error", ""))
        # Verify destination was NOT overwritten
        self.assertEqual(Path(dst).read_text(encoding="utf-8"), "destination content")

    def test_11_rename_folder_destination_exists(self):
        src_f = os.path.join(self.test_dir, "src_dir")
        dst_f = os.path.join(self.test_dir, "dst_dir")
        os.makedirs(src_f, exist_ok=True)
        os.makedirs(dst_f, exist_ok=True)

        res = file_ctl.rename_file(src_f, dst_f, overwrite=False)
        self.assertFalse(res.get("success"))
        self.assertTrue(res.get("destination_exists"))
        self.assertIn("folder 'dst_dir' already exists", res.get("error", ""))


class TestGitPreconditions(unittest.TestCase):
    """Test 12: Git operation preconditions."""

    def test_12_create_already_existing_branch(self):
        # Test git_create_branch when branch already exists in repo
        with patch("automation.git_control._find_repo") as mock_find:
            mock_repo = MagicMock()
            branch1 = MagicMock()
            branch1.name = "main"
            mock_repo.branches = [branch1]
            mock_find.return_value = mock_repo

            # Creating 'main' when 'main' already exists
            res = git_ctl.git_create_branch("main", checkout_if_exists=False)
            self.assertFalse(res.get("success"))
            self.assertTrue(res.get("branch_exists"))
            self.assertIn("Would you like to switch to it instead?", res.get("error", ""))


class TestClipboardReliability(unittest.TestCase):
    """Test 13: Clipboard write, synchronization, and read-back verification."""

    def test_13_set_and_verify_clipboard(self):
        test_payload = "IntelliDesk Reliability Verification Payload 42"
        res_set = kbd_ctl.set_clipboard_text(test_payload)
        self.assertTrue(res_set.get("success"), f"Set clipboard failed: {res_set.get('error')}")
        self.assertTrue(res_set.get("verified"))

        res_get = kbd_ctl.get_clipboard_text()
        self.assertTrue(res_get.get("success"))
        self.assertEqual(res_get.get("text"), test_payload)


class TestNetworkResilience(unittest.TestCase):
    """Tests 14-16: Bounded network timeouts, connection resets, and HTTP 429 quota handling."""

    @patch("llm.grok_client.client.chat.completions.create")
    def test_14_simulated_timeout(self, mock_create):
        from openai import APITimeoutError
        mock_create.side_effect = APITimeoutError("Request timed out")

        with self.assertRaises(LLMTimeoutError) as ctx:
            execute_llm_request(
                messages=[{"role": "user", "content": "hi"}],
                timeout=1.0,
                max_retries=1,
            )
        self.assertIn("timed out", str(ctx.exception).lower())

    @patch("llm.grok_client.client.chat.completions.create")
    def test_15_simulated_connection_reset(self, mock_create):
        from openai import APIConnectionError
        mock_create.side_effect = APIConnectionError(message="Connection reset by peer", request=MagicMock())

        with self.assertRaises(LLMConnectionError) as ctx:
            execute_llm_request(
                messages=[{"role": "user", "content": "hi"}],
                timeout=1.0,
                max_retries=1,
            )
        self.assertIn("connection failed", str(ctx.exception).lower())

    @patch("llm.grok_client.client.chat.completions.create")
    def test_16_simulated_http_429_quota(self, mock_create):
        from openai import RateLimitError
        mock_response = MagicMock()
        mock_response.headers = {"retry-after": "45"}
        mock_create.side_effect = RateLimitError(
            message="Rate limit exceeded",
            response=mock_response,
            body={"error": "quota_exceeded"},
        )

        with self.assertRaises(LLMRateLimitError) as ctx:
            execute_llm_request(
                messages=[{"role": "user", "content": "hi"}],
                timeout=5.0,
                max_retries=0,
            )
        self.assertEqual(ctx.exception.status_code, 429)
        self.assertEqual(ctx.exception.retry_after, 45.0)


class TestRouterArgumentValidation(unittest.TestCase):
    """Tests 17-20: Intent schema validation and argument recovery."""

    def test_17_missing_required_url(self):
        # Empty URL in open_url intent
        raw_url = {"intent": "open_url", "url": ""}
        validated_url = validate_and_normalize_intent(raw_url, user_command="open url")
        self.assertEqual(validated_url.get("intent"), "validation_error")
        self.assertEqual(validated_url.get("missing_field"), "url")

        # Empty / vague application in open_application
        raw_app = {"intent": "open_application", "application": ""}
        validated_app = validate_and_normalize_intent(raw_app, user_command="open something vague")
        self.assertEqual(validated_app.get("intent"), "validation_error")
        self.assertEqual(validated_app.get("missing_field"), "application")

    def test_18_missing_required_file_path(self):
        raw = {"intent": "file_action", "action": "create_folder", "path": ""}
        validated = validate_and_normalize_intent(raw, user_command="create folder")
        self.assertEqual(validated.get("intent"), "validation_error")
        self.assertEqual(validated.get("missing_field"), "path")

    def test_19_invalid_intent_structure(self):
        raw = {"not_an_intent": "foo"}
        validated = validate_and_normalize_intent(raw, user_command="do something")
        self.assertEqual(validated.get("intent"), "unknown")

    def test_20_missing_window_target(self):
        raw = {"intent": "window_action", "action": "minimize", "title": ""}
        validated = validate_and_normalize_intent(raw, user_command="minimize", session_context=None)
        self.assertEqual(validated.get("intent"), "validation_error")
        self.assertEqual(validated.get("missing_field"), "title")


class TestSafetyGating(unittest.TestCase):
    """Tests 21-22: Destructive command interception and ambiguous destructive language."""

    @patch("intent_router.execute_mcp_tool")
    def test_21_destructive_command_requires_confirmation(self, mock_mcp):
        # Mock MCP so real OS shutdown is not called
        mock_mcp.return_value = {"success": True, "action": "shutdown_system", "delay_seconds": 60}

        raw_shutdown = {"intent": "power_action", "action": "shutdown", "delay_seconds": 60}
        routed = handle_intent(raw_shutdown, user_command="Shutdown the computer", speak_response=False)
        self.assertTrue(routed.get("success"))
        self.assertIn("Cancel shutdown", routed.get("response", ""))

    def test_22_ambiguous_destructive_phrase_intercepted(self):
        context._init_state()
        context.set_current_app("chrome")
        # 'shut it down' must be intercepted by confirmation/clarification gate
        routed = handle_intent(
            {"intent": "power_action", "action": "shutdown"},
            user_command="shut it down",
            speak_response=False,
        )
        self.assertFalse(routed.get("success"))
        self.assertTrue(routed.get("clarification_needed"))
        self.assertIn("Do you want to close the current application or shut down Windows?", routed.get("response", ""))


class TestOCRExtraction(unittest.TestCase):
    """Test 23: OCR extraction across the four benchmark targets."""

    def test_23_ocr_targets_extraction(self):
        reader = _get_reader()
        if reader is None:
            self.skipTest("EasyOCR model not available")

        from PIL import Image, ImageDraw

        targets = [
            ("ocr_target_1", "IntelliDesk OCR Test 12345"),
            ("ocr_target_2", "IEEE Conference Benchmark 2026"),
            ("ocr_target_3", "Session Context Multi-Modal Automation"),
            ("ocr_target_4", "Error: Process terminated with status code 0x80004005"),
        ]

        temp_dir = tempfile.mkdtemp()
        try:
            for tid, text in targets:
                img = Image.new("RGB", (800, 200), color=(255, 255, 255))
                draw = ImageDraw.Draw(img)
                draw.text((30, 80), text, fill=(0, 0, 0))
                p = os.path.join(temp_dir, f"{tid}.png")
                img.save(p)

                res = extract_text_from_image(p)
                self.assertTrue(res.get("success"), f"OCR extraction failed for {tid}")
                detected = res.get("text", "")

                if tid == "ocr_target_1":
                    self.assertIn("IntelliDesk", detected)
                    self.assertIn("12345", detected)
                elif tid == "ocr_target_2":
                    # Previously missed 'IEEE Conference' entirely!
                    self.assertIn("IEEE Conference", detected, f"Expected 'IEEE Conference' in '{detected}'")
                    self.assertIn("Benchmark", detected)
                elif tid == "ocr_target_3":
                    self.assertEqual(detected, text)
                elif tid == "ocr_target_4":
                    # Previously missed 'Error:' and merged 'terminatedwIth'
                    self.assertIn("Error:", detected, f"Expected 'Error:' in '{detected}'")
                    self.assertIn("0x80004005", detected)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
