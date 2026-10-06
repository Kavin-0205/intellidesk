# IntelliDesk — AI Desktop Assistant

An intelligent, voice-and-chat-enabled Windows desktop automation assistant powered by **Groq LLM**, **PySide6 (Qt)**, **Model Context Protocol (MCP)**, and **MongoDB Atlas**.

---

## 🌟 Overview

IntelliDesk bridges high-speed Large Language Models with local Windows OS automation. It enables users to interact naturally via voice or text to control desktop applications, manage files, inspect screens via OCR, operate Git repositories safely, and monitor system resources in real-time.

```
+-------------------------------------------------------------+
|                      IntelliDesk GUI                         |
|     (Dashboard | Voice | Chat | OCR | Code | Files | Settings)|
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                     AI Intent Router                         |
|  - Context & Pronoun Resolution (context/context_manager.py) |
|  - Groq LLM Classifier (openai/gpt-oss-120b)                |
|  - Direct Q&A & Notepad Integration                         |
+------------------------------+------------------------------+
                               |
              +----------------+----------------+
              |                                 |
              v                                 v
+-----------------------------+   +-----------------------------+
|     MCP Tool Server         |   |    Persistent Memory        |
|  - App Discovery (160+ apps)|   |  - MongoDB Atlas Cluster    |
|  - Window & Power Controls  |   |  - Local In-Memory Fallback |
|  - File & Browser Actions   |   |  - App Usage Frequencies    |
|  - Input (Mouse & Keyboard) |   +-----------------------------+
|  - Git & Secret Scanner     |
|  - Screen OCR Analyzer      |
+-----------------------------+
```

---

## ✨ Features

### 1. 🖥 Desktop GUI (PySide6)
- **Dashboard**: Live CPU, RAM, Disk usage meters, system uptime, and session statistics.
- **Voice Assistant**: Interactive microphone button with real-time listening state and conversational bubble history.
- **AI Chat**: Text-based chat with quick-prompt suggestions.
- **Screen Reader**: Screenshot capture, EasyOCR text extraction, screen summarization, and AI error analysis.
- **Coding Assistant**: Git control center (status, recent commits, branches, secret scan) and AI code explanation.
- **File Manager**: Shortcuts to system folders (Downloads, Documents, Desktop) and file search interface.
- **History & Memory**: Live list of executed commands, Q&A pairs, and most-used applications.
- **Settings & Diagnostics**: In-app Groq API validation, MongoDB Atlas connection test, voice testing, and environment diagnostics.

### 2. 🤖 AI Intent Routing & Context
- **Groq LLM**: Ultra-low-latency classification using `openai/gpt-oss-120b`.
- **Context-Aware Reference Resolution**: Resolves pronouns like *"close it"*, *"save that to Notepad"*, or *"what am I working on?"*.
- **Direct Q&A**: Answers general knowledge, coding, and technical questions naturally without JSON artifacts.

### 3. ⚡ Automation & Model Context Protocol (MCP)
- **App Discovery & Launch**: Detects 160+ installed Windows applications (EXEs, Start Menu shortcuts, UWP modern apps, web shortcuts).
- **Window Management**: Minimize, maximize, focus, list active windows, and safe protected-process management.
- **System Power**: Screen lock, sleep, timed shutdown (60s countdown), and shutdown abort.
- **Volume & Brightness**: Windows audio endpoint integration (pycaw) and display brightness control.
- **Input Control**: Virtual keyboard typing, hotkeys, mouse clicks, and clipboard manipulation.
- **Browser Automation**: Direct searches on Google, YouTube, GitHub, and web navigation.
- **Git Control & Secret Scanner**: Repository status, branch management, and automated secret scanning that prevents accidental commits of API keys or `.env` files.

### 4. 💾 Dual-Layer Memory & MongoDB Atlas
- Automatically logs commands, app events, and Q&A history to **MongoDB Atlas**.
- Seamless fallback: Operates smoothly in memory if the database is offline or during network dropouts.

---

## 📁 Repository Structure

