"""
IntelliDesk Benchmark Environment Collector.
Collects hardware specs, OS version, Python version, and dependency versions.
Writes results to evaluation/results/environment.txt.
"""

import os
import sys
import platform
from pathlib import Path
import psutil

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def collect_environment() -> dict:
    env = {}

    # OS Info
    env["os_platform"] = platform.platform()
    env["os_system"] = platform.system()
    env["os_release"] = platform.release()
    env["os_version"] = platform.version()
    env["os_edition"] = platform.win32_edition() if hasattr(platform, "win32_edition") else "Windows"
    env["architecture"] = platform.architecture()[0]

    # CPU Info
    env["cpu_processor"] = platform.processor()
    env["cpu_machine"] = platform.machine()
    env["cpu_logical_cores"] = psutil.cpu_count(logical=True)
    env["cpu_physical_cores"] = psutil.cpu_count(logical=False)

    # Memory Info
    mem = psutil.virtual_memory()
    env["ram_total_bytes"] = mem.total
    env["ram_total_gb"] = round(mem.total / (1024 ** 3), 2)

    # Python Info
    env["python_version"] = sys.version.split()[0]
    env["python_full_version"] = sys.version
    env["python_executable"] = sys.executable
    env["python_compiler"] = platform.python_compiler()

    # GPU / PyTorch
    try:
        import torch
        env["torch_version"] = torch.__version__
        env["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            env["gpu_name"] = torch.cuda.get_device_name(0)
            env["cuda_version"] = torch.version.cuda
        else:
            env["gpu_name"] = "None (CPU Execution)"
            env["cuda_version"] = "N/A"
    except Exception as e:
        env["torch_version"] = f"Error: {e}"
        env["cuda_available"] = False
        env["gpu_name"] = "None"
        env["cuda_version"] = "N/A"

    # Packages
    packages = [
        "openai", "mcp", "easyocr", "PySide6", "speech_recognition",
        "pyautogui", "pygetwindow", "pycaw", "screen_brightness_control",
        "git", "pymongo", "psutil", "matplotlib", "numpy", "scipy", "pyperclip"
    ]
    pkg_versions = {}
    for pkg in packages:
        try:
            mod = __import__(pkg)
            pkg_versions[pkg] = getattr(mod, "__version__", "installed")
        except ImportError:
            pkg_versions[pkg] = "NOT_INSTALLED"
        except Exception as ex:
            pkg_versions[pkg] = f"Error: {ex}"
    env["packages"] = pkg_versions

    # LLM Model config inspection
    try:
        from llm.ai_router import MODEL_NAME
        env["configured_model_name"] = MODEL_NAME
    except Exception as e:
        env["configured_model_name"] = f"Error reading MODEL_NAME: {e}"

    # EasyOCR model availability
    try:
        from screen.ocr import easyocr_model_available
        env["easyocr_model_cached"] = easyocr_model_available()
    except Exception as e:
        env["easyocr_model_cached"] = f"Error: {e}"

    return env


def save_environment_report(output_path: Path):
    env = collect_environment()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "=" * 60,
        "INTELLIDESK EXPERIMENTAL EVALUATION ENVIRONMENT",
        "=" * 60,
        "",
        "--- SYSTEM & HARDWARE ---",
        f"Operating System:    {env['os_platform']} ({env['os_edition']})",
        f"OS Release/Version:  {env['os_release']} / {env['os_version']}",
        f"Architecture:        {env['architecture']}",
        f"CPU Processor:       {env['cpu_processor']}",
        f"Physical Cores:      {env['cpu_physical_cores']}",
        f"Logical Cores:       {env['cpu_logical_cores']}",
        f"Total RAM:           {env['ram_total_gb']} GB ({env['ram_total_bytes']} bytes)",
        f"GPU Device:          {env['gpu_name']}",
        f"CUDA Available:      {env['cuda_available']}",
        f"CUDA Version:        {env['cuda_version']}",
        "",
        "--- RUNTIME & COMPILERS ---",
        f"Python Version:      {env['python_version']}",
        f"Python Executable:   {env['python_executable']}",
        f"Python Compiler:     {env['python_compiler']}",
        f"Configured LLM Model:{env['configured_model_name']}",
        f"EasyOCR Model Cached:{env['easyocr_model_cached']}",
        "",
        "--- DEPENDENCIES & LIBRARIES ---",
    ]
    for pkg, ver in sorted(env["packages"].items()):
        lines.append(f"{pkg:24}: {ver}")

    lines.extend([
        "",
        "=" * 60,
        f"Generated automatically by collect_environment.py",
        "=" * 60,
    ])

    report = "\n".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Environment saved to: {output_path}")
    print(report)


if __name__ == "__main__":
    out_file = PROJECT_ROOT / "evaluation" / "results" / "environment.txt"
    save_environment_report(out_file)
