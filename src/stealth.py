"""
Anti-bot evasion utilities for Playwright.

Strategies applied:
1. Chromium launch flags — disable automation fingerprints at browser level
2. JS init script — patch navigator.webdriver, plugins, chrome object, permissions
3. Realistic User-Agent pool — random selection per browser instance
4. Realistic viewport pool — random common screen sizes
5. Random inter-page delay — breaks timing regularity
6. Gradual human-like scroll — stepwise scroll with random speed
"""

import random
import time

# ---------------------------------------------------------------------------
# Chromium launch arguments
# ---------------------------------------------------------------------------
STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-infobars",
    "--disable-browser-side-navigation",
    "--disable-gpu",
]

# ---------------------------------------------------------------------------
# User-Agent pool — real Chrome 124 strings across platforms
# ---------------------------------------------------------------------------
USER_AGENTS = [
    # Windows Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # macOS Chrome
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Linux Chrome
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# ---------------------------------------------------------------------------
# Viewport pool — common desktop resolutions
# ---------------------------------------------------------------------------
VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1280, "height": 800},
    {"width": 1600, "height": 900},
]

# ---------------------------------------------------------------------------
# JS patches injected before every page load
# ---------------------------------------------------------------------------
_STEALTH_JS = """
// Remove webdriver flag
Object.defineProperty(navigator, 'webdriver', { get: () => false });

// Fake plugin list (headless has 0 plugins)
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const arr = [1, 2, 3, 4, 5];
        arr.__proto__ = PluginArray.prototype;
        return arr;
    }
});

// Realistic language list
Object.defineProperty(navigator, 'languages', {
    get: () => ['zh-CN', 'zh', 'en-US', 'en']
});

// Add window.chrome (absent in headless)
if (!window.chrome) {
    window.chrome = {
        runtime: {},
        loadTimes: function() { return {}; },
        csi: function() { return {}; },
        app: { isInstalled: false },
    };
}

// Fix permissions.query to not expose automation
const _origPermQuery = window.navigator.permissions.query.bind(navigator.permissions);
window.navigator.permissions.query = (params) => {
    if (params.name === 'notifications') {
        return Promise.resolve({ state: Notification.permission, onchange: null });
    }
    return _origPermQuery(params);
};

// Mask headless in User-Agent Client Hints
if (navigator.userAgentData) {
    Object.defineProperty(navigator, 'userAgentData', {
        get: () => undefined,
    });
}
"""


def apply_stealth(page) -> None:
    """Inject JS patches that run before every page navigation."""
    page.add_init_script(_STEALTH_JS)


def random_ua() -> str:
    return random.choice(USER_AGENTS)


def random_viewport() -> dict:
    return random.choice(VIEWPORTS)


def inter_page_delay(min_s: float = 1.5, max_s: float = 4.0) -> None:
    """Sleep a random duration between page navigations."""
    time.sleep(random.uniform(min_s, max_s))


def human_scroll(page) -> None:
    """
    Scroll the page in small random steps to simulate human behaviour,
    then scroll back to top.
    """
    page_height = page.evaluate("document.body.scrollHeight")
    viewport_height = page.evaluate("window.innerHeight")

    current = 0
    while current < page_height:
        step = random.randint(200, 500)
        current = min(current + step, page_height)
        page.evaluate(f"window.scrollTo(0, {current})")
        time.sleep(random.uniform(0.08, 0.25))

    # Pause at bottom, then scroll back
    time.sleep(random.uniform(0.5, 1.2))
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(random.uniform(0.3, 0.7))
