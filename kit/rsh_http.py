"""One bounded HTTP call.

* The whole call (DNS, connect, upload, download) runs in a daemon worker thread and is
  abandoned at an absolute deadline; the caller gets TimeoutError and the CLI exits right after.
* Redirects are not followed: a 3xx answer is an error, so there is exactly one request.
* The response body is capped, and the chat-completion shape is checked strictly.
"""
from __future__ import annotations

import json
import threading
import urllib.request
from functools import partial
from typing import Callable, Protocol

TOTAL_TIMEOUT_S = 300
MAX_BYTES = 4_000_000
CHUNK = 65_536


class Readable(Protocol):
    def read(self, size: int) -> bytes: ...


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: urllib.request.Request, fp: object, code: int, msg: str,
                         headers: object, newurl: str) -> None:
        return None  # urllib then raises HTTPError for the 3xx answer


def read_capped(response: Readable, limit: int = MAX_BYTES) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = response.read(CHUNK)
        if not chunk:
            return b"".join(chunks)
        size += len(chunk)
        if size > limit:
            raise ValueError(f"auditor response is larger than {limit} bytes")
        chunks.append(chunk)


def _run_into(fn: Callable[[], bytes], box: dict) -> None:
    try:
        box["value"] = fn()
    except Exception as err:  # handed to the caller, which re-raises it
        box["error"] = err


def call_with_deadline(fn: Callable[[], bytes], seconds: float) -> bytes:
    box: dict = {}
    worker = threading.Thread(target=_run_into, args=(fn, box), daemon=True)
    worker.start()
    worker.join(seconds)
    if worker.is_alive():
        raise TimeoutError(f"auditor call took longer than {seconds} s")
    if "error" in box:
        raise box["error"]
    return box["value"]


def _fetch(request: urllib.request.Request) -> bytes:
    opener = urllib.request.build_opener(NoRedirect)
    with opener.open(request, timeout=TOTAL_TIMEOUT_S) as response:
        return read_capped(response)


def post_json(url: str, headers: dict[str, str], body: dict) -> bytes:
    request = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers)
    return call_with_deadline(partial(_fetch, request), TOTAL_TIMEOUT_S)


def chat_content(raw: bytes) -> str:
    """Return choices[0].message.content of a chat completion or raise ValueError."""
    data = json.loads(raw)
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as err:
        raise ValueError("auditor response has no choices[0].message.content") from err
    if not isinstance(content, str):
        raise ValueError("auditor message content is not text")
    return content
