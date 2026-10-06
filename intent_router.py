"""
IntelliDesk Central Intent Router.

Routes classified user intents to appropriate subsystems:
- General AI questions -> Groq direct Q&A (bypasses MCP) -> TTS
- Desktop & system automation -> MCP Client -> MCP Server -> Windows
- File & folder operations -> MCP Client (open_folder, search_files, create, delete, read, rename, copy)
- Keyboard, mouse & clipboard -> MCP Client
- Screen capture -> MCP Client (take_screenshot)
- Web search -> MCP Client (search_web)
- Workspaces & Context -> Context/Workspace Managers
- Feedback generation -> Response Manager -> Text-to-Speech
"""

import sys
from typing import Any, Dict, Optional

# Ensure UTF-8 output on Windows consoles to prevent charmap UnicodeEncodeError
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from mcp_layer.client import execute_mcp_tool
from llm.ai_router import answer_general_question
from utils.response_manager import format_response
from speech.tts import speak
from context.context_manager import context

# MongoDB persistence (graceful no-op if unavailable)
try:
    from memory.conversation_memory import save_qa_pair, save_command
    from memory.app_history import record_app_open, record_app_close
    _MEMORY_AVAILABLE = True
except Exception:
    _MEMORY_AVAILABLE = False
    def save_qa_pair(*a, **kw): return False
    def save_command(*a, **kw): return False
    def record_app_open(*a, **kw): return {}
    def record_app_close(*a, **kw): return {}


def _unwrap_tool_res(res: Any) -> Dict[str, Any]:
    if not isinstance(res, dict):
        return {}
    if "result" in res and isinstance(res["result"], dict):
        merged = dict(res)
        merged.update(res["result"])
        return merged
    return res


