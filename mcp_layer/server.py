import sys
from pathlib import Path

# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# MCP
# ============================================================

from mcp.server import MCPServer


# ============================================================
# AUTOMATION MODULE IMPORTS
# ============================================================

from automation.app_launcher import (
    open_application,
    close_application,
)
from automation.app_discovery import (
    get_installed_applications_list,
    discover_applications,
)
from context.workspace_manager import (
    start_workspace as start_workspace_impl,
    list_workspaces,
)
from context.usage_manager import (
    get_most_used_app as get_most_used_app_impl,
    get_top_apps,
)
from automation.system_control import (
    get_volume,
    set_volume,
    increase_volume,
    decrease_volume,
    mute_volume,
    unmute_volume,
    get_brightness,
    set_brightness,
    increase_brightness,
    decrease_brightness,
)
import automation.file_control as file_ctl
import automation.keyboard_control as kbd_ctl
import automation.mouse_control as mouse_ctl
import automation.screen_control as screen_ctl
import automation.browser_control as browser_ctl


# ============================================================
# CREATE MCP SERVER
# ============================================================

mcp = MCPServer("IntelliDesk")


# ============================================================
# APPLICATION CONTROL
# ============================================================

@mcp.tool()
def open_app(application: str) -> dict:
    """Open a desktop application through IntelliDesk."""
    try:
        import automation.app_launcher as launcher
        result = launcher.open_application(application)
        return {
            "success": bool(result),
            "action": "open_application",
            "application": application,
            "launcher_module": launcher.__file__,
            "python": sys.executable,
            "cwd": str(Path.cwd()),
        }
    except Exception as e:
        return {
            "success": False,
            "action": "open_application",
            "application": application,
            "error": repr(e),
            "python": sys.executable,
            "cwd": str(Path.cwd()),
        }


@mcp.tool()
def launcher_diagnostic() -> dict:
    """Diagnose the application launcher used by MCP."""
    try:
        import automation.app_launcher as launcher
        chrome_path = launcher.find_chrome()
        return {
            "success": True,
            "launcher_module": launcher.__file__,
            "python": sys.executable,
            "cwd": str(Path.cwd()),
            "project_root": str(PROJECT_ROOT),
            "chrome_path": chrome_path,
            "chrome_exists": (
                chrome_path is not None
                and Path(chrome_path).is_file()
            ),
        }
    except Exception as e:
        return {
            "success": False,
            "error": repr(e),
            "python": sys.executable,
            "cwd": str(Path.cwd()),
            "project_root": str(PROJECT_ROOT),
        }


@mcp.tool()
def close_app(application: str) -> dict:
    """Close a desktop application."""
    try:
        success = close_application(application)
        return {
            "success": bool(success),
            "action": "close_application",
            "application": application,
        }
    except Exception as e:
        return {
            "success": False,
            "action": "close_application",
            "application": application,
            "error": str(e),
        }


@mcp.tool()
def list_installed_apps() -> dict:
    """List discovered desktop applications installed on Windows."""
    try:
        apps = get_installed_applications_list()
        return {
            "success": True,
            "action": "list_installed_apps",
            "count": len(apps),
            "applications": apps,
        }
    except Exception as e:
        return {
            "success": False,
            "action": "list_installed_apps",
            "error": str(e),
        }


@mcp.tool()
def start_workspace(workspace_name: str) -> dict:
    """Start a configured multi-application workspace (e.g. work, study, entertainment)."""
    try:
        result = start_workspace_impl(workspace_name)
        return {
            "success": result.get("success", False),
            "action": "start_workspace",
            "workspace": workspace_name,
            "explanation": result.get("explanation", ""),
            "opened": result.get("opened", []),
            "failed": result.get("failed", []),
        }
    except Exception as e:
        return {
            "success": False,
            "action": "start_workspace",
            "workspace": workspace_name,
            "error": str(e),
        }


