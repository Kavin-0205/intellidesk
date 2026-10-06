"""
End-to-End simulated command integration test for IntelliDesk Router.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from llm.ai_router import classify_intent
from intent_router import handle_intent
from context.context_manager import context


def test_router_integration():
    print("\n--- TEST: Intent Router Integration ---")

    commands = [
        ("What is machine learning?", "general_question"),
        ("What applications are installed?", "list_applications"),
        ("What is my volume?", "system_volume"),
        ("What is my brightness?", "system_brightness"),
        ("What am I working on?", "context_query"),
    ]

    for cmd, expected_intent in commands:
        print(f"\n[Command]: '{cmd}'")
        intent_data = classify_intent(cmd, session_context=context.get_context_summary())
        print(f"[Detected Intent]: {intent_data.get('intent')}")
        assert intent_data.get("intent") == expected_intent, f"Expected {expected_intent}, got {intent_data.get('intent')}"

        res = handle_intent(intent_data, user_command=cmd, speak_response=False)
        print(f"[Response]: {res.get('response')}")
        assert res.get("success") is True

    print("\n[SUCCESS] Router Integration tests passed!")


if __name__ == "__main__":
    test_router_integration()
