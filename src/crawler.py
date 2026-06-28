import hashlib
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urlencode, parse_qsl, urlunparse

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from .raw_io import _etld1
from .stealth import (
    STEALTH_ARGS,
    apply_stealth,
    human_scroll,
    inter_page_delay,
    random_ua,
    random_viewport,
)

RESOURCE_TYPES = {"script", "stylesheet", "image", "media", "font", "xhr", "fetch"}

_SESSION_PARAMS = {"token", "session", "sid", "sessionid", "sess", "auth", "jwt", "access_token"}

_ABORT_TYPES = {"image", "media", "font"}

_SKIP_PATH_SEGMENTS = {
    "login", "logout", "signin", "signout", "signup", "register",
    "cart", "checkout", "basket", "account", "profile", "password",
    "admin", "dashboard", "settings", "preferences",
}


def _should_skip_path(url: str) -> bool:
    path = urlparse(url).path.lower()
    segments = {s for s in path.split("/") if s}
    return bool(segments & _SKIP_PATH_SEGMENTS)


def _checkpoint_path(url: str, checkpoint_dir: str) -> str:
    h = hashlib.sha1(url.encode()).hexdigest()[:16]
    return os.path.join(checkpoint_dir, f"{h}.done")


def _is_checkpointed(url: str, checkpoint_dir: str) -> bool:
    return os.path.exists(_checkpoint_path(url, checkpoint_dir))


def _mark_checkpointed(url: str, checkpoint_dir: str) -> None:
    os.makedirs(checkpoint_dir, exist_ok=True)
    open(_checkpoint_path(url, checkpoint_dir), "w").close()


def _should_abort(resource_type: str) -> bool:
    return resource_type in _ABORT_TYPES


def _normalize_url(url: str) -> str:
    """Strip fragment and session-like query params; normalise scheme to https; strip trailing slash."""
    p = urlparse(url)
    clean_qs = [(k, v) for k, v in parse_qsl(p.query) if k.lower() not in _SESSION_PARAMS]
    path = p.path.rstrip("/") or "/"
    return urlunparse(("https", p.netloc, path, p.params, urlencode(clean_qs), ""))


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


def _collect_same_site_links(page, site_etld1: str) -> list[str]:
    """Extract and normalise all same-site <a href> links from the current page."""
    try:
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    except Exception:
        return []
    return [
        _normalize_url(href)
        for href in hrefs
        if _same_site(href, site_etld1)
    ]


def _crawl_page(page, url: str, resources: list[dict], timeout_ms: int, stealth: bool,
                fast_timeout_ms: int = 5_000, idle_timeout_ms: int = 5_000) -> str:
    """
    Navigate to url, attach request/response listeners, scroll, return status.
    Appends resource dicts into resources list.
    """
    status = "ok"
    # Maps request URL → list of resource-list indices awaiting a response.
    # One URL can fire multiple requests (retries, preload), so we track all.
    pending: dict[str, list[int]] = {}

    def on_request(req):
        parsed = urlparse(req.url)
        try:
            initiator_info = req.initiator()
            initiator = initiator_info.get("type", "") if isinstance(initiator_info, dict) else ""
        except Exception:
            initiator = ""
        # Record from_iframe only when the request originates from a nested frame,
        # not from the main frame itself.
        try:
            if req.frame and req.frame != page.main_frame:
                frame_url = req.frame.url or ""
            else:
                frame_url = ""
        except Exception:
            frame_url = ""

        idx = len(resources)
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
        pending.setdefault(req.url, []).append(idx)

    def on_response(resp):
        req_url = resp.request.url
        indices = pending.get(req_url)
        if not indices:
            return
        for idx in reversed(indices):
            r = resources[idx]
            if r["status_code"] == "":
                headers = resp.headers
                r.update({
                    "status_code": resp.status,
                    "content_type": headers.get("content-type", ""),
                    "content_length_bytes": int(headers.get("content-length", -1)),
                })
                break

    page.on("request", on_request)
    page.on("response", on_response)

    def handle_route(route):
        if _should_abort(route.request.resource_type):
            try:
                route.abort()
            except Exception:
                pass
        else:
            try:
                route.continue_()
            except Exception:
                pass

    page.route("**/*", handle_route)

    try:
        try:
            page.goto(url, timeout=fast_timeout_ms, wait_until="networkidle")
        except PlaywrightTimeout:
            page.goto(url, timeout=timeout_ms, wait_until="networkidle")

        if stealth:
            human_scroll(page)
        else:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1.5)
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(0.5)
        try:
            page.wait_for_load_state("networkidle", timeout=idle_timeout_ms)
        except PlaywrightTimeout:
            pass
    except PlaywrightTimeout:
        status = "timeout"
    except Exception:
        status = "error"

    page.remove_listener("request", on_request)
    page.remove_listener("response", on_response)
    try:
        page.unroute("**/*", handle_route)
    except Exception:
        pass
    return status


