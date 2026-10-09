"""
IntelliDesk Screen OCR Module.

Uses EasyOCR (already installed) to extract text from screenshots.
Falls back to Pillow + basic extraction if EasyOCR fails.
"""

import sys
import os
import tempfile
from pathlib import Path
from typing import List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# EasyOCR reader singleton
_ocr_reader = None
_OCR_AVAILABLE = False   # set True once reader initializes successfully
_OCR_INIT_ATTEMPTED = False  # don't retry after first failure


def easyocr_model_available() -> bool:
    """
    Check if EasyOCR model files are already cached locally.
    Does NOT trigger any download.
    Returns True only if the model is present and ready.
    """
    model_dir = Path.home() / ".EasyOCR" / "model"
    required = ["craft_mlt_25k.pth"]  # detection model is the key file
    return any((model_dir / f).exists() for f in required)


def _get_reader():
    """
    Lazy-load EasyOCR reader only if model is already cached.
    Returns None without blocking if model is not downloaded.
    """
    global _ocr_reader, _OCR_AVAILABLE, _OCR_INIT_ATTEMPTED

    if _OCR_AVAILABLE and _ocr_reader is not None:
        return _ocr_reader

    if _OCR_INIT_ATTEMPTED:
        return None  # don't retry

    _OCR_INIT_ATTEMPTED = True

    if not easyocr_model_available():
        print(
            "[OCR] EasyOCR model not cached. To enable OCR, run once:\n"
            "  python -c \"import easyocr; easyocr.Reader(['en'])\"\n"
            "[OCR] Operating without OCR until model is downloaded.",
            file=sys.stderr,
        )
        return None

    try:
        import easyocr
        _ocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        _OCR_AVAILABLE = True
        print("[OCR] EasyOCR reader initialized.", flush=True)
    except Exception as e:
        print(f"[OCR] EasyOCR init failed: {e}", file=sys.stderr)

    return _ocr_reader if _OCR_AVAILABLE else None


def extract_text_from_image(image_path: str) -> dict:
    """
    Extract text from an image file using EasyOCR.

    Args:
        image_path: Path to an image file (PNG, JPG, etc.)

    Returns:
        dict with success, text (combined string), lines (list).
        If EasyOCR model is not cached, returns success=False with a
        descriptive error (does NOT trigger a download).
    """
    if not image_path or not Path(image_path).exists():
        return {
            "success": False,
            "error": f"Image file not found: {image_path}",
            "text": "",
            "lines": [],
        }

    try:
        reader = _get_reader()
        if reader is None:
            return {
                "success": False,
                "error": "EasyOCR model not available. Run: python -c \"import easyocr; easyocr.Reader(['en'])\"",
                "text": "",
                "lines": [],
            }

        results = reader.readtext(
            str(image_path),
            mag_ratio=1.5,
            paragraph=False,
            contrast_ths=0.1,
            adjust_contrast=0.5,
        )
        # Filter by confidence > 20%
        valid_results = [r for r in results if r[2] > 0.2]

        # Sort spatially: top-to-bottom (bucketed by ~15px lines), then left-to-right
        sorted_results = sorted(
            valid_results,
            key=lambda r: (round(r[0][0][1] / 15) * 15, r[0][0][0])
        )

        lines = [r[1] for r in sorted_results]
        combined_text = " ".join(lines).strip()

        return {
            "success": True,
            "text": combined_text,
            "lines": lines,
            "character_count": len(combined_text),
            "line_count": len(lines),
            "raw_results": [{"box": r[0], "text": r[1], "confidence": float(r[2])} for r in results],
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "text": "",
            "lines": [],
        }


def extract_text_from_screenshot() -> dict:
    """
    Take a screenshot and immediately extract text via OCR.
    Uses the existing screen_control module for capture.

    Returns:
        dict with success, text, lines, screenshot_path.
    """
    try:
        # Use existing screen_control module
        import automation.screen_control as screen_ctl

        screenshot_result = screen_ctl.capture_screen()
        if not screenshot_result.get("success"):
            return {
                "success": False,
                "error": f"Screenshot failed: {screenshot_result.get('error', 'unknown')}",
                "text": "",
                "lines": [],
            }

        screenshot_path = screenshot_result.get("path")
        if not screenshot_path or not Path(screenshot_path).exists():
            return {
                "success": False,
                "error": "Screenshot path not found.",
                "text": "",
                "lines": [],
            }

        ocr_result = extract_text_from_image(screenshot_path)
        ocr_result["screenshot_path"] = screenshot_path
        return ocr_result

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "text": "",
            "lines": [],
        }
