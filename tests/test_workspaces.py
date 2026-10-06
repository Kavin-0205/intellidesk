"""
Unit test for Workspaces, Context & Usage Manager.
"""

from context.workspace_manager import list_workspaces, get_workspace, generate_workspace_explanation
from context.usage_manager import record_launch, get_top_apps, get_most_used_app
from context.context_manager import ContextManager


def test_workspaces_and_context():
    print("\n--- TEST: Workspaces, Context & Usage ---")

    # 1. Workspaces
    ws_list = list_workspaces()
    print(f"[Workspaces]: {ws_list}")
    assert "work" in ws_list
    assert "study" in ws_list
    assert "entertainment" in ws_list

    # Explanation test
    explanation = generate_workspace_explanation("Work", [
        {"name": "vscode", "display_name": "VS Code", "role": "development"},
        {"name": "chatgpt", "display_name": "ChatGPT", "role": "assistance"},
        {"name": "email", "display_name": "Email", "role": "communication"}
    ])
    print(f"[Explanation]: {explanation}")
    assert "VS Code for development" in explanation
    assert "ChatGPT for assistance" in explanation

    # 2. Usage Manager
    record_launch("vscode")
    record_launch("vscode")
    record_launch("chrome")
    top = get_top_apps(3)
    print(f"[Top Apps]: {top}")
    assert len(top) > 0

    # 3. Context Manager
    ctx = ContextManager()
    ctx.set_current_app("chrome")
    resolved = ctx.resolve_reference("close it")
    print(f"[Pronoun Resolution 'close it']: {resolved}")
    assert "chrome" in resolved

    print("\n[SUCCESS] Workspaces, Context & Usage tests passed!")


if __name__ == "__main__":
    test_workspaces_and_context()
