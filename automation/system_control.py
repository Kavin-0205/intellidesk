
import sys

import comtypes
from pycaw.pycaw import AudioUtilities

import screen_brightness_control as sbc
# ============================================================
# WINDOWS COM
# ============================================================

def initialize_com():
    """Initialize COM for the current thread."""

    try:
        comtypes.CoInitialize()
        return True

    except Exception as e:
        print(
            f"COM initialization failed: {repr(e)}",
            file=sys.stderr,
            flush=True,
        )
        return False


# ============================================================
# GET AUDIO ENDPOINT
# ============================================================

def get_audio_endpoint():
    """Return the Windows master audio endpoint."""

    try:

        # IMPORTANT:
        # MCP runs the server in a separate process.
        # Initialize COM every time before accessing pycaw.
        if not initialize_com():
            return None

        device = AudioUtilities.GetSpeakers()

        print(
            f"AUDIO DEVICE: {device}",
            file=sys.stderr,
            flush=True,
        )

        if device is None:
            print(
                "AUDIO DEVICE IS NONE",
                file=sys.stderr,
                flush=True,
            )
            return None

        endpoint = device.EndpointVolume

        print(
            "ENDPOINT VOLUME: obtained successfully",
            file=sys.stderr,
            flush=True,
        )

        return endpoint

    except Exception as e:

        print(
            f"AUDIO ENDPOINT ERROR: {repr(e)}",
            file=sys.stderr,
            flush=True,
        )

        return None


# ============================================================
# GET VOLUME
# ============================================================

def get_volume():

    endpoint = get_audio_endpoint()

    if endpoint is None:
        return None

    try:

        scalar = endpoint.GetMasterVolumeLevelScalar()

        volume = round(float(scalar) * 100)

        print(
            f"Current volume: {volume}%",
            file=sys.stderr,
            flush=True,
        )

        return volume

    except Exception as e:

        print(
            f"GET VOLUME ERROR: {repr(e)}",
            file=sys.stderr,
            flush=True,
        )

        return None


# ============================================================
# SET VOLUME
# ============================================================

def set_volume(level):

    try:

        level = int(level)

        level = max(0, min(100, level))

        endpoint = get_audio_endpoint()

        if endpoint is None:
            return False

        scalar = level / 100.0

        endpoint.SetMasterVolumeLevelScalar(
            scalar,
            None,
        )

        print(
            f"Volume set to {level}%",
            file=sys.stderr,
            flush=True,
        )

        return True

    except Exception as e:

        print(
            f"SET VOLUME ERROR: {repr(e)}",
            file=sys.stderr,
            flush=True,
        )

        return False


# ============================================================
# INCREASE VOLUME
# ============================================================

def increase_volume(amount=10):

    try:

        amount = int(amount)

        current = get_volume()

        if current is None:
            return False

        new_volume = min(
            100,
            current + amount,
        )

        return set_volume(new_volume)

    except Exception as e:

        print(
            f"INCREASE VOLUME ERROR: {repr(e)}",
            file=sys.stderr,
            flush=True,
        )

        return False


# ============================================================
# DECREASE VOLUME
# ============================================================

def decrease_volume(amount=10):

    try:

        amount = int(amount)

        current = get_volume()

        if current is None:
            return False

        new_volume = max(
            0,
            current - amount,
        )

        return set_volume(new_volume)

    except Exception as e:

        print(
            f"DECREASE VOLUME ERROR: {repr(e)}",
            file=sys.stderr,
            flush=True,
        )

        return False


# ============================================================
# MUTE
# ============================================================

def mute_volume():

    try:

        endpoint = get_audio_endpoint()

        if endpoint is None:
            return False

        endpoint.SetMute(1, None)

        print(
            "Volume muted.",
            file=sys.stderr,
            flush=True,
        )

        return True

    except Exception as e:

        print(
            f"MUTE VOLUME ERROR: {repr(e)}",
            file=sys.stderr,
            flush=True,
        )

        return False


# ============================================================
# UNMUTE
# ============================================================

def unmute_volume():

    try:

        endpoint = get_audio_endpoint()

        if endpoint is None:
            return False

        endpoint.SetMute(0, None)

        print(
            "Volume unmuted.",
            file=sys.stderr,
            flush=True,
        )

        return True

    except Exception as e:

        print(
            f"UNMUTE VOLUME ERROR: {repr(e)}",
            file=sys.stderr,
            flush=True,
        )

        return False

# ============================================================
# GET BRIGHTNESS
# ============================================================

def get_brightness():
    """
    Get current screen brightness as an integer from 0 to 100.
    """

    try:
        brightness = sbc.get_brightness()

        if not brightness:
            print(
                "Failed to get brightness: no value returned",
                file=sys.stderr,
                flush=True,
            )
            return None

        # screen_brightness_control normally returns a list
        if isinstance(brightness, list):
            brightness = brightness[0]

        brightness = int(brightness)

        print(
            f"Current brightness: {brightness}%",
            file=sys.stderr,
            flush=True,
        )

        return brightness

    except Exception as e:

        print(
            f"Failed to get brightness: {repr(e)}",
            file=sys.stderr,
            flush=True,
        )

        return None


# ============================================================
# SET BRIGHTNESS
# ============================================================

def set_brightness(level):
    """
    Set screen brightness from 0 to 100.
    """

    try:
        level = int(level)

        # Keep brightness between 0 and 100
        level = max(0, min(100, level))

        sbc.set_brightness(level)

        print(
            f"Brightness set to {level}%",
            file=sys.stderr,
            flush=True,
        )

        return True

    except Exception as e:

        print(
            f"Failed to set brightness: {repr(e)}",
            file=sys.stderr,
            flush=True,
        )

        return False


# ============================================================
# INCREASE BRIGHTNESS
# ============================================================

def increase_brightness(amount=10):
    """
    Increase screen brightness.
    """

    try:
        amount = int(amount)

        current = get_brightness()

        if current is None:
            return False

        new_brightness = min(
            100,
            current + amount
        )

        return set_brightness(new_brightness)

    except Exception as e:

        print(
            f"Failed to increase brightness: {repr(e)}",
            file=sys.stderr,
            flush=True,
        )

        return False


# ============================================================
# DECREASE BRIGHTNESS
# ============================================================

def decrease_brightness(amount=10):
    """
    Decrease screen brightness.
    """

    try:
        amount = int(amount)

        current = get_brightness()

        if current is None:
            return False

        new_brightness = max(
            0,
            current - amount
        )

        return set_brightness(new_brightness)

    except Exception as e:

        print(
            f"Failed to decrease brightness: {repr(e)}",
            file=sys.stderr,
            flush=True,
        )

        return False