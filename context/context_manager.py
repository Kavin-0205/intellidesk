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
        self.history: List[dict] = []

    def record_interaction(self, user_command: str, intent_data: dict, result: Any, response_text: str):
        """Record a completed turn in session context."""
        self.last_command = user_command
        self.last_intent = intent_data
        self.last_result = result if isinstance(result, dict) else {"result": str(result)}
        self.last_response = response_text

        # Track app context
        app = intent_data.get("application") if intent_data else None
        if app:
            self.set_current_app(app)

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

    def resolve_reference(self, text: str) -> str:
        """
        Resolve pronoun references such as "it", "that", "this" based on context.
        Considers active application, last window, and last Q&A topic.
        """
        if not text:
            return text

        lower = text.lower().strip()
        app_target = self.current_application or (self.recently_opened_apps[0] if self.recently_opened_apps else None)

        # Handle specific common desktop follow-ups
        if app_target:
            if lower in ("shut it down", "turn it off"):
                return f"close {app_target}"
            if lower in ("close it", "exit it", "quit it", "kill it"):
                return f"close {app_target}"
            if lower in ("minimize it", "minimize that", "minimize that window", "minimize this"):
                return f"minimize {app_target}"
            if lower in ("maximize it", "maximize that", "maximize that window", "maximize this"):
                return f"maximize {app_target}"
            if lower in ("focus it", "bring it to front", "bring it forward", "switch to it"):
                return f"focus {app_target}"

        # Pronouns that may refer to the last discussed topic or app
        pronouns = [" it", " that", " this"]
        for p in pronouns:
            if lower.endswith(p) or f"{p} " in lower:
                # Prefer Q&A topic over app name for conceptual follow-ups
                if self.last_question and any(w in lower for w in ["explain", "what", "who", "how", "why", "tell"]):
                    target = self.last_question
                else:
                    target = app_target or self.current_project or "the active application"
                resolved = text
                for pronoun_word in ["it", "that", "this"]:
                    words = resolved.split()
                    new_words = [target if w.lower().strip(",.?!") == pronoun_word else w for w in words]
                    resolved = " ".join(new_words)
                return resolved

        return text

    def get_context_summary(self) -> dict:
        """Return a structured context dictionary suitable for LLM prompting."""
        return {
            "current_application": self.current_application,
            "recent_applications": self.recently_opened_apps[:3],
            "current_workspace": self.current_workspace,
            "current_project": self.current_project,
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
