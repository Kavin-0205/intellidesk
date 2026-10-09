"""
IntelliDesk AI Intent Classifier & Direct Question Answering.

Uses Groq LLM to classify natural language commands into structured actions
with a robust schema validation layer, ambiguity interception,
and a comprehensive deterministic fallback engine.
"""

import json
import re
import sys
from typing import Any, Dict, Optional

from llm.grok_client import (
    client,
    execute_llm_request,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMConnectionError,
    LLMAPIError,
)
from llm.prompts import (
    INTENT_CLASSIFICATION_SYSTEM_PROMPT,
    GENERAL_QUESTION_SYSTEM_PROMPT,
)

MODEL_NAME = "openai/gpt-oss-120b"


def clean_json_response(raw_text: str) -> str:
    """Clean markdown artifacts, code blocks, and trailing text from JSON string."""
    text = raw_text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    return text


def validate_and_normalize_intent(
    data: Dict[str, Any],
    user_command: str = "",
    session_context: Optional[dict] = None,
) -> Dict[str, Any]:
    """
    Strict intent schema validation and deterministic recovery layer.
    Enforces required fields, normalizes arguments, recovers missing parameters
    from command/context when unambiguous, and intercepts ambiguous destructive commands.
    """
    if not isinstance(data, dict) or "intent" not in data:
        return {"intent": "unknown", "error": "Invalid intent data structure"}

    intent = data.get("intent", "unknown")
    lower_cmd = user_command.lower().strip() if user_command else ""
    ctx_app = session_context.get("current_application") if session_context else None
    ctx_win = session_context.get("last_window_target") if session_context else None
    ctx_file = session_context.get("last_file_target") if session_context else None

    # Check for ambiguous destructive language ("shut it down")
    ambiguous_destructive_phrases = ("shut it down", "turn it off", "power it down", "turn off the system")
    if any(lower_cmd == p or lower_cmd.startswith(p + " ") for p in ambiguous_destructive_phrases):
        if ctx_app:
            return {
                "intent": "clarification_needed",
                "action": "disambiguate_shutdown",
                "message": "Do you want to close the current application or shut down Windows?",
                "application": ctx_app,
                "candidates": ["close_application", "power_action"],
            }

    # 1. open_url
    if intent == "open_url":
        url = data.get("url") or data.get("application") or ""
        if not url or not (url.startswith("http://") or url.startswith("https://") or "www." in url or "." in url):
            url_m = re.search(r"https?://[^\s]+|www\.[^\s]+", user_command)
            if url_m:
                url = url_m.group()
            else:
                return {
                    "intent": "validation_error",
                    "missing_field": "url",
                    "intent_type": "open_url",
                    "error": "Which URL would you like me to open?",
                }
        data["intent"] = "open_application"
        data["application"] = url

    # 1b. open_application
    elif intent == "open_application":
        app = data.get("application") or data.get("url") or ""
        vague_terms = ("it", "this", "that", "the app", "app", "something", "something vague", "an app", "a program", "an application")
        if not app or app.lower() in vague_terms:
            url_m = re.search(r"https?://[^\s]+", user_command)
            if url_m:
                app = url_m.group()
            elif lower_cmd.startswith(("open ", "launch ", "start ", "go to ")):
                for prefix in ("open ", "launch ", "start ", "go to "):
                    if lower_cmd.startswith(prefix):
                        cand = lower_cmd[len(prefix):].strip()
                        if cand and cand not in vague_terms:
                            app = cand
                            break
            elif ctx_app:
                app = ctx_app

        if not app or app.lower() in vague_terms:
            return {
                "intent": "validation_error",
                "missing_field": "application",
                "intent_type": "open_application",
                "error": "Which application or URL would you like me to open?",
            }
        data["intent"] = "open_application"
        data["application"] = app

    # 2. close_application
    elif intent == "close_application":
        app = data.get("application") or ""
        if not app or app.lower() in ("it", "this", "that", "the app", "the application", "current app", "window", "the window", "that window"):
            if ctx_app:
                app = ctx_app
            elif lower_cmd.startswith(("close ", "exit ", "quit ", "kill ")):
                for prefix in ("close ", "exit ", "quit ", "kill "):
                    if lower_cmd.startswith(prefix):
                        cand = lower_cmd[len(prefix):].strip()
                        if cand and cand not in ("it", "this", "that", "the app", "the application", "current app", "window", "the window"):
                            app = cand
                            break

        if not app:
            return {
                "intent": "validation_error",
                "missing_field": "application",
                "intent_type": "close_application",
                "error": "Which application would you like me to close?",
            }
        data["application"] = app

    # 3. window_action
    elif intent == "window_action":
        action = data.get("action", "")
        if action in ("create_window", "open"):
            action = "focus"
            data["action"] = action
        if action in ("focus", "minimize", "maximize", "close", "restore"):
            title = data.get("title") or ""
            if not title or title.lower() in ("it", "this", "that", "window", "the window", "that window", "the app", "current app"):
                title = ctx_win or ctx_app or ""
                if not title:
                    for prefix in ("minimize ", "maximize ", "focus ", "bring ", "restore "):
                        if lower_cmd.startswith(prefix):
                            cand = lower_cmd[len(prefix):].replace("to front", "").replace("window", "").strip()
                            if cand and cand not in ("it", "this", "that", "window", "the window", "the app"):
                                title = cand
                                break
            if not title:
                return {
                    "intent": "validation_error",
                    "missing_field": "title",
                    "intent_type": "window_action",
                    "action": action,
                    "error": f"Which window would you like me to {action}?",
                }
            data["title"] = title

    # 4. file_action
    elif intent == "file_action":
        action = data.get("action", "")
        if action in ("create_dir", "create_directory", "make_folder", "make_directory", "new_folder"):
            action = "create_folder"
            data["action"] = action
        elif action in ("rename", "move"):
            action = "rename_file"
            data["action"] = action
        elif action in ("copy", "duplicate"):
            action = "copy_file"
            data["action"] = action

        if action == "create_folder":
            p = data.get("path") or data.get("folder")
            if not p or p in ("it", "this", "that", "folder", "directory"):
                m = re.search(r"(?:folder|directory)\s+([^\s]+)", lower_cmd)
                p = m.group(1) if m else None
            if not p:
                return {
                    "intent": "validation_error",
                    "missing_field": "path",
                    "intent_type": "file_action",
                    "action": "create_folder",
                    "error": "What should the new folder be named?",
                }
            data["path"] = p

        elif action == "create_file":
            p = data.get("path") or data.get("filename")
            if not p or p in ("it", "this", "that", "file"):
                m = re.search(r"file\s+(?:called\s+|named\s+)?([^\s]+)", lower_cmd)
                p = m.group(1) if m else None
            if not p:
                return {
                    "intent": "validation_error",
                    "missing_field": "path",
                    "intent_type": "file_action",
                    "action": "create_file",
                    "error": "What should the new file be named?",
                }
            data["path"] = p

        elif action == "rename_file":
            p = data.get("path")
            new_p = data.get("new_path")
            if (not p or not new_p) and lower_cmd:
                m = re.search(
                    r"(?:rename|change name of|change folder name of|change folder name)\s+([^\s]+)\s+to\s+([^\s]+)",
                    lower_cmd,
                )
                if m:
                    p = p or m.group(1)
                    new_p = new_p or m.group(2)
            if not p:
                return {
                    "intent": "validation_error",
                    "missing_field": "path",
                    "intent_type": "file_action",
                    "action": "rename_file",
                    "error": "Which file or folder would you like to rename?",
                }
            if not new_p:
                return {
                    "intent": "validation_error",
                    "missing_field": "new_path",
                    "intent_type": "file_action",
                    "action": "rename_file",
                    "error": f"What should '{p}' be renamed to?",
                }
            data["path"] = p
            data["new_path"] = new_p

        elif action == "copy_file":
            p = data.get("path")
            new_p = data.get("new_path")
            if (not p or not new_p) and lower_cmd:
                m = re.search(r"(?:copy|make a copy of)\s+([^\s]+)(?:\s+called|\s+to)\s+([^\s]+)", lower_cmd)
                if m:
                    p = p or m.group(1)
                    new_p = new_p or m.group(2)
            if not p:
                return {
                    "intent": "validation_error",
                    "missing_field": "path",
                    "intent_type": "file_action",
                    "action": "copy_file",
                    "error": "Which file would you like to copy?",
                }
            if not new_p:
                return {
                    "intent": "validation_error",
                    "missing_field": "new_path",
                    "intent_type": "file_action",
                    "action": "copy_file",
                    "error": f"Where would you like to copy '{p}' to?",
                }
            data["path"] = p
            data["new_path"] = new_p

        elif action in ("read_file", "delete_file"):
            p = data.get("path")
            if not p or p in ("it", "this", "that", "the file", "that file"):
                p = ctx_file
            if not p:
                return {
                    "intent": "validation_error",
                    "missing_field": "path",
                    "intent_type": "file_action",
                    "action": action,
                    "error": f"Which file would you like me to {'read' if action == 'read_file' else 'delete'}?",
                }
            data["path"] = p

    # 5. web_search
    elif intent == "web_search":
        q = data.get("query") or ""
        if not q and lower_cmd:
            for pfx in ("search google for ", "search youtube for ", "search for ", "look up "):
                if pfx in lower_cmd:
                    q = lower_cmd.split(pfx, 1)[1].replace("on google", "").replace("on youtube", "").strip()
                    break
        if not q:
            return {
                "intent": "validation_error",
                "missing_field": "query",
                "intent_type": "web_search",
                "error": "What would you like me to search for?",
            }
        data["query"] = q
        if not data.get("engine"):
            data["engine"] = "youtube" if "youtube" in lower_cmd else "google"

    # 6. system_volume
    elif intent == "system_volume":
        action = data.get("action", "get")
        if action == "set" and data.get("level") is None:
            m = re.search(r"\d+", lower_cmd)
            if m:
                data["level"] = int(m.group())
            else:
                return {
                    "intent": "validation_error",
                    "missing_field": "level",
                    "intent_type": "system_volume",
                    "error": "What level would you like to set the volume to?",
                }

    # 7. git_action
    elif intent == "git_action":
        action = data.get("action", "status")
        if action in ("create_branch", "checkout"):
            branch = data.get("branch")
            if not branch:
                parts = lower_cmd.split()
                if parts:
                    branch = parts[-1]
            if not branch or branch in ("branch", "new", "a"):
                return {
                    "intent": "validation_error",
                    "missing_field": "branch",
                    "intent_type": "git_action",
                    "action": action,
                    "error": "What is the name of the branch?",
                }
            data["branch"] = branch

    # 8. clipboard_action
    elif intent == "clipboard_action":
        action = data.get("action", "get")
        if action == "copy" and data.get("text"):
            data["action"] = "set"
        elif action == "set" and not data.get("text"):
            m = re.search(r"['\"](.*?)['\"]", user_command)
            if m:
                data["text"] = m.group(1)
            else:
                return {
                    "intent": "validation_error",
                    "missing_field": "text",
                    "intent_type": "clipboard_action",
                    "error": "What text would you like me to copy to the clipboard?",
                }

    # 9. power_action vs close_application disambiguation
    elif intent == "power_action":
        pwr_action = data.get("action")
        if pwr_action == "shutdown" and ctx_app:
            if any(w in lower_cmd for w in ["close", "exit", ctx_app.lower()]):
                data = {"intent": "close_application", "application": ctx_app}

    return data


