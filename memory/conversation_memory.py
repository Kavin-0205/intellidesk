"""
IntelliDesk Conversation Memory Module.

Persists Q&A pairs and command history to MongoDB.
Called automatically from the intent router after each interaction.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import mongodb


def save_qa_pair(question: str, answer: str) -> bool:
    """Persist a question-answer pair to MongoDB."""
    return mongodb.record_question(question, answer)


def save_command(
    command: str,
    intent: str,
    success: bool,
    response: str = "",
    source: str = "voice",
) -> bool:
    """Persist a user command with intent and result to MongoDB."""
    return mongodb.record_command(command, intent, success, response, source)


def get_recent_qa(limit: int = 10) -> List[Dict[str, Any]]:
    """Return recent Q&A history from MongoDB."""
    return mongodb.get_recent_questions(limit=limit)


def get_recent_commands(limit: int = 20) -> List[Dict[str, Any]]:
    """Return recent command history from MongoDB."""
    return mongodb.get_recent_commands(limit=limit)
