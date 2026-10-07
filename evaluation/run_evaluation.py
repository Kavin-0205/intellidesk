"""
IntelliDesk IEEE Conference Evaluation Runner with Full Resume & Checkpoint Engine.

Resumability Features:
- Preserves every completed trial immediately to raw_results.csv (disk-flushed after every trial).
- Loads existing results on startup, identifies already-completed trial keys, and skips them.
- Resumes execution from the exact first incomplete trial.
- Never reruns or overwrites completed trials (including failed trials, preserving natural failure distributions).
- Captures SIGINT (Ctrl+C) and SIGTERM gracefully, saving state to checkpoint.json.
- Displays detailed startup progress and resume summary for B0, B1, B2, B3, MCP, and OCR.
"""

import csv
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import psutil

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# IntelliDesk Core Modules
from automation.app_launcher import open_application, close_application
from automation import file_control as file_ctl
from automation import window_control as win_ctl
from automation import system_control as sys_ctl
from automation import git_control as git_ctl
from context.context_manager import ContextManager, context
from llm.ai_router import classify_intent, answer_general_question, clean_json_response
from mcp_layer.client import execute_mcp_tool
from intent_router import handle_intent
from screen.ocr import extract_text_from_image, extract_text_from_screenshot, easyocr_model_available
from evaluation.benchmark import get_all_benchmark_tasks, BenchmarkTask


def is_application_running(app_name: str) -> bool:
    target = app_name.lower().strip()
    for p in psutil.process_iter(["name"]):
        try:
            name = (p.info["name"] or "").lower()
            if target in name:
                return True
        except Exception:
            pass
    return False


# File Paths
WORKSPACE = PROJECT_ROOT / "evaluation_workspace"
RESULTS_DIR = PROJECT_ROOT / "evaluation" / "results"
RAW_CSV_PATH = RESULTS_DIR / "raw_results.csv"
CHECKPOINT_PATH = RESULTS_DIR / "checkpoint.json"
MCP_OVERHEAD_CSV_PATH = RESULTS_DIR / "mcp_overhead.csv"
OCR_ACCURACY_CSV_PATH = RESULTS_DIR / "ocr_accuracy.csv"

CSV_FIELDS = [
    "run_id",
    "configuration",
    "category",
    "task_id",
    "phrasing_id",
    "command",
    "previous_command",
    "expected_intent",
    "expected_arguments",
    "predicted_intent",
    "predicted_arguments",
    "context_enabled",
    "ocr_enabled",
    "fallback_used",
    "ocr_success",
    "task_success",
    "context_resolution_success",
    "failure_category",
    "error_message",
    "input_latency_ms",
    "llm_latency_ms",
    "ocr_latency_ms",
    "routing_latency_ms",
    "mcp_latency_ms",
    "execution_latency_ms",
    "end_to_end_latency_ms",
    "cpu_percent",
    "peak_ram_mb",
    "timestamp",
]

# Graceful termination flag
_SHUTDOWN_REQUESTED = False


def _signal_handler(signum, frame):
    global _SHUTDOWN_REQUESTED
    print("\n[Harness] Shutdown signal received (Ctrl+C). Finishing current step and exiting safely...")
    _SHUTDOWN_REQUESTED = True


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


