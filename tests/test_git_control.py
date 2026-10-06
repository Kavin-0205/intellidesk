"""
IntelliDesk Git/GitHub Control Test Suite (Phase 6).
Tests:
  1. git_status on valid repo
  2. git_status on non-repo path
  3. git_log last N commits
  4. git_branch_list
  5. Secret scanner - detects .env filename
  6. Secret scanner - detects API key pattern in content
  7. Secret scanner - passes clean file
  8. Commit blocked by secret scan
  9. Intent classification: 'Show git status'
  10. Intent classification: 'Push my project to GitHub'
  11. Intent classification: 'Create a branch called feature'
  12. Intent classification: 'Show my recent commits'
  13. E2E handle_intent: git_action status
  14. E2E handle_intent: git_action scan_secrets
"""

import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from automation import git_control as git_ctl
from llm.ai_router import classify_intent
from intent_router import handle_intent


# ============================================================
# HELPERS
# ============================================================

def _make_temp_repo():
    """Create a temp directory with an initialized git repo for testing."""
    import git
    tmp = tempfile.mkdtemp(prefix="intellidesk_git_test_")
    repo = git.Repo.init(tmp)
    repo.config_writer().set_value("user", "name", "IntelliDesk Test").release()
    repo.config_writer().set_value("user", "email", "test@intellidesk.local").release()
    return tmp, repo


def _cleanup(tmp_path: str):
    import shutil
    try:
        shutil.rmtree(tmp_path, ignore_errors=True)
    except Exception:
        pass


# ============================================================
# TESTS
# ============================================================

def test_git_status_valid_repo():
    """git_status on the IntelliDesk repo itself should succeed."""
    print("\n[TEST 1] git_status: valid repo (IntelliDesk project)")
    result = git_ctl.git_status(str(PROJECT_ROOT))
    print(f"  Result: branch={result.get('branch')}, modified={result.get('modified_count')}, "
          f"untracked={result.get('untracked_count')}")
    assert result.get("success") is True, f"Expected success: {result}"
    assert "branch" in result
    assert isinstance(result.get("modified_count"), int)
    print("  [PASS]")


def test_git_status_invalid_path():
    """git_status on a non-git directory should fail gracefully."""
    print("\n[TEST 2] git_status: non-git directory")
    result = git_ctl.git_status(tempfile.gettempdir())
    print(f"  Result: {result}")
    assert result.get("success") is False, "Should fail for non-git dir"
    assert "error" in result
    print("  [PASS]")


def test_git_log():
    """git_log should return list of commits."""
    print("\n[TEST 3] git_log: recent commits on IntelliDesk repo")
    result = git_ctl.git_log(str(PROJECT_ROOT), limit=3)
    print(f"  Commits returned: {result.get('count', 0)}")
    assert result.get("success") is True, f"Expected success: {result}"
    commits = result.get("commits", [])
    if commits:
        assert "hash" in commits[0]
        assert "message" in commits[0]
        print(f"  Latest commit: {commits[0]['hash']} - {commits[0]['message'][:50]}")
    print("  [PASS]")


def test_git_branch_list():
    """git_branch_list should return branches and current branch."""
    print("\n[TEST 4] git_branch_list: list branches")
    result = git_ctl.git_branch_list(str(PROJECT_ROOT))
    print(f"  Branches: {result.get('branches')}, current: {result.get('current_branch')}")
    assert result.get("success") is True, f"Expected success: {result}"
    assert isinstance(result.get("branches"), list)
    print("  [PASS]")


def test_secret_scan_detects_env_filename():
    """Secret scanner must block .env file."""
    print("\n[TEST 5] git_scan_secrets: detect .env filename")
    tmp, repo = _make_temp_repo()
    try:
        env_file = Path(tmp) / ".env"
        env_file.write_text("GROQ_API_KEY=gsk_test123456\nSECRET=supersecret\n", encoding="utf-8")

        result = git_ctl.git_scan_secrets(tmp)
        print(f"  Safe: {result.get('safe')}, violations: {result.get('violations')}")
        assert result.get("success") is True
        assert result.get("safe") is False, "Should detect .env as sensitive"
        assert any(".env" in f for f in result.get("blocked_files", []))
        print("  [PASS]")
    finally:
        _cleanup(tmp)


def test_secret_scan_detects_api_key_in_content():
    """Secret scanner must detect API key patterns inside file content."""
    print("\n[TEST 6] git_scan_secrets: detect API key pattern in file content")
    tmp, repo = _make_temp_repo()
    try:
        config_file = Path(tmp) / "config.py"
        config_file.write_text("GROQ_API_KEY = 'gsk_reallyLongSecretTokenThatShouldBeBlocked12345'\n", encoding="utf-8")

        result = git_ctl.git_scan_secrets(tmp)
        print(f"  Safe: {result.get('safe')}, violations: {result.get('violations')}")
        assert result.get("success") is True
        assert result.get("safe") is False, "Should detect API key in content"
        print("  [PASS]")
    finally:
        _cleanup(tmp)