def crawl_site(
    entry_url: str,
    max_pages: int = 20,
    depth: int = 2,
    timeout_ms: int = 5_000,
    fast_timeout_ms: int = 5_000,
    idle_timeout_ms: int = 5_000,
    stealth: bool = True,
    checkpoint_dir: str | None = None,
    page_workers: int = 1,
) -> dict:
    """
    BFS crawl of a site starting from entry_url.

    When stealth=True:
    - Random User-Agent and viewport per browser context
    - JS init patches (navigator.webdriver, plugins, chrome object)
    - Chromium launched with automation-disabling flags
    - Human-like random-step scroll on each page
    - Random delay between page navigations

    page_workers > 1 crawls multiple sub-pages concurrently, each in its own
    browser context. Capped at 3 to limit bot-detection risk.
    """
    site_etld1 = _etld1(urlparse(entry_url).netloc)
    normalized_entry = _normalize_url(entry_url)
    visited: set[str] = set()
    visited_lock = threading.Lock()
    queue: list[tuple[str, int]] = [(normalized_entry, 0)]
    all_resources: list[dict] = []
    resources_lock = threading.Lock()
    overall_status = "ok"

    effective_workers = min(page_workers, 3) if page_workers > 1 else 1

    launch_kwargs: dict = {"headless": True}
    if stealth:
        launch_kwargs["args"] = STEALTH_ARGS

    def _crawl_one(browser, url: str, depth_val: int) -> tuple[str, str, list[dict], list[str]]:
        """Crawl a single URL in its own context; return (url, status, resources, new_links)."""
        ctx_kwargs: dict = {}
        if stealth:
            ctx_kwargs["user_agent"] = random_ua()
            ctx_kwargs["viewport"] = random_viewport()
        context = browser.new_context(**ctx_kwargs)
        page = context.new_page()
        if stealth:
            apply_stealth(page)
        local_resources: list[dict] = []
        status = _crawl_page(page, url, local_resources, timeout_ms, stealth,
                              fast_timeout_ms=fast_timeout_ms, idle_timeout_ms=idle_timeout_ms)
        new_links: list[str] = []
        if depth_val < depth and status == "ok":
            new_links = _collect_same_site_links(page, site_etld1)
        context.close()
        return url, status, local_resources, new_links

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(**launch_kwargs)

            while queue:
                with visited_lock:
                    if len(visited) >= max_pages:
                        break
                    batch: list[tuple[str, int]] = []
                    in_batch: set[str] = set()
                    while queue and len(visited) + len(batch) < max_pages:
                        candidate, dep = queue.pop(0)
                        if candidate in visited or candidate in in_batch:
                            continue
                        if checkpoint_dir and _is_checkpointed(candidate, checkpoint_dir):
                            visited.add(candidate)
                            continue
                        batch.append((candidate, dep))
                        in_batch.add(candidate)
                        if len(batch) >= effective_workers:
                            break
                    for url_b, _ in batch:
                        visited.add(url_b)

                if not batch:
                    break

                if stealth and len(visited) > 1:
                    inter_page_delay(min_s=0.5, max_s=1.5)

                if effective_workers == 1:
                    url_b, dep = batch[0]
                    _, status, local_res, new_links = _crawl_one(browser, url_b, dep)
                    if url_b == normalized_entry and status != "ok":
                        overall_status = status
                    if checkpoint_dir and status == "ok":
                        _mark_checkpointed(url_b, checkpoint_dir)
                    all_resources.extend(local_res)
                    for link in new_links:
                        with visited_lock:
                            if link not in visited and not _should_skip_path(link):
                                queue.append((link, dep + 1))
                else:
                    futures = {}
                    with ThreadPoolExecutor(max_workers=effective_workers) as executor:
                        for url_b, dep in batch:
                            fut = executor.submit(_crawl_one, browser, url_b, dep)
                            futures[fut] = (url_b, dep)
                        for fut in as_completed(futures):
                            url_b, dep = futures[fut]
                            try:
                                _, status, local_res, new_links = fut.result()
                            except Exception:
                                status, local_res, new_links = "error", [], []
                            if url_b == normalized_entry and status != "ok":
                                overall_status = status
                            if checkpoint_dir and status == "ok":
                                _mark_checkpointed(url_b, checkpoint_dir)
                            with resources_lock:
                                all_resources.extend(local_res)
                            with visited_lock:
                                for link in new_links:
                                    if link not in visited and not _should_skip_path(link):
                                        queue.append((link, dep + 1))

            browser.close()
    except Exception:
        overall_status = "error"

    return {"url": entry_url, "status": overall_status, "resources": all_resources}


def crawl(url: str, timeout_ms: int = 5_000) -> dict:
    """Backwards-compatible single-page crawl."""
    return crawl_site(url, max_pages=1, depth=0, timeout_ms=timeout_ms)