def handle_intent(intent_data: Dict[str, Any], user_command: str = "", speak_response: bool = True) -> Dict[str, Any]:
    """
    Handle detected intent and execute the appropriate action.

    Parameters:
        intent_data (dict): The parsed intent structure from LLM.
        user_command (str): Original spoken or typed command.
        speak_response (bool): Whether to speak the output response aloud via TTS.

    Returns:
        dict: Structured result containing success status, response text, and details.
    """
    if not intent_data or not isinstance(intent_data, dict):
        response_text = "I couldn't understand that command."
        if speak_response:
            speak(response_text, wait=False)
        return {"success": False, "response": response_text}

    intent = intent_data.get("intent", "unknown")
    application = intent_data.get("application")
    action = intent_data.get("action", "")
    level = intent_data.get("level")
    amount = intent_data.get("amount")
    workspace = intent_data.get("workspace")
    question = intent_data.get("question")
    folder = intent_data.get("folder")
    path = intent_data.get("path")
    query = intent_data.get("query")
    key = intent_data.get("key")
    hotkey = intent_data.get("hotkey")
    text = intent_data.get("text")

    result_data: Dict[str, Any] = {}
    is_success = False

    # ========================================================
    # 1. GENERAL AI QUESTIONS (Bypasses MCP)
    # ========================================================
    if intent == "general_question":
        target_question = question or user_command
        save_to_notepad = bool(intent_data.get("save_to_notepad", False))
        print(f"[Router] Answering general question: {target_question}")
        if save_to_notepad:
            print("[Router] save_to_notepad=True — will open Notepad after answering")
        answer = answer_general_question(target_question)

        result_data = {"success": True, "answer": answer}
        is_success = True

        print(f"\n[IntelliDesk]: {answer}")

        # Speak the answer first
        if speak_response:
            speak(answer, wait=False)

        # Optionally save to Notepad
        notepad_result = None
        if save_to_notepad:
            notepad_text = f"Question:\n{target_question}\n\nAnswer:\n{answer}"
            notepad_result = execute_mcp_tool(
                "save_to_notepad",
                {"text": answer, "question": target_question}
            )
            if notepad_result.get("success"):
                confirmation = "I've also saved the answer in Notepad."
                print(f"[IntelliDesk]: {confirmation}")
                if speak_response:
                    speak(confirmation, wait=False)
            else:
                err = notepad_result.get("error", "unknown error")
                print(f"[IntelliDesk]: Couldn't save to Notepad: {err}", file=sys.stderr)

        response_text = answer
        context.record_interaction(user_command, intent_data, result_data, response_text)
        # Persist Q&A to MongoDB
        if save_to_notepad is False or save_to_notepad is None:
            save_qa_pair(target_question, answer)
        else:
            save_qa_pair(target_question, answer)
        save_command(user_command, intent, True, answer[:300])
        return {"success": True, "response": response_text, "data": result_data}

    # ========================================================
    # 1b. SAVE LAST ANSWER TO NOTEPAD ("Save that in Notepad")
    # ========================================================
    elif intent == "save_last_answer":
        prev_question = context.last_question
        prev_answer = context.last_answer

        if not prev_answer:
            response_text = "I don't have a previous answer to save. Please ask me a question first."
            print(f"[IntelliDesk]: {response_text}")
            if speak_response:
                speak(response_text, wait=False)
            return {"success": False, "response": response_text}

        print(f"[Router] Saving last answer to Notepad. Topic: {prev_question}")
        notepad_result = execute_mcp_tool(
            "save_to_notepad",
            {"text": prev_answer, "question": prev_question or ""}
        )
        is_success = notepad_result.get("success", False)
        result_data = notepad_result

        if is_success:
            response_text = "I've saved the previous answer in Notepad."
        else:
            err = notepad_result.get("error", "unknown error")
            response_text = f"I couldn't save to Notepad: {err}"

        print(f"[IntelliDesk]: {response_text}")
        if speak_response:
            speak(response_text, wait=False)

        context.record_interaction(user_command, intent_data, result_data, response_text)
        return {"success": is_success, "response": response_text, "data": result_data}

    # ========================================================
    # 2. OPEN APPLICATION
    # ========================================================
    elif intent == "open_application":
        if not application:
            response_text = "Which application would you like me to open?"
            print(f"[IntelliDesk]: {response_text}")
            if speak_response:
                speak(response_text, wait=False)
            return {"success": False, "response": response_text}

        print(f"[Router] Executing open application: {application}")
        mcp_res = execute_mcp_tool("open_app", {"application": application})
        is_success = mcp_res.get("success", False)
        result_data = mcp_res.get("result", mcp_res)

        response_text = format_response(intent_data, mcp_res)
        print(f"[IntelliDesk]: {response_text}")
        if speak_response:
            speak(response_text, wait=False)

        # Record app open to MongoDB
        if is_success:
            record_app_open(application)
        save_command(user_command, intent, is_success, response_text[:300])
        context.record_interaction(user_command, intent_data, result_data, response_text)
        return {"success": is_success, "response": response_text, "data": result_data}

    # ========================================================
    # 3. CLOSE APPLICATION
    # ========================================================
    elif intent == "close_application":
        # Resolve pronoun references ("close it")
        if not application:
            application = context.current_application

        if not application:
            response_text = "Which application would you like me to close?"
            print(f"[IntelliDesk]: {response_text}")
            if speak_response:
                speak(response_text, wait=False)
            return {"success": False, "response": response_text}

        print(f"[Router] Executing close application: {application}")
        mcp_res = execute_mcp_tool("close_app", {"application": application})
        is_success = mcp_res.get("success", False)
        result_data = mcp_res.get("result", mcp_res)

        response_text = format_response(intent_data, mcp_res)
        print(f"[IntelliDesk]: {response_text}")
        if speak_response:
            speak(response_text, wait=False)

        context.record_interaction(user_command, intent_data, result_data, response_text)
        return {"success": is_success, "response": response_text, "data": result_data}

    # ========================================================
    # 4. LIST INSTALLED APPLICATIONS
    # ========================================================
    elif intent == "list_applications":
        print("[Router] Listing installed applications...")
        mcp_res = execute_mcp_tool("list_installed_apps", {})
        is_success = mcp_res.get("success", False)
        result_data = mcp_res.get("result", mcp_res)

        response_text = format_response(intent_data, result_data)
        print(f"[IntelliDesk]: {response_text}")
        if speak_response:
            speak(response_text, wait=False)

        context.record_interaction(user_command, intent_data, result_data, response_text)
        return {"success": is_success, "response": response_text, "data": result_data}

    # ========================================================
    # 5. WORKSPACES
    # ========================================================
    elif intent == "workspace_action":
        target_ws = (workspace or "work").lower().strip()
        print(f"[Router] Starting workspace: {target_ws}")
        mcp_res = execute_mcp_tool("start_workspace", {"workspace_name": target_ws})
        is_success = mcp_res.get("success", False)
        result_data = mcp_res.get("result", mcp_res)

        response_text = format_response(intent_data, result_data)
        print(f"[IntelliDesk]: {response_text}")
        if speak_response:
            speak(response_text, wait=False)

        context.record_interaction(user_command, intent_data, result_data, response_text)
        return {"success": is_success, "response": response_text, "data": result_data}

    # ========================================================
    # 6. FILE AND FOLDER OPERATIONS (PHASE 3)
    # ========================================================
    elif intent == "file_action":
        print(f"[Router] File action: {action}")
        mcp_tool = "open_folder"
        args = {}

        if action == "open_folder":
            mcp_tool = "open_folder"
            args = {"folder_name": folder or path or "downloads"}
        elif action == "search":
            mcp_tool = "search_files"
            args = {
                "query": query or path or "",
                "file_ext": intent_data.get("file_ext", "") or "",
                "modified_today": bool(intent_data.get("modified_today", False))
            }
        elif action == "create_file":
            mcp_tool = "create_file"
            args = {"file_path": path or "new_file.txt", "content": intent_data.get("content", "")}
        elif action == "create_folder":
            mcp_tool = "create_folder"
            args = {"folder_path": folder or path or "New Folder"}
        elif action == "read_file":
            mcp_tool = "read_text_file"
            args = {"file_path": path or query or ""}
        elif action == "delete_file":
            mcp_tool = "delete_file"
            args = {"file_path": path or ""}
        elif action == "rename_file":
            mcp_tool = "rename_file"
            args = {"old_path": path or "", "new_path": intent_data.get("new_path", "")}
        elif action == "copy_file":
            mcp_tool = "copy_file"
            args = {"src_path": path or "", "dst_path": intent_data.get("new_path", "")}

        mcp_res = execute_mcp_tool(mcp_tool, args)
        is_success = mcp_res.get("success", False)
        result_data = mcp_res.get("result", mcp_res)

        response_text = format_response(intent_data, result_data)
        print(f"[IntelliDesk]: {response_text}")
        if speak_response:
            speak(response_text, wait=False)

        context.record_interaction(user_command, intent_data, result_data, response_text)
        return {"success": is_success, "response": response_text, "data": result_data}

    # ========================================================
    # 7. KEYBOARD CONTROL (PHASE 3)
    # ========================================================
    elif intent == "keyboard_action":
        print(f"[Router] Keyboard action: {action}")
        mcp_tool = "type_text"
        args = {}

        if action == "type":
            mcp_tool = "type_text"
            args = {"text": text or ""}
        elif action == "press_key":
            mcp_tool = "press_key"
            args = {"key": key or "enter"}
        elif action == "hotkey":
            mcp_tool = "press_hotkey"
            args = {"hotkey": hotkey or "ctrl+s"}

        mcp_res = execute_mcp_tool(mcp_tool, args)
        is_success = mcp_res.get("success", False)
        result_data = mcp_res.get("result", mcp_res)

        response_text = format_response(intent_data, result_data)
        print(f"[IntelliDesk]: {response_text}")
        if speak_response:
            speak(response_text, wait=False)

        context.record_interaction(user_command, intent_data, result_data, response_text)
        return {"success": is_success, "response": response_text, "data": result_data}

    # ========================================================
    # 8. MOUSE CONTROL (PHASE 3)
    # ========================================================
    elif intent == "mouse_action":
        print(f"[Router] Mouse action: {action}")
        if action == "scroll":
            clicks = intent_data.get("clicks", -3)
            mcp_res = execute_mcp_tool("scroll_mouse", {"clicks": int(clicks)})
        else:
            button = intent_data.get("button", "left")
            clicks = 2 if action == "double_click" else 1
            if action == "right_click":
                button = "right"
            mcp_res = execute_mcp_tool("click_mouse", {"button": button, "clicks": clicks})

        is_success = mcp_res.get("success", False)
        result_data = mcp_res.get("result", mcp_res)

        response_text = format_response(intent_data, result_data)
        print(f"[IntelliDesk]: {response_text}")
        if speak_response:
            speak(response_text, wait=False)

        context.record_interaction(user_command, intent_data, result_data, response_text)
        return {"success": is_success, "response": response_text, "data": result_data}

    # ========================================================
    # 9. CLIPBOARD CONTROL (PHASE 3)
    # ========================================================
    elif intent == "clipboard_action":
        print(f"[Router] Clipboard action: {action}")
        if action == "get":
            mcp_res = execute_mcp_tool("get_clipboard", {})
        elif action == "clear":
            mcp_res = execute_mcp_tool("clear_clipboard", {})
        elif action == "set" or action == "copy":
            if text:
                mcp_res = execute_mcp_tool("set_clipboard", {"text": text})
            else:
                mcp_res = execute_mcp_tool("press_hotkey", {"hotkey": "ctrl+c"})
        elif action == "paste":
            mcp_res = execute_mcp_tool("press_hotkey", {"hotkey": "ctrl+v"})
        else:
            mcp_res = execute_mcp_tool("get_clipboard", {})

        is_success = mcp_res.get("success", False)
        result_data = mcp_res.get("result", mcp_res)

        response_text = format_response(intent_data, result_data)
        print(f"[IntelliDesk]: {response_text}")
        if speak_response:
            speak(response_text, wait=False)

        context.record_interaction(user_command, intent_data, result_data, response_text)
        return {"success": is_success, "response": response_text, "data": result_data}

    # ========================================================
    # 10. SCREENSHOT (PHASE 3)
    # ========================================================
    elif intent == "screen_action":
        print("[Router] Capturing screen...")
        mcp_res = execute_mcp_tool("take_screenshot", {"filename": intent_data.get("filename", "") or ""})
        is_success = mcp_res.get("success", False)
        result_data = mcp_res.get("result", mcp_res)

        response_text = format_response(intent_data, result_data)
        print(f"[IntelliDesk]: {response_text}")
        if speak_response:
            speak(response_text, wait=False)

        context.record_interaction(user_command, intent_data, result_data, response_text)
        return {"success": is_success, "response": response_text, "data": result_data}

    # ========================================================
    # 11. WEB SEARCH (PHASE 3)
    # ========================================================
    elif intent == "web_search":
        query_text = intent_data.get("query", "") or user_command
        engine = intent_data.get("engine", "google")
        print(f"[Router] Web search on {engine}: {query_text}")

        mcp_res = execute_mcp_tool("search_web", {"query": query_text, "engine": engine})
        is_success = mcp_res.get("success", False)
        result_data = mcp_res.get("result", mcp_res)

        response_text = format_response(intent_data, result_data)
        print(f"[IntelliDesk]: {response_text}")
        if speak_response:
            speak(response_text, wait=False)

        context.record_interaction(user_command, intent_data, result_data, response_text)
        return {"success": is_success, "response": response_text, "data": result_data}

    # ========================================================
    # 12. SYSTEM VOLUME
    # ========================================================
    elif intent == "system_volume":
        print(f"[Router] System volume action: {action}")
        mcp_tool = "get_system_volume"
        args = {}

        if action == "set" and level is not None:
            mcp_tool = "set_system_volume"
            args = {"level": int(level)}
        elif action == "increase":
            mcp_tool = "increase_system_volume"
            args = {"amount": int(amount) if amount else 10}
        elif action == "decrease":
            mcp_tool = "decrease_system_volume"
            args = {"amount": int(amount) if amount else 10}
        elif action == "mute":
            mcp_tool = "mute_system_volume"
        elif action == "unmute":
            mcp_tool = "unmute_system_volume"

        mcp_res = execute_mcp_tool(mcp_tool, args)
        is_success = mcp_res.get("success", False)
        result_data = mcp_res.get("result", mcp_res)

        response_text = format_response(intent_data, result_data)
        print(f"[IntelliDesk]: {response_text}")
        if speak_response:
            speak(response_text, wait=False)

        context.record_interaction(user_command, intent_data, result_data, response_text)
        return {"success": is_success, "response": response_text, "data": result_data}

    # ========================================================
    # 13. SYSTEM BRIGHTNESS
    # ========================================================
    elif intent == "system_brightness":
        print(f"[Router] System brightness action: {action}")
        mcp_tool = "get_system_brightness"
        args = {}

        if action == "set" and level is not None:
            mcp_tool = "set_system_brightness"
            args = {"level": int(level)}
        elif action == "increase":
            mcp_tool = "increase_system_brightness"
            args = {"amount": int(amount) if amount else 10}
        elif action == "decrease":
            mcp_tool = "decrease_system_brightness"
            args = {"amount": int(amount) if amount else 10}

        mcp_res = execute_mcp_tool(mcp_tool, args)
        is_success = mcp_res.get("success", False)
        result_data = mcp_res.get("result", mcp_res)

        response_text = format_response(intent_data, result_data)
        print(f"[IntelliDesk]: {response_text}")
        if speak_response:
            speak(response_text, wait=False)

        context.record_interaction(user_command, intent_data, result_data, response_text)
        return {"success": is_success, "response": response_text, "data": result_data}

    # ========================================================
    # 14. USAGE QUERIES ("Open most used app", "What app do I use most?")
    # ========================================================
    elif intent == "usage_query":
        mcp_res = execute_mcp_tool("get_most_used_app", {})
        result_data = mcp_res.get("result", mcp_res)
        most_app = result_data.get("app")

        if action == "open_usual" and most_app:
            print(f"[Router] Opening usual application: {most_app}")
            open_res = execute_mcp_tool("open_app", {"application": most_app})
            is_success = open_res.get("success", False)
            response_text = f"I opened {most_app.title()}, your most frequently used application."
        else:
            is_success = True
            response_text = format_response(intent_data, result_data)

        print(f"[IntelliDesk]: {response_text}")
        if speak_response:
            speak(response_text, wait=False)

        context.record_interaction(user_command, intent_data, result_data, response_text)
        return {"success": is_success, "response": response_text, "data": result_data}

    # ========================================================
    # 15. CONTEXT QUERY ("What am I working on?")
    # ========================================================
    elif intent == "context_query":
        summary = context.get_context_summary()
        curr_app = summary.get("current_application")
        curr_proj = summary.get("current_project", "IntelliDesk")
        curr_ws = summary.get("current_workspace")

        parts = []
        if curr_ws:
            parts.append(f"in your {curr_ws.title()} workspace")
        if curr_app:
            parts.append(f"using {curr_app.title()}")
        if curr_proj:
            parts.append(f"on the {curr_proj} project")

        if parts:
            response_text = f"You are currently working {' '.join(parts)}."
        else:
            response_text = "You are currently working in your desktop workspace."

        print(f"[IntelliDesk]: {response_text}")
        if speak_response:
            speak(response_text, wait=False)

        context.record_interaction(user_command, intent_data, summary, response_text)
        return {"success": True, "response": response_text, "data": summary}

    # ========================================================
    # 16. GIT / GITHUB CONTROL
    # ========================================================
    elif intent == "git_action":
        git_action = action  # 'action' is already extracted from intent_data above
        branch = intent_data.get("branch") or ""
        commit_msg = intent_data.get("message") or ""
        repo_path = intent_data.get("repo_path") or ""
        log_limit = int(intent_data.get("limit", 5))

        print(f"[Router] Git action: {git_action}")

        if git_action == "status":
            mcp_res = execute_mcp_tool("git_status", {"repo_path": repo_path})
            is_success = mcp_res.get("success", False)
            if is_success:
                mod = mcp_res.get("modified_count", 0)
                staged = mcp_res.get("staged_count", 0)
                untracked = mcp_res.get("untracked_count", 0)
                br = mcp_res.get("branch", "unknown")
                response_text = (
                    f"You are on branch {br}. "
                    f"There are {mod} modified, {staged} staged, and {untracked} untracked files."
                )
                # List files if there are any
                files = mcp_res.get("modified_files", []) + mcp_res.get("untracked_files", [])
                if files:
                    preview = ", ".join(files[:4])
                    response_text += f" Changed files include: {preview}."
            else:
                response_text = f"I couldn't get the git status. {mcp_res.get('error', '')}"

        elif git_action == "log":
            mcp_res = execute_mcp_tool("git_log", {"repo_path": repo_path, "limit": log_limit})
            is_success = mcp_res.get("success", False)
            if is_success:
                commits = mcp_res.get("commits", [])
                if commits:
                    summaries = ". ".join([f"{c['hash']}: {c['message']}" for c in commits[:3]])
                    response_text = f"Your last {len(commits)} commits: {summaries}."
                else:
                    response_text = "No commits found in this repository."
            else:
                response_text = f"I couldn't get the commit log. {mcp_res.get('error', '')}"

        elif git_action == "branches":
            mcp_res = execute_mcp_tool("git_branches", {"repo_path": repo_path})
            is_success = mcp_res.get("success", False)
            if is_success:
                branches = mcp_res.get("branches", [])
                current = mcp_res.get("current_branch", "")
                response_text = (
                    f"You have {len(branches)} branch{'es' if len(branches) != 1 else ''}. "
                    f"Your current branch is {current}. "
                    f"All branches: {', '.join(branches)}."
                )
            else:
                response_text = f"I couldn't list the branches. {mcp_res.get('error', '')}"

        elif git_action == "checkout":
            if not branch:
                response_text = "Which branch would you like to switch to?"
                is_success = False
                mcp_res = {}
            else:
                mcp_res = execute_mcp_tool("git_checkout_branch", {"branch_name": branch, "repo_path": repo_path})
                is_success = mcp_res.get("success", False)
                response_text = (
                    f"Switched to branch {branch}."
                    if is_success else
                    f"I couldn't switch to branch {branch}. {mcp_res.get('error', '')}"
                )

        elif git_action == "create_branch":
            if not branch:
                response_text = "What would you like to name the new branch?"
                is_success = False
                mcp_res = {}
            else:
                mcp_res = execute_mcp_tool("git_create_branch", {"branch_name": branch, "repo_path": repo_path})
                is_success = mcp_res.get("success", False)
                response_text = (
                    f"Created and switched to new branch {branch}."
                    if is_success else
                    f"I couldn't create branch {branch}. {mcp_res.get('error', '')}"
                )

        elif git_action == "scan_secrets":
            mcp_res = execute_mcp_tool("git_scan_secrets", {"repo_path": repo_path})
            is_success = mcp_res.get("success", False)
            if is_success:
                if mcp_res.get("safe"):
                    response_text = f"Security scan complete. No secrets detected in {mcp_res.get('files_scanned', 0)} files. It is safe to commit."
                else:
                    violations = mcp_res.get("violations", [])
                    blocked = mcp_res.get("blocked_files", [])
                    response_text = (
                        f"Warning! I found {len(violations)} potential secret{'s' if len(violations) != 1 else ''} "
                        f"in {len(blocked)} file{'s' if len(blocked) != 1 else ''}. "
                        f"I will not commit until these are excluded. "
                        f"Blocked files: {', '.join(blocked[:3])}."
                    )
            else:
                response_text = f"Secret scan failed. {mcp_res.get('error', '')}"

        elif git_action == "commit":
            mcp_res = execute_mcp_tool("git_commit", {"message": commit_msg, "repo_path": repo_path})
            is_success = mcp_res.get("success", False)
            if is_success:
                response_text = f"Committed successfully. Commit hash: {mcp_res.get('commit_hash', '')}. Message: {mcp_res.get('commit_message', '')}."
            else:
                err = mcp_res.get("error", "Unknown error")
                if mcp_res.get("violations"):
                    response_text = f"I cannot commit because secrets were detected. {err}. Please add sensitive files to your .gitignore."
                else:
                    response_text = f"Commit failed. {err}"

        elif git_action == "push":
            mcp_res = execute_mcp_tool("git_push", {"repo_path": repo_path, "branch": branch})
            is_success = mcp_res.get("success", False)
            response_text = (
                f"Pushed to {mcp_res.get('remote', 'remote')} on branch {mcp_res.get('branch', '')  }."
                if is_success else
                f"Push failed. {mcp_res.get('error', 'Unknown error')}"
            )

        elif git_action == "commit_and_push":
            mcp_res = execute_mcp_tool("git_commit_and_push", {"message": commit_msg, "repo_path": repo_path})
            is_success = mcp_res.get("success", False)
            if is_success:
                if mcp_res.get("already_clean"):
                    response_text = "Your project is already up to date. Nothing to commit or push."
                else:
                    response_text = (
                        f"Successfully committed and pushed your project. "
                        f"Commit: {mcp_res.get('commit_hash', '')}. "
                        f"{mcp_res.get('files_changed', 0)} file{'s' if mcp_res.get('files_changed', 0) != 1 else ''} changed. "
                        f"Branch: {mcp_res.get('branch', '')}."
                    )
            else:
                err = mcp_res.get("push_error") or mcp_res.get("error") or "Unknown error"
                if mcp_res.get("violations"):
                    response_text = f"I found sensitive files and will not push. Please add them to .gitignore. Details: {err}"
                else:
                    response_text = f"Commit and push failed. {err}"

        elif git_action == "pull":
            mcp_res = execute_mcp_tool("git_pull", {"repo_path": repo_path})
            is_success = mcp_res.get("success", False)
            response_text = (
                "Pulled the latest changes successfully."
                if is_success else
                f"Pull failed. {mcp_res.get('error', 'Unknown error')}"
            )

        elif git_action == "init":
            mcp_res = execute_mcp_tool("git_init", {"repo_path": repo_path})
            is_success = mcp_res.get("success", False)
            response_text = (
                f"Initialized a new Git repository at {mcp_res.get('repo_path', 'the directory')}."
                if is_success else
                f"Git init failed. {mcp_res.get('error', 'Unknown error')}"
            )

        else:
            mcp_res = {}
            is_success = False
            response_text = f"I don't know how to perform git action '{git_action}'."

        result_data = mcp_res
        print(f"[IntelliDesk]: {response_text}")
        if speak_response:
            speak(response_text, wait=False)

        context.record_interaction(user_command, intent_data, result_data, response_text)
        return {"success": is_success, "response": response_text, "data": result_data}

    # ========================================================
    # 17. SCREEN / OCR INTELLIGENCE
    # ========================================================
    elif intent == "screen_action":
        screen_task = action  # "read" | "summarize" | "explain_error" | "describe"
        print(f"[Router] Screen action: {screen_task}")

        if screen_task == "read":
            print("[Router] OCR: reading screen text (no LLM)")
            mcp_res = execute_mcp_tool("read_screen_text", {})
            is_success = mcp_res.get("success", False)
            if is_success:
                text = mcp_res.get("text", "")
                if text:
                    response_text = f"Here is the text on your screen: {text[:400]}"
                else:
                    response_text = "I couldn't detect any text on the screen."
            else:
                response_text = f"I couldn't read the screen. {mcp_res.get('error', '')}"

        elif screen_task in ("summarize", "describe"):
            print("[Router] Screen analyze: summarize")
            mcp_res = execute_mcp_tool("analyze_screen", {"task": "summarize"})
            is_success = mcp_res.get("success", False)
            if is_success:
                response_text = mcp_res.get("explanation") or "I captured the screen but couldn't extract meaningful content."
            else:
                response_text = f"I couldn't analyze the screen. {mcp_res.get('error', '')}"

        elif screen_task == "explain_error":
            print("[Router] Screen analyze: explain error")
            mcp_res = execute_mcp_tool("explain_screen_error", {})
            is_success = mcp_res.get("success", False)
            if is_success:
                response_text = mcp_res.get("explanation") or "I captured the screen but couldn't identify a specific error."
            else:
                response_text = f"I couldn't analyze the screen. {mcp_res.get('error', '')}"

        else:
            mcp_res = {}
            is_success = False
            response_text = f"I don't know how to perform screen action '{screen_task}'."

        result_data = mcp_res
        print(f"[IntelliDesk]: {response_text[:120]}")
        if speak_response:
            speak(response_text, wait=False)

        context.record_interaction(user_command, intent_data, result_data, response_text)
        return {"success": is_success, "response": response_text, "data": result_data}

    # ========================================================
    # 18. WINDOW MANAGEMENT
    # ========================================================
    elif intent == "window_action":
        win_task = action
        win_title = intent_data.get("title") or ""
        print(f"[Router] Window action: {win_task} | title: '{win_title}'")

        if win_task == "list":
            mcp_raw = execute_mcp_tool("list_open_windows", {})
            mcp_res = _unwrap_tool_res(mcp_raw)
            is_success = mcp_res.get("success", False)
            if is_success:
                windows = mcp_res.get("windows", [])
                count = mcp_res.get("count", 0)
                if windows:
                    preview = ", ".join(w for w in windows[:5] if w.strip())
                    response_text = f"You have {count} open windows, including: {preview}."
                else:
                    response_text = "No open windows were found."
            else:
                response_text = f"I couldn't list the open windows. {mcp_res.get('error', '')}"

        elif win_task == "active":
            mcp_raw = execute_mcp_tool("get_active_window", {})
            mcp_res = _unwrap_tool_res(mcp_raw)
            is_success = mcp_res.get("success", False)
            title = mcp_res.get("title")
            response_text = (
                f"The currently active window is '{title}'."
                if is_success and title else
                "I couldn't determine the active window."
            )

        elif win_task == "focus":
            if not win_title:
                response_text = "Which window would you like me to bring to the front?"
                is_success = False
                mcp_res = {}
            else:
                mcp_raw = execute_mcp_tool("focus_window", {"title": win_title})
                mcp_res = _unwrap_tool_res(mcp_raw)
                is_success = mcp_res.get("success", False)
                response_text = (
                    f"Brought '{mcp_res.get('title', win_title)}' to the foreground."
                    if is_success else
                    f"I couldn't find a window matching '{win_title}'. {mcp_res.get('error', '')}"
                )

        elif win_task == "minimize":
            if not win_title:
                response_text = "Which window would you like me to minimize?"
                is_success = False
                mcp_res = {}
            else:
                mcp_raw = execute_mcp_tool("minimize_window", {"title": win_title})
                mcp_res = _unwrap_tool_res(mcp_raw)
                is_success = mcp_res.get("success", False)
                response_text = (
                    f"Minimized '{mcp_res.get('title', win_title)}'."
                    if is_success else
                    f"I couldn't minimize '{win_title}'. {mcp_res.get('error', '')}"
                )

        elif win_task == "maximize":
            if not win_title:
                response_text = "Which window would you like me to maximize?"
                is_success = False
                mcp_res = {}
            else:
                mcp_raw = execute_mcp_tool("maximize_window", {"title": win_title})
                mcp_res = _unwrap_tool_res(mcp_raw)
                is_success = mcp_res.get("success", False)
                response_text = (
                    f"Maximized '{mcp_res.get('title', win_title)}'."
                    if is_success else
                    f"I couldn't maximize '{win_title}'. {mcp_res.get('error', '')}"
                )

        elif win_task == "close":
            if not win_title:
                response_text = "Which window would you like me to close?"
                is_success = False
                mcp_res = {}
            else:
                mcp_raw = execute_mcp_tool("close_window", {"title": win_title})
                mcp_res = _unwrap_tool_res(mcp_raw)
                is_success = mcp_res.get("success", False)
                response_text = (
                    f"Closed '{mcp_res.get('title', win_title)}'."
                    if is_success else
                    f"I couldn't close '{win_title}'. {mcp_res.get('error', '')}"
                )

        else:
            mcp_res = {}
            is_success = False
            response_text = f"I don't understand the window action '{win_task}'."

        result_data = mcp_res
        print(f"[IntelliDesk]: {response_text}")
        if speak_response:
            speak(response_text, wait=False)
        context.record_interaction(user_command, intent_data, result_data, response_text)
        return {"success": is_success, "response": response_text, "data": result_data}

    # ========================================================
    # 19. SYSTEM POWER COMMANDS
    # ========================================================
    elif intent == "power_action":
        pwr_task = action
        delay = int(intent_data.get("delay_seconds", 60))
        print(f"[Router] Power action: {pwr_task}")

        if pwr_task == "lock":
            mcp_raw = execute_mcp_tool("lock_screen", {})
            mcp_res = _unwrap_tool_res(mcp_raw)
            is_success = mcp_res.get("success", False)
            response_text = "Locking your screen now." if is_success else f"Failed to lock screen. {mcp_res.get('error', '')}"

        elif pwr_task == "sleep":
            mcp_raw = execute_mcp_tool("sleep_system", {})
            mcp_res = _unwrap_tool_res(mcp_raw)
            is_success = mcp_res.get("success", False)
            response_text = "Putting the computer to sleep." if is_success else f"Failed to sleep. {mcp_res.get('error', '')}"

        elif pwr_task == "shutdown":
            mcp_raw = execute_mcp_tool("shutdown_system", {"delay_seconds": delay})
            mcp_res = _unwrap_tool_res(mcp_raw)
            is_success = mcp_res.get("success", False)
            if is_success:
                response_text = (
                    f"Shutdown scheduled in {delay} seconds. "
                    f"Say 'Cancel shutdown' to abort."
                )
            else:
                response_text = f"Failed to schedule shutdown. {mcp_res.get('error', '')}"

        elif pwr_task == "restart":
            mcp_raw = execute_mcp_tool("restart_system", {"delay_seconds": delay})
            mcp_res = _unwrap_tool_res(mcp_raw)
            is_success = mcp_res.get("success", False)
            if is_success:
                response_text = (
                    f"Restart scheduled in {delay} seconds. "
                    f"Say 'Cancel shutdown' to abort."
                )
            else:
                response_text = f"Failed to schedule restart. {mcp_res.get('error', '')}"

        elif pwr_task == "cancel_shutdown":
            mcp_raw = execute_mcp_tool("cancel_shutdown", {})
            mcp_res = _unwrap_tool_res(mcp_raw)
            is_success = mcp_res.get("success", False)
            response_text = "Shutdown cancelled." if is_success else f"No pending shutdown to cancel. {mcp_res.get('error', '')}"

        else:
            mcp_res = {}
            is_success = False
            response_text = f"I don't understand the power action '{pwr_task}'."

        result_data = mcp_res
        print(f"[IntelliDesk]: {response_text}")
        if speak_response:
            speak(response_text, wait=False)
        context.record_interaction(user_command, intent_data, result_data, response_text)
        return {"success": is_success, "response": response_text, "data": result_data}

    # ========================================================
    # 20. UNKNOWN
    # ========================================================
    else:
        response_text = "I'm not sure how to handle that request."
        print(f"[IntelliDesk]: {response_text}")
        if speak_response:
            speak(response_text, wait=False)
        return {"success": False, "response": response_text}