```
finalproject/
├── app.py                      # Application entry point (PySide6 GUI)
├── intent_router.py            # Central intent classifier and tool dispatcher
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variable configuration template
│
├── automation/                 # OS Automation Modules
│   ├── app_discovery.py        # Windows installed app scanner (EXE, UWP, Start Menu)
│   ├── app_launcher.py         # Application launch and terminate logic
│   ├── browser_control.py      # Web searches and URL navigation
│   ├── file_control.py         # File/folder CRUD and search operations
│   ├── git_control.py          # Git commands and secret scanning engine
│   ├── keyboard_control.py     # Virtual typing, hotkeys, clipboard
│   ├── mouse_control.py        # Mouse movements and clicks
│   ├── notepad_control.py      # Notepad export and note-taking
│   ├── screen_control.py       # Screenshot capture utilities
│   ├── system_control.py       # Volume, brightness, and power management
│   └── window_control.py       # Window focus, minimize, maximize, list
│
├── context/                    # Session & Workspace Context
│   ├── context_manager.py      # Session memory and pronoun resolver
│   ├── usage_manager.py        # Resource tracking
│   └── workspace_manager.py    # Workspace configuration runner
│
├── database/                   # Database Layer
│   └── mongodb.py              # MongoDB Atlas client and collections manager
│
├── gui/                        # PySide6 Desktop Interface
│   ├── cards.py                # Dashboard metric cards
│   ├── chat.py                 # AI Chat page
│   ├── code_page.py            # Coding & Git assistant page
│   ├── dashboard.py            # System health dashboard page
│   ├── files_page.py           # File explorer page
│   ├── history_page.py         # Command and Q&A history page
│   ├── main_window.py          # Central QMainWindow and sidebar navigation
│   ├── screen_page.py          # Screen OCR reader page
│   ├── settings.py             # Settings and diagnostics page
│   ├── styles.py               # Dark theme stylesheet
│   └── voice_page.py           # Voice assistant page
│
├── llm/                        # LLM Client & Prompts
│   ├── ai_router.py            # Intent classification and prompt pipeline
│   ├── grok_client.py          # Groq OpenAI-compatible client
│   └── prompts.py              # System prompts for intent classification
│
├── mcp_layer/                  # Model Context Protocol
│   ├── client.py               # Tool execution client
│   └── server.py               # FastMCP tool server definitions
│
├── memory/                     # Local Memory Utilities
│   ├── app_history.py          # App usage frequency tracking
│   └── conversation_memory.py  # Session conversation logs
│
├── screen/                     # Screen OCR & Vision
│   ├── ocr.py                  # EasyOCR engine wrapper
│   └── screen_analyzer.py      # Screen summarizer and error explainer
│
├── speech/                     # Speech Audio
│   ├── speech_capture.py       # Microphone speech recognition (STT)
│   └── tts.py                  # Text-to-Speech engine (Windows SAPI5)
│
└── tests/                      # Automated Test Suite (70+ tests)
    ├── test_app_discovery.py
    ├── test_file_control.py
    ├── test_general_questions.py
    ├── test_git_control.py
    ├── test_gui.py
    ├── test_input_control.py
    ├── test_mcp_extended.py
    ├── test_mongodb.py
    ├── test_phase3_integration.py
    ├── test_qa_notepad.py
    ├── test_router_integration.py
    ├── test_screen_control.py
    ├── test_screen_ocr.py
    ├── test_window_power.py
    └── test_workspaces.py
```

---

## 🚀 Quick Start

### 1. Prerequisites
- **Windows 10 or 11** (64-bit)
- **Python 3.11+**
- A **Groq API Key** ([console.groq.com](https://console.groq.com))
- *(Optional)* A **MongoDB Atlas** connection string for cloud persistence

### 2. Setup Environment

Clone the repository and set up a virtual environment:

```powershell
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install required packages
pip install -r requirements.txt
```

### 3. Configure Credentials

Create a `.env` file from `.env.example`:

```powershell
cp .env.example .env
```

Open `.env` and fill in your keys:

```env
GROQ_API_KEY=gsk_your_groq_api_key_here
MONGO_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?appName=intellidesk
```

*(Note: If you leave `MONGO_URI` unset, IntelliDesk will automatically run in local memory mode without errors.)*

### 4. Run the Application

Launch the desktop GUI:

```powershell
python app.py
```

To test microphone voice interaction via the CLI:

```powershell
python test_intent.py
```

---

## 🧪 Running Tests

Execute individual test suites to verify subsystem health:

```powershell
# GUI components & page layout
python -m unittest tests/test_gui.py

# MongoDB Atlas persistence
python tests/test_mongodb.py

# Git control & secret scanner
python tests/test_git_control.py

# Screen OCR & Vision
python tests/test_screen_ocr.py

# Q&A, Notepad & Context memory
python tests/test_qa_notepad.py

# Windows Management & Power
python -m unittest tests/test_window_power.py tests/test_workspaces.py

# Installed App Discovery
python tests/test_app_discovery.py
```

---

## 🛡 Security & Privacy

- **Secret Scanner**: Before executing git commits, IntelliDesk scans files for API keys, bearer tokens, passwords, and `.env` files to prevent accidental credential leaks.
- **Protected Processes**: Prevents programmatic closing of critical system processes (e.g., `Taskmgr.exe`, `explorer.exe`, `csrss.exe`).
- **Input Sanitization**: MongoDB URIs and user commands are sanitized against prompt injection and malicious formatting.

---

## 📄 License

MIT License. Developed for intelligent Windows desktop workflow automation.