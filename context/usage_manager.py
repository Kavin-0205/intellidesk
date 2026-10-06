"""
IntelliDesk Application Usage Manager.

Tracks application launch counts, last used timestamps, and frequencies
to personalize recommendations and support queries like "Open my most used app".
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parent.parent
USAGE_FILE = PROJECT_ROOT / "data" / "app_usage.json"


def _ensure_storage_dir():
    USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_usage_data() -> Dict[str, dict]:
    """Load application usage data from persistent JSON file."""
    _ensure_storage_dir()
    if not USAGE_FILE.exists():
        return {}

    try:
        with open(USAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[UsageManager] Failed to load usage data: {repr(e)}", file=sys.stderr)
        return {}


def save_usage_data(data: Dict[str, dict]) -> bool:
    """Save application usage data to persistent JSON file."""
    _ensure_storage_dir()
    try:
        with open(USAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[UsageManager] Failed to save usage data: {repr(e)}", file=sys.stderr)
        return False


def record_launch(app_name: str, category: Optional[str] = None) -> dict:
    """
    Record an application launch event and update counts and timestamps.
    """
    if not app_name:
        return {}

    norm_name = str(app_name).lower().strip()
    data = load_usage_data()

    now_iso = datetime.now().isoformat()
    entry = data.get(norm_name, {
        "name": app_name,
        "count": 0,
        "first_used": now_iso,
        "last_used": now_iso,
        "category": category or "general"
    })

    entry["count"] = entry.get("count", 0) + 1
    entry["last_used"] = now_iso
    if category:
        entry["category"] = category

    data[norm_name] = entry
    save_usage_data(data)
    return entry


def get_most_used_app(category: Optional[str] = None) -> Optional[Tuple[str, dict]]:
    """
    Return the most frequently used application.
    Optionally filter by category (e.g., 'coding', 'browser', 'media').
    """
    data = load_usage_data()
    if not data:
        return None

    filtered = data
    if category:
        filtered = {
            k: v for k, v in data.items()
            if v.get("category") == category
        }
        if not filtered:
            filtered = data

    sorted_apps = sorted(
        filtered.items(),
        key=lambda item: item[1].get("count", 0),
        reverse=True
    )

    if sorted_apps:
        return sorted_apps[0]
    return None


def get_top_apps(limit: int = 5) -> List[Tuple[str, dict]]:
    """Return top N most used applications sorted by launch count."""
    data = load_usage_data()
    sorted_apps = sorted(
        data.items(),
        key=lambda item: item[1].get("count", 0),
        reverse=True
    )
    return sorted_apps[:limit]


if __name__ == "__main__":
    print("Testing UsageManager...")
    record_launch("chrome")
    record_launch("vscode")
    record_launch("vscode")
    top = get_top_apps(3)
    print("Top apps:", top)
    most = get_most_used_app()
    print("Most used app:", most)
