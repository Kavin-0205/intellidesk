"""
IntelliDesk Git/GitHub Control Module.

Provides safe, voice-driven Git automation for Windows:
- Repository detection
- Git status, diff, log
- Stage, commit, push, pull
- Branch management
- Secret/sensitive file scanning before any commit or push
- Confirmation safeguards for destructive operations

SECURITY RULES (enforced at this layer):
- Never commit .env, API keys, tokens, passwords, credentials
- Never force-push
- Always scan staged files for secrets before commit
- Never execute arbitrary shell strings from LLM output
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# SENSITIVE FILE / SECRET PATTERNS
# ============================================================

SENSITIVE_FILENAMES = {
    ".env", ".env.local", ".env.production", ".env.development",
    ".env.test", ".env.staging", "secrets.json", "credentials.json",
    "private_key.pem", "private_key.key", ".pem", ".key", ".pfx",
    "id_rsa", "id_ed25519", ".ssh", "htpasswd", ".netrc",
}

SENSITIVE_PATTERNS = [
    # API keys
    r"(?i)(api[_\-]?key|apikey)\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{20,}",
    r"(?i)(secret[_\-]?key|secret)\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{20,}",
    # Tokens
    r"(?i)(access[_\-]?token|auth[_\-]?token|bearer)\s*[=:]\s*['\"]?[A-Za-z0-9_\-\.]{20,}",
    r"(?i)ghp_[A-Za-z0-9]{36,}",          # GitHub Personal Access Token
    r"(?i)ghs_[A-Za-z0-9]{36,}",          # GitHub Actions token
    r"(?i)(sk|pk)-[A-Za-z0-9]{32,}",      # Stripe / OpenAI style
    # Passwords
    r"(?i)password\s*[=:]\s*['\"]?[^\s'\"]{6,}",
    # MongoDB URIs
    r"mongodb(\+srv)?://[^@\s\r\n]+:[^@\s\r\n]+@",
    # Groq / OpenAI style
    r"(?i)gsk_[A-Za-z0-9]{40,}",
    r"(?i)sk-[A-Za-z0-9]{40,}",
]

SENSITIVE_COMPILED = [re.compile(p) for p in SENSITIVE_PATTERNS]


# ============================================================
# HELPERS
# ============================================================

def _import_git():
    """Lazy import of gitpython with helpful error."""
    try:
        import git
        return git
    except ImportError:
        raise RuntimeError(
            "gitpython is not installed. Run: pip install gitpython"
        )


def _find_repo(path: Optional[str] = None) -> Any:
    """Find the Git repository at the given path or from cwd."""
    git = _import_git()
    search_path = Path(path).resolve() if path else Path.cwd()
    try:
        repo = git.Repo(search_path, search_parent_directories=True)
        return repo
    except git.InvalidGitRepositoryError:
        raise RuntimeError(f"No Git repository found at or above: {search_path}")


def _is_sensitive_filename(filepath: str) -> bool:
    """Check if a file path matches known sensitive file patterns."""
    name = Path(filepath).name.lower()
    # Explicitly allowed example or sample templates
    if name.endswith(".example") or name.endswith(".sample"):
        return False
    # Exact match
    if name in SENSITIVE_FILENAMES:
        return True
    # Extension match
    for sensitive in SENSITIVE_FILENAMES:
        if name.endswith(sensitive) and sensitive.startswith("."):
            return True
    return False


def _scan_file_content(filepath: str) -> List[str]:
    """Scan a text file for secret patterns. Returns list of findings."""
    p = Path(filepath)
    # Don't flag documentation files, examples, or test suites containing mock strings
    if p.name.endswith((".md", ".example", ".sample")) or "tests" in p.parts:
        return []

    findings = []
    try:
        content = p.read_text(encoding="utf-8", errors="ignore")
        for pattern in SENSITIVE_COMPILED:
            match = pattern.search(content)
            if match:
                findings.append(f"Pattern match in '{p.name}': {match.group()[:40]}...")
    except Exception:
        pass
    return findings


def _get_safe_summary(repo: Any, max_files: int = 10) -> dict:
    """Generate a human-readable summary of repo state (no secret values)."""
    git = _import_git()
    try:
        branch = repo.active_branch.name
    except Exception:
        branch = "detached HEAD"

    modified = [item.a_path for item in repo.index.diff(None)]
    staged = [item.a_path for item in repo.index.diff("HEAD")]
    untracked = repo.untracked_files[:max_files]

    return {
        "branch": branch,
        "modified_files": modified[:max_files],
        "staged_files": staged[:max_files],
        "untracked_files": untracked,
        "modified_count": len(modified),
        "staged_count": len(staged),
        "untracked_count": len(untracked),
    }


# ============================================================
# PUBLIC API
# ============================================================

def git_status(repo_path: Optional[str] = None) -> dict:
    """
    Return the Git status of the repository.
    Shows modified, staged, and untracked files.
    """
    try:
        repo = _find_repo(repo_path)
        summary = _get_safe_summary(repo)
        return {
            "success": True,
            "action": "git_status",
            "repo_path": str(repo.working_tree_dir),
            **summary,
        }
    except Exception as e:
        return {"success": False, "action": "git_status", "error": str(e)}


def git_log(repo_path: Optional[str] = None, limit: int = 5) -> dict:
    """Return recent commit log (last N commits)."""
    try:
        repo = _find_repo(repo_path)
        commits = []
        for commit in list(repo.iter_commits(max_count=limit)):
            commits.append({
                "hash": commit.hexsha[:8],
                "message": commit.message.strip().split("\n")[0],
                "author": commit.author.name,
                "date": datetime.fromtimestamp(commit.committed_date).strftime("%Y-%m-%d %H:%M"),
            })
        return {
            "success": True,
            "action": "git_log",
            "commits": commits,
            "count": len(commits),
        }
    except Exception as e:
        return {"success": False, "action": "git_log", "error": str(e)}


def git_branch_list(repo_path: Optional[str] = None) -> dict:
    """List all branches in the repository."""
    try:
        repo = _find_repo(repo_path)
        branches = [b.name for b in repo.branches]
        try:
            current = repo.active_branch.name
        except Exception:
            current = None
        return {
            "success": True,
            "action": "git_branch_list",
            "branches": branches,
            "current_branch": current,
        }
    except Exception as e:
        return {"success": False, "action": "git_branch_list", "error": str(e)}


def git_checkout(branch_name: str, repo_path: Optional[str] = None) -> dict:
    """Switch to an existing branch."""
    try:
        repo = _find_repo(repo_path)
        repo.git.checkout(branch_name)
        return {
            "success": True,
            "action": "git_checkout",
            "branch": branch_name,
        }
    except Exception as e:
        return {"success": False, "action": "git_checkout", "branch": branch_name, "error": str(e)}


def git_create_branch(branch_name: str, repo_path: Optional[str] = None) -> dict:
    """Create and switch to a new branch, or checkout if it already exists."""
    try:
        repo = _find_repo(repo_path)
        existing_branches = [b.name for b in repo.branches]
        if branch_name in existing_branches:
            repo.git.checkout(branch_name)
        else:
            repo.git.checkout("-b", branch_name)
        return {
            "success": True,
            "action": "git_create_branch",
            "branch": branch_name,
        }
    except Exception as e:
        return {"success": False, "action": "git_create_branch", "branch": branch_name, "error": str(e)}


def git_pull(repo_path: Optional[str] = None) -> dict:
    """Pull latest changes from the remote."""
    try:
        repo = _find_repo(repo_path)
        origin = repo.remotes.origin
        result = origin.pull()
        return {
            "success": True,
            "action": "git_pull",
            "repo_path": str(repo.working_tree_dir),
            "result": str(result),
        }
    except Exception as e:
        return {"success": False, "action": "git_pull", "error": str(e)}


def git_scan_secrets(repo_path: Optional[str] = None) -> dict:
    """
    Scan all modified and staged files for secrets/sensitive content.
    MUST be called before any commit or push.
    """
    try:
        repo = _find_repo(repo_path)
        repo_root = Path(repo.working_tree_dir)

        violations: List[str] = []

        # In fresh repos (no commits), HEAD doesn't exist — handle gracefully
        has_commits = True
        try:
            repo.head.commit
        except Exception:
            has_commits = False

        staged_paths: List[str] = []
        modified_paths: List[str] = []

        if has_commits:
            try:
                staged_paths = [item.a_path for item in repo.index.diff("HEAD")]
                modified_paths = [item.a_path for item in repo.index.diff(None)]
            except Exception:
                pass

        untracked_paths: List[str] = repo.untracked_files

        all_paths = list(set(staged_paths + modified_paths + untracked_paths))

        blocked_files = []
        for rel_path in all_paths:
            abs_path = repo_root / rel_path

            # Filename check
            if _is_sensitive_filename(rel_path):
                blocked_files.append(rel_path)
                violations.append(f"Sensitive filename: {rel_path}")
                continue

            # Content scan for text files
            if abs_path.exists() and abs_path.is_file():
                findings = _scan_file_content(str(abs_path))
                if findings:
                    blocked_files.append(rel_path)
                    violations.extend(findings)

        is_safe = len(violations) == 0

        return {
            "success": True,
            "action": "git_scan_secrets",
            "safe": is_safe,
            "violations": violations[:10],  # cap output
            "blocked_files": blocked_files[:10],
            "files_scanned": len(all_paths),
        }
    except Exception as e:
        return {"success": False, "action": "git_scan_secrets", "error": str(e)}


def git_add_and_commit(message: str = "", repo_path: Optional[str] = None) -> dict:
    """
    Stage all safe files and create a commit.
    Refuses to commit if secrets are detected.
    """
    try:
        repo = _find_repo(repo_path)

        # Security scan FIRST
        scan = git_scan_secrets(repo_path)
        if not scan.get("safe", False):
            return {
                "success": False,
                "action": "git_commit",
                "error": "Secret scan failed. Will not commit.",
                "violations": scan.get("violations", []),
                "blocked_files": scan.get("blocked_files", []),
            }

        # Stage all files (excluding .env via .gitignore)
        repo.git.add("--all")

        # Check if there's anything staged after add
        if not repo.index.diff("HEAD") and not repo.untracked_files:
            return {
                "success": False,
                "action": "git_commit",
                "error": "Nothing to commit. Working tree is clean.",
            }

        # Generate commit message if not provided
        if not message or not message.strip():
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            changed = [item.a_path for item in repo.index.diff("HEAD")]
            files_preview = ", ".join(changed[:3])
            if len(changed) > 3:
                files_preview += f" and {len(changed) - 3} more"
            message = f"IntelliDesk auto-commit: {files_preview} [{timestamp}]"

        commit = repo.index.commit(message)

        return {
            "success": True,
            "action": "git_commit",
            "commit_hash": commit.hexsha[:8],
            "commit_message": message,
            "repo_path": str(repo.working_tree_dir),
        }
    except Exception as e:
        return {"success": False, "action": "git_commit", "error": str(e)}


def git_push(repo_path: Optional[str] = None, branch: Optional[str] = None) -> dict:
    """
    Push committed changes to the remote.
    Never force-pushes. Scans for secrets before pushing.
    """
    try:
        repo = _find_repo(repo_path)

        # Verify remote exists
        if not repo.remotes:
            return {
                "success": False,
                "action": "git_push",
                "error": "No remote repository configured. Use 'git remote add origin <url>' first.",
            }

        # Security scan before push
        scan = git_scan_secrets(repo_path)
        if not scan.get("safe", False):
            return {
                "success": False,
                "action": "git_push",
                "error": "Secret scan failed. Will not push.",
                "violations": scan.get("violations", []),
            }

        origin = repo.remotes.origin
        target_branch = branch or repo.active_branch.name
        result = origin.push(target_branch)

        # Check push result flags
        push_info = result[0] if result else None
        if push_info and push_info.flags & push_info.ERROR:
            return {
                "success": False,
                "action": "git_push",
                "error": f"Push failed: {push_info.summary}",
            }

        return {
            "success": True,
            "action": "git_push",
            "branch": target_branch,
            "repo_path": str(repo.working_tree_dir),
            "remote": origin.url,
        }
    except Exception as e:
        return {"success": False, "action": "git_push", "error": str(e)}


def git_commit_and_push(message: str = "", repo_path: Optional[str] = None) -> dict:
    """
    Combined: scan secrets → stage → commit → push.
    This is the primary voice command handler for 'push my project'.
    """
    # Step 1: Status check
    status = git_status(repo_path)
    if not status.get("success"):
        return {"success": False, "action": "git_commit_and_push", "error": status.get("error")}

    modified_count = status.get("modified_count", 0) + status.get("untracked_count", 0)
    if modified_count == 0:
        return {
            "success": True,
            "action": "git_commit_and_push",
            "message": "Nothing to commit. Your project is already up to date.",
            "already_clean": True,
        }

    # Step 2: Commit
    commit_result = git_add_and_commit(message=message, repo_path=repo_path)
    if not commit_result.get("success"):
        return commit_result

    # Step 3: Push
    push_result = git_push(repo_path=repo_path)
    if not push_result.get("success"):
        return {
            "success": False,
            "action": "git_commit_and_push",
            "commit": commit_result,
            "push_error": push_result.get("error"),
        }

    return {
        "success": True,
        "action": "git_commit_and_push",
        "commit_hash": commit_result.get("commit_hash"),
        "commit_message": commit_result.get("commit_message"),
        "branch": push_result.get("branch"),
        "remote": push_result.get("remote"),
        "files_changed": modified_count,
    }


def git_init(repo_path: Optional[str] = None) -> dict:
    """Initialize a new Git repository."""
    try:
        git = _import_git()
        target = Path(repo_path).resolve() if repo_path else Path.cwd()
        repo = git.Repo.init(target)
        return {
            "success": True,
            "action": "git_init",
            "repo_path": str(repo.working_tree_dir),
        }
    except Exception as e:
        return {"success": False, "action": "git_init", "error": str(e)}
