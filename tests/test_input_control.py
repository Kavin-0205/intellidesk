"""
Unit test for Keyboard, Mouse & Clipboard Automation.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.keyboard_control import (
    type_text,
    press_key,
    press_hotkey,
    set_clipboard_text,
    get_clipboard_text,
    clear_clipboard,
)
from automation.mouse_control import (
    click,
    double_click,
    right_click,
    get_mouse_position,
    scroll,
)


def test_input_operations():
    print("\n--- TEST: Keyboard, Mouse & Clipboard ---")

    # 1. Clipboard test
    test_msg = "IntelliDesk Automated Test 12345"
    set_res = set_clipboard_text(test_msg)
    print(f"[Set Clipboard]: {set_res}")
    assert set_res.get("success") is True

    get_res = get_clipboard_text()
    print(f"[Get Clipboard]: {get_res}")
    assert get_res.get("text") == test_msg

    clear_res = clear_clipboard()
    print(f"[Clear Clipboard]: {clear_res}")
    assert clear_res.get("success") is True

    # 2. Mouse position
    pos_res = get_mouse_position()
    print(f"[Mouse Position]: {pos_res}")
    assert pos_res.get("success") is True

    print("\n[SUCCESS] Keyboard, Mouse & Clipboard tests passed!")


if __name__ == "__main__":
    test_input_operations()
