import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import pytest
from daily_report import load_report_from_api, flatten_report, ask_model_nonstream, ask_model_stream


class DummyResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code != 200:
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


# 1) Тест загрузки JSON-отчёта через API
def test_load_report_from_api(monkeypatch):
    sample = {"some": "data"}

    def fake_get(url, auth, headers):
        assert url == "http://example/api/report/UUID/suites/json"
        assert auth == ("user", "pass")
        assert headers["Accept"] == "application/json"
        return DummyResponse(sample)

    monkeypatch.setattr("daily_report.requests.get", fake_get)

    result = load_report_from_api(
        "http://example/api/report/UUID/suites/json",
        auth=("user", "pass")
    )
    assert result == sample


# 2) Тест сплющивания дерева
def test_flatten_report_simple():
    nested = {
        "name": "root",
        "children": [
            {"name": "c1", "status": "passed", "uid": "1"},
            {
                "name": "c2",
                "children": [
                    {"name": "g1", "status": "failed", "uid": "2"}
                ]
            }
        ]
    }
    flat = flatten_report(nested)
    assert len(flat) == 2
    paths = {item["path"] for item in flat}
    assert "root > c1" in paths
    assert "root > c2 > g1" in paths
    statuses = {item["status"] for item in flat}
    assert statuses == {"passed", "failed"}


# 3) Тест формирования payload для модели
def test_ask_model_nonstream_includes_full_context(monkeypatch, tmp_path):
    data = {"key": "x" * 500}
    context = json.dumps(data, ensure_ascii=False)

    captured = {}
    def fake_post(url, json):
        captured["url"] = url
        captured["json"] = json
        return DummyResponse({"choices": [{"text": "OK"}]})

    monkeypatch.setattr("daily_report.requests.post", fake_post)

    out = ask_model_nonstream(
        prompt="TestPrompt",
        context=context,
        model_name="gemma-test",
        host="h.test",
        port=1234,
        max_tokens=50
    )

    assert out == "OK"
    sent = captured["json"]["prompt"]
    assert context in sent
    assert "Запрос: TestPrompt" in sent
    assert captured["url"] == "http://h.test:1234/v1/completions"
    assert captured["json"]["model"] == "gemma-test"


# 4) Тест для ask_model_stream: успешный стриминг
def test_ask_model_stream_success(monkeypatch):
    lines = [
        b'data: {"choices":[{"delta":{"content":"Hel"}}]}',
        b'data: {"choices":[{"delta":{"content":"lo"}}]}',
        b'data: {"choices":[{"delta":{"content":" World"}}]}',
        b'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}',
        b'data: [DONE]'
    ]
    class DummyStream:
        def __init__(self, lines): self._lines = lines
        def raise_for_status(self): pass
        def iter_lines(self, decode_unicode=True): return self._lines

    def fake_post(url, json, stream):
        assert stream is True
        return DummyStream(lines)
    monkeypatch.setattr("daily_report.requests.post", fake_post)
    monkeypatch.setattr("daily_report.ask_model_nonstream", lambda *args, **kwargs: "SHOULD_NOT_BE_CALLED")

    result = ask_model_stream(
        prompt="P",
        context="CTX",
        model_name="m",
        host="h",
        port=1,
        max_tokens=10
    )
    assert result == "Hello World"


# 5) Тест для ask_model_stream: пустой стриминг -> fallback
def test_ask_model_stream_fallback(monkeypatch):
    class DummyStreamEmpty:
        def raise_for_status(self): pass
        def iter_lines(self, decode_unicode=True): return []

    def fake_post_empty(url, json, stream): return DummyStreamEmpty()
    monkeypatch.setattr("daily_report.requests.post", fake_post_empty)

    called = {}
    def fake_nonstream(prompt, context, model_name, host, port, max_tokens):
        called['args'] = (prompt, context, model_name, host, port, max_tokens)
        return 'FALLBACK'
    monkeypatch.setattr("daily_report.ask_model_nonstream", fake_nonstream)

    result = ask_model_stream(
        prompt="P2",
        context="CTX2",
        model_name="m2",
        host="h2",
        port=2,
        max_tokens=20
    )
    assert result == 'FALLBACK'
    assert called['args'][0] == 'P2'
