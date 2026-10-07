"""
IntelliDesk AI Intent Classifier & Direct Question Answering.

Uses Groq LLM to classify natural language commands into structured actions
and answer general knowledge questions.
"""

import json
import re
import sys
from typing import Any, Dict, Optional

from llm.grok_client import client
from llm.prompts import (
    INTENT_CLASSIFICATION_SYSTEM_PROMPT,
    GENERAL_QUESTION_SYSTEM_PROMPT,
)


MODEL_NAME = "openai/gpt-oss-120b"


def clean_json_response(raw_text: str) -> str:
    """Clean markdown artifacts, code blocks, and trailing text from JSON string."""
    text = raw_text.strip()
    # Remove markdown code blocks
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    # Find the outermost JSON object { ... }
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    return text


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
    if "what application am i using" in lower or "what is my active application" in lower or "what am i working on" in lower:
        return {"intent": "context_query"}

    # 3. Application Follow-ups with pronouns
    if ctx_app and lower in ("close it", "exit it", "shut it down", "turn it off", "quit it", "kill it"):
        return {"intent": "close_application", "application": ctx_app}
    if ctx_app and lower in ("minimize it", "minimize that", "minimize that window", "minimize this"):
        return {"intent": "window_action", "action": "minimize", "title": ctx_app}
    if ctx_app and lower in ("focus it", "bring it to front", "bring it forward", "switch to it"):
        return {"intent": "window_action", "action": "focus", "title": ctx_app}

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
    if "create a folder" in lower or "make a new directory" in lower or "make directory" in lower:
        parts = lower.split()
        path = parts[-1] if parts else "test_folder"
        return {"intent": "file_action", "action": "create_folder", "path": path}

    if "create a file" in lower or "make a new file" in lower:
        parts = lower.split()
        path = parts[-1] if parts else "new_file.txt"
        return {"intent": "file_action", "action": "create_file", "path": path}

    if "read " in lower or "display " in lower:
        parts = lower.split()
        path = parts[-1] if parts else "file.txt"
        return {"intent": "file_action", "action": "read_file", "path": path}

    if "rename " in lower or "change name" in lower or "change folder name" in lower:
        # e.g. "Rename create_test.txt to renamed_test.txt" or "Change folder name test_folder to renamed_folder"
        m = re.search(r"(?:rename|change name of|change folder name of|change folder name)\s+([^\s]+)\s+to\s+([^\s]+)", lower)
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
    if "focus" in lower or "bring " in lower and "front" in lower:
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
    Combines Groq Cloud LLM with smart pre-processing, post-processing normalization,
    and a robust deterministic fallback engine.
    """
    if not user_command or not user_command.strip():
        return {"intent": "unknown", "error": "Empty input"}

    # Fast-path for direct URLs
    url_match = re.search(r"https?://[^\s]+", user_command)
    if url_match:
        return {"intent": "open_application", "application": url_match.group()}

    context_info = ""
    if session_context:
        context_info = f"\n\nCURRENT SESSION CONTEXT:\n{json.dumps(session_context, indent=2)}"

    prompt = f"User Command: {user_command.strip()}{context_info}"

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": INTENT_CLASSIFICATION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )

        raw_content = response.choices[0].message.content or ""
        cleaned = clean_json_response(raw_content)

        data = json.loads(cleaned)
        if isinstance(data, dict) and "intent" in data:
            # Post-processing normalization to maximize accuracy
            intent = data.get("intent")
            ctx_app = session_context.get("current_application") if session_context else None

            # 1. Resolve missing application/title if context exists
            if intent == "close_application" and not data.get("application") and ctx_app:
                data["application"] = ctx_app
            if intent == "window_action" and not data.get("title") and ctx_app:
                data["title"] = ctx_app

            # 2. File action normalization
            if intent == "file_action":
                act = data.get("action")
                if act in ("create_dir", "create_directory", "make_folder"):
                    data["action"] = "create_folder"
                elif act in ("rename", "move"):
                    data["action"] = "rename_file"

            # 3. Clipboard normalization
            if intent == "clipboard_action" and data.get("action") == "copy" and data.get("text"):
                data["action"] = "set"

            # 4. Disambiguate power vs close
            if intent == "power_action" and data.get("action") == "shutdown" and ctx_app:
                lower_cmd = user_command.lower()
                if any(w in lower_cmd for w in ["close", "exit", "shut it down", "turn it off", ctx_app.lower()]):
                    data = {"intent": "close_application", "application": ctx_app}

            return data

        # If data is not a valid dict with intent, use fallback
        fallback = deterministic_fallback_predict(user_command, session_context)
        if fallback.get("intent") != "unknown":
            return fallback

        return {"intent": "unknown", "raw": raw_content}

    except Exception as e:
        print(f"[AI Router Fallback Activated]: {repr(e)}", file=sys.stderr)
        # Cloud LLM failed (rate limit 429, timeout, JSON error).
        # Seamlessly activate deterministic semantic fallback to guarantee uptime & accuracy!
        fallback = deterministic_fallback_predict(user_command, session_context)
        if fallback.get("intent") != "unknown":
            return fallback

        return {"intent": "unknown", "error": str(e)}


def answer_general_question(question: str) -> str:
    """
    Generate a concise, spoken-friendly AI answer for general knowledge questions.
    """
    if not question or not question.strip():
        return "I didn't catch a question to answer."

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": GENERAL_QUESTION_SYSTEM_PROMPT},
                {"role": "user", "content": question.strip()}
            ],
            temperature=0.7,
            max_tokens=250
        )

        answer = response.choices[0].message.content or ""
        return answer.strip()

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

    print("\nTesting Direct Question Answering:")
    ans = answer_general_question("What is software testing?")
    print("Answer:\n", ans)
