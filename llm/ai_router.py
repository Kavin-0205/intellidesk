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


def classify_intent(user_command: str, session_context: Optional[dict] = None) -> Dict[str, Any]:
    """
    Classify user input text into structured intent and parameters.
    """
    if not user_command or not user_command.strip():
        return {"intent": "unknown", "error": "Empty input"}

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
            return data

        return {"intent": "unknown", "raw": raw_content}

    except json.JSONDecodeError as e:
        print(f"[AI Router JSON Error]: {repr(e)} | Raw: {raw_content}", file=sys.stderr)
        # Fallback keyword checks for high reliability
        lower = user_command.lower()
        if any(w in lower for w in ["what is", "explain", "who is", "how does", "why is", "tell me about"]):
            return {"intent": "general_question", "question": user_command}
        if "open " in lower or "launch " in lower:
            app = lower.replace("open ", "").replace("launch ", "").strip()
            return {"intent": "open_application", "application": app}
        if "close " in lower or "exit " in lower:
            app = lower.replace("close ", "").replace("exit ", "").strip()
            return {"intent": "close_application", "application": app}
        return {"intent": "unknown", "error": "Failed to parse JSON"}

    except Exception as e:
        print(f"[AI Router Exception]: {repr(e)}", file=sys.stderr)
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
