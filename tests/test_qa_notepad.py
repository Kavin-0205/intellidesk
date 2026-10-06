"""
Tests for General Question Answering + Save to Notepad + Context Memory.
Covers:
  - Intent classification accuracy (general_question, save_to_notepad flag, save_last_answer)
  - Q&A answer generation (dynamic, non-JSON)
  - Notepad control module (file creation)
  - Context memory (last_question / last_answer tracking)
  - Follow-up resolution via session context
  - E2E intent routing (handle_intent)
"""

import os
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ============================================================
# Module imports
# ============================================================
from llm.ai_router import classify_intent, answer_general_question
from automation.notepad_control import save_text_to_notepad, NOTEPAD_FILE
from context.context_manager import context
from intent_router import handle_intent


def test_intent_general_question_plain():
    """Plain question should classify as general_question with save_to_notepad=False."""
    print("\n[TEST 1] classify_intent: plain question")
    result = classify_intent("What is Java?")
    print(f"  Result: {result}")
    assert result.get("intent") == "general_question", f"Expected general_question, got {result.get('intent')}"
    assert result.get("save_to_notepad") is not True, "save_to_notepad should be False for plain question"
    print("  [PASS]")


def test_intent_general_question_with_notepad():
    """Combined question + save command should set save_to_notepad=True."""
    print("\n[TEST 2] classify_intent: question + save to Notepad")
    result = classify_intent("What is Java and save it in Notepad")
    print(f"  Result: {result}")
    assert result.get("intent") == "general_question", f"Expected general_question, got {result.get('intent')}"
    assert result.get("save_to_notepad") is True, "save_to_notepad should be True"
    print("  [PASS]")


def test_intent_save_last_answer():
    """'Save that in Notepad' should be save_last_answer."""
    print("\n[TEST 3] classify_intent: save previous answer")
    result = classify_intent("Save that in Notepad")
    print(f"  Result: {result}")
    assert result.get("intent") == "save_last_answer", f"Expected save_last_answer, got {result.get('intent')}"
    print("  [PASS]")


def test_answer_generation_not_json():
    """LLM answer must be natural text, not raw JSON."""
    print("\n[TEST 4] answer_general_question: non-JSON natural answer")
    answer = answer_general_question("What is Java?")
    # Safe print: strip characters that cp1252 can't handle
    safe_preview = answer[:100].encode("ascii", errors="replace").decode("ascii")
    print(f"  Answer: {safe_preview}...")
    assert isinstance(answer, str), "Answer must be a string"
    assert len(answer) > 20, "Answer too short"
    # Must not start with a JSON brace
    assert not answer.strip().startswith("{"), "Answer should not be raw JSON"
    assert "java" in answer.lower() or "programming" in answer.lower(), "Answer should be about Java"
    print("  [PASS]")


def test_answer_generation_software_testing():
    """Dynamic answer for software testing question."""
    print("\n[TEST 5] answer_general_question: software testing")
    answer = answer_general_question("What is software testing?")
    print(f"  Answer: {answer[:100]}...")
    assert len(answer) > 20
    assert "test" in answer.lower() or "software" in answer.lower()
    print("  [PASS]")


def test_notepad_module_creates_file():
    """save_text_to_notepad should create data/notepad_output.txt."""
    print("\n[TEST 6] save_text_to_notepad: file creation")
    result = save_text_to_notepad(
        text="Java is a high-level, object-oriented programming language.",
        question="What is Java?"
    )
    print(f"  Result: {result}")
    assert result.get("success") is True, f"Expected success, got: {result}"
    assert NOTEPAD_FILE.exists(), f"File not created at {NOTEPAD_FILE}"
    content = NOTEPAD_FILE.read_text(encoding="utf-8")
    assert "Java" in content
    assert "Question:" in content
    assert "Answer:" in content
    print("  [PASS]")


def test_context_tracks_last_question_answer():
    """After a Q&A intent, context.last_question/last_answer should be populated."""
    print("\n[TEST 7] context: last_question / last_answer tracking")
    intent_data = {
        "intent": "general_question",
        "question": "What is Selenium?",
        "save_to_notepad": False
    }
    fake_answer = "Selenium is a browser automation framework used for testing web applications."
    result_data = {"success": True, "answer": fake_answer}
    context.record_interaction("What is Selenium?", intent_data, result_data, fake_answer)

    assert context.last_question == "What is Selenium?", f"Got: {context.last_question}"
    assert context.last_answer == fake_answer, f"Got: {context.last_answer}"
    print(f"  last_question: {context.last_question}")
    print(f"  last_answer:   {context.last_answer[:60]}...")
    print("  [PASS]")


