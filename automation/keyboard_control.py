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


def get_clipboard_text() -> dict:
    """Get the current text content stored in Windows clipboard."""
    try:
        win32clipboard.OpenClipboard()
        try:
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                return {
                    "success": True,
                    "action": "get_clipboard",
                    "text": str(data)
                }
            elif win32clipboard.IsClipboardFormatAvailable(win32con.CF_TEXT):
                data = win32clipboard.GetClipboardData(win32con.CF_TEXT)
                return {
                    "success": True,
                    "action": "get_clipboard",
                    "text": data.decode("utf-8", errors="ignore")
                }
            else:
                return {
                    "success": True,
                    "action": "get_clipboard",
                    "text": "",
                    "note": "Clipboard does not contain text."
                }
        finally:
            win32clipboard.CloseClipboard()
    except Exception as e:
        return {
            "success": False,
            "action": "get_clipboard",
            "error": str(e)
        }


def set_clipboard_text(text: str) -> dict:
    """Set the Windows clipboard text content."""
    try:
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, str(text))
            return {
                "success": True,
                "action": "set_clipboard",
                "text": text
            }
        finally:
            win32clipboard.CloseClipboard()
    except Exception as e:
        return {
            "success": False,
            "action": "set_clipboard",
            "error": str(e)
        }


def clear_clipboard() -> dict:
    """Clear all contents from Windows clipboard."""
    try:
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            return {
                "success": True,
                "action": "clear_clipboard"
            }
        finally:
            win32clipboard.CloseClipboard()
    except Exception as e:
        return {
            "success": False,
            "action": "clear_clipboard",
            "error": str(e)
        }