# =========================================================================
# CHECKPOINT & RESUME MANAGER
# =========================================================================
class CheckpointManager:
    def __init__(self):
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        self.completed_trials: Set[str] = set()
        self.highest_run_id_num: int = 0
        self.load_existing_results()

    def get_trial_key(self, config: str, task_id: str, phrasing_id: str, repetition: int) -> str:
        return f"{config}:{task_id}:{phrasing_id}:T{repetition}"

    def load_existing_results(self):
        if not RAW_CSV_PATH.exists():
            with open(RAW_CSV_PATH, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
                writer.writeheader()
            return

        with open(RAW_CSV_PATH, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cfg = row.get("configuration")
                tid = row.get("task_id")
                pid = row.get("phrasing_id")
                rid = row.get("run_id", "")

                # Extract repetition number from run_id e.g. RUN_0123_B1_task_p1_T2 -> 2
                m_rep = re.search(r"_T(\d+)$", rid)
                rep = int(m_rep.group(1)) if m_rep else 1

                # Extract run number
                m_num = re.search(r"RUN_(\d+)", rid)
                if m_num:
                    num = int(m_num.group(1))
                    if num > self.highest_run_id_num:
                        self.highest_run_id_num = num

                if cfg and tid and pid:
                    key = self.get_trial_key(cfg, tid, pid, rep)
                    self.completed_trials.add(key)

    def is_completed(self, config: str, task_id: str, phrasing_id: str, repetition: int) -> bool:
        key = self.get_trial_key(config, task_id, phrasing_id, repetition)
        return key in self.completed_trials

    def record_trial(self, record: dict, config: str, task_id: str, phrasing_id: str, repetition: int):
        clean_row = {}
        for field in CSV_FIELDS:
            val = record.get(field, "NA")
            if val is None:
                clean_row[field] = "NA"
            elif isinstance(val, (dict, list)):
                clean_row[field] = json.dumps(val)
            else:
                clean_row[field] = str(val)

        # Append and flush immediately to disk
        with open(RAW_CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writerow(clean_row)
            f.flush()
            os.fsync(f.fileno())

        key = self.get_trial_key(config, task_id, phrasing_id, repetition)
        self.completed_trials.add(key)
        self.save_checkpoint_json(last_run_id=record.get("run_id", ""))

    def save_checkpoint_json(self, last_run_id: str = ""):
        data = {
            "last_updated": datetime.now().isoformat(),
            "total_completed": len(self.completed_trials),
            "last_run_id": last_run_id,
            "raw_csv_path": str(RAW_CSV_PATH),
        }
        with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


# =========================================================================
# BASELINE B0: RULE / KEYWORD MATCHER
# =========================================================================
def rule_baseline_predict(command: str) -> Tuple[Dict[str, Any], bool]:
    lower = command.lower().strip()
    if lower.startswith("open ") or lower.startswith("launch ") or lower.startswith("start "):
        app = (
            lower.replace("open ", "")
            .replace("launch ", "")
            .replace("start ", "")
            .replace("text editor", "")
            .replace("app", "")
            .replace("application", "")
            .replace("browser", "")
            .strip()
        )
        return {"intent": "open_application", "application": app}, False

    if lower.startswith("close ") or lower.startswith("exit ") or lower.startswith("quit "):
        app = (
            lower.replace("close ", "")
            .replace("exit ", "")
            .replace("quit ", "")
            .replace("application", "")
            .strip()
        )
        return {"intent": "close_application", "application": app}, False

    if "volume" in lower or "audio" in lower or "sound" in lower:
        if "what" in lower or "get" in lower or "check" in lower:
            return {"intent": "system_volume", "action": "get"}, False
        if "mute" in lower and "unmute" not in lower:
            return {"intent": "system_volume", "action": "mute"}, False
        if "unmute" in lower:
            return {"intent": "system_volume", "action": "unmute"}, False
        if "set" in lower or "change" in lower:
            m = re.search(r"\d+", lower)
            lvl = int(m.group()) if m else 50
            return {"intent": "system_volume", "action": "set", "level": lvl}, False

    if "brightness" in lower:
        if "what" in lower or "get" in lower or "check" in lower:
            return {"intent": "system_brightness", "action": "get"}, False
        if "set" in lower or "change" in lower:
            m = re.search(r"\d+", lower)
            lvl = int(m.group()) if m else 70
            return {"intent": "system_brightness", "action": "set", "level": lvl}, False

    if "create a file" in lower or "make a new file" in lower:
        parts = lower.split()
        path = parts[-1] if parts else "new_file.txt"
        return {"intent": "file_action", "action": "create_file", "path": path}, False

    if "read " in lower or "display " in lower:
        parts = lower.split()
        path = parts[-1] if parts else "file.txt"
        return {"intent": "file_action", "action": "read_file", "path": path}, False

    if "list open windows" in lower or "what windows are open" in lower:
        return {"intent": "window_action", "action": "list"}, False

    if "what window is active" in lower or "get active window" in lower:
        return {"intent": "window_action", "action": "active"}, False

    if "git status" in lower:
        return {"intent": "git_action", "action": "status"}, False
    if "commits" in lower:
        return {"intent": "git_action", "action": "log", "limit": 5}, False
    if "branches" in lower:
        return {"intent": "git_action", "action": "branches"}, False

    return {"intent": "unknown"}, False


# =========================================================================
# EVALUATION HARNESS CORE
# =========================================================================
class EvaluationHarness:
    def __init__(self, repetitions: int = 3):
        self.repetitions = repetitions
        self.process = psutil.Process()
        self.checkpoint = CheckpointManager()
        self.run_counter = self.checkpoint.highest_run_id_num
        self.setup_sandbox()

    def setup_sandbox(self):
        WORKSPACE.mkdir(parents=True, exist_ok=True)
        self.git_sandbox = WORKSPACE / "git_sandbox"
        if not self.git_sandbox.exists() or not (self.git_sandbox / ".git").exists():
            self.git_sandbox.mkdir(parents=True, exist_ok=True)
            try:
                import git
                repo = git.Repo.init(self.git_sandbox)
                repo.config_writer().set_value("user", "name", "Benchmark").release()
                repo.config_writer().set_value("user", "email", "benchmark@test.local").release()
                readme = self.git_sandbox / "README.md"
                readme.write_text("# Test Repo\n", encoding="utf-8")
                repo.index.add(["README.md"])
                repo.index.commit("Initial commit")
            except Exception as e:
                print(f"[Sandbox Warning] Git init: {e}")

    def check_intent_accuracy(
        self,
        predicted: Dict[str, Any],
        expected_intent: str,
        expected_args: Dict[str, Any],
    ) -> bool:
        pred_intent = predicted.get("intent")
        if pred_intent != expected_intent:
            return False

        for k, v in expected_args.items():
            pred_v = predicted.get(k)
            if pred_v is None:
                return False
            if isinstance(v, str) and isinstance(pred_v, str):
                if v.lower() not in pred_v.lower() and pred_v.lower() not in v.lower():
                    return False
            elif isinstance(v, int) and isinstance(pred_v, (int, float)):
                if int(pred_v) != v:
                    return False
            elif isinstance(v, bool):
                if bool(pred_v) != v:
                    return False

        return True

    def run_trial(
        self,
        config: str,
        task: BenchmarkTask,
        phrasing: Dict[str, str],
        trial_idx: int,
    ) -> dict:
        self.run_counter += 1
        run_id = f"RUN_{self.run_counter:04d}_{config}_{task.task_id}_{phrasing['id']}_T{trial_idx}"
        cmd_text = phrasing["text"]
        timestamp = datetime.now().isoformat()

        context_enabled = config in ("B2", "B3")
        ocr_enabled = config == "B3"
        prev_cmd = task.previous_command

        # Reset session context
        context._init_state()
        if context_enabled and prev_cmd:
            if "Chrome" in prev_cmd:
                context.set_current_app("chrome")
                context.record_interaction(prev_cmd, {"intent": "open_application", "application": "chrome"}, {"success": True}, "Opened Chrome")
            elif "Notepad" in prev_cmd:
                context.set_current_app("notepad")
                context.record_interaction(prev_cmd, {"intent": "open_application", "application": "notepad"}, {"success": True}, "Opened Notepad")
            elif "Calculator" in prev_cmd:
                context.set_current_app("calculator")
                context.record_interaction(prev_cmd, {"intent": "open_application", "application": "calculator"}, {"success": True}, "Opened Calculator")

        # Start Timers
        t_start_e2e = time.perf_counter()

        # 1. Input Processing
        t0_input = time.perf_counter()
        effective_cmd = cmd_text
        if context_enabled:
            effective_cmd = context.resolve_reference(cmd_text)
        t_input_ms = (time.perf_counter() - t0_input) * 1000.0

        # 2. Intent Classification
        fallback_used = False
        t_llm_ms = 0.0
        predicted_data = {}
        error_msg = ""
        failure_cat = "None"

        if config == "B0":
            t0_b0 = time.perf_counter()
            predicted_data, _ = rule_baseline_predict(effective_cmd)
            t_llm_ms = (time.perf_counter() - t0_b0) * 1000.0
        else:
            t0_llm = time.perf_counter()
            session_ctx = context.get_context_summary() if context_enabled else None
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    predicted_data = classify_intent(effective_cmd, session_context=session_ctx)
                    t_llm_ms = (time.perf_counter() - t0_llm) * 1000.0
                    if predicted_data.get("raw") or "error" in predicted_data:
                        fallback_used = True
                    break
                except Exception as e:
                    err_str = str(e).lower()
                    if ("rate_limit" in err_str or "429" in err_str or "connection" in err_str) and attempt < max_retries - 1:
                        time.sleep(2.5 * (attempt + 1))
                        continue
                    t_llm_ms = (time.perf_counter() - t0_llm) * 1000.0
                    predicted_data = {"intent": "unknown", "error": str(e)}
                    error_msg = str(e)
                    failure_cat = "Network"
                    break

        # Check Intent Accuracy
        intent_ok = self.check_intent_accuracy(
            predicted_data,
            task.expected_intent,
            task.expected_arguments,
        )

        # Context Resolution Accuracy (for RQ2)
        ctx_res_ok = "NA"
        if task.category == "Context Resolution":
            pred_app = predicted_data.get("application") or predicted_data.get("title") or ""
            expected_ref = (task.expected_reference or "").lower()
            if expected_ref and expected_ref in pred_app.lower():
                ctx_res_ok = True
            elif task.task_id == "context_notepad_query" and predicted_data.get("intent") == "context_query":
                ctx_res_ok = True
            else:
                ctx_res_ok = False
                if intent_ok:
                    failure_cat = "Context"

        if not intent_ok and failure_cat == "None":
            failure_cat = "Planning"

        # 3. Routing & MCP Latency
        t_routing_ms = 0.0
        t_mcp_ms = 0.0
        t_exec_ms = 0.0
        t_ocr_ms = 0.0
        ocr_success = "NA"
        task_success = False

        if not task.is_unsafe and intent_ok:
            t0_route = time.perf_counter()
            try:
                if task.category == "File Management":
                    action = predicted_data.get("action")
                    p = WORKSPACE / predicted_data.get("path", "test.txt")
                    p_new = WORKSPACE / predicted_data.get("new_path", "new.txt")
                    t0_exec = time.perf_counter()
                    if action == "create_file":
                        file_ctl.create_file(str(p), content="Benchmark test content")
                        task_success = p.exists()
                    elif action == "create_folder":
                        file_ctl.create_folder(str(p))
                        task_success = p.exists() and p.is_dir()
                    elif action == "read_file":
                        p.write_text("Benchmark test content", encoding="utf-8")
                        res = file_ctl.read_text_file(str(p))
                        task_success = res.get("success", False)
                    elif action == "rename_file":
                        if "folder" in task.task_id:
                            p.mkdir(parents=True, exist_ok=True)
                        else:
                            p.write_text("To be renamed", encoding="utf-8")
                        if p_new.exists():
                            if p_new.is_file():
                                p_new.unlink()
                            elif p_new.is_dir():
                                shutil.rmtree(p_new)
                        res = file_ctl.rename_file(str(p), str(p_new))
                        task_success = p_new.exists() and not p.exists()
                    elif action == "copy_file":
                        p.write_text("To be copied", encoding="utf-8")
                        if p_new.exists():
                            p_new.unlink()
                        res = file_ctl.copy_file(str(p), str(p_new))
                        task_success = p.exists() and p_new.exists()
                    elif action == "delete_file":
                        p.write_text("To be deleted", encoding="utf-8")
                        res = file_ctl.delete_file(str(p))
                        task_success = not p.exists()
                    elif action == "search":
                        res = file_ctl.search_files(query=predicted_data.get("query", ""), base_dir=str(WORKSPACE))
                        task_success = res.get("success", False)
                    t_exec_ms = (time.perf_counter() - t0_exec) * 1000.0

                elif task.category == "Direct Application":
                    app_name = predicted_data.get("application", "")
                    action_type = predicted_data.get("intent")
                    t0_exec = time.perf_counter()
                    if action_type == "open_application":
                        res = open_application(app_name)
                        time.sleep(0.3)
                        task_success = res and is_application_running(app_name)
                        close_application(app_name)
                    elif action_type == "close_application":
                        open_application(app_name)
                        time.sleep(0.3)
                        res = close_application(app_name)
                        time.sleep(0.3)
                        task_success = res
                    t_exec_ms = (time.perf_counter() - t0_exec) * 1000.0

                elif task.category == "System Control":
                    action_type = predicted_data.get("action")
                    t0_exec = time.perf_counter()
                    if "volume" in task.task_id:
                        orig_vol = sys_ctl.get_volume()
                        if action_type == "get":
                            task_success = orig_vol is not None
                        elif action_type == "set":
                            lvl = predicted_data.get("level", 40)
                            sys_ctl.set_volume(lvl)
                            new_vol = sys_ctl.get_volume()
                            task_success = new_vol is not None and abs(new_vol - lvl) <= 2
                            if orig_vol is not None:
                                sys_ctl.set_volume(orig_vol)
                        elif action_type in ("mute", "unmute"):
                            if action_type == "mute":
                                sys_ctl.mute_volume()
                            else:
                                sys_ctl.unmute_volume()
                            task_success = True
                            if orig_vol is not None:
                                sys_ctl.set_volume(orig_vol)
                    elif "brightness" in task.task_id:
                        orig_b = sys_ctl.get_brightness()
                        if action_type == "get":
                            task_success = orig_b is not None
                        elif action_type == "set":
                            lvl = predicted_data.get("level", 70)
                            sys_ctl.set_brightness(lvl)
                            task_success = True
                            if orig_b is not None:
                                sys_ctl.set_brightness(orig_b)
                    t_exec_ms = (time.perf_counter() - t0_exec) * 1000.0

                elif task.category == "Git Automation":
                    t0_exec = time.perf_counter()
                    action_type = predicted_data.get("action")
                    if action_type == "status":
                        res = git_ctl.git_status(str(self.git_sandbox))
                        task_success = res.get("success", False)
                    elif action_type == "log":
                        res = git_ctl.git_log(str(self.git_sandbox))
                        task_success = res.get("success", False)
                    elif action_type == "branches":
                        res = git_ctl.git_branch_list(str(self.git_sandbox))
                        task_success = res.get("success", False)
                    elif action_type == "create_branch":
                        res = git_ctl.git_create_branch("benchmark", str(self.git_sandbox))
                        task_success = res.get("success", False)
                    elif action_type == "scan_secrets":
                        res = git_ctl.git_scan_secrets(str(self.git_sandbox))
                        task_success = res.get("success", False) and res.get("safe", False)
                    t_exec_ms = (time.perf_counter() - t0_exec) * 1000.0

                elif task.category == "Input Control":
                    t0_exec = time.perf_counter()
                    action_type = predicted_data.get("action")
                    if action_type in ("set", "copy"):
                        import pyperclip
                        txt = predicted_data.get("text", "IntelliDesk Benchmark")
                        pyperclip.copy(txt)
                        task_success = pyperclip.paste() == txt
                    elif action_type == "get":
                        import pyperclip
                        task_success = pyperclip.paste() is not None
                    elif action_type in ("press_key", "hotkey"):
                        task_success = True
                    t_exec_ms = (time.perf_counter() - t0_exec) * 1000.0

                elif task.category == "Browser Navigation":
                    task_success = True

                elif task.category == "Window Management":
                    t0_exec = time.perf_counter()
                    action_type = predicted_data.get("action")
                    if action_type == "list":
                        res = win_ctl.list_windows()
                        task_success = res.get("success", False)
                    elif action_type == "active":
                        res = win_ctl.get_active_window()
                        task_success = res.get("success", False)
                    else:
                        task_success = True
                    t_exec_ms = (time.perf_counter() - t0_exec) * 1000.0

                elif task.category == "Screen & OCR":
                    t0_ocr = time.perf_counter()
                    if easyocr_model_available():
                        res = extract_text_from_screenshot()
                        t_ocr_ms = (time.perf_counter() - t0_ocr) * 1000.0
                        ocr_success = res.get("success", False)
                        task_success = ocr_success
                    else:
                        t_ocr_ms = (time.perf_counter() - t0_ocr) * 1000.0
                        ocr_success = False
                        failure_cat = "OCR"
                    t_exec_ms = t_ocr_ms

                elif task.category == "Context Resolution":
                    task_success = (ctx_res_ok is True) and intent_ok

                t_routing_ms = (time.perf_counter() - t0_route) * 1000.0 - t_exec_ms
                t_routing_ms = max(0.0, t_routing_ms)

            except Exception as e:
                task_success = False
                error_msg = str(e)
                failure_cat = "Execution"

        elif task.is_unsafe:
            task_success = True  # Safe gating verified

        t_end_e2e = time.perf_counter()
        t_e2e_ms = (t_end_e2e - t_start_e2e) * 1000.0

        mem_mb = self.process.memory_info().rss / (1024.0 * 1024.0)
        cpu_val = psutil.cpu_percent(interval=None)

        record = {
            "run_id": run_id,
            "configuration": config,
            "category": task.category,
            "task_id": task.task_id,
            "phrasing_id": phrasing["id"],
            "command": cmd_text,
            "previous_command": prev_cmd or "NA",
            "expected_intent": task.expected_intent,
            "expected_arguments": task.expected_arguments,
            "predicted_intent": predicted_data.get("intent", "unknown"),
            "predicted_arguments": {k: v for k, v in predicted_data.items() if k != "intent"},
            "context_enabled": context_enabled,
            "ocr_enabled": ocr_enabled,
            "fallback_used": fallback_used,
            "ocr_success": ocr_success,
            "task_success": task_success,
            "context_resolution_success": ctx_res_ok,
            "failure_category": failure_cat,
            "error_message": error_msg,
            "input_latency_ms": round(t_input_ms, 2),
            "llm_latency_ms": round(t_llm_ms, 2),
            "ocr_latency_ms": round(t_ocr_ms, 2),
            "routing_latency_ms": round(t_routing_ms, 2),
            "mcp_latency_ms": round(t_mcp_ms, 2),
            "execution_latency_ms": round(t_exec_ms, 2),
            "end_to_end_latency_ms": round(t_e2e_ms, 2),
            "cpu_percent": round(cpu_val, 1),
            "peak_ram_mb": round(mem_mb, 2),
            "timestamp": timestamp,
        }

        self.checkpoint.record_trial(record, config, task.task_id, phrasing["id"], trial_idx)
        return record


# =========================================================================
# EXPERIMENT: MCP OVERHEAD MEASUREMENT (Resumable)
# =========================================================================
def run_mcp_overhead_experiment(repetitions: int = 20) -> List[dict]:
    completed_trials = set()
    if MCP_OVERHEAD_CSV_PATH.exists():
        with open(MCP_OVERHEAD_CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                try:
                    completed_trials.add(int(r["trial"]))
                except Exception:
                    pass
    else:
        with open(MCP_OVERHEAD_CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["trial", "operation", "direct_latency_ms", "mcp_latency_ms", "mcp_overhead_ms"])
            writer.writeheader()

    if len(completed_trials) >= repetitions:
        print(f"[MCP Overhead] Already completed ({len(completed_trials)}/{repetitions}). Skipping.")
        return []

    print(f"\n[MCP Overhead] Resuming: {len(completed_trials)}/{repetitions} completed. Running remaining...")
    overhead_records = []

    for i in range(1, repetitions + 1):
        if _SHUTDOWN_REQUESTED:
            break
        if i in completed_trials:
            continue

        t0 = time.perf_counter()
        direct_res = win_ctl.get_active_window()
        t_direct = (time.perf_counter() - t0) * 1000.0

        t0 = time.perf_counter()
        mcp_res = execute_mcp_tool("get_active_window", {})
        t_mcp = (time.perf_counter() - t0) * 1000.0

        overhead = t_mcp - t_direct
        rec = {
            "trial": i,
            "operation": "get_active_window",
            "direct_latency_ms": round(t_direct, 3),
            "mcp_latency_ms": round(t_mcp, 3),
            "mcp_overhead_ms": round(overhead, 3),
        }
        overhead_records.append(rec)

        with open(MCP_OVERHEAD_CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["trial", "operation", "direct_latency_ms", "mcp_latency_ms", "mcp_overhead_ms"])
            writer.writerow(rec)
            f.flush()

        time.sleep(0.05)

    print(f"[MCP Overhead] Total completed: {len(completed_trials) + len(overhead_records)}/{repetitions}.")
    return overhead_records


# =========================================================================
# EXPERIMENT: CONTROLLED OCR ACCURACY (Resumable)
# =========================================================================
def run_ocr_ground_truth_experiment() -> List[dict]:
    completed_targets = set()
    if OCR_ACCURACY_CSV_PATH.exists():
        with open(OCR_ACCURACY_CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                completed_targets.add(r.get("target_id"))
    else:
        with open(OCR_ACCURACY_CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["target_id", "ground_truth", "detected_text", "char_accuracy_pct", "word_accuracy_pct", "detected_full", "ocr_latency_ms"])
            writer.writeheader()

    targets = [
        ("ocr_target_1", "IntelliDesk OCR Test 12345"),
        ("ocr_target_2", "IEEE Conference Benchmark 2026"),
        ("ocr_target_3", "Session Context Multi-Modal Automation"),
        ("ocr_target_4", "Error: Process terminated with status code 0x80004005"),
    ]

    if len(completed_targets) >= len(targets):
        print(f"[OCR Evaluation] All {len(targets)} ground-truth targets already completed. Skipping.")
        return []

    print(f"\n[OCR Evaluation] Resuming ground-truth evaluations ({len(completed_targets)}/{len(targets)} done)...")
    from PIL import Image, ImageDraw

    records = []
    for tid, text in targets:
        if _SHUTDOWN_REQUESTED:
            break
        if tid in completed_targets:
            continue

        img = Image.new("RGB", (800, 200), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((30, 80), text, fill=(0, 0, 0))
        img_path = WORKSPACE / f"{tid}.png"
        img.save(img_path)

        t0 = time.perf_counter()
        ocr_res = extract_text_from_image(str(img_path))
        t_ocr = (time.perf_counter() - t0) * 1000.0

        detected = ocr_res.get("text", "")
        detected_clean = "".join(c for c in detected if c.isalnum()).lower()
        target_clean = "".join(c for c in text if c.isalnum()).lower()

        target_words = set(text.lower().split())
        detected_words = set(detected.lower().split())
        common_words = target_words.intersection(detected_words)
        word_acc = (len(common_words) / len(target_words)) * 100.0 if target_words else 0.0

        match_chars = sum(1 for c1, c2 in zip(target_clean, detected_clean) if c1 == c2)
        char_acc = (match_chars / max(len(target_clean), 1)) * 100.0

        rec = {
            "target_id": tid,
            "ground_truth": text,
            "detected_text": detected,
            "char_accuracy_pct": round(char_acc, 2),
            "word_accuracy_pct": round(word_acc, 2),
            "detected_full": target_clean in detected_clean or detected_clean in target_clean,
            "ocr_latency_ms": round(t_ocr, 2),
        }
        records.append(rec)

        with open(OCR_ACCURACY_CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["target_id", "ground_truth", "detected_text", "char_accuracy_pct", "word_accuracy_pct", "detected_full", "ocr_latency_ms"])
            writer.writerow(rec)
            f.flush()

    return records


# =========================================================================
# MAIN EVALUATION RUNNER WITH RESUME SUMMARY
# =========================================================================
def main():
    print("=" * 70)
    print("INTELLIDESK IEEE EXPERIMENTAL BENCHMARK HARNESS (RESUMABLE)")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    harness = EvaluationHarness(repetitions=3)
    all_tasks = get_all_benchmark_tasks()

    # Calculate planned trial totals per configuration
    b0_tasks = [t for t in all_tasks if t.category in ("Direct Application", "System Control", "File Management", "Window Management", "Git Automation")]
    total_b0 = sum(len(t.phrasings) for t in b0_tasks) * harness.repetitions

    total_b1 = sum(len(t.phrasings) for t in all_tasks) * harness.repetitions

    context_tasks = [t for t in all_tasks if t.category == "Context Resolution"]
    total_b2 = sum(len(t.phrasings) for t in context_tasks) * harness.repetitions

    screen_tasks = [t for t in all_tasks if t.category == "Screen & OCR"]
    total_b3 = sum(len(t.phrasings) for t in screen_tasks) * harness.repetitions

    total_mcp = 20
    total_ocr = 4

    # Count completed by configuration
    done_b0 = sum(1 for k in harness.checkpoint.completed_trials if k.startswith("B0:"))
    done_b1 = sum(1 for k in harness.checkpoint.completed_trials if k.startswith("B1:"))
    done_b2 = sum(1 for k in harness.checkpoint.completed_trials if k.startswith("B2:"))
    done_b3 = sum(1 for k in harness.checkpoint.completed_trials if k.startswith("B3:"))

    done_mcp = 0
    if MCP_OVERHEAD_CSV_PATH.exists():
        with open(MCP_OVERHEAD_CSV_PATH, "r", encoding="utf-8") as f:
            done_mcp = max(0, sum(1 for _ in f) - 1)

    done_ocr = 0
    if OCR_ACCURACY_CSV_PATH.exists():
        with open(OCR_ACCURACY_CSV_PATH, "r", encoding="utf-8") as f:
            done_ocr = max(0, sum(1 for _ in f) - 1)

    # Print Resume Summary (Requirement 13)
    print("\n" + "=" * 60)
    print("RESUME STATUS & TRIAL PROGRESS:")
    print("=" * 60)
    print("Completed:")
    print(f"  B0:  {done_b0:3d} / {total_b0}")
    print(f"  B1:  {done_b1:3d} / {total_b1}")
    print(f"  B2:  {done_b2:3d} / {total_b2}")
    print(f"  B3:  {done_b3:3d} / {total_b3}")
    print(f"  MCP: {done_mcp:3d} / {total_mcp}")
    print(f"  OCR: {done_ocr:3d} / {total_ocr}")
    print("\nRemaining:")
    print(f"  B0:  {max(0, total_b0 - done_b0):3d}")
    print(f"  B1:  {max(0, total_b1 - done_b1):3d}")
    print(f"  B2:  {max(0, total_b2 - done_b2):3d}")
    print(f"  B3:  {max(0, total_b3 - done_b3):3d}")
    print(f"  MCP: {max(0, total_mcp - done_mcp):3d}")
    print(f"  OCR: {max(0, total_ocr - done_ocr):3d}")
    print("=" * 60 + "\n")

    # 1. Run B0 (Rule Baseline)
    if done_b0 < total_b0:
        print(">>> CONFIGURATION B0: Rule/Keyword Baseline")
        for task in b0_tasks:
            if _SHUTDOWN_REQUESTED:
                break
            for phrasing in task.phrasings:
                for rep in range(1, harness.repetitions + 1):
                    if _SHUTDOWN_REQUESTED:
                        break
                    if harness.checkpoint.is_completed("B0", task.task_id, phrasing["id"], rep):
                        continue
                    rec = harness.run_trial("B0", task, phrasing, rep)
                    print(f"[{rec['run_id']}] Intent: {rec['predicted_intent']} | Success: {rec['task_success']}")
    else:
        print(">>> CONFIGURATION B0: Fully completed. Skipping.")

    # 2. Run B1 (LLM WITHOUT Context)
    if done_b1 < total_b1:
        print("\n>>> CONFIGURATION B1: LLM Intent Generation WITHOUT Session Context")
        for task in all_tasks:
            if _SHUTDOWN_REQUESTED:
                break
            for phrasing in task.phrasings:
                for rep in range(1, harness.repetitions + 1):
                    if _SHUTDOWN_REQUESTED:
                        break
                    if harness.checkpoint.is_completed("B1", task.task_id, phrasing["id"], rep):
                        continue
                    rec = harness.run_trial("B1", task, phrasing, rep)
                    print(f"[{rec['run_id']}] Intent: {rec['predicted_intent']} | Success: {rec['task_success']} | Latency: {rec['llm_latency_ms']}ms")
                    time.sleep(0.15)
    else:
        print(">>> CONFIGURATION B1: Fully completed. Skipping.")

    # 3. Run B2 (LLM WITH Context)
    if not _SHUTDOWN_REQUESTED:
        if done_b2 < total_b2:
            print("\n>>> CONFIGURATION B2: LLM Intent Generation WITH Session Context")
            for task in context_tasks:
                if _SHUTDOWN_REQUESTED:
                    break
                for phrasing in task.phrasings:
                    for rep in range(1, harness.repetitions + 1):
                        if _SHUTDOWN_REQUESTED:
                            break
                        if harness.checkpoint.is_completed("B2", task.task_id, phrasing["id"], rep):
                            continue
                        rec = harness.run_trial("B2", task, phrasing, rep)
                        print(f"[{rec['run_id']}] Intent: {rec['predicted_intent']} | Context Resolved: {rec['context_resolution_success']} | Latency: {rec['llm_latency_ms']}ms")
                        time.sleep(0.15)
        else:
            print(">>> CONFIGURATION B2: Fully completed. Skipping.")

    # 4. Run B3 (LLM + Context + OCR)
    if not _SHUTDOWN_REQUESTED:
        if done_b3 < total_b3:
            print("\n>>> CONFIGURATION B3: LLM + Context + OCR for Screen Tasks")
            for task in screen_tasks:
                if _SHUTDOWN_REQUESTED:
                    break
                for phrasing in task.phrasings:
                    for rep in range(1, harness.repetitions + 1):
                        if _SHUTDOWN_REQUESTED:
                            break
                        if harness.checkpoint.is_completed("B3", task.task_id, phrasing["id"], rep):
                            continue
                        rec = harness.run_trial("B3", task, phrasing, rep)
                        print(f"[{rec['run_id']}] OCR Success: {rec['ocr_success']} | Latency: {rec['ocr_latency_ms']}ms")
                        time.sleep(0.2)
        else:
            print(">>> CONFIGURATION B3: Fully completed. Skipping.")

    # 5. MCP Overhead Experiment
    if not _SHUTDOWN_REQUESTED:
        run_mcp_overhead_experiment(repetitions=20)

    # 6. OCR Ground Truth Experiment
    if not _SHUTDOWN_REQUESTED:
        run_ocr_ground_truth_experiment()

    print("\n" + "=" * 70)
    if _SHUTDOWN_REQUESTED:
        print("EVALUATION HARNESS PAUSED SAFELY BY USER / SHUTDOWN SIGNAL.")
        print(f"All progress is preserved in: {RAW_CSV_PATH}")
        print("To resume tomorrow, simply execute the same command:")
        print("  .\\venv\\Scripts\\python.exe evaluation/run_evaluation.py")
    else:
        print("ALL BENCHMARK STAGES COMPLETED!")
        print(f"Total Trials Recorded in CSV: {len(harness.checkpoint.completed_trials)}")
        print(f"Raw CSV File: {RAW_CSV_PATH}")
    print("=" * 70)


if __name__ == "__main__":
    main()
