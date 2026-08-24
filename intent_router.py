from automation.app_launcher import open_application, close_application


def handle_intent(intent_data):
    intent = intent_data.get("intent")
    application = intent_data.get("application")

    if intent == "open_application":

        if not application:
            print("\n⚠️ Which application would you like me to open?")
            return False

        print(f"\n⚙️ Executing: open {application}")
        return open_application(application)

    elif intent == "close_application":

        if not application:
            print("\n⚠️ Which application would you like me to close?")
            return False

        print(f"\n⚙️ Executing: close {application}")
        return close_application(application)

    else:
        print(f"\n⚠️ I don't know how to handle intent: {intent}")
        return False