"""
Unit test for Screen Control & Screenshot Module.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.screen_control import capture_screen, get_screen_size


def test_screen_operations():
    print("\n--- TEST: Screen Control & Screenshot ---")

    # 1. Screen size
    size_res = get_screen_size()
    print(f"[Screen Size]: {size_res}")
    assert size_res.get("success") is True
    assert size_res.get("width", 0) > 0

    # 2. Capture screenshot
    shot_res = capture_screen(filename="test_phase3_shot.png")
    print(f"[Capture Screen]: {shot_res}")
    assert shot_res.get("success") is True
    assert os.path.exists(shot_res.get("path"))
    assert os.path.getsize(shot_res.get("path")) > 0

    print("\n[SUCCESS] Screen Control tests passed!")


if __name__ == "__main__":
    test_screen_operations()
