"""
IntelliDesk Text-to-Speech (TTS) Module.

Provides fast, natural voice output for IntelliDesk assistant responses.
Supports Windows SAPI (instant, offline) and edge-tts (neural online).
"""

import sys
import threading
from typing import Optional


_sapi_lock = threading.Lock()


def speak_sapi(text: str, rate: int = 1) -> bool:
    """Speak text using Windows native SAPI voice engine."""
    if not text or not text.strip():
        return False

    try:
        import win32com.client
        import pythoncom

        # Initialize COM on this thread
        pythoncom.CoInitialize()
        try:
            with _sapi_lock:
                speaker = win32com.client.Dispatch("SAPI.SpVoice")
                speaker.Rate = rate
                speaker.Speak(text.strip())
            return True
        finally:
            pythoncom.CoUninitialize()
    except Exception as e:
        print(f"[TTS SAPI Error]: {repr(e)}", file=sys.stderr, flush=True)
        return False


def speak(text: str, wait: bool = True) -> bool:
    """
    Speak text response aloud to the user.

    Parameters:
        text (str): The text to speak.
        wait (bool): If True, blocks until speech completes. If False, runs in background thread.
    """
    if not text or not text.strip():
        return False

    clean_text = text.strip()

    if wait:
        return speak_sapi(clean_text)
    else:
        thread = threading.Thread(target=speak_sapi, args=(clean_text,), daemon=True)
        thread.start()
        return True


if __name__ == "__main__":
    print("Testing IntelliDesk TTS...")
    speak("IntelliDesk voice system is operational.")
