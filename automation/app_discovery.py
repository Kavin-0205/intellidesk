"""
IntelliDesk Application Discovery Module.

Dynamically discovers installed desktop applications, Start Menu shortcuts,
and system utilities on Windows without requiring manual aliases.
"""

import difflib
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Common Windows system tools and UWP protocol mappings
BUILTIN_WINDOWS_APPS = {
    "notepad": {
        "name": "Notepad",
        "path": "notepad.exe",
        "type": "system",
        "process": "notepad.exe"
    },
    "calculator": {
        "name": "Calculator",
        "path": "calc.exe",
        "type": "system",
        "process": "CalculatorApp.exe"
    },
    "camera": {
        "name": "Camera",
        "path": "microsoft.windows.camera:",
        "type": "uwp",
        "process": "WindowsCamera.exe"
    },
    "paint": {
        "name": "Paint",
        "path": "mspaint.exe",
        "type": "system",
        "process": "mspaint.exe"
    },
    "task manager": {
        "name": "Task Manager",
        "path": "taskmgr.exe",
        "type": "system",
        "process": "Taskmgr.exe"
    },
    "file explorer": {
        "name": "File Explorer",
        "path": "explorer.exe",
        "type": "system",
        "process": "explorer.exe"
    },
    "command prompt": {
        "name": "Command Prompt",
        "path": "cmd.exe",
        "type": "system",
        "process": "cmd.exe"
    },
    "terminal": {
        "name": "Windows Terminal",
        "path": "wt.exe",
        "type": "system",
        "process": "WindowsTerminal.exe"
    },
    "powershell": {
        "name": "PowerShell",
        "path": "powershell.exe",
        "type": "system",
        "process": "powershell.exe"
    },
    "settings": {
        "name": "Settings",
        "path": "ms-settings:",
        "type": "uwp",
        "process": "SystemSettings.exe"
    },
    "snipping tool": {
        "name": "Snipping Tool",
        "path": "snippingtool.exe",
        "type": "system",
        "process": "SnippingTool.exe"
    }
}

# Common web application services
WEB_APPS = {
    "hotstar": {"name": "Disney+ Hotstar", "path": "https://www.hotstar.com", "type": "web", "process": None},
    "jiohotstar": {"name": "JioHotstar", "path": "https://www.hotstar.com", "type": "web", "process": None},
    "chatgpt": {"name": "ChatGPT", "path": "https://chatgpt.com", "type": "web", "process": None},
    "github": {"name": "GitHub", "path": "https://github.com", "type": "web", "process": None},
    "gmail": {"name": "Gmail", "path": "https://mail.google.com", "type": "web", "process": None},
    "email": {"name": "Email", "path": "https://mail.google.com", "type": "web", "process": None},
    "youtube": {"name": "YouTube", "path": "https://www.youtube.com", "type": "web", "process": None},
}

# Common nickname / synonym aliases
DEFAULT_SYNONYMS = {
    "vs code": "visual studio code",
    "vscode": "visual studio code",
    "code": "visual studio code",
    "calc": "calculator",
    "google chrome": "chrome",
    "google chrome browser": "chrome",
    "chrome browser": "chrome",
    "ms edge": "microsoft edge",
    "edge": "microsoft edge",
    "cmd": "command prompt",
    "my computer": "file explorer",
    "explorer": "file explorer",
    "hotstar": "jiohotstar",
}

# Ignore patterns for shortcuts (uninstallers, help guides, documentation)
IGNORE_KEYWORDS = [
    "uninstall", "remove", "help", "manual", "documentation", "readme",
    "license", "website", "homepage", "configuration tool", "diagnostic"
]

_app_cache: Optional[Dict[str, dict]] = None


