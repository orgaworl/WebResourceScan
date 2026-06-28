import time
from urllib.parse import urlparse, urlencode, parse_qsl, urlunparse

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from .raw_io import _etld1

RESOURCE_TYPES = {"script", "stylesheet", "image", "media", "font", "xhr", "fetch"}

_SESSION_PARAMS = {"token", "session", "sid", "sessionid", "sess", "auth", "jwt", "access_token"}


def _normalize_url(url: str) -> str:
    """Strip fragment and session-like query params; return canonical URL string."""
    p = urlparse(url)
    clean_qs = [(k, v) for k, v in parse_qsl(p.query) if k.lower() not in _SESSION_PARAMS]
    return urlunparse((p.scheme, p.netloc, p.path, p.params, urlencode(clean_qs), ""))


def _same_site(url: str, site_etld1: str) -> bool:
    """Return True if url belongs to site_etld1 (eTLD+1 match) and is http/https."""
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        return False
    return _etld1(p.netloc) == site_etld1


def _normalize_type(rt: str) -> str:
    if rt == "fetch":
        return "xhr"
    if rt in RESOURCE_TYPES:
        return rt
    return "other"


def _scroll_page(page) -> None:
    """Scroll to bottom then back to top to trigger lazy-loaded resources."""
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1.5)
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(0.5)


def _collect_same_site_links(page, site_etld1: str) -> list[str]:
    """Extract and normalise all same-site <a href> links from the current page."""
    try:
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    except Exception:
        return []
    links = []
    for href in hrefs:
        if _same_site(href, site_etld1):
            links.append(_normalize_url(href))
    return links


def _crawl_page(page, url: str, resources: list[dict], timeout_ms: int) -> str:
    """
    Navigate to url, attach request/response listeners, scroll, collect links.
    Appends resource dicts (with source_page set) into resources list.
    Returns crawl status: "ok" | "timeout" | "error".
    """
    status = "ok"
    # index into resources list at the start of this page — used to match responses
    start_idx = len(resources)

    def on_request(req):
        parsed = urlparse(req.url)
        try:
            initiator_info = req.initiator()
            initiator = initiator_info.get("type", "") if isinstance(initiator_info, dict) else ""
        except Exception:
            initiator = ""
        try:
            frame_url = req.frame.url if req.frame and req.frame.url != url else ""
        except Exception:
            frame_url = ""

        resources.append({
            "resource_url": req.url,
            "resource_type": _normalize_type(req.resource_type),
            "domain": parsed.netloc,
            "method": req.method,
            "status_code": "",
            "content_type": "",
            "content_length_bytes": -1,
            "source_page": url,
            "initiator": initiator,
            "from_iframe": frame_url,
        })

    def on_response(resp):
        req_url = resp.request.url
        for r in reversed(resources[start_idx:]):
            if r["resource_url"] == req_url and r["source_page"] == url and r["status_code"] == "":
                headers = resp.headers
                r.update({
                    "status_code": resp.status,
                    "content_type": headers.get("content-type", ""),
                    "content_length_bytes": int(headers.get("content-length", -1)),
                })
                break

    page.on("request", on_request)
    page.on("response", on_response)

    try:
        page.goto(url, timeout=timeout_ms, wait_until="networkidle")
        _scroll_page(page)
        try:
            page.wait_for_load_state("networkidle", timeout=5_000)
        except PlaywrightTimeout:
            pass
    except PlaywrightTimeout:
        status = "timeout"
    except Exception:
        status = "error"

    page.remove_listener("request", on_request)
    page.remove_listener("response", on_response)
    return status


def crawl_site(
    entry_url: str,
    max_pages: int = 20,
    depth: int = 2,
    timeout_ms: int = 30_000,
) -> dict:
    """
    BFS crawl of a site starting from entry_url.
    Visits up to max_pages unique pages within the same eTLD+1, up to given depth.
    Returns {"url": entry_url, "status": str, "resources": [...]}.
    """
    site_etld1 = _etld1(urlparse(entry_url).netloc)
    visited: set[str] = set()
    queue: list[tuple[str, int]] = [(_normalize_url(entry_url), 0)]
    all_resources: list[dict] = []
    overall_status = "ok"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            while queue and len(visited) < max_pages:
                current_url, current_depth = queue.pop(0)
                if current_url in visited:
                    continue
                visited.add(current_url)

                status = _crawl_page(page, current_url, all_resources, timeout_ms)

                if current_url == _normalize_url(entry_url) and status != "ok":
                    overall_status = status

                if current_depth < depth and status == "ok":
                    links = _collect_same_site_links(page, site_etld1)
                    for link in links:
                        if link not in visited:
                            queue.append((link, current_depth + 1))

            browser.close()
    except Exception:
        overall_status = "error"

    return {"url": entry_url, "status": overall_status, "resources": all_resources}


def crawl(url: str, timeout_ms: int = 30_000) -> dict:
    """Backwards-compatible single-page crawl."""
    return crawl_site(url, max_pages=1, depth=0, timeout_ms=timeout_ms)
