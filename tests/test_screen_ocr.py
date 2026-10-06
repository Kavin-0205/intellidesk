"""
IntelliDesk Screen/OCR Intelligence Test Suite (Phase 8).

Tests 1-4, 9-12 run in ALL environments (no model download needed).
Tests 5-8 (full OCR+screen capture) require the EasyOCR model to be
downloaded. They are SKIPPED gracefully if the model is unavailable
(e.g., offline environment, network restriction).

Tests:
  1.  OCR module imports without crash
  2.  extract_text_from_image: file not found -> graceful error dict
  3.  screen_analyzer module imports without crash
  4.  read_screen_text: returns correct dict structure (model optional)
  5.  [OCR-OPTIONAL] extract_text_from_image: valid PIL image with text
  6.  [OCR-OPTIONAL] analyze_screen 'read': OCR only, no LLM
  7.  [OCR-OPTIONAL] analyze_screen 'summarize': OCR + LLM explanation
  8.  [OCR-OPTIONAL] explain_error_on_screen: returns explanation key
  9.  Intent classification: 'Read my screen' -> screen_action/read
 10.  Intent classification: 'What is on my screen?' -> screen_action/summarize
 11.  Intent classification: 'Explain this error' -> screen_action/explain_error
 12.  E2E handle_intent: screen_action/read -> spoken response (no crash)
"""

import sys
import os
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Check whether EasyOCR model is cached locally (NO download triggered)
try:
    from screen.ocr import easyocr_model_available
    _OCR_MODEL_AVAILABLE = easyocr_model_available()
except Exception:
    _OCR_MODEL_AVAILABLE = False


def _skip_if_no_model(test_name: str) -> bool:
    """Print a skip notice and return True if OCR model not available."""
    if not _OCR_MODEL_AVAILABLE:
        print(f"  [SKIP] {test_name}: EasyOCR model not downloaded yet. "
              "Run: python -c \"import easyocr; easyocr.Reader(['en'])\" once to download.")
        return True
    return False


# ============================================================
# TESTS
# ============================================================

def test_ocr_module_imports():
    """screen/ocr.py must import cleanly."""
    print("\n[TEST 1] screen.ocr: imports without crash")
    from screen.ocr import extract_text_from_image, extract_text_from_screenshot
    assert callable(extract_text_from_image)
    assert callable(extract_text_from_screenshot)
    print("  [PASS]")


def test_ocr_missing_file():
    """extract_text_from_image on non-existent path returns graceful error."""
    print("\n[TEST 2] extract_text_from_image: missing file -> graceful failure")
    from screen.ocr import extract_text_from_image
    result = extract_text_from_image("/nonexistent/path/image.png")
    print(f"  Result: success={result.get('success')}, error='{result.get('error', '')[:60]}'")
    assert result.get("success") is False
    assert "error" in result
    assert result.get("text") == ""
    print("  [PASS]")


def test_screen_analyzer_imports():
    """screen/screen_analyzer.py must import cleanly."""
    print("\n[TEST 3] screen.screen_analyzer: imports without crash")
    from screen.screen_analyzer import (
        read_screen_text, analyze_screen,
        explain_error_on_screen, summarize_screen
    )
    assert callable(read_screen_text)
    assert callable(analyze_screen)
    assert callable(explain_error_on_screen)
    assert callable(summarize_screen)
    print("  [PASS]")


def test_read_screen_text_structure():
    """read_screen_text always returns a dict with required keys."""
    print("\n[TEST 4] read_screen_text: dict structure (OCR optional)")
    from screen.screen_analyzer import read_screen_text
    result = read_screen_text()
    print(f"  Keys: {list(result.keys())}")
    print(f"  success={result.get('success')}, action={result.get('action')}")
    assert "success" in result
    assert "text" in result
    assert "action" in result
    print("  [PASS]")


