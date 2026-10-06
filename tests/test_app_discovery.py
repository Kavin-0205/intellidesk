"""
Unit test for Application Discovery pipeline.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.app_discovery import (
    discover_applications,
    find_application,
    get_installed_applications_list
)


def test_app_discovery():
    print("\n--- TEST: Application Discovery ---")

    apps = discover_applications(force_refresh=True)
    print(f"[Total Discovered Apps]: {len(apps)}")
    assert len(apps) > 10, "Should discover at least 10 installed applications on Windows"

    # Test common lookups
    queries = ["chrome", "notepad", "calculator", "camera", "vs code", "hotstar"]
    for q in queries:
        info = find_application(q)
        print(f"[Query '{q}'] -> Found: {info['name'] if info else None} (Type: {info.get('type') if info else None})")
        assert info is not None, f"Failed to find application for '{q}'"

    # Test list
    installed = get_installed_applications_list()
    print(f"[Installed App Names Sample]: {installed[:10]}")
    assert len(installed) > 5

    print("\n[SUCCESS] Application Discovery tests passed!")


if __name__ == "__main__":
    test_app_discovery()
