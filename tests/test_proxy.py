from common.http_client import assert_live_proxy_ok, proxy_status, resolve_proxy_url


def test_proxy_required_blocks_live(monkeypatch):
    monkeypatch.setenv("LIVE_SCRAPE", "1")
    monkeypatch.setenv("REQUIRE_PROXY_FOR_LIVE", "1")
    monkeypatch.delenv("PROXY_URL", raising=False)
    monkeypatch.delenv("HTTPS_PROXY", raising=False)
    monkeypatch.delenv("HTTP_PROXY", raising=False)
    monkeypatch.delenv("ALL_PROXY", raising=False)
    # clear lru if any
    try:
        from common.http_client import get_http_client

        get_http_client.cache_clear()
    except Exception:
        pass
    try:
        assert_live_proxy_ok()
        raised = False
    except RuntimeError as e:
        raised = True
        assert "PROXY_URL" in str(e)
    assert raised


def test_proxy_status_reports_missing(monkeypatch):
    monkeypatch.delenv("PROXY_URL", raising=False)
    monkeypatch.delenv("HTTPS_PROXY", raising=False)
    monkeypatch.delenv("HTTP_PROXY", raising=False)
    st = proxy_status()
    assert st["proxy_configured"] is False


def test_resolve_proxy_url(monkeypatch):
    monkeypatch.setenv("PROXY_URL", "http://127.0.0.1:7890")
    assert resolve_proxy_url() == "http://127.0.0.1:7890"