@mcp.tool()
def get_most_used_app(category: str = "") -> dict:
    """Get the most frequently used application from history."""
    try:
        most = get_most_used_app_impl(category=category if category else None)
        if most:
            app_key, info = most
            return {
                "success": True,
                "action": "get_most_used_app",
                "app": app_key,
                "count": info.get("count", 0),
                "last_used": info.get("last_used"),
            }
        return {
            "success": True,
            "action": "get_most_used_app",
            "app": None,
            "count": 0,
        }
    except Exception as e:
        return {
            "success": False,
            "action": "get_most_used_app",
            "error": str(e),
        }


# ============================================================
# SYSTEM VOLUME CONTROL
# ============================================================

@mcp.tool()
def get_system_volume() -> dict:
    """Get current Windows master volume."""
    try:
        volume = get_volume()
        if volume is None:
            return {"success": False, "action": "get_volume", "error": "Unable to get system volume."}
        return {"success": True, "action": "get_volume", "volume": int(volume)}
    except Exception as e:
        return {"success": False, "action": "get_volume", "error": str(e)}


@mcp.tool()
def set_system_volume(level: int) -> dict:
    """Set Windows master volume from 0 to 100."""
    try:
        level = max(0, min(100, int(level)))
        success = set_volume(level)
        return {"success": bool(success), "action": "set_volume", "volume": level}
    except Exception as e:
        return {"success": False, "action": "set_volume", "volume": level, "error": str(e)}


@mcp.tool()
def increase_system_volume(amount: int = 10) -> dict:
    """Increase Windows master volume."""
    try:
        amount = int(amount)
        success = increase_volume(amount)
        return {"success": bool(success), "action": "increase_volume", "amount": amount}
    except Exception as e:
        return {"success": False, "action": "increase_volume", "amount": amount, "error": str(e)}


@mcp.tool()
def decrease_system_volume(amount: int = 10) -> dict:
    """Decrease Windows master volume."""
    try:
        amount = int(amount)
        success = decrease_volume(amount)
        return {"success": bool(success), "action": "decrease_volume", "amount": amount}
    except Exception as e:
        return {"success": False, "action": "decrease_volume", "amount": amount, "error": str(e)}


@mcp.tool()
def mute_system_volume() -> dict:
    """Mute Windows master volume."""
    try:
        success = mute_volume()
        return {"success": bool(success), "action": "mute_volume"}
    except Exception as e:
        return {"success": False, "action": "mute_volume", "error": str(e)}


@mcp.tool()
def unmute_system_volume() -> dict:
    """Unmute Windows master volume."""
    try:
        success = unmute_volume()
        return {"success": bool(success), "action": "unmute_volume"}
    except Exception as e:
        return {"success": False, "action": "unmute_volume", "error": str(e)}


@mcp.tool()
def volume_diagnostic() -> dict:
    """Diagnose the MCP volume system."""
    try:
        import automation.system_control as system_control
        volume = system_control.get_volume()
        return {
            "success": volume is not None,
            "module": str(system_control.__file__),
            "volume": volume,
            "python": sys.executable,
            "project_root": str(PROJECT_ROOT),
        }
    except Exception as e:
        return {
            "success": False,
            "error": repr(e),
            "python": sys.executable,
            "project_root": str(PROJECT_ROOT),
        }


# ============================================================
# SYSTEM BRIGHTNESS CONTROL
# ============================================================

@mcp.tool()
def get_system_brightness() -> dict:
    """Get the current Windows screen brightness."""
    try:
        brightness = get_brightness()
        if brightness is None:
            return {"success": False, "action": "get_brightness", "error": "Unable to get system brightness."}
        return {"success": True, "action": "get_brightness", "brightness": int(brightness)}
    except Exception as e:
        return {"success": False, "action": "get_brightness", "error": str(e)}


@mcp.tool()
def set_system_brightness(level: int) -> dict:
    """Set Windows screen brightness from 0 to 100."""
    try:
        level = max(0, min(100, int(level)))
        success = set_brightness(level)
        return {"success": bool(success), "action": "set_brightness", "brightness": level}
    except Exception as e:
        return {"success": False, "action": "set_brightness", "brightness": level, "error": str(e)}


@mcp.tool()
def increase_system_brightness(amount: int = 10) -> dict:
    """Increase Windows screen brightness."""
    try:
        amount = int(amount)
        success = increase_brightness(amount)
        return {"success": bool(success), "action": "increase_brightness", "amount": amount}
    except Exception as e:
        return {"success": False, "action": "increase_brightness", "amount": amount, "error": str(e)}


