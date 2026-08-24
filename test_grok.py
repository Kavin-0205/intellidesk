from llm.grok_client import ask_grok

print("Sending request to Groq...")

result = ask_grok(
    "I am testing the IntelliDesk Groq connection. "
    "Reply exactly with: Groq connection successful."
)

print("Groq response:")
print(result)