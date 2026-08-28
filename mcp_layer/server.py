
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
# APPLICATION CONTROL
# ============================================================

from automation.app_launcher import (
    open_application,
    close_application,
)


# ============================================================
# SYSTEM CONTROL
# ============================================================



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
# ============================================================
# CREATE MCP SERVER
# ============================================================

mcp = MCPServer("IntelliDesk")


# ============================================================
# OPEN APPLICATION
# ============================================================

@mcp.tool()
def open_app(application: str) -> dict:
    """Open a desktop application through IntelliDesk."""

    try:
        import automation.app_launcher as launcher

        print(
            f"MCP OPEN APP REQUEST: {application}",
            file=sys.stderr,
            flush=True,
        )

        print(
            f"MCP LAUNCHER MODULE: {launcher.__file__}",
            file=sys.stderr,
            flush=True,
        )

        print(
            f"MCP PYTHON: {sys.executable}",
            file=sys.stderr,
            flush=True,
        )

        print(
            f"MCP CWD: {Path.cwd()}",
            file=sys.stderr,
            flush=True,
        )

        result = launcher.open_application(application)

        print(
            f"MCP OPEN APP RESULT: {result}",
            file=sys.stderr,
            flush=True,
        )

        return {
            "success": bool(result),
            "action": "open_application",
            "application": application,
            "launcher_module": launcher.__file__,
            "python": sys.executable,
            "cwd": str(Path.cwd()),
        }

    except Exception as e:

        print(
            f"MCP OPEN APP EXCEPTION: {repr(e)}",
            file=sys.stderr,
            flush=True,
        )

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
# ============================================================
# CLOSE APPLICATION
# ============================================================

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
        print(
            f"CLOSE APP ERROR: {repr(e)}",
            file=sys.stderr,
            flush=True,
        )

        return {
            "success": False,
            "action": "close_application",
            "application": application,
            "error": str(e),
        }


# ============================================================
# GET VOLUME
# ============================================================

@mcp.tool()
def get_system_volume() -> dict:
    """Get current Windows master volume."""

    try:
        volume = get_volume()

        print(
            f"MCP GET VOLUME: {volume}",
            file=sys.stderr,
            flush=True,
        )

        if volume is None:
            return {
                "success": False,
                "action": "get_volume",
                "error": "Unable to get system volume.",
            }

        return {
            "success": True,
            "action": "get_volume",
            "volume": int(volume),
        }

    except Exception as e:
        print(
            f"GET VOLUME ERROR: {repr(e)}",
            file=sys.stderr,
            flush=True,
        )

        return {
            "success": False,
            "action": "get_volume",
            "error": str(e),
        }


# ============================================================
# SET VOLUME
# ============================================================

@mcp.tool()
def set_system_volume(level: int) -> dict:
    """Set Windows master volume from 0 to 100."""

    try:
        level = max(0, min(100, int(level)))

        print(
            f"MCP SET VOLUME: {level}",
            file=sys.stderr,
            flush=True,
        )

        success = set_volume(level)

        return {
            "success": bool(success),
            "action": "set_volume",
            "volume": level,
        }

    except Exception as e:
        print(
            f"SET VOLUME ERROR: {repr(e)}",
            file=sys.stderr,
            flush=True,
        )

        return {
            "success": False,
            "action": "set_volume",
            "volume": level,
            "error": str(e),
        }


# ============================================================
# INCREASE VOLUME
# ============================================================

@mcp.tool()
def increase_system_volume(amount: int = 10) -> dict:
    """Increase Windows master volume."""

    try:
        amount = int(amount)

        success = increase_volume(amount)

        return {
            "success": bool(success),
            "action": "increase_volume",
            "amount": amount,
        }

    except Exception as e:
        return {
            "success": False,
            "action": "increase_volume",
            "amount": amount,
            "error": str(e),
        }


# ============================================================
# DECREASE VOLUME
# ============================================================

@mcp.tool()
def decrease_system_volume(amount: int = 10) -> dict:
    """Decrease Windows master volume."""

    try:
        amount = int(amount)

        success = decrease_volume(amount)

        return {
            "success": bool(success),
            "action": "decrease_volume",
            "amount": amount,
        }

    except Exception as e:
        return {
            "success": False,
            "action": "decrease_volume",
            "amount": amount,
            "error": str(e),
        }


# ============================================================
# MUTE
# ============================================================

@mcp.tool()
def mute_system_volume() -> dict:
    """Mute Windows master volume."""

    try:
        success = mute_volume()

        return {
            "success": bool(success),
            "action": "mute_volume",
        }

    except Exception as e:
        return {
            "success": False,
            "action": "mute_volume",
            "error": str(e),
        }