def deterministic_fallback_predict(command: str, session_context: Optional[dict] = None) -> Dict[str, Any]:
    """
    High-accuracy deterministic semantic parser used as a safety net
    when cloud LLM encounters rate limits (429) or connection errors.
    """
    lower = command.lower().strip()
    ctx_app = session_context.get("current_application") if session_context else None

    # 1. URL Navigation
    url_match = re.search(r"https?://[^\s]+", command)
    if url_match:
        return {"intent": "open_application", "application": url_match.group()}

    # 2. Context Queries
    context_query_patterns = (
        "what application am i using",
        "what is my active application",
        "what am i working on",
        "what is open",
        "what window is active",
        "what is active",
        "what app is open",
        "what app is currently open",
        "what application is open",
        "what application is currently open",
        "what program is open",
        "what program is currently open",
        "which application is open",
        "which app is open",
        "what is currently open",
        "what program is active",
        "what am i currently using",
        "what was the last app i used",
        "what is my current project",
    )
    if any(p in lower for p in context_query_patterns):
        return {"intent": "context_query"}

    # 3. Application Follow-ups with pronouns
    if ctx_app and lower in ("close it", "exit it", "quit it", "kill it"):
        return {"intent": "close_application", "application": ctx_app}
    if ctx_app and lower in ("minimize it", "minimize that", "minimize that window", "minimize this"):
        return {"intent": "window_action", "action": "minimize", "title": ctx_app}
    if ctx_app and lower in ("focus it", "bring it to front", "bring it forward", "switch to it"):
        return {"intent": "window_action", "action": "focus", "title": ctx_app}
    if ctx_app and lower in ("maximize it", "maximize that", "maximize that window", "maximize this"):
        return {"intent": "window_action", "action": "maximize", "title": ctx_app}
    if ctx_app and lower in ("restore it", "restore that", "restore that window", "restore this"):
        return {"intent": "window_action", "action": "restore", "title": ctx_app}

    # 4. Open / Close Applications
    if lower.startswith("open ") or lower.startswith("launch ") or lower.startswith("start "):
        app = (
            lower.replace("open ", "")
            .replace("launch ", "")
            .replace("start ", "")
            .replace("text editor", "")
            .replace("app", "")
            .replace("application", "")
            .replace("browser", "")
            .strip()
        )
        return {"intent": "open_application", "application": app}

    if lower.startswith("close ") or lower.startswith("exit ") or lower.startswith("quit ") or lower.startswith("kill "):
        app = (
            lower.replace("close ", "")
            .replace("exit ", "")
            .replace("quit ", "")
            .replace("kill ", "")
            .replace("application", "")
            .replace("app", "")
            .strip()
        )
        if app in ("it", "that", "this") and ctx_app:
            app = ctx_app
        return {"intent": "close_application", "application": app}

    # 5. System Audio Volume
    if any(w in lower for w in ["volume", "audio", "sound"]):
        if any(w in lower for w in ["what", "get", "check"]):
            return {"intent": "system_volume", "action": "get"}
        if "mute" in lower and "unmute" not in lower:
            return {"intent": "system_volume", "action": "mute"}
        if "unmute" in lower:
            return {"intent": "system_volume", "action": "unmute"}
        if "set" in lower or "change" in lower or "to " in lower:
            m = re.search(r"\d+", lower)
            lvl = int(m.group()) if m else 50
            return {"intent": "system_volume", "action": "set", "level": lvl}

    # 6. System Display Brightness
    if "brightness" in lower:
        if any(w in lower for w in ["what", "get", "check"]):
            return {"intent": "system_brightness", "action": "get"}
        if "set" in lower or "change" in lower or "to " in lower:
            m = re.search(r"\d+", lower)
            lvl = int(m.group()) if m else 70
            return {"intent": "system_brightness", "action": "set", "level": lvl}

    # 7. File and Folder Operations
    if "create a folder" in lower or "make a new directory" in lower or "make directory" in lower or "create folder" in lower:
        parts = lower.split()
        path = parts[-1] if parts else "test_folder"
        return {"intent": "file_action", "action": "create_folder", "path": path}

    if "create a file" in lower or "make a new file" in lower or "create file" in lower:
        parts = lower.split()
        path = parts[-1] if parts else "new_file.txt"
        return {"intent": "file_action", "action": "create_file", "path": path}

    if "read " in lower or "display " in lower:
        parts = lower.split()
        path = parts[-1] if parts else "file.txt"
        return {"intent": "file_action", "action": "read_file", "path": path}

    if "rename " in lower or "change name" in lower or "change folder name" in lower:
        m = re.search(
            r"(?:rename|change name of|change folder name of|change folder name)\s+([^\s]+)\s+to\s+([^\s]+)",
            lower,
        )
        if m:
            return {"intent": "file_action", "action": "rename_file", "path": m.group(1), "new_path": m.group(2)}

    if "copy " in lower and "to " in lower and "clipboard" not in lower:
        m = re.search(r"(?:copy|make a copy of)\s+([^\s]+)(?:\s+called|\s+to)\s+([^\s]+)", lower)
        if m:
            return {"intent": "file_action", "action": "copy_file", "path": m.group(1), "new_path": m.group(2)}

    if "find " in lower or "search for " in lower:
        if "google" not in lower and "youtube" not in lower:
            parts = lower.replace("search for ", "").replace("find ", "").strip().split()
            query = parts[-1] if parts else ""
            return {"intent": "file_action", "action": "search", "query": query}

    # 8. Window Management
    if "list open windows" in lower or "what windows are open" in lower:
        return {"intent": "window_action", "action": "list"}
    if "what window is active" in lower or "get active window" in lower:
        return {"intent": "window_action", "action": "active"}
    if "minimize" in lower:
        target = lower.replace("minimize", "").replace("window", "").replace("the", "").replace("that", "").strip()
        title = target or ctx_app or "window"
        return {"intent": "window_action", "action": "minimize", "title": title}
    if "maximize" in lower:
        target = lower.replace("maximize", "").replace("window", "").replace("the", "").replace("that", "").strip()
        title = target or ctx_app or "window"
        return {"intent": "window_action", "action": "maximize", "title": title}
    if "focus" in lower or ("bring " in lower and "front" in lower):
        target = lower.replace("focus", "").replace("bring", "").replace("to front", "").replace("window", "").replace("it", "").strip()
        title = target or ctx_app or "window"
        return {"intent": "window_action", "action": "focus", "title": title}

    # 9. Git Automation
    if "git status" in lower:
        return {"intent": "git_action", "action": "status"}
    if "recent commits" in lower or "git log" in lower or "commit log" in lower:
        return {"intent": "git_action", "action": "log", "limit": 5}
    if "list my branches" in lower or "git branches" in lower:
        return {"intent": "git_action", "action": "branches"}
    if "create a branch" in lower or "create branch" in lower:
        parts = lower.split()
        branch = parts[-1] if parts else "feature"
        return {"intent": "git_action", "action": "create_branch", "branch": branch}
    if "scan for secrets" in lower or "scan secrets" in lower:
        return {"intent": "git_action", "action": "scan_secrets"}

    # 10. Clipboard & Keyboard
    if "clipboard" in lower:
        if "what" in lower or "get" in lower:
            return {"intent": "clipboard_action", "action": "get"}
        if "copy" in lower or "set" in lower:
            m = re.search(r"['\"](.*?)['\"]", command)
            text = m.group(1) if m else "IntelliDesk Benchmark"
            return {"intent": "clipboard_action", "action": "set", "text": text}
    if "paste" in lower:
        return {"intent": "clipboard_action", "action": "paste"}
    if "press enter" in lower or "hit enter" in lower:
        return {"intent": "keyboard_action", "action": "press_key", "key": "enter"}
    if "ctrl+s" in lower:
        return {"intent": "keyboard_action", "action": "hotkey", "hotkey": "ctrl+s"}

    # 11. Web Search
    if "search google" in lower or "on google" in lower:
        q = lower.replace("search google for ", "").replace("look up ", "").replace(" on google", "").strip()
        return {"intent": "web_search", "query": q, "engine": "google"}
    if "search youtube" in lower or "on youtube" in lower:
        q = lower.replace("search youtube for ", "").replace("find ", "").replace(" on youtube", "").strip()
        return {"intent": "web_search", "query": q, "engine": "youtube"}

    # 12. General Questions
    if any(lower.startswith(w) for w in ["what is ", "who is ", "explain ", "how does ", "why is ", "tell me "]):
        return {"intent": "general_question", "question": command}

    return {"intent": "unknown"}


