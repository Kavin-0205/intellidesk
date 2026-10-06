"""
Unit test for File & Folder Operations module.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.file_control import (
    resolve_folder_path,
    search_files,
    create_file,
    create_folder,
    read_text_file,
    delete_file,
    rename_file,
    copy_file,
)


def test_file_operations():
    print("\n--- TEST: File & Folder Control ---")

    # 1. Resolve folder
    downloads = resolve_folder_path("downloads")
    print(f"[Resolve Downloads]: {downloads}")
    assert downloads is not None and "Downloads" in downloads

    # 2. Create file
    test_path = "scratch_test.txt"
    create_res = create_file(test_path, "Hello from IntelliDesk file automation!")
    print(f"[Create File]: {create_res}")
    assert create_res.get("success") is True

    # 3. Read file
    read_res = read_text_file(test_path)
    print(f"[Read File]: {read_res.get('content')}")
    assert "IntelliDesk" in read_res.get("content", "")

    # 4. Search files
    search_res = search_files(query="scratch_test", file_ext=".txt")
    print(f"[Search Files Found]: {search_res.get('count')}")
    assert search_res.get("count", 0) >= 1

    # 5. Rename file
    renamed_path = "scratch_renamed.txt"
    rename_res = rename_file(test_path, renamed_path)
    print(f"[Rename File]: {rename_res}")
    assert rename_res.get("success") is True

    # 6. Delete file
    del_res = delete_file(renamed_path)
    print(f"[Delete File]: {del_res}")
    assert del_res.get("success") is True

    print("\n[SUCCESS] File & Folder Control tests passed!")


if __name__ == "__main__":
    test_file_operations()
