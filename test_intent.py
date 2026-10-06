"""
IntelliDesk Voice & Intent Pipeline Test Script.

Listens to microphone input, performs Speech-to-Text, classifies intent with Groq LLM,
routes to MCP or Direct Q&A, updates context, and speaks response.
"""

from speech.speech_capture import capture_speech
from llm.ai_router import classify_intent
from intent_router import handle_intent
from context.context_manager import context


def run_voice_cycle():
    print("=" * 60)
    print("🎤 IntelliDesk is listening... (Speak a command or question)")
    print("=" * 60)

    # 1. Speech Capture
    text = capture_speech()

    if not text:
        print("❌ No speech detected.")
        return

    print(f"\n📝 Transcribed Spoken Text: \"{text}\"")

    # 2. Pronoun and Reference Resolution from Context
    resolved_text = context.resolve_reference(text)
    if resolved_text != text:
        print(f"🔄 Context Resolved: \"{resolved_text}\"")

    # 3. Intent Classification with Groq LLM
    print("\n🤖 Analyzing command with Groq LLM...")
    session_summary = context.get_context_summary()
    intent_data = classify_intent(resolved_text, session_context=session_summary)

    print("\n🎯 Detected Intent Data:")
    print(intent_data)

    # 4. Route and Execute
    print("\n⚡ Executing Intent...")
    result = handle_intent(intent_data, user_command=resolved_text, speak_response=True)
    print("\n✨ Turn Complete. Result:", result.get("success"))


if __name__ == "__main__":
    run_voice_cycle()