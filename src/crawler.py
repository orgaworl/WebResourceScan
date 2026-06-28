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
    resources: dict[str, dict] = {}
    status = "ok"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            def on_request(req):
                parsed = urlparse(req.url)
                resources[req.url] = {
                    "resource_url": req.url,
                    "resource_type": _normalize_type(req.resource_type),
                    "domain": parsed.netloc,
                    "method": req.method,
                    "status_code": "",
                    "content_type": "",
                    "content_length_bytes": -1,
                }

            def on_response(resp):
                key = resp.request.url
                if key in resources:
                    headers = resp.headers
                    resources[key].update({
                        "status_code": resp.status,
                        "content_type": headers.get("content-type", ""),
                        "content_length_bytes": int(headers.get("content-length", -1)),
                    })

            page.on("request", on_request)
            page.on("response", on_response)

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

    return {"url": url, "status": status, "resources": list(resources.values())}
