"""
IntelliDesk Browser and Web Search Automation Module.

Handles distinct web searches (Google, YouTube) and direct navigation to websites (GitHub, Gmail, etc.).
"""

import urllib.parse
import webbrowser
from typing import Optional


def open_url(url: str) -> dict:
    """Open a web URL in the default browser."""
    if not url:
        return {"success": False, "action": "open_url", "error": "No URL provided."}

    target = url.strip()
    if not target.startswith("http://") and not target.startswith("https://"):
        target = f"https://{target}"

    try:
        webbrowser.open(target)
        return {
            "success": True,
            "action": "open_url",
            "url": target
        }
    except Exception as e:
        return {
            "success": False,
            "action": "open_url",
            "url": target,
            "error": str(e)
        }


def search_google(query: str) -> dict:
    """Perform a Google web search in the browser."""
    if not query:
        return {"success": False, "action": "search_google", "error": "Search query is empty."}

    encoded = urllib.parse.quote_plus(query.strip())
    url = f"https://www.google.com/search?q={encoded}"
    return open_url(url)


def search_youtube(query: str) -> dict:
    """Perform a YouTube video search in the browser."""
    if not query:
        return {"success": False, "action": "search_youtube", "error": "Search query is empty."}

    encoded = urllib.parse.quote_plus(query.strip())
    url = f"https://www.youtube.com/results?search_query={encoded}"
    return open_url(url)


def open_gmail() -> dict:
    """Open Gmail in browser."""
    return open_url("https://mail.google.com")


def open_github(repo_path: Optional[str] = None) -> dict:
    """Open GitHub in browser."""
    url = f"https://github.com/{repo_path.strip('/')}" if repo_path else "https://github.com"
    return open_url(url)


if __name__ == "__main__":
    print("Testing Browser Control Module...")
    print("Google Search URL prepared:", search_google("software testing"))
