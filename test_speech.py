from speech.speech_capture import capture_speech


print("Starting IntelliDesk speech capture...")

text = capture_speech()

print("Final text:", text)