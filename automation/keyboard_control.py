"""
IntelliDesk Keyboard and Clipboard Automation Module.

Provides safe keyboard typing, key presses, hotkeys, and clipboard control.
"""

import sys
import time
from typing import List, Optional, Union
import pyautogui
import win32clipboard
import win32con


# Disable corner fail-safe to prevent background execution failures at (0,0)
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05

KEY_ALIASES = {
    "enter": "enter",
    "return": "enter",
    "esc": "escape",
    "escape": "escape",
    "space": "space",
    "tab": "tab",
    "backspace": "backspace",
    "delete": "delete",
    "del": "delete",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "pageup": "pageup",
    "pagedown": "pagedown",
    "home": "home",
    "end": "end",
    "win": "win",
    "windows": "win",
}


def type_text(text: str) -> dict:
    """Type string characters into the currently focused window."""
    if not text:
        return {"success": False, "action": "type_text", "error": "Empty text provided."}

    try:
        pyautogui.write(text, interval=0.01)
        return {
            "success": True,
            "action": "type_text",
            "text": text,
            "characters_typed": len(text)
        }
    except Exception as e:
        return {
            "success": False,
            "action": "type_text",
            "text": text,
            "error": str(e)
        }


def press_key(key: str) -> dict:
    """Press a single keyboard key (e.g., enter, escape, tab)."""
    if not key:
        return {"success": False, "action": "press_key", "error": "No key specified."}

    key_norm = KEY_ALIASES.get(key.lower().strip(), key.lower().strip())

    try:
        pyautogui.press(key_norm)
        return {
            "success": True,
            "action": "press_key",
            "key": key_norm
        }
    except Exception as e:
        return {
            "success": False,
            "action": "press_key",
            "key": key,
            "error": str(e)
        }


def press_hotkey(hotkey: Union[str, List[str]]) -> dict:
    """
    Press a keyboard shortcut combination (e.g. 'ctrl+c', 'ctrl+v', 'ctrl+s', 'alt+tab').
    """
    if not hotkey:
        return {"success": False, "action": "press_hotkey", "error": "No hotkey specified."}

    if isinstance(hotkey, str):
        parts = [p.strip().lower() for p in hotkey.replace("-", "+").split("+")]
    else:
        parts = [str(p).strip().lower() for p in hotkey]

    mapped_parts = [KEY_ALIASES.get(p, p) for p in parts if p]

    if not mapped_parts:
        return {"success": False, "action": "press_hotkey", "error": "Invalid hotkey."}

    try:
        pyautogui.hotkey(*mapped_parts)
        return {
            "success": True,
            "action": "press_hotkey",
            "hotkey": "+".join(mapped_parts)
        }
    except Exception as e:
        return {
            "success": False,
            "action": "press_hotkey",
            "hotkey": str(hotkey),
            "error": str(e)
        }


def get_clipboard_text(max_retries: int = 5, retry_delay: float = 0.04) -> dict:
    """Get the current text content stored in Windows clipboard with bounded retries."""
    last_error = ""
    for attempt in range(max_retries):
        opened = False
        try:
            win32clipboard.OpenClipboard()
            opened = True
            text_data = ""
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                text_data = str(data)
            elif win32clipboard.IsClipboardFormatAvailable(win32con.CF_TEXT):
                data = win32clipboard.GetClipboardData(win32con.CF_TEXT)
                text_data = data.decode("utf-8", errors="ignore") if isinstance(data, bytes) else str(data)
            else:
                text_data = ""
            win32clipboard.CloseClipboard()
            opened = False
            return {
                "success": True,
                "action": "get_clipboard",
                "text": text_data
            }
        except Exception as e:
            last_error = str(e)
            if opened:
                try:
                    win32clipboard.CloseClipboard()
                except Exception:
                    pass
            time.sleep(retry_delay * (attempt + 1))

    return {
        "success": False,
        "action": "get_clipboard",
        "text": "",
        "error": f"Failed to access clipboard after {max_retries} attempts: {last_error}"
    }


def set_clipboard_text(text: str, max_retries: int = 5, retry_delay: float = 0.04) -> dict:
    """
    Set the Windows clipboard text content with bounded retries and write verification.
    Ensures clipboard lock is acquired and validates content matches expected value.
    """
    target_str = str(text) if text is not None else ""
    last_error = ""

    for attempt in range(max_retries):
        opened = False
        try:
            win32clipboard.OpenClipboard()
            opened = True
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, target_str)
            win32clipboard.CloseClipboard()
            opened = False

            # Bounded synchronization check: verify text was successfully committed
            time.sleep(0.02)
            check = get_clipboard_text(max_retries=3, retry_delay=0.03)
            if check.get("success") and check.get("text") == target_str:
                return {
                    "success": True,
                    "action": "set_clipboard",
                    "text": target_str,
                    "verified": True
                }
            elif attempt == max_retries - 1:
                return {
                    "success": False,
                    "action": "set_clipboard",
                    "text": target_str,
                    "verified": False,
                    "error": f"Clipboard content mismatch: expected '{target_str}', read '{check.get('text')}'"
                }

        except Exception as e:
            last_error = str(e)
            if opened:
                try:
                    win32clipboard.CloseClipboard()
                except Exception:
                    pass
            time.sleep(retry_delay * (attempt + 1))

    return {
        "success": False,
        "action": "set_clipboard",
        "error": f"Failed to set clipboard after {max_retries} attempts: {last_error}"
    }


def clear_clipboard(max_retries: int = 5, retry_delay: float = 0.04) -> dict:
    """Clear all contents from Windows clipboard with bounded retry handling."""
    last_error = ""
    for attempt in range(max_retries):
        opened = False
        try:
            win32clipboard.OpenClipboard()
            opened = True
            win32clipboard.EmptyClipboard()
            win32clipboard.CloseClipboard()
            opened = False
            return {
                "success": True,
                "action": "clear_clipboard"
            }
        except Exception as e:
            last_error = str(e)
            if opened:
                try:
                    win32clipboard.CloseClipboard()
                except Exception:
                    pass
            time.sleep(retry_delay * (attempt + 1))

    return {
        "success": False,
        "action": "clear_clipboard",
        "error": f"Failed to clear clipboard after {max_retries} attempts: {last_error}"
    }
