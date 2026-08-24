import subprocess
import os


def open_application(application):
    application = application.lower().strip()

    if application == "chrome":
        chrome_paths = [
            os.path.expandvars(
                r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"
            ),
            os.path.expandvars(
                r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
            ),
            os.path.expandvars(
                r"%LocalAppData%\Google\Chrome\Application\chrome.exe"
            )
        ]

        for path in chrome_paths:
            if os.path.exists(path):
                subprocess.Popen([path])
                print("✅ Opening Chrome...")
                return True

        print("❌ Chrome executable was not found.")
        return False

    elif application == "notepad":
        subprocess.Popen(["notepad.exe"])
        print("✅ Opening Notepad...")
        return True

    elif application == "calculator" or application == "calc":
        subprocess.Popen(["calc.exe"])
        print("✅ Opening Calculator...")
        return True

    elif application == "camera":
        subprocess.Popen(
            ["cmd", "/c", "start", "microsoft.windows.camera:"],
            shell=False
        )
        print("✅ Opening Camera...")
        return True

    else:
        print(f"❌ I don't know how to open: {application}")
        return False

def close_application(application):
    application = application.lower().strip()

    process_names = {
        "chrome": "chrome.exe",
        "notepad": "notepad.exe",
        "calculator": "CalculatorApp.exe",
        "calc": "CalculatorApp.exe",
        "camera": "WindowsCamera.exe"
    }

    process = process_names.get(application)

    if process:
        subprocess.run(
            ["taskkill", "/F", "/IM", process],
            capture_output=True,
            text=True
        )

        print(f"✅ Closing {application}...")
        return True

    print(f"❌ I don't know how to close: {application}")
    return False