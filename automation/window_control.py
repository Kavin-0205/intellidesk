"""
IntelliDesk Window Control Module.

Provides robust window management using pygetwindow with session context resolution,
alias mapping, process awareness, and safe retry logic:
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
import time
from typing import Any, Dict, List, Optional, Tuple

import psutil

# Protected window titles that must never be forcefully closed
_PROTECTED_TITLES = {
    "task manager", "system configuration", "registry editor",
    "windows defender", "windows security", "command prompt",
    "windows powershell",
}

# Common application to window title aliases
APP_WINDOW_ALIASES = {
    "chrome": ["google chrome", "chrome"],
    "notepad": ["notepad", "*notepad", "untitled - notepad"],
    "calc": ["calculator"],
    "calculator": ["calculator"],
    "vscode": ["visual studio code", "vscode", "code"],
    "code": ["visual studio code", "vscode", "code"],
    "explorer": ["file explorer", "windows explorer", "explorer"],
    "edge": ["microsoft edge", "edge"],
    "terminal": ["windows powershell", "command prompt", "terminal"],
}


def _is_protected(title: str) -> bool:
    if not title:
        return False
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


def find_matching_window(
    title_or_app: str,
    max_retries: int = 3,
    retry_delay: float = 0.15,
) -> Tuple[Optional[Any], Optional[str]]:
    """
    Discover matching window handle and title from application name or window title.
    Supports alias mapping, session context pronoun resolution, and bounded retries.
    """
    target = (title_or_app or "").strip()

    # 1. Resolve pronouns or missing titles from session context
    pronouns = ("it", "that", "this", "window", "the window", "that window", "the app", "current app")
    if not target or target.lower() in pronouns:
        try:
            from context.context_manager import context
            target = context.last_window_target or context.current_application or ""
        except Exception:
            pass

    if not target:
        return None, None

    gw = _import_gw()
    clean_target = target.lower()

    # Build search candidates from direct name and alias map
    search_tokens = [clean_target]
    if clean_target in APP_WINDOW_ALIASES:
        search_tokens.extend(APP_WINDOW_ALIASES[clean_target])

    for attempt in range(max_retries):
        try:
            all_windows = gw.getAllWindows()
            visible_windows = [w for w in all_windows if w.title and w.title.strip()]

            # Step A: Exact title match (case-insensitive)
            for w in visible_windows:
                w_title_lower = w.title.lower()
                for token in search_tokens:
                    if w_title_lower == token:
                        return w, w.title

            # Step B: Substring match for alias tokens
            for w in visible_windows:
                w_title_lower = w.title.lower()
                for token in search_tokens:
                    if token in w_title_lower:
                        return w, w.title

            # Step C: Check if process is running; if so, wait briefly for window creation
            if attempt < max_retries - 1:
                proc_running = False
                for p in psutil.process_iter(["name"]):
                    try:
                        p_name = (p.info["name"] or "").lower()
                        if any(token in p_name for token in search_tokens):
                            proc_running = True
                            break
                    except Exception:
                        pass
                if proc_running:
                    time.sleep(retry_delay)
                    continue

        except Exception:
            pass

        if attempt < max_retries - 1:
            time.sleep(retry_delay)

    return None, None


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
    """Bring a window matching the title or application name to the foreground."""
    win, matched_title = find_matching_window(title)
    if not win:
        return {
            "success": False,
            "action": "focus_window",
            "error": f"No window found matching '{title}'",
        }
    try:
        win.activate()
        return {"success": True, "action": "focus_window", "title": matched_title}
    except Exception as e:
        # On Windows, activate can sometimes fail if minimized; restore first
        try:
            win.restore()
            win.activate()
            return {"success": True, "action": "focus_window", "title": matched_title}
        except Exception:
            return {"success": False, "action": "focus_window", "error": str(e)}


def minimize_window(title: str) -> dict:
    """Minimize a window by title or application name."""
    win, matched_title = find_matching_window(title)
    if not win:
        return {
            "success": False,
            "action": "minimize_window",
            "error": f"No window found matching '{title}'",
        }
    try:
        win.minimize()
        return {"success": True, "action": "minimize_window", "title": matched_title}
    except Exception as e:
        return {"success": False, "action": "minimize_window", "error": str(e)}


def maximize_window(title: str) -> dict:
    """Maximize a window by title or application name."""
    win, matched_title = find_matching_window(title)
    if not win:
        return {
            "success": False,
            "action": "maximize_window",
            "error": f"No window found matching '{title}'",
        }
    try:
        win.maximize()
        return {"success": True, "action": "maximize_window", "title": matched_title}
    except Exception as e:
        return {"success": False, "action": "maximize_window", "error": str(e)}


def restore_window(title: str) -> dict:
    """Restore a minimized or maximized window to normal size."""
    win, matched_title = find_matching_window(title)
    if not win:
        return {
            "success": False,
            "action": "restore_window",
            "error": f"No window found matching '{title}'",
        }
    try:
        win.restore()
        return {"success": True, "action": "restore_window", "title": matched_title}
    except Exception as e:
        return {"success": False, "action": "restore_window", "error": str(e)}


def close_window(title: str) -> dict:
    """
    Close a window by title or application name.
    Refuses to close protected system windows.
    """
    if not title:
        return {"success": False, "action": "close_window", "error": "No title provided."}
    if _is_protected(title):
        return {
            "success": False,
            "action": "close_window",
            "error": f"Cannot close protected system window: '{title}'",
        }
    win, matched_title = find_matching_window(title)
    if not win:
        return {
            "success": False,
            "action": "close_window",
            "error": f"No window found matching '{title}'",
        }
    if _is_protected(matched_title or ""):
        return {
            "success": False,
            "action": "close_window",
            "error": f"Cannot close protected system window: '{matched_title}'",
        }
    try:
        win.close()
        return {"success": True, "action": "close_window", "title": matched_title}
    except Exception as e:
        return {"success": False, "action": "close_window", "error": str(e)}
