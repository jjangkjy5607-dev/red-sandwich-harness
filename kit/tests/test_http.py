import sys
import threading
import time
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT))

import rsh_audit  # noqa: E402
import rsh_http  # noqa: E402
from rsh_evidence import check_findings  # noqa: E402


class FakeResponse:
    def __init__(self, chunks: list[bytes]):
        self.chunks = list(chunks)

    def read(self, size: int) -> bytes:
        return self.chunks.pop(0) if self.chunks else b""


def test_capped_read_joins_chunks():
    assert rsh_http.read_capped(FakeResponse([b'{"a"', b": 1}"])) == b'{"a": 1}'


def test_capped_read_stops_at_size_limit():
    with pytest.raises(ValueError):
        rsh_http.read_capped(FakeResponse([b"x" * 6, b"x" * 6]), limit=10)


def test_deadline_abandons_a_call_that_never_returns():
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        rsh_http.call_with_deadline(lambda: threading.Event().wait(30) or b"", 0.2)
    assert time.monotonic() - started < 5


def test_deadline_passes_values_and_errors_through():
    assert rsh_http.call_with_deadline(lambda: b"ok", 5) == b"ok"
    with pytest.raises(ValueError):
        rsh_http.call_with_deadline(lambda: rsh_http.chat_content(b"[]"), 5)


def test_redirects_are_refused():
    handler = rsh_http.NoRedirect()
    request = rsh_http.urllib.request.Request("https://example.invalid/v1/chat/completions")
    assert handler.redirect_request(request, None, 302, "Found", {}, "https://elsewhere.invalid/") is None


@pytest.mark.parametrize("raw", [b'{"choices": []}', b'{"choices": [{"message": {"content": 5}}]}', b"[]",
                                 b'{"choices": [{"message": null}]}', b"not json"])
def test_bad_chat_shapes_raise_value_error(raw):
    with pytest.raises(ValueError):
        rsh_http.chat_content(raw)


def test_good_chat_shape():
    assert rsh_http.chat_content(b'{"choices": [{"message": {"content": "{}"}}]}') == "{}"


def test_bad_server_answer_exits_2(tmp_path, monkeypatch):
    monkeypatch.chdir(KIT)
    monkeypatch.setenv("RSH_AUDIT_API_KEY", "test-key")
    monkeypatch.setenv("RSH_AUDIT_MODEL", "test-model")
    monkeypatch.setattr(rsh_http, "post_json", lambda url, headers, body: b'{"choices": []}')
    code = rsh_audit.main(["--spec", "examples/spec_step01.md", "--files", "examples/good_unit.py",
                           "--out", str(tmp_path / "r.json")])
    assert code == 2


def test_boolean_line_is_rejected():
    sources = {"a.py": ["value = compute_total(items)"]}
    finding = {"file": "a.py", "line": True, "quote": "value = compute_total(items)", "severity": "high"}
    assert check_findings([finding], sources).kept == []
