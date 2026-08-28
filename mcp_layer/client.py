import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ============================================================
# CALL MCP TOOL
# ============================================================

async def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    """
    Connect to IntelliDesk MCP server and execute a tool.
    """

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_layer.server"],
        cwd=str(PROJECT_ROOT),
    )

    async with stdio_client(server_params) as (read, write):

        async with ClientSession(read, write) as session:

            # ------------------------------------------------
            # Initialize MCP connection
            # ------------------------------------------------

            await session.initialize()

            # ------------------------------------------------
            # Execute MCP tool
            # ------------------------------------------------

            result = await session.call_tool(
                tool_name,
                arguments=arguments,
            )

            print(
                f"MCP raw result: {result}",
                file=sys.stderr,
                flush=True,
            )

            # ------------------------------------------------
            # MCP-level error
            # ------------------------------------------------

            if result.is_error:

                error_messages = []

                for content in result.content:

                    if hasattr(content, "text"):

                        error_messages.append(
                            content.text
                        )

                return {
                    "success": False,
                    "error": "\n".join(error_messages),
                }

            # ------------------------------------------------
            # Extract actual MCP response
            # ------------------------------------------------

            for content in result.content:

                if not hasattr(content, "text"):
                    continue

                text = content.text.strip()

                try:

                    data = json.loads(text)

                    if isinstance(data, dict):

                        return {
                            "success": bool(
                                data.get("success", False)
                            ),
                            "result": data,
                            "content": result.content,
                        }

                except json.JSONDecodeError:

                    continue

            # ------------------------------------------------
            # Structured content fallback
            # ------------------------------------------------

            if result.structured_content:

                data = result.structured_content

                if isinstance(data, dict):

                    return {
                        "success": bool(
                            data.get("success", False)
                        ),
                        "result": data,
                        "content": result.content,
                    }

            # ------------------------------------------------
            # No valid response
            # ------------------------------------------------

            return {
                "success": False,
                "error": "MCP returned no valid result.",
                "content": result.content,
            }


# ============================================================
# SYNCHRONOUS WRAPPER
# ============================================================

def execute_mcp_tool(
    tool_name: str,
    arguments: dict,
) -> dict:

    return asyncio.run(
        call_mcp_tool(
            tool_name,
            arguments,
        )
    )