@mcp.tool()
def decrease_system_brightness(amount: int = 10) -> dict:
    """Decrease Windows screen brightness."""
    try:
        amount = int(amount)
        success = decrease_brightness(amount)
        return {"success": bool(success), "action": "decrease_brightness", "amount": amount}
    except Exception as e:
        return {"success": False, "action": "decrease_brightness", "amount": amount, "error": str(e)}


# ============================================================
# FILE AND FOLDER OPERATIONS (PHASE 3)
# ============================================================

@mcp.tool()
def open_folder(folder_name: str) -> dict:
    """Open a folder in Windows File Explorer (e.g., Downloads, Desktop, Documents)."""
    return file_ctl.open_folder(folder_name)


@mcp.tool()
def search_files(query: str = "", file_ext: str = "", modified_today: bool = False) -> dict:
    """Search for files across user folders by name, extension, or date."""
    return file_ctl.search_files(query=query, file_ext=file_ext, modified_today=modified_today)


@mcp.tool()
def create_file(file_path: str, content: str = "") -> dict:
    """Create a new file with optional content."""
    return file_ctl.create_file(file_path, content)


@mcp.tool()
def create_folder(folder_path: str) -> dict:
    """Create a new folder."""
    return file_ctl.create_folder(folder_path)


@mcp.tool()
def read_text_file(file_path: str, max_lines: int = 50) -> dict:
    """Read the content of a text file."""
    return file_ctl.read_text_file(file_path, max_lines)


@mcp.tool()
def delete_file(file_path: str) -> dict:
    """Delete a file or folder safely."""
    return file_ctl.delete_file(file_path)


@mcp.tool()
def rename_file(old_path: str, new_path: str) -> dict:
    """Rename or move a file."""
    return file_ctl.rename_file(old_path, new_path)


@mcp.tool()
def copy_file(src_path: str, dst_path: str) -> dict:
    """Copy a file to another location."""
    return file_ctl.copy_file(src_path, dst_path)


# ============================================================
# KEYBOARD & CLIPBOARD (PHASE 3)
# ============================================================

@mcp.tool()
def type_text(text: str) -> dict:
    """Type text into the currently active window."""
    return kbd_ctl.type_text(text)


@mcp.tool()
def press_key(key: str) -> dict:
    """Press a single keyboard key (e.g. enter, escape, tab)."""
    return kbd_ctl.press_key(key)


@mcp.tool()
def press_hotkey(hotkey: str) -> dict:
    """Press a keyboard hotkey combination (e.g. 'ctrl+c', 'ctrl+v', 'ctrl+s', 'alt+tab')."""
    return kbd_ctl.press_hotkey(hotkey)


@mcp.tool()
def get_clipboard() -> dict:
    """Get current clipboard text."""
    return kbd_ctl.get_clipboard_text()


@mcp.tool()
def set_clipboard(text: str) -> dict:
    """Set clipboard text."""
    return kbd_ctl.set_clipboard_text(text)


@mcp.tool()
def clear_clipboard() -> dict:
    """Clear clipboard contents."""
    return kbd_ctl.clear_clipboard()


# ============================================================
# MOUSE CONTROL (PHASE 3)
# ============================================================

@mcp.tool()
def click_mouse(button: str = "left", clicks: int = 1) -> dict:
    """Click mouse button ('left', 'right', 'middle')."""
    return mouse_ctl.click(button=button, clicks=clicks)


@mcp.tool()
def scroll_mouse(clicks: int = -3) -> dict:
    """Scroll mouse wheel (positive up, negative down)."""
    return mouse_ctl.scroll(clicks)


# ============================================================
# SCREEN CONTROL (PHASE 3)
# ============================================================

@mcp.tool()
def take_screenshot(filename: str = "") -> dict:
    """Take a full screenshot of the desktop and save to assets/screenshots."""
    return screen_ctl.capture_screen(filename=filename if filename else None)


# ============================================================
# BROWSER & WEB SEARCH (PHASE 3)
# ============================================================