def test_secret_scan_passes_clean_file():
    """Secret scanner should pass a clean Python file."""
    print("\n[TEST 7] git_scan_secrets: clean file passes scan")
    tmp, repo = _make_temp_repo()
    try:
        clean_file = Path(tmp) / "main.py"
        clean_file.write_text("print('Hello, IntelliDesk!')\n", encoding="utf-8")

        result = git_ctl.git_scan_secrets(tmp)
        print(f"  Safe: {result.get('safe')}, files_scanned: {result.get('files_scanned')}")
        assert result.get("success") is True
        assert result.get("safe") is True, f"Clean file should pass scan: {result.get('violations')}"
        print("  [PASS]")
    finally:
        _cleanup(tmp)


def test_commit_blocked_by_secret_scan():
    """git_add_and_commit must refuse if .env is present."""
    print("\n[TEST 8] git_add_and_commit: blocked by secret scan")
    tmp, repo = _make_temp_repo()
    try:
        # Create .env with a secret
        env_file = Path(tmp) / ".env"
        env_file.write_text("GROQ_API_KEY=gsk_supersecret123456789\n", encoding="utf-8")

        result = git_ctl.git_add_and_commit("test commit", repo_path=tmp)
        print(f"  Result: success={result.get('success')}, error={result.get('error', '')[:80]}")
        assert result.get("success") is False, "Should refuse commit with .env present"
        assert "violations" in result or "secret" in result.get("error", "").lower()
        print("  [PASS]")
    finally:
        _cleanup(tmp)


def test_intent_classify_git_status():
    """'Show git status' should classify as git_action / status."""
    print("\n[TEST 9] classify_intent: 'Show git status'")
    result = classify_intent("Show git status")
    print(f"  Result: {result}")
    assert result.get("intent") == "git_action", f"Expected git_action, got {result.get('intent')}"
    assert result.get("action") == "status", f"Expected status, got {result.get('action')}"
    print("  [PASS]")


def test_intent_classify_git_push():
    """'Push my project to GitHub' should classify as git_action / commit_and_push."""
    print("\n[TEST 10] classify_intent: 'Push my project to GitHub'")
    result = classify_intent("Push my project to GitHub")
    print(f"  Result: {result}")
    assert result.get("intent") == "git_action", f"Expected git_action, got {result.get('intent')}"
    assert result.get("action") in ("push", "commit_and_push"), f"Expected push/commit_and_push, got {result.get('action')}"
    print("  [PASS]")


def test_intent_classify_create_branch():
    """'Create a branch called feature' should classify as git_action / create_branch with branch='feature'."""
    print("\n[TEST 11] classify_intent: 'Create a branch called feature'")
    result = classify_intent("Create a branch called feature")
    print(f"  Result: {result}")
    assert result.get("intent") == "git_action", f"Expected git_action, got {result.get('intent')}"
    assert result.get("action") == "create_branch"
    assert "feature" in (result.get("branch") or "").lower()
    print("  [PASS]")


def test_intent_classify_git_log():
    """'Show my recent commits' should classify as git_action / log."""
    print("\n[TEST 12] classify_intent: 'Show my recent commits'")
    result = classify_intent("Show my recent commits")
    print(f"  Result: {result}")
    assert result.get("intent") == "git_action", f"Expected git_action, got {result.get('intent')}"
    assert result.get("action") == "log"
    print("  [PASS]")


def test_e2e_handle_intent_git_status():
    """E2E: handle_intent for git status should return spoken summary."""
    print("\n[TEST 13] handle_intent: git_action status")
    intent_data = {
        "intent": "git_action",
        "action": "status",
        "repo_path": str(PROJECT_ROOT),
    }
    result = handle_intent(intent_data, user_command="Show git status", speak_response=False)
    print(f"  Response: {result.get('response', '')[:120]}")
    assert result.get("success") is True
    response = result.get("response", "")
    assert "branch" in response.lower()
    print("  [PASS]")


def test_e2e_handle_intent_git_scan_secrets():
    """E2E: handle_intent for git scan_secrets should describe result."""
    print("\n[TEST 14] handle_intent: git_action scan_secrets")
    intent_data = {
        "intent": "git_action",
        "action": "scan_secrets",
        "repo_path": str(PROJECT_ROOT),
    }
    result = handle_intent(intent_data, user_command="Scan for secrets", speak_response=False)
    print(f"  Response: {result.get('response', '')[:120]}")
    # Should always return a result (success even if secrets found, because scan itself ran)
    assert result.get("response"), "Should have a spoken response"
    print("  [PASS]")


if __name__ == "__main__":
    print("=" * 65)
    print("IntelliDesk Git/GitHub Control Test Suite (Phase 6)")
    print("=" * 65)

    tests = [
        test_git_status_valid_repo,
        test_git_status_invalid_path,
        test_git_log,
        test_git_branch_list,
        test_secret_scan_detects_env_filename,
        test_secret_scan_detects_api_key_in_content,
        test_secret_scan_passes_clean_file,
        test_commit_blocked_by_secret_scan,
        test_intent_classify_git_status,
        test_intent_classify_git_push,
        test_intent_classify_create_branch,
        test_intent_classify_git_log,
        test_e2e_handle_intent_git_status,
        test_e2e_handle_intent_git_scan_secrets,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {t.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print("\n" + "=" * 65)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    if failed == 0:
        print("[SUCCESS] All Git/GitHub tests passed!")
    else:
        print("[PARTIAL] Some tests failed. Review output above.")
    print("=" * 65)
