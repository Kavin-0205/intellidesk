import speech_recognition as sr


def capture_speech():
    recognizer = sr.Recognizer()

    with sr.Microphone() as source:
        print("🎤 Listening...")
        print("Speak now...")

        recognizer.adjust_for_ambient_noise(source, duration=1)

        print("🎤 Ready!")
        audio = recognizer.listen(
            source,
            timeout=5,
            phrase_time_limit=8
        )

    try:
        print("🔄 Converting speech to text...")

        text = recognizer.recognize_google(
            audio,
            language="en-IN"
        )

        print(f"📝 You said: {text}")

        return text

    except sr.UnknownValueError:
        print("❌ Speech was captured, but I couldn't understand it.")
        return None

    except sr.RequestError as e:
        print(f"❌ Google Speech Recognition error: {e}")
        return None

    except sr.WaitTimeoutError:
        print("❌ You didn't speak within the timeout.")
        return None