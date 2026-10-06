"""
IntelliDesk MongoDB Manager.

Provides a connection manager and helper functions for all MongoDB
persistent memory operations across IntelliDesk modules.

Collections:
  - app_history:       Application open/close events with timestamps
  - command_history:   Every user voice command + result
  - question_history:  Q&A pairs (question + answer + timestamp)
  - workflow_history:  Workspace/workflow activation events

SECURITY:
  - Never stores API keys, passwords, tokens, or .env values.
  - Connection string is read from MONGO_URI env variable.
  - Falls back gracefully (no-op) if MongoDB is unavailable.
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass


# ============================================================
# CONNECTION
# ============================================================

_client = None
_db = None
_connected = False
_connection_error: Optional[str] = None
_last_connect_attempt: float = 0.0
_CONNECT_COOLDOWN_SECONDS: float = 30.0

DB_NAME = "intellidesk"
MONGO_URI_ENV = "MONGO_URI"
DEFAULT_FALLBACK_URI = "mongodb://localhost:27017/"


def _get_uri() -> str:
    """Read MongoDB URI from environment. Falls back to localhost."""
    uri = os.environ.get(MONGO_URI_ENV, DEFAULT_FALLBACK_URI).strip()
    if "<" in uri and ">" in uri:
        import re
        uri = re.sub(r":<([^>]+)>@", r":\1@", uri)
    return uri


def connect(force: bool = False) -> bool:
    """
    Connect to MongoDB. Returns True on success, False on failure.
    Uses a 30-second cooldown on failed attempts to prevent blocking callers.
    """
    global _client, _db, _connected, _connection_error, _last_connect_attempt

    if force and _client is not None:
        try:
            _client.close()
        except Exception:
            pass
        _client = None
        _db = None
        _connected = False

    if _connected and _db is not None:
        return True

    now = time.time()
    if not force and (now - _last_connect_attempt) < _CONNECT_COOLDOWN_SECONDS:
        return False

    _last_connect_attempt = now
    client = None

    try:
        from pymongo import MongoClient

        uri = _get_uri()
        client = MongoClient(
            uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=3000,
            socketTimeoutMS=3000
        )

        # Verify connection
        client.admin.command("ping")
        _client = client
        _db = _client[DB_NAME]
        _connected = True
        _connection_error = None
        print(f"[MongoDB] Connected to {DB_NAME} at {uri.split('@')[-1]}", flush=True)

        # Create indexes for fast sorted queries
        try:
            _db["question_history"].create_index([("timestamp", -1)], background=True)
            _db["command_history"].create_index([("timestamp", -1)], background=True)
            _db["app_history"].create_index([("application", 1)], background=True)
        except Exception:
            pass

        return True

    except Exception as e:
        _connected = False
        _connection_error = str(e)
        if client is not None:
            try:
                client.close()
            except Exception:
                pass
        _client = None
        _db = None
        print(f"[MongoDB] Unavailable: {e} — running without persistence.", file=sys.stderr, flush=True)
        return False


def get_collection(name: str):
    """Return a MongoDB collection, connecting if needed. Returns None if unavailable."""
    global _db
    if not _connected:
        connect()
    if _db is None:
        return None
    try:
        return _db[name]
    except Exception:
        return None


def is_connected() -> bool:
    """Return current connection status."""
    return _connected


def is_mongodb_available(force: bool = False) -> bool:
    """Check if MongoDB is currently available, optionally forcing reconnect."""
    if _connected and _db is not None:
        return True
    return connect(force=force)


def close_connection():
    """Safely close the MongoDB client connection."""
    global _client, _db, _connected
    if _client is not None:
        try:
            _client.close()
        except Exception:
            pass
    _client = None
    _db = None
    _connected = False



# ============================================================
# APP HISTORY
# ============================================================

def record_app_event(application: str, action: str, source: str = "voice") -> bool:
    """
    Record an application open/close event.

    Args:
        application: App name (e.g., "Google Chrome")
        action:      "open" or "close"
        source:      "voice", "gui", "api"

    Returns True if saved to MongoDB, False if unavailable (non-fatal).
    """
    if not application:
        return False

    col = get_collection("app_history")
    if col is None:
        return False

    try:
        col.insert_one({
            "application": application,
            "action": action,
            "source": source,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })
        return True
    except Exception as e:
        print(f"[MongoDB] record_app_event error: {e}", file=sys.stderr)
        return False


def get_app_frequency(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Return applications sorted by open-frequency from MongoDB.

    Returns list of: {"application": str, "count": int, "last_opened": str}
    """
    col = get_collection("app_history")
    if col is None:
        return []

    try:
        pipeline = [
            {"$match": {"action": "open"}},
            {"$group": {
                "_id": "$application",
                "count": {"$sum": 1},
                "last_opened": {"$max": "$timestamp"},
            }},
            {"$sort": {"count": -1}},
            {"$limit": limit},
        ]
        results = list(col.aggregate(pipeline))
        return [
            {
                "application": r["_id"],
                "count": r["count"],
                "last_opened": r.get("last_opened"),
            }
            for r in results
        ]
    except Exception as e:
        print(f"[MongoDB] get_app_frequency error: {e}", file=sys.stderr)
        return []


