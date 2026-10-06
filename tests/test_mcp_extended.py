"""
Extended unit tests for MCP server tools.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp_layer.client import execute_mcp_tool


def test_mcp_tools():
    print("\n--- TEST: Extended MCP Tools ---")

    # 1. Volume
    print("\n[Testing get_system_volume]...")
    vol_res = execute_mcp_tool("get_system_volume", {})
    print("Volume Result:", vol_res)
    assert vol_res.get("success") is True

    # 2. Brightness
    print("\n[Testing get_system_brightness]...")
    br_res = execute_mcp_tool("get_system_brightness", {})
    print("Brightness Result:", br_res)
    assert br_res.get("success") is True

    # 3. List installed apps
    print("\n[Testing list_installed_apps]...")
    apps_res = execute_mcp_tool("list_installed_apps", {})
    print(f"Apps Result Count: {apps_res.get('result', {}).get('count')}")
    assert apps_res.get("success") is True
    assert apps_res.get("result", {}).get("count", 0) > 0

    # 4. Get most used app
    print("\n[Testing get_most_used_app]...")
    used_res = execute_mcp_tool("get_most_used_app", {})
    print("Most Used App Result:", used_res)
    assert used_res.get("success") is True

    print("\n[SUCCESS] All Extended MCP tool tests passed!")


if __name__ == "__main__":
    test_mcp_tools()
