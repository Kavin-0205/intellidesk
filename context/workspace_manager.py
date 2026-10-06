"""
IntelliDesk Workspace & Mode Manager.

Manages configurable productivity and media workspaces (Work, Study, Entertainment, Meeting, Development),
orchestrates application launches, and generates natural spoken explanations.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "workspaces.json"


def _ensure_config_dir():
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_workspaces() -> Dict[str, dict]:
    """Load workspace configurations from JSON file."""
    _ensure_config_dir()
    if not CONFIG_FILE.exists():
        return {}

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WorkspaceManager] Failed to load workspaces: {repr(e)}", file=sys.stderr)
        return {}


def save_workspaces(workspaces: Dict[str, dict]) -> bool:
    """Save workspace configurations to JSON file."""
    _ensure_config_dir()
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(workspaces, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[WorkspaceManager] Failed to save workspaces: {repr(e)}", file=sys.stderr)
        return False


def get_workspace(name: str) -> Optional[dict]:
    """Get a workspace definition by name (case-insensitive)."""
    if not name:
        return None
    norm_name = str(name).lower().strip()
    workspaces = load_workspaces()
    return workspaces.get(norm_name)


def list_workspaces() -> List[str]:
    """List all available workspace names."""
    workspaces = load_workspaces()
    return list(workspaces.keys())


def generate_workspace_explanation(workspace_name: str, app_details: List[dict]) -> str:
    """
    Generate natural spoken explanation for launched workspace.
    Example: "I opened your work workspace: VS Code for development, ChatGPT for assistance, and Email for communication."
    """
    if not app_details:
        return f"I started your {workspace_name} workspace."

    parts = []
    for item in app_details:
        name = item.get("display_name", item.get("name", ""))
        role = item.get("role", "")
        if role:
            parts.append(f"{name} for {role}")
        else:
            parts.append(name)

    if len(parts) == 1:
        apps_phrase = parts[0]
    elif len(parts) == 2:
        apps_phrase = f"{parts[0]} and {parts[1]}"
    else:
        apps_phrase = ", ".join(parts[:-1]) + f", and {parts[-1]}"

    return f"I opened your {workspace_name} workspace: {apps_phrase}."


def start_workspace(workspace_name: str) -> dict:
    """
    Start a workspace: launch all configured applications and generate an explanation.
    """
    import automation.app_launcher as launcher
    from context.context_manager import context

    workspace = get_workspace(workspace_name)
    if not workspace:
        return {
            "success": False,
            "workspace": workspace_name,
            "error": f"Workspace '{workspace_name}' was not found.",
            "explanation": f"I couldn't find a workspace named {workspace_name}."
        }

    display_name = workspace.get("name", workspace_name.title())
    apps_to_launch = workspace.get("apps", [])

    opened = []
    failed = []
    app_details = []

    for app_item in apps_to_launch:
        if isinstance(app_item, dict):
            app_id = app_item.get("name")
            role = app_item.get("role", "")
        else:
            app_id = str(app_item)
            role = ""

        if not app_id:
            continue

        success = launcher.open_application(app_id)
        if success:
            opened.append(app_id)
            app_details.append({
                "name": app_id,
                "display_name": app_id.title(),
                "role": role
            })
        else:
            failed.append(app_id)

    # Generate explanation
    explanation = generate_workspace_explanation(display_name, app_details)

    # Update context
    context.current_workspace = workspace_name

    return {
        "success": len(opened) > 0,
        "workspace": workspace_name,
        "display_name": display_name,
        "opened": opened,
        "failed": failed,
        "explanation": explanation
    }


if __name__ == "__main__":
    print("Testing WorkspaceManager...")
    ws = list_workspaces()
    print("Available workspaces:", ws)
    for w in ws:
        info = get_workspace(w)
        print(f"  Workspace '{w}': {info.get('description')}")
