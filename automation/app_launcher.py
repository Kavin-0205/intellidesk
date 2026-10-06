import os
import subprocess
import sys
import webbrowser
from pathlib import Path


# ============================================================
# APPLICATION ALIASES (Preserved for compatibility & fallback)
# ============================================================

APP_ALIASES = {
    "chrome": "chrome",
    "chrome browser": "chrome",
    "google chrome": "chrome",
    "google chrome browser": "chrome",

    "notepad": "notepad",
    "windows notepad": "notepad",

    "calculator": "calculator",
    "windows calculator": "calculator",
    "calc": "calculator",

    "camera": "camera",
    "windows camera": "camera",

    "vscode": "visual studio code",
    "vs code": "visual studio code",
    "code": "visual studio code",

    "terminal": "terminal",
    "powershell": "powershell",
    "cmd": "command prompt",
}


# ============================================================
# FIND CHROME
# ============================================================

def find_chrome():
    """
    Find Google Chrome executable.

    Uses multiple locations because the MCP server runs
    in a separate Python subprocess.
    """

    possible_paths = []

    # --------------------------------------------------------
    # ProgramFiles
    # --------------------------------------------------------

    program_files = os.environ.get("ProgramFiles")

    if program_files:
        possible_paths.append(
            os.path.join(
                program_files,
                "Google",
                "Chrome",
                "Application",
                "chrome.exe",
            )
        )

    # --------------------------------------------------------
    # ProgramFiles(x86)
    # --------------------------------------------------------

    program_files_x86 = os.environ.get("ProgramFiles(x86)")

    if program_files_x86:
        possible_paths.append(
            os.path.join(
                program_files_x86,
                "Google",
                "Chrome",
                "Application",
                "chrome.exe",
            )
        )

    # --------------------------------------------------------
    # LOCALAPPDATA
    # --------------------------------------------------------

    local_appdata = os.environ.get("LOCALAPPDATA")

    if local_appdata:
        possible_paths.append(
            os.path.join(
                local_appdata,
                "Google",
                "Chrome",
                "Application",
                "chrome.exe",
            )
        )

    # --------------------------------------------------------
    # USERPROFILE
    # --------------------------------------------------------

    user_profile = os.environ.get("USERPROFILE")

    if user_profile:
        possible_paths.append(
            os.path.join(
                user_profile,
                "AppData",
                "Local",
                "Google",
                "Chrome",
                "Application",
                "chrome.exe",
            )
        )

    # --------------------------------------------------------
    # HARD-CODED COMMON WINDOWS LOCATION
    # --------------------------------------------------------

    possible_paths.extend(
        [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
    )

    # --------------------------------------------------------
    # Remove duplicates
    # --------------------------------------------------------

    possible_paths = list(
        dict.fromkeys(possible_paths)
    )

    # --------------------------------------------------------
    # Check paths
    # --------------------------------------------------------

    print(
        "Searching for Chrome...",
        file=sys.stderr,
        flush=True,
    )

    for path in possible_paths:
        try:
            exists = os.path.isfile(path)
        except Exception as e:
            print(
                f"Path check error: {repr(e)}",
                file=sys.stderr,
                flush=True,
            )
            exists = False

        if exists:
            print(
                f"CHROME FOUND: {path}",
                file=sys.stderr,
                flush=True,
            )
            return path

    # --------------------------------------------------------
    # Chrome not found
    # --------------------------------------------------------

    print(
        "CHROME NOT FOUND.",
        file=sys.stderr,
        flush=True,
    )

    return None


# ============================================================
# OPEN APPLICATION
# ============================================================

def open_application(application):

    if not application:
        print(
            "Application name is missing.",
            file=sys.stderr,
            flush=True,
        )
        return False

    raw_application = str(application).strip()
    application_norm = raw_application.lower()

    application_norm = APP_ALIASES.get(
        application_norm,
        application_norm,
    )

    print(
        f"Normalized application: {application_norm}",
        file=sys.stderr,
        flush=True,
    )

    # Helper to track context and usage
    def _record_success(app_key):
        try:
            from context.usage_manager import record_launch
            from context.context_manager import context
            record_launch(app_key)
            context.set_current_app(app_key)
        except Exception as ex:
            print(f"[Tracker Warning]: {repr(ex)}", file=sys.stderr)

    # ========================================================
    # CHROME
    # ========================================================

    if application_norm == "chrome":
        chrome_path = find_chrome()

        if chrome_path is None:
            print(
                "ERROR: Chrome executable was not found.",
                file=sys.stderr,
                flush=True,
            )
            return False

        try:
            print(
                "Launching Chrome...",
                file=sys.stderr,
                flush=True,
            )
            os.startfile(chrome_path)
            print(
                "Chrome launch command completed.",
                file=sys.stderr,
                flush=True,
            )
            _record_success("chrome")
            return True

        except Exception as e:
            print(
                f"Chrome launch failed: {repr(e)}",
                file=sys.stderr,
                flush=True,
            )
            return False

    # ========================================================
    # NOTEPAD
    # ========================================================

    elif application_norm == "notepad":
        try:
            subprocess.Popen(
                ["notepad.exe"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            print(
                "Notepad launched.",
                file=sys.stderr,
                flush=True,
            )
            _record_success("notepad")
            return True

        except Exception as e:
            print(
                f"Notepad launch failed: {repr(e)}",
                file=sys.stderr,
                flush=True,
            )
            return False

    # ========================================================
    # CALCULATOR
    # ========================================================

    elif application_norm == "calculator":
        try:
            subprocess.Popen(
                ["calc.exe"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            print(
                "Calculator launched.",
                file=sys.stderr,
                flush=True,
            )
            _record_success("calculator")
            return True

        except Exception as e:
            print(
                f"Calculator launch failed: {repr(e)}",
                file=sys.stderr,
                flush=True,
            )
            return False

    # ========================================================
    # CAMERA
    # ========================================================

    elif application_norm == "camera":
        try:
            subprocess.Popen(
                [
                    "cmd.exe",
                    "/c",
                    "start",
                    "",
                    "microsoft.windows.camera:",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            print(
                "Camera launch command sent.",
                file=sys.stderr,
                flush=True,
            )
            _record_success("camera")
            return True

        except Exception as e:
            print(
                f"Camera launch failed: {repr(e)}",
                file=sys.stderr,
                flush=True,
            )
            return False

    # ========================================================
    # DYNAMIC DISCOVERY FALLBACK
    # ========================================================

    try:
        from automation.app_discovery import find_application
        app_info = find_application(raw_application) or find_application(application_norm)

        if app_info:
            target_path = app_info.get("path")
            app_type = app_info.get("type", "exe")
            app_display_name = app_info.get("name", raw_application)

            print(
                f"Found discovered app '{app_display_name}': {target_path} (type: {app_type})",
                file=sys.stderr,
                flush=True,
            )

            # Web application
            if app_type == "web":
                webbrowser.open(target_path)
                _record_success(app_display_name.lower())
                return True

            # UWP application
            elif app_type == "uwp":
                subprocess.Popen(
                    ["cmd.exe", "/c", "start", "", target_path],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                _record_success(app_display_name.lower())
                return True

            # Executable / Shortcut
            elif target_path:
                os.startfile(target_path)
                _record_success(app_display_name.lower())
                return True

    except Exception as e:
        print(
            f"Dynamic application launch failed: {repr(e)}",
            file=sys.stderr,
            flush=True,
        )

    print(
        f"I don't know how to open: {application}",
        file=sys.stderr,
        flush=True,
    )
    return False


# ============================================================
# CHECK PROCESS
# ============================================================

def is_process_running(process_name):
    try:
        result = subprocess.run(
            [
                "tasklist",
                "/FI",
                f"IMAGENAME eq {process_name}",
            ],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return (
            process_name.lower()
            in result.stdout.lower()
        )

    except Exception as e:
        print(
            f"Process check failed: {repr(e)}",
            file=sys.stderr,
            flush=True,
        )
        return False


# ============================================================
# CLOSE APPLICATION
# ============================================================

def close_application(application):

    if not application:
        print(
            "Application name is missing.",
            file=sys.stderr,
            flush=True,
        )
        return False

    raw_application = str(application).strip()
    application_norm = raw_application.lower()

    application_norm = APP_ALIASES.get(
        application_norm,
        application_norm,
    )

    print(
        f"Normalized application: {application_norm}",
        file=sys.stderr,
        flush=True,
    )

    process_names = {
        "chrome": "chrome.exe",
        "notepad": "notepad.exe",
        "calculator": "CalculatorApp.exe",
        "camera": "WindowsCamera.exe",
        "visual studio code": "Code.exe",
        "vscode": "Code.exe",
        "code": "Code.exe",
        "terminal": "WindowsTerminal.exe",
        "powershell": "powershell.exe",
        "command prompt": "cmd.exe",
        "paint": "mspaint.exe",
        "task manager": "Taskmgr.exe",
    }

    process = process_names.get(application_norm)

    if not process:
        try:
            from automation.app_discovery import find_application
            info = find_application(raw_application) or find_application(application_norm)
            if info and info.get("process"):
                process = info.get("process")
        except Exception:
            pass

    if process is None:
        print(
            f"I don't know how to close: {application}",
            file=sys.stderr,
            flush=True,
        )
        return False

    try:
        print(
            f"Checking process: {process}",
            file=sys.stderr,
            flush=True,
        )

        if not is_process_running(process):
            print(
                f"{application} is not currently running.",
                file=sys.stderr,
                flush=True,
            )
            return False

        print(
            f"Closing {application}...",
            file=sys.stderr,
            flush=True,
        )

        result = subprocess.run(
            [
                "taskkill",
                "/F",
                "/T",
                "/IM",
                process,
            ],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        if result.stdout:
            print(
                result.stdout.strip(),
                file=sys.stderr,
                flush=True,
            )

        if result.stderr:
            print(
                result.stderr.strip(),
                file=sys.stderr,
                flush=True,
            )

        if result.returncode == 0:
            print(
                f"{application} closed successfully.",
                file=sys.stderr,
                flush=True,
            )
            return True

        print(
            f"Failed to close {application}. "
            f"Exit code: {result.returncode}",
            file=sys.stderr,
            flush=True,
        )
        return False

    except Exception as e:
        print(
            f"Close operation failed: {repr(e)}",
            file=sys.stderr,
            flush=True,
        )
        return False