@mcp.tool()
def search_web(query: str, engine: str = "google") -> dict:
    """Search Google or YouTube in the web browser."""
    if "youtube" in engine.lower():
        return browser_ctl.search_youtube(query)
    return browser_ctl.search_google(query)


@mcp.tool()
def open_url(url: str) -> dict:
    """Open a web URL in the browser."""
    return browser_ctl.open_url(url)


# ============================================================
# NOTEPAD (PHASE 4)
# ============================================================

@mcp.tool()
def save_to_notepad(text: str, question: str = "") -> dict:
    """Write text (and optional question) to a file and open it in Windows Notepad."""
    import automation.notepad_control as notepad_ctl
    return notepad_ctl.save_text_to_notepad(text=text, question=question)


# ============================================================
# GIT / GITHUB CONTROL (PHASE 6)
# ============================================================

@mcp.tool()
def git_status(repo_path: str = "") -> dict:
    """Get the Git status of the current repository (modified, staged, untracked files)."""
    import automation.git_control as git_ctl
    return git_ctl.git_status(repo_path if repo_path else None)


@mcp.tool()
def git_log(repo_path: str = "", limit: int = 5) -> dict:
    """Show the last N commit messages from the Git log."""
    import automation.git_control as git_ctl
    return git_ctl.git_log(repo_path if repo_path else None, limit=limit)


@mcp.tool()
def git_branches(repo_path: str = "") -> dict:
    """List all branches in the repository."""
    import automation.git_control as git_ctl
    return git_ctl.git_branch_list(repo_path if repo_path else None)


@mcp.tool()
def git_checkout_branch(branch_name: str, repo_path: str = "") -> dict:
    """Switch to an existing branch."""
    import automation.git_control as git_ctl
    return git_ctl.git_checkout(branch_name, repo_path if repo_path else None)


@mcp.tool()
def git_create_branch(branch_name: str, repo_path: str = "") -> dict:
    """Create and switch to a new Git branch."""
    import automation.git_control as git_ctl
    return git_ctl.git_create_branch(branch_name, repo_path if repo_path else None)


@mcp.tool()
def git_scan_secrets(repo_path: str = "") -> dict:
    """Scan repository files for secrets, API keys, tokens, and credentials before committing."""
    import automation.git_control as git_ctl
    return git_ctl.git_scan_secrets(repo_path if repo_path else None)


@mcp.tool()
def git_commit(message: str = "", repo_path: str = "") -> dict:
    """Stage all safe files and create a Git commit. Refuses if secrets are detected."""
    import automation.git_control as git_ctl
    return git_ctl.git_add_and_commit(message=message, repo_path=repo_path if repo_path else None)


@mcp.tool()
def git_push(repo_path: str = "", branch: str = "") -> dict:
    """Push committed changes to the remote. Never force-pushes. Scans for secrets first."""
    import automation.git_control as git_ctl
    return git_ctl.git_push(repo_path=repo_path if repo_path else None, branch=branch if branch else None)


@mcp.tool()
def git_commit_and_push(message: str = "", repo_path: str = "") -> dict:
    """Combined: scan secrets → stage → commit → push. Primary handler for 'push my project'."""
    import automation.git_control as git_ctl
    return git_ctl.git_commit_and_push(message=message, repo_path=repo_path if repo_path else None)


@mcp.tool()
def git_pull(repo_path: str = "") -> dict:
    """Pull latest changes from the remote repository."""
    import automation.git_control as git_ctl
    return git_ctl.git_pull(repo_path if repo_path else None)


@mcp.tool()
def git_init(repo_path: str = "") -> dict:
    """Initialize a new Git repository in the specified directory."""
    import automation.git_control as git_ctl
    return git_ctl.git_init(repo_path if repo_path else None)


# ============================================================
# SCREEN / OCR INTELLIGENCE (PHASE 8)
# ============================================================

@mcp.tool()
def read_screen_text() -> dict:
    """Capture the screen and extract all visible text using OCR (no LLM needed)."""
    from screen.ocr import extract_text_from_screenshot
    return extract_text_from_screenshot()


