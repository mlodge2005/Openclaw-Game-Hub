"""HTTP client for OpenClaw /v1/chat/completions."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Optional


class OpenClawError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class OpenClawUnavailable(OpenClawError):
    """OpenClaw unreachable or returned an error."""


class OpenClawClient:
    """Sync HTTP client for OpenClaw Gateway chat completions API."""

    def __init__(
        self,
        base_url: str,
        token: str,
        agent_id: str = "main",
        timeout_seconds: int = 120,
        max_retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.agent_id = agent_id
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def request_move(self, message: str, timeout_seconds: Optional[int] = None) -> str:
        """Send a prompt to the agent and return the assistant response text.

        POSTs to /v1/chat/completions with Bearer auth and model: openclaw/<agent_id>.
        Retries on 5xx with exponential backoff. Raises OpenClawUnavailable on failure.
        """
        url = f"{self.base_url}/v1/chat/completions"
        timeout = timeout_seconds or self.timeout_seconds
        body = json.dumps(
            {
                "model": f"openclaw/{self.agent_id}",
                "user": "terminal-game-hub",
                "messages": [{"role": "user", "content": message}],
            }
        ).encode("utf-8")

        last_exc: Optional[BaseException] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                req = urllib.request.Request(
                    url,
                    data=body,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                choices = data.get("choices", [])
                if not choices:
                    raise OpenClawError("no choices in response")
                return choices[0].get("message", {}).get("content", "")
            except urllib.error.HTTPError as exc:
                status = exc.code
                body_text = exc.read().decode("utf-8", errors="replace")
                if status == 401:
                    raise OpenClawUnavailable(
                        "auth rejected (401) — check gateway token", status_code=401
                    ) from exc
                if status == 404:
                    raise OpenClawUnavailable(
                        "endpoint not found (404) — is /v1/chat/completions enabled?",
                        status_code=404,
                    ) from exc
                if status >= 500 and attempt < self.max_retries:
                    last_exc = OpenClawUnavailable(
                        f"server error {status}: {body_text[:200]}", status_code=status
                    )
                    time.sleep(2**attempt)
                    continue
                raise OpenClawUnavailable(
                    f"HTTP {status}: {body_text[:200]}", status_code=status
                ) from exc
            except (urllib.error.URLError, ConnectionError, TimeoutError) as exc:
                last_exc = OpenClawUnavailable(f"connection failed: {exc}")
                if attempt < self.max_retries:
                    time.sleep(2**attempt)
                    continue
                raise OpenClawUnavailable(f"connection failed after retries: {exc}") from exc
        raise OpenClawUnavailable(f"request failed after {self.max_retries} retries") from last_exc
