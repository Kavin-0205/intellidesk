"""
IntelliDesk MongoDB Persistence Test Suite (Phase 7).
Tests:
  1. connect() - graceful success or graceful failure
  2. record_app_event - does not crash if MongoDB unavailable
  3. record_question - does not crash if MongoDB unavailable
  4. record_command - does not crash if MongoDB unavailable
  5. get_status - returns structured status dict
  6. get_app_frequency - returns list (empty OK if not connected)
  7. get_recent_questions - returns list (empty OK)
  8. get_recent_commands - returns list (empty OK)
  9. memory/app_history.py: record_app_open dual-write
 10. memory/conversation_memory.py: save_qa_pair
 11. memory/conversation_memory.py: save_command
 12. E2E: Q&A via handle_intent auto-saves to MongoDB (no crash)
"""

import sys
from pathlib import Path

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database import mongodb
from memory import app_history, conversation_memory
from intent_router import handle_intent


# ============================================================
# TESTS
# ============================================================

def test_connect_graceful():
    """connect() must not crash regardless of MongoDB availability."""
    print("\n[TEST 1] mongodb.connect(): graceful")
    result = mongodb.connect()
    print(f"  Connected: {result} (OK whether True or False)")
    # No assertion needed — just must not raise
    print("  [PASS]")


def test_record_app_event_no_crash():
    """record_app_event must never crash regardless of connection status."""
    print("\n[TEST 2] mongodb.record_app_event(): no crash")
    result = mongodb.record_app_event("Google Chrome", "open", "test")
    print(f"  Result: {result} (True if connected, False if not — both OK)")
    assert isinstance(result, bool)
    print("  [PASS]")


def test_record_question_no_crash():
    """record_question must not crash."""
    print("\n[TEST 3] mongodb.record_question(): no crash")
    result = mongodb.record_question("What is Python?", "Python is a programming language.")
    print(f"  Result: {result}")
    assert isinstance(result, bool)
    print("  [PASS]")


def test_record_command_no_crash():
    """record_command must not crash."""
    print("\n[TEST 4] mongodb.record_command(): no crash")
    result = mongodb.record_command("Open Chrome", "open_application", True, "Opening Chrome.", "test")
    print(f"  Result: {result}")
    assert isinstance(result, bool)
    print("  [PASS]")


def test_get_status():
    """get_status must return a structured dict."""
    print("\n[TEST 5] mongodb.get_status(): returns structured dict")
    status = mongodb.get_status()
    print(f"  Status: connected={status.get('connected')}, db={status.get('database')}")
    assert "connected" in status
    assert "database" in status
    assert status["database"] == "intellidesk"
    print("  [PASS]")


def test_get_app_frequency_no_crash():
    """get_app_frequency must return a list (empty if not connected)."""
    print("\n[TEST 6] mongodb.get_app_frequency(): returns list")
    result = mongodb.get_app_frequency(limit=5)
    print(f"  Result type: {type(result).__name__}, length: {len(result)}")
    assert isinstance(result, list)
    print("  [PASS]")


def test_get_recent_questions_no_crash():
    """get_recent_questions must return a list."""
    print("\n[TEST 7] mongodb.get_recent_questions(): returns list")
    result = mongodb.get_recent_questions(limit=5)
    print(f"  Result type: {type(result).__name__}, length: {len(result)}")
    assert isinstance(result, list)
    print("  [PASS]")


def test_get_recent_commands_no_crash():
    """get_recent_commands must return a list."""
    print("\n[TEST 8] mongodb.get_recent_commands(): returns list")
    result = mongodb.get_recent_commands(limit=5)
    print(f"  Result type: {type(result).__name__}, length: {len(result)}")
    assert isinstance(result, list)
    print("  [PASS]")


def test_app_history_record_open():
    """memory/app_history.record_app_open() must dual-write without crash."""
    print("\n[TEST 9] memory.app_history.record_app_open(): dual-write")
    result = app_history.record_app_open("VS Code", source="test")
    print(f"  Result: {result}")
    assert "app" in result
    assert result.get("count", 0) >= 1
    print("  [PASS]")


def test_conversation_memory_save_qa():
    """memory/conversation_memory.save_qa_pair() must not crash."""
    print("\n[TEST 10] memory.conversation_memory.save_qa_pair(): no crash")
    result = conversation_memory.save_qa_pair(
        "What is machine learning?",
        "Machine learning is a branch of AI that enables learning from data."
    )
    print(f"  Result: {result}")
    assert isinstance(result, bool)
    print("  [PASS]")


def test_conversation_memory_save_command():
    """memory/conversation_memory.save_command() must not crash."""
    print("\n[TEST 11] memory.conversation_memory.save_command(): no crash")
    result = conversation_memory.save_command(
        "Open Chrome", "open_application", True, "Opening Chrome.", "test"
    )
    print(f"  Result: {result}")
    assert isinstance(result, bool)
    print("  [PASS]")


def test_e2e_qa_auto_saves_to_mongodb():
    """E2E: Q&A intent should auto-save to MongoDB without crashing."""
    print("\n[TEST 12] handle_intent: Q&A auto-saves to MongoDB")
    intent_data = {
        "intent": "general_question",
        "question": "What is cloud computing?",
        "save_to_notepad": False,
    }
    result = handle_intent(intent_data, user_command="What is cloud computing?", speak_response=False)
    safe_preview = result.get('response', '')[:60].encode("ascii", errors="replace").decode("ascii")
    print(f"  Response: {safe_preview}...")
    assert result.get("success") is True
    assert len(result.get("response", "")) > 10
    # Verify it went to MongoDB (or gracefully skipped)
    if mongodb.is_connected():
        questions = mongodb.get_recent_questions(limit=3)
        found = any("cloud" in q.get("question", "").lower() for q in questions)
        print(f"  Found in MongoDB: {found}")
        assert found, "Q&A should be persisted to MongoDB"
    else:
        print("  MongoDB not available — graceful skip")
    print("  [PASS]")


if __name__ == "__main__":
    print("=" * 60)
    print("IntelliDesk MongoDB Persistence Test Suite (Phase 7)")
    print("=" * 60)

    tests = [
        test_connect_graceful,
        test_record_app_event_no_crash,
        test_record_question_no_crash,
        test_record_command_no_crash,
        test_get_status,
        test_get_app_frequency_no_crash,
        test_get_recent_questions_no_crash,
        test_get_recent_commands_no_crash,
        test_app_history_record_open,
        test_conversation_memory_save_qa,
        test_conversation_memory_save_command,
        test_e2e_qa_auto_saves_to_mongodb,
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
        print("[SUCCESS] All MongoDB tests passed!")
    else:
        print("[PARTIAL] Some tests failed. Review above.")
    print("=" * 60)