# ============================================================
# UNMUTE
# ============================================================

@mcp.tool()
def unmute_system_volume() -> dict:
    """Unmute Windows master volume."""

    try:
        success = unmute_volume()

        return {
            "success": bool(success),
            "action": "unmute_volume",
        }

    except Exception as e:
        return {
            "success": False,
            "action": "unmute_volume",
            "error": str(e),
        }


# ============================================================
# DIAGNOSTIC
# ============================================================

@mcp.tool()
def volume_diagnostic() -> dict:
    """Diagnose the MCP volume system."""

    try:
        import automation.system_control as system_control

        volume = system_control.get_volume()

        print(
            f"DIAGNOSTIC MODULE: {system_control.__file__}",
            file=sys.stderr,
            flush=True,
        )

        print(
            f"DIAGNOSTIC VOLUME: {volume}",
            file=sys.stderr,
            flush=True,
        )

        return {
            "success": volume is not None,
            "module": str(system_control.__file__),
            "volume": volume,
            "python": sys.executable,
            "project_root": str(PROJECT_ROOT),
        }

    except Exception as e:
        print(
            f"DIAGNOSTIC ERROR: {repr(e)}",
            file=sys.stderr,
            flush=True,
        )

        return {
            "success": False,
            "error": repr(e),
            "python": sys.executable,
            "project_root": str(PROJECT_ROOT),
        }
# ============================================================
# GET SYSTEM BRIGHTNESS
# ============================================================

@mcp.tool()
def get_system_brightness() -> dict:
    """Get the current Windows screen brightness."""

    try:
        brightness = get_brightness()

        print(
            f"MCP GET BRIGHTNESS: {brightness}",
            file=sys.stderr,
            flush=True,
        )

        if brightness is None:
            return {
                "success": False,
                "action": "get_brightness",
                "error": "Unable to get system brightness.",
            }

        return {
            "success": True,
            "action": "get_brightness",
            "brightness": int(brightness),
        }

    except Exception as e:
        print(
            f"MCP GET BRIGHTNESS ERROR: {repr(e)}",
            file=sys.stderr,
            flush=True,
        )

        return {
            "success": False,
            "action": "get_brightness",
            "error": str(e),
        }


# ============================================================
# SET SYSTEM BRIGHTNESS
# ============================================================

@mcp.tool()
def set_system_brightness(level: int) -> dict:
    """Set Windows screen brightness from 0 to 100."""

    try:
        level = int(level)

        level = max(0, min(100, level))

        print(
            f"MCP SET BRIGHTNESS: {level}",
            file=sys.stderr,
            flush=True,
        )

        success = set_brightness(level)

        return {
            "success": bool(success),
            "action": "set_brightness",
            "brightness": level,
        }

    except Exception as e:
        print(
            f"MCP SET BRIGHTNESS ERROR: {repr(e)}",
            file=sys.stderr,
            flush=True,
        )

        return {
            "success": False,
            "action": "set_brightness",
            "brightness": level,
            "error": str(e),
        }


# ============================================================
# INCREASE SYSTEM BRIGHTNESS
# ============================================================

@mcp.tool()
def increase_system_brightness(amount: int = 10) -> dict:
    """Increase Windows screen brightness."""

    try:
        amount = int(amount)

        success = increase_brightness(amount)

        return {
            "success": bool(success),
            "action": "increase_brightness",
            "amount": amount,
        }

    except Exception as e:
        print(
            f"MCP INCREASE BRIGHTNESS ERROR: {repr(e)}",
            file=sys.stderr,
            flush=True,
        )

        return {
            "success": False,
            "action": "increase_brightness",
            "amount": amount,
            "error": str(e),
        }


# ============================================================
# DECREASE SYSTEM BRIGHTNESS
# ============================================================

@mcp.tool()
def decrease_system_brightness(amount: int = 10) -> dict:
    """Decrease Windows screen brightness."""

    try:
        amount = int(amount)

        success = decrease_brightness(amount)

        return {
            "success": bool(success),
            "action": "decrease_brightness",
            "amount": amount,
        }

    except Exception as e:
        print(
            f"MCP DECREASE BRIGHTNESS ERROR: {repr(e)}",
            file=sys.stderr,
            flush=True,
        )

        return {
            "success": False,
            "action": "decrease_brightness",
            "amount": amount,
            "error": str(e),
        }

# ============================================================
# SERVER START
# ============================================================

if __name__ == "__main__":
    mcp.run()

