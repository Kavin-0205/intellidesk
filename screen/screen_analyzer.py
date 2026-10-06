"""
IntelliDesk Screen Analyzer Module.

Combines screenshot capture + OCR + Groq LLM to provide:
- Screen text reading
- Error message explanation
- Screen content summarization
- Context-aware screen understanding
"""

import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from screen.ocr import extract_text_from_screenshot, extract_text_from_image


SCREEN_ANALYSIS_PROMPT = """You are IntelliDesk, an AI desktop assistant analyzing screen content.
The following text was extracted from the user's current screen via OCR.
Provide a clear, concise spoken-friendly explanation suitable for text-to-speech output.
Do not use markdown, bullet points, or symbols that sound awkward when spoken aloud.
"""


def _call_llm(system_prompt: str, user_prompt: str) -> str:
    """Call Groq LLM for screen analysis."""
    try:
        from llm.grok_client import client
        from llm.ai_router import MODEL_NAME
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=300,
        )
        return (response.choices[0].message.content or "").strip()
    except Exception as e:
        return f"I had trouble analyzing the screen: {e}"


def read_screen_text() -> dict:
    """
    Capture the screen and return its text content (OCR only, no LLM).
    Fast — no API call needed.
    """
    ocr = extract_text_from_screenshot()
    if not ocr.get("success"):
        return {
            "success": False,
            "action": "read_screen_text",
            "error": ocr.get("error", "OCR failed"),
            "text": "",
        }

    text = ocr.get("text", "")
    return {
        "success": True,
        "action": "read_screen_text",
        "text": text,
        "line_count": ocr.get("line_count", 0),
        "character_count": ocr.get("character_count", 0),
        "screenshot_path": ocr.get("screenshot_path", ""),
    }


def analyze_screen(task: str = "summarize") -> dict:
    """
    Capture the screen, OCR it, then use Groq to explain/summarize the content.

    Args:
        task: "summarize" | "explain_error" | "read" | "describe"

    Returns:
        dict with success, action, text (raw OCR), explanation (LLM output).
    """
    # Step 1: Capture and OCR
    ocr = extract_text_from_screenshot()
    if not ocr.get("success"):
        return {
            "success": False,
            "action": "analyze_screen",
            "error": ocr.get("error", "Screenshot/OCR failed"),
            "text": "",
            "explanation": "",
        }

    raw_text = ocr.get("text", "").strip()

    if not raw_text:
        return {
            "success": True,
            "action": "analyze_screen",
            "text": "",
            "explanation": "I couldn't detect any readable text on the screen.",
            "screenshot_path": ocr.get("screenshot_path", ""),
        }

    # Step 2: Build LLM prompt based on task
    task_lower = task.lower()
    if "error" in task_lower or "explain" in task_lower:
        user_prompt = (
            f"The following text was extracted from the user's screen. "
            f"It appears to contain an error or error message. "
            f"Please explain what this error means and suggest how to fix it.\n\n"
            f"Screen text:\n{raw_text[:2000]}"
        )
    elif "read" in task_lower:
        # Just return OCR text, no LLM needed
        return {
            "success": True,
            "action": "analyze_screen",
            "text": raw_text,
            "explanation": raw_text,
            "screenshot_path": ocr.get("screenshot_path", ""),
        }
    else:
        user_prompt = (
            f"The following text was extracted from the user's screen. "
            f"Please summarize what is currently showing on the screen in 2-3 sentences.\n\n"
            f"Screen text:\n{raw_text[:2000]}"
        )

    # Step 3: LLM explanation
    explanation = _call_llm(SCREEN_ANALYSIS_PROMPT, user_prompt)

    return {
        "success": True,
        "action": "analyze_screen",
        "task": task,
        "text": raw_text,
        "explanation": explanation,
        "screenshot_path": ocr.get("screenshot_path", ""),
        "character_count": ocr.get("character_count", 0),
    }


def explain_error_on_screen() -> dict:
    """Shortcut: capture screen and explain any error message found."""
    return analyze_screen(task="explain_error")


def summarize_screen() -> dict:
    """Shortcut: capture screen and summarize what's visible."""
    return analyze_screen(task="summarize")