def test_context_summary_includes_qa():
    """get_context_summary should expose last_question/last_answer to LLM prompting."""
    print("\n[TEST 8] context: get_context_summary includes Q&A fields")
    summary = context.get_context_summary()
    print(f"  Summary keys: {list(summary.keys())}")
    assert "last_question" in summary
    assert "last_answer" in summary
    print("  [PASS]")


def test_followup_classification_with_context():
    """'Who developed it?' with Java in context should resolve to Java."""
    print("\n[TEST 9] classify_intent: follow-up with session context")
    session_ctx = {
        "last_question": "What is Java?",
        "last_answer": "Java is a high-level programming language by Sun Microsystems.",
        "current_application": None,
        "last_intent": "general_question"
    }
    result = classify_intent("Who developed it?", session_context=session_ctx)
    print(f"  Result: {result}")
    assert result.get("intent") == "general_question", f"Got: {result.get('intent')}"
    # The resolved question should reference Java
    question = result.get("question", "")
    assert "java" in question.lower() or "developed" in question.lower(), \
        f"Follow-up question not resolved to Java context: '{question}'"
    print("  [PASS]")


def test_e2e_handle_intent_qa_no_notepad():
    """E2E: handle_intent for plain Q&A should return answer, record context."""
    print("\n[TEST 10] handle_intent: Q&A without Notepad")
    intent_data = {"intent": "general_question", "question": "What is an API?", "save_to_notepad": False}
    result = handle_intent(intent_data, user_command="What is an API?", speak_response=False)
    print(f"  Response: {result.get('response', '')[:80]}...")
    assert result.get("success") is True
    assert len(result.get("response", "")) > 10
    # Context should now have last_question set
    assert context.last_question == "What is an API?"
    print("  [PASS]")


def test_e2e_handle_intent_qa_with_notepad():
    """E2E: handle_intent for Q&A + save to Notepad opens file."""
    print("\n[TEST 11] handle_intent: Q&A + save to Notepad")
    intent_data = {
        "intent": "general_question",
        "question": "What is machine learning?",
        "save_to_notepad": True
    }
    result = handle_intent(intent_data, user_command="What is machine learning and save it in Notepad", speak_response=False)
    print(f"  Response: {result.get('response', '')[:80]}...")
    assert result.get("success") is True
    assert NOTEPAD_FILE.exists()
    content = NOTEPAD_FILE.read_text(encoding="utf-8")
    print(f"  Notepad content preview: {content[:100]}")
    assert "machine learning" in content.lower() or "learning" in content.lower()
    print("  [PASS]")


def test_e2e_save_last_answer():
    """E2E: save_last_answer intent should save context.last_answer to Notepad."""
    print("\n[TEST 12] handle_intent: save_last_answer")
    # First set context with a known answer
    context.last_question = "What is cloud computing?"
    context.last_answer = "Cloud computing is the delivery of computing services over the internet."

    intent_data = {"intent": "save_last_answer", "destination": "notepad"}
    result = handle_intent(intent_data, user_command="Save that in Notepad", speak_response=False)
    print(f"  Response: {result.get('response')}")
    assert result.get("success") is True
    content = NOTEPAD_FILE.read_text(encoding="utf-8")
    assert "cloud" in content.lower() or "computing" in content.lower()
    print("  [PASS]")


def test_e2e_save_last_answer_no_previous():
    """save_last_answer with no previous Q&A should return graceful failure."""
    print("\n[TEST 13] handle_intent: save_last_answer with no prior Q&A")
    # Clear context
    context.last_question = None
    context.last_answer = None

    intent_data = {"intent": "save_last_answer", "destination": "notepad"}
    result = handle_intent(intent_data, user_command="Save that in Notepad", speak_response=False)
    print(f"  Response: {result.get('response')}")
    assert result.get("success") is False
    assert "ask me a question" in result.get("response", "").lower() or "don't have" in result.get("response", "").lower()
    print("  [PASS]")


if __name__ == "__main__":
    print("=" * 60)
    print("IntelliDesk Q&A + Notepad + Context Memory Test Suite")
    print("=" * 60)

    tests = [
        test_intent_general_question_plain,
        test_intent_general_question_with_notepad,
        test_intent_save_last_answer,
        test_answer_generation_not_json,
        test_answer_generation_software_testing,
        test_notepad_module_creates_file,
        test_context_tracks_last_question_answer,
        test_context_summary_includes_qa,
        test_followup_classification_with_context,
        test_e2e_handle_intent_qa_no_notepad,
        test_e2e_handle_intent_qa_with_notepad,
        test_e2e_save_last_answer,
        test_e2e_save_last_answer_no_previous,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {t.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    if failed == 0:
        print("[SUCCESS] All Q&A + Notepad + Context Memory tests passed!")
    else:
        print("[PARTIAL] Some tests failed. Review output above.")
    print("=" * 60)
