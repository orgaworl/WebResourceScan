from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

RESOURCE_TYPES = {"script", "stylesheet", "image", "media", "font", "xhr", "fetch"}


def _normalize_type(rt: str) -> str:
    if rt == "fetch":
        return "xhr"
    if rt in RESOURCE_TYPES:
        return rt
    return "other"


def crawl(url: str, timeout_ms: int = 30_000) -> dict:
    resources = []
    status = "ok"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            def on_request(req):
                parsed = urlparse(req.url)
                resources.append({
                    "url": req.url,
                    "type": _normalize_type(req.resource_type),
                    "domain": parsed.netloc,
                })

            page.on("request", on_request)
            try:
                page.goto(url, timeout=timeout_ms, wait_until="networkidle")
            except PlaywrightTimeout:
                status = "timeout"
            except Exception:
                status = "error"
            finally:
                browser.close()
    except Exception:
        status = "error"

    return {"url": url, "status": status, "resources": resources}
