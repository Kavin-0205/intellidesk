"""
IntelliDesk File and Folder Management Module.

Provides safe, intelligent file and directory operations on Windows:
- Quick folder navigation (Downloads, Desktop, Documents, etc.)
- Fast recursive file search with pattern matching and date filters
- Safe file creation, reading, renaming, copying, moving, and deletion
"""

import os
import shutil
import subprocess
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Common Windows User Directory Shortcuts
USER_SHORTCUTS = {
    "downloads": os.path.join(os.environ.get("USERPROFILE", ""), "Downloads"),
    "desktop": os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
    "documents": os.path.join(os.environ.get("USERPROFILE", ""), "Documents"),
    "pictures": os.path.join(os.environ.get("USERPROFILE", ""), "Pictures"),
    "music": os.path.join(os.environ.get("USERPROFILE", ""), "Music"),
    "videos": os.path.join(os.environ.get("USERPROFILE", ""), "Videos"),
    "home": os.environ.get("USERPROFILE", ""),
    "project": str(PROJECT_ROOT),
    "workspace": str(PROJECT_ROOT),
    "intellidesk": str(PROJECT_ROOT),
}

# Directories to skip during search for speed and safety
SKIP_DIRECTORIES = {
    ".git", ".venv", "venv", "node_modules", "__pycache__",
    "AppData", "Windows", "Program Files", "Program Files (x86)",
    "$Recycle.Bin", "System Volume Information", ".cache", ".idea", ".vscode"
}


def resolve_folder_path(folder_name: str) -> Optional[str]:
    """Resolve user-friendly name or relative path to an absolute directory path."""
    if not folder_name:
        return None

    clean = folder_name.strip().lower()

    if clean in USER_SHORTCUTS:
        return USER_SHORTCUTS[clean]

    # Try relative to project root or user profile
    path_obj = Path(folder_name)
    if path_obj.is_absolute() and path_obj.is_dir():
        return str(path_obj)

    project_rel = PROJECT_ROOT / folder_name
    if project_rel.is_dir():
        return str(project_rel)

    user_rel = Path(os.environ.get("USERPROFILE", "")) / folder_name
    if user_rel.is_dir():
        return str(user_rel)

    return None


def open_folder(folder_name: str) -> dict:
    """Open a folder in Windows File Explorer."""
    path = resolve_folder_path(folder_name)
    if not path or not os.path.exists(path):
        return {
            "success": False,
            "action": "open_folder",
            "folder": folder_name,
            "error": f"Folder '{folder_name}' was not found."
        }

    try:
        os.startfile(path)
        return {
            "success": True,
            "action": "open_folder",
            "folder": folder_name,
            "path": path
        }
    except Exception as e:
        return {
            "success": False,
            "action": "open_folder",
            "folder": folder_name,
            "path": path,
            "error": str(e)
        }


def search_files(
    query: str,
    file_ext: Optional[str] = None,
    modified_today: bool = False,
    base_dir: Optional[str] = None,
    max_results: int = 15
) -> dict:
    """
    Intelligently search files by name, extension, or modification date across user directories.
    """
    search_roots = []
    if base_dir:
        resolved = resolve_folder_path(base_dir)
        if resolved:
            search_roots.append(resolved)
        elif os.path.exists(base_dir):
            search_roots.append(base_dir)

    if not search_roots:
        search_roots = [
            str(PROJECT_ROOT),
            USER_SHORTCUTS.get("desktop", ""),
            USER_SHORTCUTS.get("documents", ""),
            USER_SHORTCUTS.get("downloads", ""),
        ]

    search_roots = [r for r in search_roots if r and os.path.exists(r)]

    query_lower = query.lower().strip() if query else ""
    ext_lower = file_ext.lower().strip() if file_ext else ""
    if ext_lower and not ext_lower.startswith("."):
        ext_lower = f".{ext_lower}"

    today_date = date.today()
    results = []

    for root_dir in search_roots:
        if len(results) >= max_results:
            break

        for current_root, dirs, files in os.walk(root_dir):
            # Skip heavy system/cache directories
            dirs[:] = [d for d in dirs if d not in SKIP_DIRECTORIES and not d.startswith(".")]

            for f in files:
                f_lower = f.lower()
                f_path = os.path.join(current_root, f)

                # Match extension if specified
                if ext_lower and not f_lower.endswith(ext_lower):
                    continue

                # Match name query if specified
                if query_lower and query_lower not in f_lower:
                    continue

                # Match modified today if requested
                if modified_today:
                    try:
                        mtime = datetime.fromtimestamp(os.path.getmtime(f_path)).date()
                        if mtime != today_date:
                            continue
                    except Exception:
                        continue

                results.append({
                    "name": f,
                    "path": f_path,
                    "directory": current_root,
                    "size_bytes": os.path.getsize(f_path) if os.path.exists(f_path) else 0
                })

                if len(results) >= max_results:
                    break

    return {
        "success": True,
        "action": "search_files",
        "query": query,
        "file_ext": file_ext,
        "count": len(results),
        "files": results
    }