# ============================================================
# COMMAND HISTORY
# ============================================================

def record_command(
    user_command: str,
    intent: str,
    success: bool,
    response: str = "",
    source: str = "voice",
) -> bool:
    """
    Record every user command with intent and result.
    Never stores secrets or .env values.
    """
    if not user_command:
        return False

    col = get_collection("command_history")
    if col is None:
        return False

    try:
        col.insert_one({
            "command": user_command[:500],        # cap length
            "intent": intent,
            "success": success,
            "response": response[:500],           # cap length
            "source": source,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })
        return True
    except Exception as e:
        print(f"[MongoDB] record_command error: {e}", file=sys.stderr)
        return False


def get_recent_commands(limit: int = 20) -> List[Dict[str, Any]]:
    """Return the most recent commands from history."""
    col = get_collection("command_history")
    if col is None:
        return []

    try:
        return list(
            col.find({}, {"_id": 0})
            .sort("timestamp", -1)
            .limit(limit)
        )
    except Exception as e:
        print(f"[MongoDB] get_recent_commands error: {e}", file=sys.stderr)
        return []


# ============================================================
# QUESTION HISTORY
# ============================================================

def record_question(question: str, answer: str) -> bool:
    """
    Store a Q&A pair in MongoDB.
    """
    if not question or not answer:
        return False

    col = get_collection("question_history")
    if col is None:
        return False

    try:
        col.insert_one({
            "question": question[:1000],
            "answer": answer[:2000],
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })
        return True
    except Exception as e:
        print(f"[MongoDB] record_question error: {e}", file=sys.stderr)
        return False


def get_recent_questions(limit: int = 10) -> List[Dict[str, Any]]:
    """Return the most recent Q&A pairs."""
    col = get_collection("question_history")
    if col is None:
        return []

    try:
        return list(
            col.find({}, {"_id": 0})
            .sort("timestamp", -1)
            .limit(limit)
        )
    except Exception as e:
        print(f"[MongoDB] get_recent_questions error: {e}", file=sys.stderr)
        return []


# ============================================================
# WORKFLOW HISTORY
# ============================================================

def record_workflow_start(workspace: str, apps_opened: List[str]) -> bool:
    """Record a workspace/workflow activation event."""
    col = get_collection("workflow_history")
    if col is None:
        return False

    try:
        col.insert_one({
            "workspace": workspace,
            "apps_opened": apps_opened,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })
        return True
    except Exception as e:
        print(f"[MongoDB] record_workflow_start error: {e}", file=sys.stderr)
        return False


# ============================================================
# DATABASE STATUS
# ============================================================

def get_status() -> Dict[str, Any]:
    """Return connection status and collection counts."""
    status: Dict[str, Any] = {
        "connected": _connected,
        "database": DB_NAME,
        "error": _connection_error,
    }

    if _connected and _db is not None:
        try:
            status["collections"] = {
                name: _db[name].count_documents({})
                for name in ["app_history", "command_history", "question_history", "workflow_history"]
            }
        except Exception as e:
            status["count_error"] = str(e)

    return status


if __name__ == "__main__":
    print("Testing IntelliDesk MongoDB Manager...")
    ok = connect()
    print(f"Connected: {ok}")
    if ok:
        record_app_event("Google Chrome", "open", "test")
        record_question("What is Python?", "Python is a high-level programming language.")
        record_command("What is Python?", "general_question", True, "Python is...")
        freq = get_app_frequency(5)
        print(f"App frequency: {freq}")
        recent_q = get_recent_questions(3)
        print(f"Recent questions: {[q['question'] for q in recent_q]}")
        status = get_status()
        print(f"DB Status: {status}")
