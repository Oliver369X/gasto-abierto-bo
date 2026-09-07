from playwright.sync_api import sync_playwright

def test_ui_smoke():
    """Optional local e2e when stack is up. Skips if web unreachable."""
    import urllib.request
    try:
        urllib.request.urlopen("http://localhost:3010/", timeout=2)
    except Exception:
        return
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://localhost:3010/")
        assert "Gasto Abierto" in page.content()
        page.click("text=Explorar")
        page.wait_for_url("**/explorar")
        page.goto("http://localhost:3010/incendios")
        assert "Incendios" in page.content() or "AURA" in page.content()
        browser.close()
