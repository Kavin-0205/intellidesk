from mcp_layer.client import execute_mcp_tool


print("Testing OPEN...")

result = execute_mcp_tool(
    "open_app",
    {
        "application": "chrome"
    }
)

print("Result:", result)


print("\nTesting CLOSE...")

result = execute_mcp_tool(
    "close_app",
    {
        "application": "chrome"
    }
)

print("Result:", result)