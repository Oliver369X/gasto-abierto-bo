"""Pipeline resilience: soft-fail per item and status derivation."""
from __future__ import annotations

from worker.adapters.base import RawItem, StagingRecord
from worker.pipeline import _run_status


def test_run_status_ok():
    assert _run_status(2, [], 5) == ("ok", None)


def test_run_status_partial():
    status, err = _run_status(3, [{"index": 1, "error": "boom"}], 2)
    assert status == "partial"
    assert err and "1 item" in err


def test_run_status_error_all_failed():
    status, err = _run_status(2, [{"index": 0}, {"index": 1}], 0)
    assert status == "error"
    assert err


def test_request_with_retry_succeeds_after_fail(monkeypatch):
    import httpx
    from common import http_client

    calls = {"n": 0}

    class FakeResp:
        status_code = 200

        def raise_for_status(self):
            return None

    class FakeClient:
        def request(self, method, url, **kwargs):
            calls["n"] += 1
            if calls["n"] < 2:
                raise httpx.ConnectError("fail")
            return FakeResp()

    monkeypatch.setattr(http_client, "get_http_client", lambda: FakeClient())
    monkeypatch.setenv("HTTP_RETRIES", "3")
    monkeypatch.setenv("HTTP_RETRY_BACKOFF", "0.01")
    resp = http_client.request_with_retry("GET", "http://example.test")
    assert resp.status_code == 200
    assert calls["n"] == 2