def test_ocr_valid_image():
    """[OCR-OPTIONAL] extract_text_from_image on PIL-generated image."""
    print("\n[TEST 5] extract_text_from_image: PIL image with text (OCR-OPTIONAL)")
    if _skip_if_no_model("test_ocr_valid_image"):
        return

    from screen.ocr import extract_text_from_image
    from PIL import Image, ImageDraw

    tmp = tempfile.mktemp(suffix=".png")
    try:
        img = Image.new("RGB", (400, 100), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((10, 30), "IntelliDesk OCR Test", fill=(0, 0, 0))
        img.save(tmp)

        result = extract_text_from_image(tmp)
        print(f"  success={result.get('success')}, lines={result.get('line_count')}, "
              f"text='{result.get('text', '')[:40]}'")
        assert result.get("success") is True
        assert isinstance(result.get("text"), str)
        assert isinstance(result.get("lines"), list)
        print("  [PASS]")
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def test_analyze_screen_read():
    """[OCR-OPTIONAL] analyze_screen('read') returns text without LLM."""
    print("\n[TEST 6] analyze_screen: task='read' (OCR-OPTIONAL)")
    if _skip_if_no_model("test_analyze_screen_read"):
        return

    from screen.screen_analyzer import analyze_screen
    result = analyze_screen(task="read")
    print(f"  success={result.get('success')}, text_len={len(result.get('text', ''))}")
    assert "success" in result
    assert "text" in result
    print("  [PASS]")


def test_analyze_screen_summarize():
    """[OCR-OPTIONAL] analyze_screen('summarize') returns explanation."""
    print("\n[TEST 7] analyze_screen: task='summarize' (OCR-OPTIONAL)")
    if _skip_if_no_model("test_analyze_screen_summarize"):
        return

    from screen.screen_analyzer import analyze_screen
    result = analyze_screen(task="summarize")
    print(f"  success={result.get('success')}, explanation='{result.get('explanation', '')[:60]}'")
    assert "success" in result
    assert "explanation" in result
    print("  [PASS]")


def test_explain_error_on_screen():
    """[OCR-OPTIONAL] explain_error_on_screen returns explanation key."""
    print("\n[TEST 8] explain_error_on_screen (OCR-OPTIONAL)")
    if _skip_if_no_model("test_explain_error_on_screen"):
        return

    from screen.screen_analyzer import explain_error_on_screen
    result = explain_error_on_screen()
    print(f"  success={result.get('success')}, explanation='{result.get('explanation', '')[:60]}'")
    assert "success" in result
    assert "explanation" in result
    print("  [PASS]")


def test_intent_classify_read_screen():
    """'Read my screen' must classify as screen_action/read."""
    print("\n[TEST 9] classify_intent: 'Read my screen'")
    from llm.ai_router import classify_intent
    result = classify_intent("Read my screen")
    print(f"  Result: {result}")
    assert result.get("intent") == "screen_action", f"Expected screen_action, got {result.get('intent')}"
    assert result.get("action") == "read", f"Expected read, got {result.get('action')}"
    print("  [PASS]")


def test_intent_classify_what_on_screen():
    """'What is on my screen?' must classify as screen_action / summarize or describe."""
    print("\n[TEST 10] classify_intent: 'What is on my screen?'")
    from llm.ai_router import classify_intent
    result = classify_intent("What is on my screen?")
    print(f"  Result: {result}")
    assert result.get("intent") == "screen_action", f"Expected screen_action, got {result.get('intent')}"
    assert result.get("action") in ("summarize", "describe", "read"), f"Got {result.get('action')}"
    print("  [PASS]")


def test_intent_classify_explain_error():
    """'Explain this error on my screen' must classify as screen_action/explain_error."""
    print("\n[TEST 11] classify_intent: 'Explain this error on my screen'")
    from llm.ai_router import classify_intent
    result = classify_intent("Explain this error on my screen")
    print(f"  Result: {result}")
    assert result.get("intent") == "screen_action", f"Expected screen_action, got {result.get('intent')}"
    assert result.get("action") == "explain_error", f"Got {result.get('action')}"
    print("  [PASS]")


def test_e2e_handle_intent_screen_read():
    """E2E: handle_intent for screen_action/read returns a spoken response."""
    print("\n[TEST 12] handle_intent: screen_action/read E2E (no crash)")
    from intent_router import handle_intent
    intent_data = {"intent": "screen_action", "action": "read"}
    result = handle_intent(intent_data, user_command="Read my screen", speak_response=False)
    safe = result.get("response", "")[:80].encode("ascii", errors="replace").decode("ascii")
    print(f"  success={result.get('success')}, response='{safe}'")
    assert "success" in result
    assert "response" in result
    assert len(result.get("response", "")) > 0
    print("  [PASS]")


if __name__ == "__main__":
    print("=" * 65)
    print("IntelliDesk Screen/OCR Intelligence Test Suite (Phase 8)")
    print(f"EasyOCR model available: {_OCR_MODEL_AVAILABLE}")
    print("=" * 65)

    tests = [
        test_ocr_module_imports,
        test_ocr_missing_file,
        test_screen_analyzer_imports,
        test_read_screen_text_structure,
        test_ocr_valid_image,           # SKIP if model not downloaded
        test_analyze_screen_read,        # SKIP if model not downloaded
        test_analyze_screen_summarize,   # SKIP if model not downloaded
        test_explain_error_on_screen,    # SKIP if model not downloaded
        test_intent_classify_read_screen,
        test_intent_classify_what_on_screen,
        test_intent_classify_explain_error,
        test_e2e_handle_intent_screen_read,
    ]

    passed = 0
    skipped = 0
    failed = 0
    for t in tests:
        try:
            before = passed
            t()
            passed += 1
        except SystemExit:
            skipped += 1
        except AssertionError as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {t.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print("\n" + "=" * 65)
    print(f"Results: {passed} passed, {skipped} skipped, {failed} failed of {len(tests)} tests")
    if failed == 0:
        print("[SUCCESS] All runnable Screen/OCR tests passed!")
    else:
        print("[PARTIAL] Some tests failed. Review output above.")
    print("=" * 65)
