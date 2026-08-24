import json

from speech.speech_capture import capture_speech
from llm.grok_client import ask_grok
from intent_router import handle_intent


print("🎤 IntelliDesk is listening...")

text = capture_speech()

if text:
    print("\n🤖 Sending command to Groq...")

    response = ask_grok(
        f"""
You are the intention detection module of IntelliDesk.

Analyze the user's command and return ONLY valid JSON.

The JSON must have exactly these fields:

{{
    "intent": "the user's intended action",
    "application": "application name or null"
}}

Rules:
Rules:
- Return ONLY JSON.
- Do NOT write explanations.
- Do NOT use markdown.
- If the user wants to open an application AND specifies the application, use intent "open_application".
- If the user wants to close an application AND specifies the application, use intent "close_application".
- Put the application name in the "application" field.
- NEVER guess or invent an application name.
- If the user says only "open" without specifying an application, use "open_application" with application set to null.
- If the user says only "close" without specifying an application, use "close_application" with application set to null.
- If the command is unrelated or cannot be understood, use "unknown" with application set to null.

User command:
{text}

Example:

User: Can you open Chrome?

Output:
{{
    "intent": "open_application",
    "application": "chrome"
}}
"""
    )

    print("\n🎯 Groq JSON:")
    print(response)

    try:
        intent_data = json.loads(response)

        print("\n✅ JSON parsed successfully!")
        print("Intent:", intent_data["intent"])
        print("Application:", intent_data["application"])

        # Execute the detected intent
        handle_intent(intent_data)

    except json.JSONDecodeError:
        print("\n❌ Groq returned invalid JSON.")

else:
    print("❌ No speech detected.")