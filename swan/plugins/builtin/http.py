from __future__ import annotations

import asyncio
import json as _json
import urllib.error
import urllib.request
from typing import Any

from swan.plugins.base import AgentPlugin
from swan.core.models import Task


class Plugin(AgentPlugin):
    """Makes an HTTP request using urllib (no extra dependencies).

    Required task input key:
        url (str): The URL to request.

    Optional task input keys:
        method (str):            HTTP method (default: GET).
        headers (dict):          Extra request headers.
        body (str|dict):         Request body; dicts are JSON-encoded automatically.
        timeout (float):         Per-request timeout in seconds (default: 30).
        follow_redirects (bool): Follow 3xx redirects (default: True).
    """

    plugin_type = "http"

    async def run(self, task: Task) -> dict[str, Any]:
        url: str = task.input.get("url", "")
        if not url:
            raise ValueError("HttpPlugin requires task.input['url']")

        method: str = task.input.get("method", "GET").upper()
        headers: dict = task.input.get("headers", {})
        body = task.input.get("body")
        timeout: float = task.input.get("timeout", 30.0)

        # Encode body
        data: bytes | None = None
        if body is not None:
            if isinstance(body, dict):
                data = _json.dumps(body).encode()
                headers.setdefault("Content-Type", "application/json")
            else:
                data = str(body).encode()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            _do_request,
            url, method, headers, data, timeout,
        )


def _do_request(
    url: str,
    method: str,
    headers: dict,
    data: bytes | None,
    timeout: float,
) -> dict[str, Any]:
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            resp_headers = dict(resp.headers)
            status = resp.status
    except urllib.error.HTTPError as exc:
        body = exc.read()
        resp_headers = dict(exc.headers)
        status = exc.code

    # Try to decode body as JSON; fall back to text
    try:
        decoded: Any = _json.loads(body)
    except Exception:
        decoded = body.decode(errors="replace")

    return {
        "status_code": status,
        "headers": resp_headers,
        "body": decoded,
    }
