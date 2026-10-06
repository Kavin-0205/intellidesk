"""
IntelliDesk Screen Control and Screenshot Module.

Captures full desktop screenshots and saves them with structured timestamps.
Supports PIL ImageGrab with robust Windows PowerShell / GDI fallback.
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from PIL import Image, ImageGrab


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCREENSHOT_DIR = PROJECT_ROOT / "assets" / "screenshots"


def _ensure_dir(directory: Path):
    directory.mkdir(parents=True, exist_ok=True)


def capture_screen(save_dir: Optional[str] = None, filename: Optional[str] = None) -> dict:
    """
    Take a full desktop screenshot and save to disk.
    """
    target_dir = Path(save_dir) if save_dir else DEFAULT_SCREENSHOT_DIR
    _ensure_dir(target_dir)

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
    elif not filename.endswith(".png") and not filename.endswith(".jpg"):
        filename = f"{filename}.png"

    file_path = target_dir / filename
    resolved_path = str(file_path.resolve())

    # 1. Try PIL ImageGrab
    try:
        screenshot = ImageGrab.grab(all_screens=True)
        screenshot.save(file_path)
        w, h = screenshot.size
        return {
            "success": True,
            "action": "capture_screen",
            "path": resolved_path,
            "filename": filename,
            "width": w,
            "height": h
        }
    except Exception as e:
        print(f"[ScreenControl] ImageGrab attempt failed: {repr(e)}, using PowerShell fallback...", file=sys.stderr)

    # 2. PowerShell .NET Fallback
    try:
        escaped_path = resolved_path.replace("'", "''")
        ps_cmd = (
            "Add-Type -AssemblyName System.Windows.Forms,System.Drawing; "
            "$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
            "$bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height; "
            "$g = [System.Drawing.Graphics]::FromImage($bmp); "
            "$g.CopyFromScreen($b.X, $b.Y, 0, 0, $b.Size); "
            f"$bmp.Save('{escaped_path}'); "
            "$g.Dispose(); $bmp.Dispose();"
        )

        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        if file_path.exists() and os.path.getsize(file_path) > 0:
            with Image.open(file_path) as img:
                w, h = img.size
            return {
                "success": True,
                "action": "capture_screen",
                "path": resolved_path,
                "filename": filename,
                "width": w,
                "height": h
            }

        return {
            "success": False,
            "action": "capture_screen",
            "error": res.stderr.strip() if res.stderr else "Failed to capture screenshot."
        }

    except Exception as e:
        return {
            "success": False,
            "action": "capture_screen",
            "error": str(e)
        }


def get_screen_size() -> dict:
    """Get desktop screen dimensions."""
    try:
        import pyautogui
        w, h = pyautogui.size()
        return {
            "success": True,
            "action": "get_screen_size",
            "width": w,
            "height": h
        }
    except Exception as e:
        return {
            "success": False,
            "action": "get_screen_size",
            "error": str(e)
        }


if __name__ == "__main__":
    print("Testing Screen Control...")
    res = capture_screen()
    print("Screenshot Result:", res)
