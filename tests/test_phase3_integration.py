"""
End-to-End simulated command integration test for Phase 3 features.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from llm.ai_router import classify_intent
from intent_router import handle_intent
from context.context_manager import context


def test_phase3_commands():
    print("\n--- TEST: Phase 3 Full Command Integration ---")

    test_commands = [
        ("Open Downloads", "file_action"),
        ("Find my Python files", "file_action"),
        ("Create a file called demo_test.txt", "file_action"),
        ("What's in my clipboard?", "clipboard_action"),
        ("Take a screenshot", "screen_action"),
        ("Search Google for Python tutorials", "web_search"),
        ("Search YouTube for jazz music", "web_search"),
        ("Press Enter", "keyboard_action"),
        ("Click", "mouse_action"),
    ]

    for cmd, expected_intent in test_commands:
        print(f"\n[Command]: '{cmd}'")
        intent_data = classify_intent(cmd, session_context=context.get_context_summary())
        print(f"[Detected Intent]: {intent_data.get('intent')} | Action: {intent_data.get('action')}")
        assert intent_data.get("intent") == expected_intent, f"Expected {expected_intent}, got {intent_data.get('intent')}"

        res = handle_intent(intent_data, user_command=cmd, speak_response=False)
        print(f"[Response]: {res.get('response')}")
        assert res.get("success") is True

    print("\n[SUCCESS] Phase 3 Command Integration tests passed!")


if __name__ == "__main__":
    test_phase3_commands()
