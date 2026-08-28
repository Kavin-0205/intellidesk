import sys

from mcp_layer.client import execute_mcp_tool


def handle_intent(intent_data):
    intent = intent_data.get("intent")
    application = intent_data.get("application")

    if intent == "open_application":

        if not application:
            print("Which application would you like me to open?")
            return False

        print(f"Executing: open {application}")

        result = execute_mcp_tool(
            "open_app",
            {
                "application": application
            }
        )

        if result.get("success"):
            print(f"Opening {application}")
            return True

        print(f"Failed to open {application}")
        print(result.get("error", result), file=sys.stderr)

        return False

    elif intent == "close_application":

        if not application:
            print("Which application would you like me to close?")
            return False

        print(f"Executing: close {application}")

        result = execute_mcp_tool(
            "close_app",
            {
                "application": application
            }
        )

        if result.get("success"):
            print(f"Closing {application}")
            return True

        print(f"Failed to close {application}")
        print(result.get("error", result), file=sys.stderr)

        return False

    else:
        print(f"I don't know how to handle intent: {intent}")
        return False