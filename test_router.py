from intent_router import handle_intent


print("Testing OPEN...")
handle_intent({
    "intent": "open_application",
    "application": "chrome"
})

print("\nTesting CLOSE...")
handle_intent({
    "intent": "close_application",
    "application": "chrome"
})

print("\nTesting missing application...")
handle_intent({
    "intent": "open_application",
    "application": None
})