@mcp.tool()
def analyze_screen(task: str = "summarize") -> dict:
    """Capture screen, OCR it, and use AI to explain or summarize what's on screen.
    task: 'summarize' | 'explain_error' | 'read' | 'describe'
    """
    from screen.screen_analyzer import analyze_screen as _analyze
    return _analyze(task=task)


@mcp.tool()
def explain_screen_error() -> dict:
    """Capture the screen and use AI to explain any error message currently visible."""
    from screen.screen_analyzer import explain_error_on_screen
    return explain_error_on_screen()


# ============================================================
# WINDOW MANAGEMENT (PHASE 9)
# ============================================================

@mcp.tool()
def list_open_windows() -> dict:
    """List all currently visible windows on the desktop."""
    from automation.window_control import list_windows
    return list_windows()


@mcp.tool()
def get_active_window() -> dict:
    """Return the title of the currently focused/active window."""
    from automation.window_control import get_active_window as _get
    return _get()


@mcp.tool()
def focus_window(title: str) -> dict:
    """Bring a window matching the given title to the foreground."""
    from automation.window_control import focus_window as _focus
    return _focus(title)


@mcp.tool()
def minimize_window(title: str) -> dict:
    """Minimize a window by its title."""
    from automation.window_control import minimize_window as _min
    return _min(title)


@mcp.tool()
def maximize_window(title: str) -> dict:
    """Maximize a window by its title."""
    from automation.window_control import maximize_window as _max
    return _max(title)


@mcp.tool()
def close_window(title: str) -> dict:
    """Close a window by title. Refuses to close protected system windows."""
    from automation.window_control import close_window as _close
    return _close(title)


@mcp.tool()
def restore_window(title: str) -> dict:
    """Restore a minimized or maximized window by its title."""
    from automation.window_control import restore_window as _rest
    return _rest(title)


# ============================================================
# SYSTEM POWER COMMANDS (PHASE 9)
# ============================================================

@mcp.tool()
def lock_screen() -> dict:
    """Lock the Windows screen immediately."""
    import ctypes
    try:
        ctypes.windll.user32.LockWorkStation()
        return {"success": True, "action": "lock_screen"}
    except Exception as e:
        return {"success": False, "action": "lock_screen", "error": str(e)}


@mcp.tool()
def sleep_system() -> dict:
    """Put the computer to sleep."""
    import subprocess
    try:
        subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], check=True)
        return {"success": True, "action": "sleep_system"}
    except Exception as e:
        return {"success": False, "action": "sleep_system", "error": str(e)}


@mcp.tool()
def shutdown_system(delay_seconds: int = 60) -> dict:
    """
    Schedule a Windows shutdown after a delay (default 60 seconds).
    Always adds a delay so the user can cancel with: shutdown /a
    """
    import subprocess
    try:
        delay = max(10, int(delay_seconds))  # minimum 10-second safety buffer
        subprocess.run(["shutdown", "/s", "/t", str(delay)], check=True)
        return {
            "success": True,
            "action": "shutdown_system",
            "delay_seconds": delay,
            "cancel_command": "shutdown /a",
        }
    except Exception as e:
        return {"success": False, "action": "shutdown_system", "error": str(e)}


@mcp.tool()
def restart_system(delay_seconds: int = 60) -> dict:
    """
    Schedule a Windows restart after a delay (default 60 seconds).
    Always adds a delay so the user can cancel with: shutdown /a
    """
    import subprocess
    try:
        delay = max(10, int(delay_seconds))
        subprocess.run(["shutdown", "/r", "/t", str(delay)], check=True)
        return {
            "success": True,
            "action": "restart_system",
            "delay_seconds": delay,
            "cancel_command": "shutdown /a",
        }
    except Exception as e:
        return {"success": False, "action": "restart_system", "error": str(e)}


@mcp.tool()
def cancel_shutdown() -> dict:
    """Cancel a pending scheduled shutdown or restart."""
    import subprocess
    try:
        subprocess.run(["shutdown", "/a"], check=True)
        return {"success": True, "action": "cancel_shutdown"}
    except Exception as e:
        return {"success": False, "action": "cancel_shutdown", "error": str(e)}


# ============================================================
# SERVER START
# ============================================================

if __name__ == "__main__":
    mcp.run()