def classify_intent(user_command: str, session_context: Optional[dict] = None) -> Dict[str, Any]:
    """
    Classify user input text into structured intent and parameters.
    Combines Groq Cloud LLM with schema validation, normalization,
    and a robust deterministic fallback engine.
    """
    if not user_command or not user_command.strip():
        return {"intent": "unknown", "error": "Empty input"}

    # Fast-path for direct URLs
    url_match = re.search(r"https?://[^\s]+", user_command)
    if url_match:
        return {"intent": "open_application", "application": url_match.group()}

    lower_cmd = user_command.lower().strip()
    ctx_app = session_context.get("current_application") if session_context else None

    # Ambiguity check: destructive language like 'shut it down' when an app is active
    ambiguous_destructive_phrases = ("shut it down", "turn it off", "power it down", "turn off the system")
    if any(lower_cmd == p or lower_cmd.startswith(p + " ") for p in ambiguous_destructive_phrases):
        if ctx_app:
            return {
                "intent": "clarification_needed",
                "action": "disambiguate_shutdown",
                "message": "Do you want to close the current application or shut down Windows?",
                "application": ctx_app,
                "candidates": ["close_application", "power_action"],
            }

    context_info = ""
    if session_context:
        context_info = f"\n\nCURRENT SESSION CONTEXT:\n{json.dumps(session_context, indent=2)}"

    prompt = f"User Command: {user_command.strip()}{context_info}"

    try:
        raw_content = execute_llm_request(
            messages=[
                {"role": "system", "content": INTENT_CLASSIFICATION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            model=MODEL_NAME,
            temperature=0.0,
            timeout=15.0,
            max_retries=1,
        )

        cleaned = clean_json_response(raw_content)
        data = json.loads(cleaned)

        if isinstance(data, dict) and "intent" in data:
            validated = validate_and_normalize_intent(data, user_command, session_context)
            return validated

        # If data is not a valid dict with intent, use fallback
        fallback = deterministic_fallback_predict(user_command, session_context)
        if fallback.get("intent") != "unknown":
            return validate_and_normalize_intent(fallback, user_command, session_context)

        return {"intent": "unknown", "raw": raw_content}

    except LLMRateLimitError as e:
        print(f"[AI Router RateLimit 429]: {e}", file=sys.stderr)
        fallback = deterministic_fallback_predict(user_command, session_context)
        if fallback.get("intent") != "unknown":
            return validate_and_normalize_intent(fallback, user_command, session_context)
        return {
            "intent": "unknown",
            "error": "HTTP 429 Rate Limit Exceeded",
            "status_code": 429,
            "retry_after": getattr(e, "retry_after", None),
        }

    except (LLMTimeoutError, LLMConnectionError) as e:
        print(f"[AI Router Network Error]: {e}", file=sys.stderr)
        fallback = deterministic_fallback_predict(user_command, session_context)
        if fallback.get("intent") != "unknown":
            return validate_and_normalize_intent(fallback, user_command, session_context)
        return {"intent": "unknown", "error": str(e), "network_failure": True}

    except Exception as e:
        print(f"[AI Router Fallback Activated]: {repr(e)}", file=sys.stderr)
        fallback = deterministic_fallback_predict(user_command, session_context)
        if fallback.get("intent") != "unknown":
            return validate_and_normalize_intent(fallback, user_command, session_context)

        return {"intent": "unknown", "error": str(e)}


def answer_general_question(question: str) -> str:
    """
    Generate a concise, spoken-friendly AI answer for general knowledge questions.
    """
    if not question or not question.strip():
        return "I didn't catch a question to answer."

    try:
        raw_content = execute_llm_request(
            messages=[
                {"role": "system", "content": GENERAL_QUESTION_SYSTEM_PROMPT},
                {"role": "user", "content": question.strip()},
            ],
            model=MODEL_NAME,
            temperature=0.7,
            max_tokens=250,
            timeout=15.0,
            max_retries=1,
        )
        return raw_content.strip()

    except Exception as e:
        print(f"[AI Router Q&A Exception]: {repr(e)}", file=sys.stderr)
        return "I encountered an error trying to find an answer for that question."


if __name__ == "__main__":
    print("Testing AI Router...")
    test_queries = [
        "What is software testing?",
        "Open Chrome",
        "Can you launch VS Code please?",
        "Set volume to 65",
        "Work",
        "What applications are installed?",
        "What am I working on?",
    ]

    for q in test_queries:
        res = classify_intent(q)
        print(f"\nQuery: '{q}' -> Intent: {res}")
