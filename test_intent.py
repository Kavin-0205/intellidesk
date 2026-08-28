import json

from speech.speech_capture import capture_speech
from llm.grok_client import ask_grok
from intent_router import handle_intent


print("🎤 IntelliDesk is listening...")

text = capture_speech()

if text:
    print("\n🤖 Sending command to Groq...")

    response = ask_grok(f"""
You are the intention detection module of IntelliDesk.

Analyze the user's command and return ONLY valid JSON.

Return exactly this format:

{{
    "intent": "open_application | close_application | unknown",
    "application": "application name or null"
}}

Rules:
- Return ONLY JSON.
- Do NOT use markdown.
- Never guess an application name.
- If the user says only "open", set application to null.
- If the user says only "close", set application to null.

User command:
{text}
""")

    print("\n🎯 Groq Response:")
    print(response)

    try:
        # Clean accidental markdown if Groq returns it
        response = response.strip().replace("```json", "").replace("```", "")

        intent_data = json.loads(response)

        print("\n✅ Intent detected")
        print("Intent:", intent_data["intent"])
        print("Application:", intent_data["application"])

        # Execute through MCP
        handle_intent(intent_data)

    except json.JSONDecodeError:
        print("\n❌ Invalid JSON returned by Groq.")
        print(response)
else:
    print("No speech detected.")