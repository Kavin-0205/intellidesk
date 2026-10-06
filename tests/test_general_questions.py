"""
Unit test for General AI Questions pipeline.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from llm.ai_router import classify_intent, answer_general_question
from intent_router import handle_intent


def test_general_questions():
    print("\n--- TEST: General AI Questions ---")
    questions = [
        "What is software testing?",
        "Explain polymorphism in object oriented programming.",
        "What is an operating system?"
    ]

    for q in questions:
        print(f"\n[Prompt]: {q}")
        intent_data = classify_intent(q)
        print(f"[Detected Intent]: {intent_data}")
        assert intent_data.get("intent") == "general_question", f"Expected general_question, got {intent_data}"

        # Execute through router (with speak_response=False for automated test)
        res = handle_intent(intent_data, user_command=q, speak_response=False)
        print(f"[AI Answer]: {res.get('response')}")
        assert res.get("success") is True
        assert len(res.get("response", "")) > 10

    print("\n[SUCCESS] All General Question tests passed!")


if __name__ == "__main__":
    test_general_questions()
