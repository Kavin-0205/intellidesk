"""
IntelliDesk Window Control Module.

Provides voice-driven window management using pygetwindow:
- List open windows
- Focus / bring window to foreground
- Minimize / maximize / restore windows
- Close a specific window
- Get currently active window title

SAFETY:
- Close operations are limited to named windows (no blind close-all)
- System-critical windows are protected from close commands
"""

import sys
from typing import Any, Dict, List, Optional


# Protected window titles that must never be forcefully closed
_PROTECTED_TITLES = {
    "task manager", "system configuration", "registry editor",
    "windows defender", "windows security", "command prompt",
    "windows powershell",
}


def _is_protected(title: str) -> bool:
    lower = title.lower()
    return any(p in lower for p in _PROTECTED_TITLES)


def _import_gw():
    """Lazy import pygetwindow."""
    try:
        import pygetwindow as gw
        return gw
    except ImportError:
        raise RuntimeError(
            "pygetwindow is not installed. Run: pip install pygetwindow"
        )


# ============================================================
# PUBLIC API
# ============================================================

def list_windows() -> dict:
    """Return titles of all currently visible windows."""
    try:
        gw = _import_gw()
        all_titles = [t for t in gw.getAllTitles() if t.strip()]
        return {
            "success": True,
            "action": "list_windows",
            "windows": all_titles,
            "count": len(all_titles),
        }
    except Exception as e:
        return {"success": False, "action": "list_windows", "error": str(e), "windows": []}


def get_active_window() -> dict:
    """Return the title of the currently focused window."""
    try:
        gw = _import_gw()
        active = gw.getActiveWindow()
        title = active.title if active else None
        return {
            "success": True,
            "action": "get_active_window",
            "title": title,
        }
    except Exception as e:
        return {"success": False, "action": "get_active_window", "error": str(e), "title": None}


def focus_window(title: str) -> dict:
    """Bring a window matching the title to the foreground."""
    if not title:
        return {"success": False, "action": "focus_window", "error": "No window title provided."}
    try:
        gw = _import_gw()
        matches = gw.getWindowsWithTitle(title)
        if not matches:
            # Try partial match
            all_titles = gw.getAllTitles()
            matches = [gw.getWindowsWithTitle(t)[0] for t in all_titles
                       if title.lower() in t.lower() and gw.getWindowsWithTitle(t)]
        if not matches:
            return {"success": False, "action": "focus_window",
                    "error": f"No window found matching '{title}'"}
        win = matches[0]
        win.activate()
        return {"success": True, "action": "focus_window", "title": win.title}
    except Exception as e:
        return {"success": False, "action": "focus_window", "error": str(e)}


def minimize_window(title: str) -> dict:
    """Minimize a window by title."""
    if not title:
        return {"success": False, "action": "minimize_window", "error": "No title provided."}
    try:
        gw = _import_gw()
        matches = gw.getWindowsWithTitle(title)
        if not matches:
            all_titles = gw.getAllTitles()
            matches = [gw.getWindowsWithTitle(t)[0] for t in all_titles
                       if title.lower() in t.lower() and gw.getWindowsWithTitle(t)]
        if not matches:
            return {"success": False, "action": "minimize_window",
                    "error": f"No window found matching '{title}'"}
        matches[0].minimize()
        return {"success": True, "action": "minimize_window", "title": matches[0].title}
    except Exception as e:
        return {"success": False, "action": "minimize_window", "error": str(e)}


def maximize_window(title: str) -> dict:
    """Maximize a window by title."""
    if not title:
        return {"success": False, "action": "maximize_window", "error": "No title provided."}
    try:
        gw = _import_gw()
        matches = gw.getWindowsWithTitle(title)
        if not matches:
            all_titles = gw.getAllTitles()
            matches = [gw.getWindowsWithTitle(t)[0] for t in all_titles
                       if title.lower() in t.lower() and gw.getWindowsWithTitle(t)]
        if not matches:
            return {"success": False, "action": "maximize_window",
                    "error": f"No window found matching '{title}'"}
        matches[0].maximize()
        return {"success": True, "action": "maximize_window", "title": matches[0].title}
    except Exception as e:
        return {"success": False, "action": "maximize_window", "error": str(e)}


def close_window(title: str) -> dict:
    """
    Close a window by title.
    Refuses to close protected system windows.
    """
    if not title:
        return {"success": False, "action": "close_window", "error": "No title provided."}
    if _is_protected(title):
        return {"success": False, "action": "close_window",
                "error": f"Cannot close protected system window: '{title}'"}
    try:
        gw = _import_gw()
        matches = gw.getWindowsWithTitle(title)
        if not matches:
            all_titles = gw.getAllTitles()
            matches = [gw.getWindowsWithTitle(t)[0] for t in all_titles
                       if title.lower() in t.lower() and gw.getWindowsWithTitle(t)]
        if not matches:
            return {"success": False, "action": "close_window",
                    "error": f"No window found matching '{title}'"}
        win = matches[0]
        if _is_protected(win.title):
            return {"success": False, "action": "close_window",
                    "error": f"Cannot close protected system window: '{win.title}'"}
        win.close()
        return {"success": True, "action": "close_window", "title": win.title}
    except Exception as e:
        return {"success": False, "action": "close_window", "error": str(e)}