def create_file(file_path: str, content: str = "") -> dict:
    """Create a new file with optional content."""
    try:
        p = Path(file_path)
        if not p.is_absolute():
            p = PROJECT_ROOT / file_path

        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "success": True,
            "action": "create_file",
            "path": str(p),
            "name": p.name
        }
    except Exception as e:
        return {
            "success": False,
            "action": "create_file",
            "path": file_path,
            "error": str(e)
        }


def create_folder(folder_path: str) -> dict:
    """Create a new directory."""
    try:
        p = Path(folder_path)
        if not p.is_absolute():
            p = PROJECT_ROOT / folder_path

        p.mkdir(parents=True, exist_ok=True)
        return {
            "success": True,
            "action": "create_folder",
            "path": str(p),
            "name": p.name
        }
    except Exception as e:
        return {
            "success": False,
            "action": "create_folder",
            "path": folder_path,
            "error": str(e)
        }


def read_text_file(file_path: str, max_lines: int = 50) -> dict:
    """Read contents of a text file."""
    try:
        p = Path(file_path)
        if not p.is_absolute():
            # Try project root or search
            if (PROJECT_ROOT / file_path).exists():
                p = PROJECT_ROOT / file_path
            else:
                s_res = search_files(query=file_path, max_results=1)
                if s_res["files"]:
                    p = Path(s_res["files"][0]["path"])

        if not p.exists() or not p.is_file():
            return {
                "success": False,
                "action": "read_text_file",
                "path": str(p),
                "error": f"File '{file_path}' does not exist."
            }

        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            lines = [f.readline() for _ in range(max_lines)]
            content = "".join(lines)

        return {
            "success": True,
            "action": "read_text_file",
            "path": str(p),
            "name": p.name,
            "content": content.strip()
        }
    except Exception as e:
        return {
            "success": False,
            "action": "read_text_file",
            "path": file_path,
            "error": str(e)
        }


def delete_file(file_path: str) -> dict:
    """Delete a file safely."""
    try:
        p = Path(file_path)
        if not p.is_absolute():
            p = PROJECT_ROOT / file_path

        if not p.exists():
            return {
                "success": False,
                "action": "delete_file",
                "path": str(p),
                "error": f"File '{file_path}' does not exist."
            }

        if p.is_file():
            p.unlink()
            return {
                "success": True,
                "action": "delete_file",
                "path": str(p),
                "name": p.name
            }
        elif p.is_dir():
            shutil.rmtree(p)
            return {
                "success": True,
                "action": "delete_file",
                "path": str(p),
                "name": p.name
            }
        return {
            "success": False,
            "action": "delete_file",
            "error": "Target is not a valid file or directory."
        }
    except Exception as e:
        return {
            "success": False,
            "action": "delete_file",
            "path": file_path,
            "error": str(e)
        }


def rename_file(old_path: str, new_name_or_path: str) -> dict:
    """Rename or move a file."""
    try:
        src = Path(old_path)
        if not src.is_absolute():
            src = PROJECT_ROOT / old_path

        if not src.exists():
            return {
                "success": False,
                "action": "rename_file",
                "error": f"Source file '{old_path}' not found."
            }

        dst = Path(new_name_or_path)
        if not dst.is_absolute():
            dst = src.parent / new_name_or_path

        src.rename(dst)
        return {
            "success": True,
            "action": "rename_file",
            "old_path": str(src),
            "new_path": str(dst)
        }
    except Exception as e:
        return {
            "success": False,
            "action": "rename_file",
            "error": str(e)
        }


def copy_file(src_path: str, dst_path: str) -> dict:
    """Copy a file to a new destination."""
    try:
        src = Path(src_path)
        if not src.is_absolute():
            src = PROJECT_ROOT / src_path

        dst = Path(dst_path)
        if not dst.is_absolute():
            dst_resolved = resolve_folder_path(dst_path)
            if dst_resolved:
                dst = Path(dst_resolved)
            else:
                dst = PROJECT_ROOT / dst_path

        if not src.exists():
            return {
                "success": False,
                "action": "copy_file",
                "error": f"Source file '{src_path}' not found."
            }

        if dst.is_dir():
            dst = dst / src.name

        shutil.copy2(src, dst)
        return {
            "success": True,
            "action": "copy_file",
            "src": str(src),
            "dst": str(dst)
        }
    except Exception as e:
        return {
            "success": False,
            "action": "copy_file",
            "error": str(e)
        }


if __name__ == "__main__":
    print("Testing FileControl...")
    print("Resolve Downloads:", resolve_folder_path("downloads"))
    print("Search python files in project:", search_files(query="app", file_ext=".py", max_results=3))
