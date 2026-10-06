"""
IntelliDesk Notepad Control Module.

Opens Windows Notepad with provided text content by writing to a temp file
and launching notepad.exe with that file path — the most reliable approach
on Windows without timing-sensitive GUI automation.
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

NOTEPAD_FILE = DATA_DIR / "notepad_output.txt"


def save_text_to_notepad(text: str, question: str = "") -> dict:
    """
    Write text to a local file and open it in Windows Notepad.

    Parameters:
        text (str): The content to display in Notepad.
        question (str): Optional question label to prepend in the file.

    Returns:
        dict: Structured result with success flag and file path.
    """
    if not text or not text.strip():
        return {
            "success": False,
            "action": "save_to_notepad",
            "error": "No text provided to save."
        }

    try:
        # Build formatted content
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if question and question.strip():
            content = (
                f"Question:\n{question.strip()}\n\n"
                f"Answer:\n{text.strip()}\n\n"
                f"---\nSaved by IntelliDesk at {timestamp}\n"
            )
        else:
            content = f"{text.strip()}\n\n---\nSaved by IntelliDesk at {timestamp}\n"

        # Write to data/notepad_output.txt
        NOTEPAD_FILE.write_text(content, encoding="utf-8")

        # Launch Notepad with the file
        subprocess.Popen(
            ["notepad.exe", str(NOTEPAD_FILE)],
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )

        return {
            "success": True,
            "action": "save_to_notepad",
            "path": str(NOTEPAD_FILE),
            "characters": len(content),
        }

    except Exception as e:
        return {
            "success": False,
            "action": "save_to_notepad",
            "error": str(e)
        }


if __name__ == "__main__":
    result = save_text_to_notepad(
        text="Java is a high-level, object-oriented programming language developed by Sun Microsystems in 1995.",
        question="What is Java?"
    )
    print(f"[Test] save_text_to_notepad result: {result}")