def _normalize_name(name: str) -> str:
    """Normalize application name for searching."""
    name = name.lower().strip()
    name = re.sub(r"\s*\(64-bit\)|\s*\(32-bit\)|\s*x64|\s*x86", "", name, flags=re.IGNORECASE)
    name = re.sub(r"[^\w\s]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _resolve_shortcut(lnk_path: str) -> Optional[str]:
    """Resolve Windows shortcut (.lnk) to its target executable path."""
    try:
        import win32com.client
        import pythoncom
        pythoncom.CoInitialize()
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(lnk_path)
        target = shortcut.TargetPath
        if target and os.path.exists(target) and target.lower().endswith(".exe"):
            return target
    except Exception:
        pass
    return None


def scan_start_menu_programs() -> Dict[str, dict]:
    """Scan Start Menu folders for installed applications."""
    discovered = {}
    directories = []

    appdata = os.environ.get("APPDATA")
    if appdata:
        user_start = os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs")
        if os.path.exists(user_start):
            directories.append(user_start)

    programdata = os.environ.get("PROGRAMDATA")
    if programdata:
        common_start = os.path.join(programdata, r"Microsoft\Windows\Start Menu\Programs")
        if os.path.exists(common_start):
            directories.append(common_start)

    local_programs = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs")
    if os.path.exists(local_programs):
        for root, _, files in os.walk(local_programs):
            for file in files:
                if file.lower().endswith(".exe") and not any(k in file.lower() for k in IGNORE_KEYWORDS):
                    exe_path = os.path.join(root, file)
                    app_name = _normalize_name(Path(file).stem)
                    if app_name and len(app_name) > 1:
                        discovered[app_name] = {
                            "name": Path(file).stem,
                            "path": exe_path,
                            "type": "exe",
                            "process": file
                        }

    for directory in directories:
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(".lnk"):
                    stem = Path(file).stem
                    lower_stem = stem.lower()

                    if any(kw in lower_stem for kw in IGNORE_KEYWORDS):
                        continue

                    lnk_path = os.path.join(root, file)
                    target_exe = _resolve_shortcut(lnk_path)
                    target_path = target_exe if target_exe else lnk_path

                    proc_name = Path(target_exe).name if target_exe else f"{stem}.exe"
                    norm_name = _normalize_name(stem)

                    if norm_name and len(norm_name) > 1:
                        discovered[norm_name] = {
                            "name": stem,
                            "path": target_path,
                            "type": "lnk" if not target_exe else "exe",
                            "process": proc_name
                        }

    return discovered


def discover_applications(force_refresh: bool = False) -> Dict[str, dict]:
    """
    Build and return the comprehensive dynamic application registry.
    """
    global _app_cache

    if _app_cache is not None and not force_refresh:
        return _app_cache

    registry: Dict[str, dict] = {}

    # 1. Built-in Windows Apps
    for key, info in BUILTIN_WINDOWS_APPS.items():
        registry[key] = info

    # 2. Web Apps
    for key, info in WEB_APPS.items():
        registry[key] = info

    # 3. Start Menu & Program files
    start_menu_apps = scan_start_menu_programs()
    for key, info in start_menu_apps.items():
        if key not in registry:
            registry[key] = info

    # 4. Dedicated Chrome check
    import automation.app_launcher as launcher
    chrome_exe = launcher.find_chrome()
    if chrome_exe and os.path.exists(chrome_exe):
        registry["chrome"] = {
            "name": "Google Chrome",
            "path": chrome_exe,
            "type": "exe",
            "process": "chrome.exe"
        }
        registry["google chrome"] = registry["chrome"]

    _app_cache = registry
    return registry


def find_application(query: str) -> Optional[dict]:
    """
    Find an application in the registry by name, alias, or fuzzy search.

    Parameters:
        query (str): The requested application name (e.g. 'VS Code', 'Chrome', 'Spotify', 'Hotstar').

    Returns:
        dict with keys {'name', 'path', 'type', 'process'} or None if not found.
    """
    if not query:
        return None

    norm_query = _normalize_name(query)

    # Check direct web apps
    if norm_query in WEB_APPS:
        return WEB_APPS[norm_query]

    # Check synonym mapping
    if norm_query in DEFAULT_SYNONYMS:
        syn = DEFAULT_SYNONYMS[norm_query]
        if syn in WEB_APPS:
            return WEB_APPS[syn]
        norm_query = syn

    apps = discover_applications()

    # 1. Exact match
    if norm_query in apps:
        return apps[norm_query]

    # 2. Substring match (e.g. "code" matches "visual studio code")
    for key, info in apps.items():
        if norm_query == key or (len(norm_query) >= 3 and norm_query in key):
            return info

    # 3. Match against display names
    for key, info in apps.items():
        if _normalize_name(info["name"]) == norm_query:
            return info

    # 4. Fuzzy match
    keys = list(apps.keys())
    matches = difflib.get_close_matches(norm_query, keys, n=1, cutoff=0.6)
    if matches:
        return apps[matches[0]]

    return None


def get_installed_applications_list() -> List[str]:
    """Return a deduplicated list of installed user-facing application names."""
    apps = discover_applications()
    names = set()
    for info in apps.values():
        if info.get("name") and info.get("type") != "web":
            names.add(info["name"])
    return sorted(list(names))
