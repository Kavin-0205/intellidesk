"""
IntelliDesk Natural Response Manager.

Converts structured intent outcomes, tool execution results, and errors
into natural, conversational spoken and displayed text.
"""

from typing import Any, Dict, Optional


def format_response(intent_data: Dict[str, Any], result: Any) -> str:
    """
    Generate a concise, natural language response based on the intent and result.
    """
    if not intent_data:
        return "I'm not sure what you'd like me to do."

    intent = intent_data.get("intent", "unknown")
    application = intent_data.get("application")
    action = intent_data.get("action")
    level = intent_data.get("level")
    amount = intent_data.get("amount")
    workspace = intent_data.get("workspace")
    folder = intent_data.get("folder")
    path = intent_data.get("path")
    query = intent_data.get("query")
    key = intent_data.get("key")
    hotkey = intent_data.get("hotkey")
    text = intent_data.get("text")

    is_success = False
    error_msg = None
    data_dict = {}

    if isinstance(result, bool):
        is_success = result
    elif isinstance(result, dict):
        is_success = result.get("success", False)
        error_msg = result.get("error")
        data_dict = result

    # 1. GENERAL QUESTION
    if intent == "general_question":
        if isinstance(result, str):
            return result
        elif isinstance(result, dict) and "answer" in result:
            return result["answer"]
        return "Here is what I found for your question."

    # 1b. SAVE LAST ANSWER
    elif intent == "save_last_answer":
        if is_success:
            return "I've saved the previous answer in Notepad."
        elif error_msg:
            return f"I couldn't save to Notepad: {error_msg}"
        return "I couldn't save the previous answer to Notepad."

    # 2. OPEN APPLICATION
    elif intent == "open_application":
        app_name = (application or "the application").title()
        if is_success:
            return f"{app_name} is now open."
        else:
            if error_msg:
                return f"I couldn't open {app_name}. {error_msg}"
            return f"I couldn't open {app_name}. Please check if it's installed."

    # 3. CLOSE APPLICATION
    elif intent == "close_application":
        app_name = (application or "the application").title()
        if is_success:
            return f"{app_name} has been closed."
        else:
            return f"{app_name} is not currently running."

    # 4. LIST APPLICATIONS
    elif intent == "list_applications":
        if isinstance(result, dict) and "applications" in result:
            apps = result["applications"]
            count = len(apps)
            sample = ", ".join(apps[:6])
            return f"You have {count} installed applications, including {sample}, and more."
        return "I found your installed applications."

    # 5. WORKSPACES
    elif intent == "workspace_action":
        if isinstance(result, dict) and result.get("explanation"):
            return result["explanation"]
        ws_name = (workspace or "workspace").title()
        if is_success:
            return f"Your {ws_name} workspace is ready."
        return f"I couldn't launch the {ws_name} workspace."

    # 6. FILE AND FOLDER ACTIONS (PHASE 3)
    elif intent == "file_action":
        if action == "open_folder":
            folder_name = (folder or path or "requested").title()
            if is_success:
                return f"Opened your {folder_name} folder in File Explorer."
            return f"I couldn't find the {folder_name} folder."

        elif action == "search":
            count = data_dict.get("count", 0)
            files = data_dict.get("files", [])
            if count == 0:
                return f"I didn't find any files matching {query or 'your search'}."
            elif count == 1:
                return f"Found {files[0]['name']} in {files[0]['directory']}."
            else:
                sample_names = ", ".join([f["name"] for f in files[:3]])
                return f"Found {count} files matching your search, including {sample_names}."

        elif action == "create_file":
            filename = (path or "file")
            if is_success:
                return f"File {filename} has been created."
            return f"Failed to create file {filename}."

        elif action == "create_folder":
            folder_target = (folder or path or "folder")
            if is_success:
                return f"Folder {folder_target} created successfully."
            return f"Failed to create folder {folder_target}."

        elif action == "read_file":
            if is_success and "content" in data_dict:
                content = data_dict["content"]
                if len(content) > 150:
                    content = content[:147] + "..."
                return f"Here is the content of {path}: {content}"
            return f"Could not read {path}."

        elif action == "delete_file":
            if is_success:
                return f"Deleted {path or 'the file'}."
            return f"Failed to delete {path or 'the file'}."

        elif action == "rename_file":
            if is_success:
                return f"Renamed {path} to {intent_data.get('new_path')}."
            return f"Failed to rename {path}."

        elif action == "copy_file":
            if is_success:
                return f"Copied {path} to {intent_data.get('new_path')}."
            return f"Failed to copy {path}."

    # 7. KEYBOARD ACTIONS (PHASE 3)
    elif intent == "keyboard_action":
        if action == "type":
            return f"Typed: {text}" if is_success else "Failed to type text."
        elif action == "press_key":
            return f"Pressed {key.title()}." if is_success else f"Failed to press {key}."
        elif action == "hotkey":
            return f"Shortcut {hotkey.upper()} executed." if is_success else f"Failed to execute shortcut {hotkey}."

    # 8. MOUSE ACTIONS (PHASE 3)
    elif intent == "mouse_action":
        if action == "click":
            return "Clicked." if is_success else "Failed to click."
        elif action == "double_click":
            return "Double clicked." if is_success else "Failed to double click."
        elif action == "right_click":
            return "Right clicked." if is_success else "Failed to right click."
        elif action == "scroll":
            direction = "up" if (data_dict.get("clicks", 0) > 0 or intent_data.get("clicks", 0) > 0) else "down"
            return f"Scrolled {direction}." if is_success else "Failed to scroll."

    # 9. CLIPBOARD ACTIONS (PHASE 3)
    elif intent == "clipboard_action":
        if action == "get":
            clip_text = data_dict.get("text", "")
            if clip_text:
                if len(clip_text) > 80:
                    clip_text = clip_text[:77] + "..."
                return f"Your clipboard contains: {clip_text}"
            return "Your clipboard is currently empty."
        elif action == "set" or action == "copy":
            return "Copied to clipboard." if is_success else "Failed to update clipboard."
        elif action == "clear":
            return "Clipboard cleared." if is_success else "Failed to clear clipboard."
        elif action == "paste":
            return "Pasted." if is_success else "Failed to paste."

    # 10. SCREEN ACTIONS – screenshot + OCR/analyze (PHASE 3 + PHASE 8)
    elif intent == "screen_action":
        screen_act = action or ""
        if screen_act == "read":
            text = data_dict.get("text", "")
            if is_success and text:
                return f"Here is the text on your screen: {text[:400]}"
            return "I couldn't detect any text on the screen." if is_success else "Failed to read the screen."
        elif screen_act in ("summarize", "describe", "explain_error"):
            explanation = data_dict.get("explanation", "")
            if is_success and explanation:
                return explanation
            return "I captured the screen but couldn't extract meaningful content." if is_success else "Failed to analyze the screen."
        else:
            # Legacy screenshot action
            if is_success:
                filename = data_dict.get("filename", "screenshot")
                return f"Screenshot captured and saved as {filename}."
            return "Failed to capture screenshot."

    # 11. WEB SEARCH (PHASE 3)
    elif intent == "web_search":
        engine = intent_data.get("engine", "google").title()
        if is_success:
            return f"Searching {engine} for {query}."
        return f"Failed to open {engine} search."

    # 12. SYSTEM VOLUME
    elif intent == "system_volume":
        if action == "get":
            vol = data_dict.get("volume", level)
            return f"Your current volume is {vol} percent." if vol is not None else "I couldn't check your volume."
        elif action == "set":
            return f"Volume set to {level} percent." if is_success else "Failed to adjust volume."
        elif action == "increase":
            return f"Volume increased by {amount or 10} percent." if is_success else "Failed to increase volume."
        elif action == "decrease":
            return f"Volume decreased by {amount or 10} percent." if is_success else "Failed to decrease volume."
        elif action == "mute":
            return "Master volume is now muted." if is_success else "Failed to mute volume."
        elif action == "unmute":
            return "Master volume is unmuted." if is_success else "Failed to unmute volume."

    # 13. SYSTEM BRIGHTNESS
    elif intent == "system_brightness":
        if action == "get":
            b = data_dict.get("brightness", level)
            return f"Screen brightness is {b} percent." if b is not None else "I couldn't check screen brightness."
        elif action == "set":
            return f"Brightness set to {level} percent." if is_success else "Failed to set brightness."
        elif action == "increase":
            return f"Brightness increased by {amount or 10} percent." if is_success else "Failed to increase brightness."
        elif action == "decrease":
            return f"Brightness decreased by {amount or 10} percent." if is_success else "Failed to decrease brightness."

    # 14. USAGE QUERIES
    elif intent == "usage_query":
        if isinstance(result, dict):
            most_app = result.get("app")
            count = result.get("count", 0)
            if most_app:
                return f"Your most used application is {most_app.title()}, launched {count} times."
        return "I checked your application usage history."

    # 15. CONTEXT QUERIES
    elif intent == "context_query":
        if isinstance(result, str):
            return result
        elif isinstance(result, dict) and "summary" in result:
            return result["summary"]
        return "You are currently working in your desktop environment."

    # DEFAULT FALLBACK
    if is_success:
        return "Action completed successfully."
    elif error_msg:
        return f"I couldn't complete that action: {error_msg}"
    else:
        return "I'm not sure how to handle that request."
