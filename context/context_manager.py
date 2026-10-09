"""
IntelliDesk Session Context Manager.

Maintains active session memory, tracks recent applications, workspaces,
active project, and performs pronoun resolution (e.g., "it", "that", "this").
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ContextManager:
    """
    Singleton-style in-memory context manager for conversational session state.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ContextManager, cls).__new__(cls)
            cls._instance._init_state()
        return cls._instance

    def _init_state(self):
        self.current_application: Optional[str] = None
        self.recently_opened_apps: List[str] = []
        self.current_workspace: Optional[str] = None
        self.current_project: Optional[str] = "IntelliDesk"
        self.current_project_path: Optional[str] = str(PROJECT_ROOT)
        self.last_command: Optional[str] = None
        self.last_intent: Optional[dict] = None
        self.last_result: Optional[dict] = None
        self.last_response: Optional[str] = None
        # Q&A context for follow-up resolution ("Who developed it?", "Save that")
        self.last_question: Optional[str] = None
        self.last_answer: Optional[str] = None
        self.last_file_target: Optional[str] = None
        self.last_window_target: Optional[str] = None
        self.history: List[dict] = []

    def record_interaction(self, user_command: str, intent_data: dict, result: Any, response_text: str):
        """Record a completed turn in session context."""
        self.last_command = user_command
        self.last_intent = intent_data
        self.last_result = result if isinstance(result, dict) else {"result": str(result)}
        self.last_response = response_text

        # Track app context
        app = intent_data.get("application") if intent_data else None
        if app and app not in ("it", "this", "that", "window", "app"):
            self.set_current_app(app)

        # Track file context
        if intent_data and intent_data.get("intent") == "file_action":
            f_target = intent_data.get("path") or intent_data.get("new_path")
            if f_target and f_target not in ("it", "this", "that", "file", "all files"):
                self.last_file_target = f_target

        # Track window context
        if intent_data and intent_data.get("intent") == "window_action":
            w_target = intent_data.get("title")
            if w_target and w_target not in ("it", "this", "that", "window"):
                self.last_window_target = w_target

        # Track workspace context
        workspace = intent_data.get("workspace") if intent_data else None
        if workspace:
            self.current_workspace = workspace

        # Track Q&A context for follow-up resolution
        if intent_data and intent_data.get("intent") == "general_question":
            q = intent_data.get("question") or user_command
            if q:
                self.last_question = q
            if isinstance(result, dict) and result.get("answer"):
                self.last_answer = result["answer"]
            elif isinstance(response_text, str) and response_text:
                self.last_answer = response_text

        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "command": user_command,
            "intent": intent_data,
            "response": response_text
        })
        # Keep sliding history size manageable
        if len(self.history) > 20:
            self.history.pop(0)

    def set_current_app(self, app_name: str):
        """Update the active application and recently opened apps list."""
        if not app_name:
            return
        self.current_application = app_name
        if app_name in self.recently_opened_apps:
            self.recently_opened_apps.remove(app_name)
        self.recently_opened_apps.insert(0, app_name)
        if len(self.recently_opened_apps) > 10:
            self.recently_opened_apps.pop()

    def set_current_project(self, project_name: str, path: Optional[str] = None):
        """Set the active project context."""
        self.current_project = project_name
        if path:
            self.current_project_path = path

    def record_file_interaction(self, file_path: str):
        """Record the most recent file operated on."""
        if file_path:
            self.last_file_target = file_path

    def record_window_interaction(self, window_title: str):
        """Record the most recent window operated on."""
        if window_title:
            self.last_window_target = window_title

    def is_ambiguous_destructive(self, text: str) -> bool:
        """
        Check if a command uses ambiguous destructive phrasing like 'shut it down'
        where it could mean either closing the active app or powering down Windows.
        """
        if not text:
            return False
        lower = text.lower().strip()
        ambiguous_phrases = ("shut it down", "turn it off", "power it down", "turn off the system")
        return any(lower == p or lower.startswith(p + " ") for p in ambiguous_phrases)

    def resolve_reference(self, text: str) -> str:
        """
        Robust general-purpose context/reference resolution mechanism.
        Resolves references such as:
          - 'it', 'this', 'that'
          - 'the app', 'the application', 'current app', 'current application'
          - 'previous app', 'previous application', 'last app'
          - 'that window', 'this window', 'current window', 'the window'
          - 'the file', 'that file', 'this file'
        Follows resolution priority:
          1. Explicit target in current command (leaves untouched)
          2. Current application/window from session state
          3. Most recent relevant successful target
          4. Previous target (for 'previous app')
        """
        if not text:
            return text

        lower = text.lower().strip()

        # 1. Do NOT mangle pure context queries (e.g. "What application am I using?")
        context_query_patterns = (
            "what application am i using",
            "what is my active application",
            "what am i working on",
            "what is open",
            "what window is active",
            "what is active"
        )
        if any(p in lower for p in context_query_patterns):
            return text

        app_target = self.current_application or (self.recently_opened_apps[0] if self.recently_opened_apps else None)
        prev_app_target = self.recently_opened_apps[1] if len(self.recently_opened_apps) > 1 else app_target

        # 2. Check for 'previous app' / 'last app' references
        if any(p in lower for p in ("previous app", "previous application", "last app", "last application")):
            target = prev_app_target or app_target
            if target:
                text_mod = lower
                for p in ("previous application", "previous app", "last application", "last app"):
                    text_mod = text_mod.replace(p, target)
                return text_mod

        # 3. Handle window management follow-up references
        window_refs = (
            "it", "that", "this", "the window", "that window", "this window",
            "the app", "the application", "current app", "current window"
        )
        target_win = self.last_window_target or app_target
        if target_win:
            # Minimize
            if lower.startswith("minimize"):
                arg = lower.replace("minimize", "").strip()
                if arg in window_refs or not arg:
                    return f"minimize {target_win}"
            # Maximize
            if lower.startswith("maximize"):
                arg = lower.replace("maximize", "").strip()
                if arg in window_refs or not arg:
                    return f"maximize {target_win}"
            # Focus / Bring to front
            if lower.startswith("focus"):
                arg = lower.replace("focus", "").strip()
                if arg in window_refs or not arg:
                    return f"focus {target_win}"
            if "bring" in lower and "front" in lower:
                return f"focus {target_win}"

            # Restore
            if lower.startswith("restore"):
                arg = lower.replace("restore", "").strip()
                if arg in window_refs or not arg:
                    return f"restore {target_win}"

        # 4. Handle file follow-up references
        file_refs = ("it", "that", "this", "the file", "that file", "this file")
        if self.last_file_target:
            if lower.startswith("delete") or lower.startswith("remove"):
                arg = lower.replace("delete", "").replace("remove", "").strip()
                if arg in file_refs:
                    return f"delete {self.last_file_target}"
            if lower.startswith("read"):
                arg = lower.replace("read", "").strip()
                if arg in file_refs:
                    return f"read {self.last_file_target}"

        # 5. Handle application follow-up references
        if app_target:
            # Closing / quitting actions
            close_verbs = ("close", "exit", "quit", "kill", "terminate", "dismiss")
            for verb in close_verbs:
                if lower.startswith(verb):
                    arg = lower.replace(verb, "").strip()
                    if arg in ("it", "that", "this", "the app", "the application", "current app", "that app", "window", "the window", "that window", ""):
                        return f"close {app_target}"

        # 6. Handle conceptual / Q&A follow-ups ("explain that", "what is it")
        if self.last_question and any(w in lower for w in ["explain", "what is", "tell me more about"]):
            for pronoun in ("that", "this", "it"):
                if lower.endswith(f" {pronoun}") or f" {pronoun} " in lower:
                    words = text.split()
                    new_words = [self.last_question if w.lower().strip(",.?!") == pronoun else w for w in words]
                    return " ".join(new_words)

        # 7. Generic pronoun substitution if context exists
        if app_target and any(lower.endswith(f" {p}") for p in ("it", "that", "this")):
            for p in ("it", "that", "this"):
                if lower.endswith(f" {p}"):
                    return text[: -(len(p))].strip() + f" {app_target}"

        return text

    def get_context_summary(self) -> dict:
        """Return a structured context dictionary suitable for LLM prompting."""
        return {
            "current_application": self.current_application,
            "recent_applications": self.recently_opened_apps[:3],
            "current_workspace": self.current_workspace,
            "current_project": self.current_project,
            "last_file_target": self.last_file_target,
            "last_window_target": self.last_window_target,
            "last_command": self.last_command,
            "last_intent": self.last_intent.get("intent") if self.last_intent else None,
            "last_question": self.last_question,
            "last_answer": self.last_answer[:200] if self.last_answer else None,
        }


# Global singleton instance
context = ContextManager()


if __name__ == "__main__":
    print("Testing ContextManager...")
    ctx = ContextManager()
    ctx.set_current_app("chrome")
    ctx.set_current_app("vscode")
    print("Recent apps:", ctx.recently_opened_apps)
    print("Resolved 'close it':", ctx.resolve_reference("close it"))
    print("Context summary:", ctx.get_context_summary())
