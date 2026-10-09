"""
IntelliDesk Groq LLM Client with Network Timeout, Retry & Rate-Limit Handling.

Provides bounded network execution preventing unbounded TCP keepalive hangs
and structured detection for HTTP 429 quota exhaustion.
"""

import os
import sys
import time
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, APITimeoutError, APIConnectionError

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("GROQ_API_KEY is not set in .env")

# Default explicit client-level timeout: 15.0 seconds
DEFAULT_TIMEOUT = 15.0

client = OpenAI(
    api_key=api_key,
    base_url="https://api.groq.com/openai/v1",
    timeout=DEFAULT_TIMEOUT,
    max_retries=0,  # We manage bounded retries explicitly to distinguish 429 from transients
)


class LLMAPIError(Exception):
    """Base class for LLM API errors."""
    pass


class LLMRateLimitError(LLMAPIError):
    """Raised on HTTP 429 quota or rate-limit exhaustion."""
    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.status_code = 429
        self.retry_after = retry_after


class LLMTimeoutError(LLMAPIError):
    """Raised when an API call exceeds bounded request timeout."""
    def __init__(self, message: str, timeout_seconds: float = DEFAULT_TIMEOUT):
        super().__init__(message)
        self.timeout_seconds = timeout_seconds


class LLMConnectionError(LLMAPIError):
    """Raised on connection resets, network drops, or socket errors."""
    def __init__(self, message: str, original_error: str = ""):
        super().__init__(message)
        self.original_error = original_error


def execute_llm_request(
    messages: List[Dict[str, str]],
    model: str = "openai/gpt-oss-120b",
    temperature: float = 0.0,
    max_tokens: Optional[int] = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = 1,
) -> str:
    """
    Execute chat completion with explicit bounded timeout and transient-only retry.
    Never spins indefinitely on HTTP 429 or network hangs.
    """
    kwargs: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "timeout": timeout,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    last_error: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""

        except RateLimitError as e:
            # HTTP 429: Do NOT retry rapidly; detect Retry-After and fail gracefully
            retry_after = None
            try:
                if hasattr(e, "response") and e.response and hasattr(e.response, "headers"):
                    ra_hdr = e.response.headers.get("retry-after")
                    if ra_hdr:
                        retry_after = float(ra_hdr)
            except Exception:
                pass
            raise LLMRateLimitError(
                f"HTTP 429 Rate limit or quota exhausted: {e}",
                retry_after=retry_after,
            ) from e

        except (APITimeoutError, TimeoutError) as e:
            last_error = e
            if attempt < max_retries:
                time.sleep(1.0)
                continue
            raise LLMTimeoutError(
                f"API request timed out after {timeout} seconds",
                timeout_seconds=timeout,
            ) from e

        except (APIConnectionError, ConnectionResetError, ConnectionError) as e:
            last_error = e
            if attempt < max_retries:
                time.sleep(1.0)
                continue
            raise LLMConnectionError(
                f"Network connection failed: {e}",
                original_error=str(e),
            ) from e

        except Exception as e:
            # Check for 429 in generic exception string
            err_str = str(e).lower()
            if "429" in err_str or "rate_limit" in err_str or "quota" in err_str:
                raise LLMRateLimitError(f"HTTP 429 Rate limit / quota reached: {e}") from e
            if "timeout" in err_str:
                raise LLMTimeoutError(f"Request timed out: {e}", timeout_seconds=timeout) from e
            raise LLMAPIError(f"API call failed: {e}") from e

    if last_error:
        raise LLMAPIError(f"API call exhausted {max_retries} retries: {last_error}")
    raise LLMAPIError("API call failed without explicit exception")


def ask_grok(user_message: str) -> str:
    """Convenience helper for single user message."""
    return execute_llm_request(
        messages=[{"role": "user", "content": user_message}],
        timeout=DEFAULT_TIMEOUT,
    )