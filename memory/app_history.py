"""
IntelliDesk Application History Memory Module.

Wraps database/mongodb.py to provide high-level app history functions
while also maintaining the local JSON usage_manager for fast in-memory
access (MongoDB is for persistence across restarts).
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import both storage backends
from database import mongodb
from context.usage_manager import record_launch, get_top_apps, get_most_used_app


def record_app_open(app_name: str, source: str = "voice") -> dict:
    """
    Record an application open event to both JSON (fast) and MongoDB (persistent).
    """
    # JSON local store (always works, instant)
    usage_entry = record_launch(app_name, category=None)

    # MongoDB (persistent, non-blocking fallback)
    mongo_ok = mongodb.record_app_event(app_name, action="open", source=source)

    return {
        "app": app_name,
        "count": usage_entry.get("count", 1),
        "saved_to_mongodb": mongo_ok,
    }


def record_app_close(app_name: str, source: str = "voice") -> dict:
    """Record an application close event to MongoDB."""
    mongo_ok = mongodb.record_app_event(app_name, action="close", source=source)
    return {
        "app": app_name,
        "action": "close",
        "saved_to_mongodb": mongo_ok,
    }


def get_top_apps_combined(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get top apps from MongoDB (most accurate cross-session),
    falling back to local JSON if MongoDB is unavailable.
    """
    # Try MongoDB first (has full cross-session history)
    mongo_results = mongodb.get_app_frequency(limit=limit)
    if mongo_results:
        return mongo_results

    # Fallback to JSON-backed usage_manager
    json_results = get_top_apps(limit=limit)
    return [
        {
            "application": info.get("name", key),
            "count": info.get("count", 0),
            "last_opened": info.get("last_used"),
        }
        for key, info in json_results
    ]


def get_most_used_app_name() -> Optional[str]:
    """Return the name of the most-used app across all sessions."""
    results = get_top_apps_combined(limit=1)
    if results:
        return results[0].get("application")
    return None
