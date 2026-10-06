"""
IntelliDesk Mouse Automation Module.

Provides safe mouse clicking, scrolling, and cursor control.
"""

from typing import Optional, Tuple
import pyautogui


# Disable corner fail-safe to prevent background execution failures at (0,0)
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05


def click(button: str = "left", clicks: int = 1) -> dict:
    """Perform a mouse click."""
    button_norm = button.lower().strip()
    if button_norm not in ["left", "right", "middle"]:
        button_norm = "left"

    try:
        pyautogui.click(button=button_norm, clicks=clicks)
        pos = pyautogui.position()
        return {
            "success": True,
            "action": "click",
            "button": button_norm,
            "clicks": clicks,
            "position": {"x": pos.x, "y": pos.y}
        }
    except Exception as e:
        return {
            "success": False,
            "action": "click",
            "error": str(e)
        }


def double_click() -> dict:
    """Perform a left mouse double-click."""
    return click(button="left", clicks=2)


def right_click() -> dict:
    """Perform a right mouse click."""
    return click(button="right", clicks=1)


def move_mouse(x: Optional[int] = None, y: Optional[int] = None, dx: int = 0, dy: int = 0) -> dict:
    """Move the mouse cursor to absolute coordinates or by a relative offset."""
    try:
        if x is not None and y is not None:
            pyautogui.moveTo(x, y, duration=0.2)
        elif dx != 0 or dy != 0:
            pyautogui.moveRel(dx, dy, duration=0.2)

        pos = pyautogui.position()
        return {
            "success": True,
            "action": "move_mouse",
            "position": {"x": pos.x, "y": pos.y}
        }
    except Exception as e:
        return {
            "success": False,
            "action": "move_mouse",
            "error": str(e)
        }


def scroll(clicks: int = -3) -> dict:
    """
    Scroll mouse wheel.
    Positive value scrolls UP, negative value scrolls DOWN.
    """
    try:
        pyautogui.scroll(clicks)
        return {
            "success": True,
            "action": "scroll",
            "clicks": clicks,
            "direction": "up" if clicks > 0 else "down"
        }
    except Exception as e:
        return {
            "success": False,
            "action": "scroll",
            "error": str(e)
        }


def get_mouse_position() -> dict:
    """Get current cursor screen coordinates."""
    pos = pyautogui.position()
    return {
        "success": True,
        "action": "get_mouse_position",
        "position": {"x": pos.x, "y": pos.y}
    }
