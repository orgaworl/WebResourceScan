"""
Rule-based domain classifier. No LLM required.

Matching order:
1. Exact domain match in KNOWN_DOMAINS
2. eTLD+1 match in KNOWN_DOMAINS
3. Keyword scan against the full domain string
4. Fallback: "other"

To extend coverage add entries to KNOWN_DOMAINS or KEYWORDS below.
"""

VALID_CATEGORIES = {"gambling", "gaming", "ad", "payment", "cdn", "other"}

KNOWN_DOMAINS: dict[str, str] = {
    # --- gambling ---
    "bet365.com": "gambling",
    "betway.com": "gambling",
    "draftkings.com": "gambling",
    "fanduel.com": "gambling",
    "pokerstars.com": "gambling",
    "888casino.com": "gambling",
    "williamhill.com": "gambling",
    "ladbrokes.com": "gambling",
    "betfair.com": "gambling",
    "pinnacle.com": "gambling",
    "unibet.com": "gambling",
    "bwin.com": "gambling",
    "casumo.com": "gambling",
    "leovegas.com": "gambling",
    "mansion88.com": "gambling",
    "sbobet.com": "gambling",
    "1xbet.com": "gambling",
    "22bet.com": "gambling",
    "melbet.com": "gambling",
    "betsson.com": "gambling",
    # --- gaming ---
    "unity3d.com": "gaming",
    "unity.com": "gaming",
    "steampowered.com": "gaming",
    "epicgames.com": "gaming",
    "roblox.com": "gaming",
    "twitch.tv": "gaming",
    "battlenet.com": "gaming",
    "blizzard.com": "gaming",
    "ea.com": "gaming",
    "ubisoft.com": "gaming",
    "gameloft.com": "gaming",
    "king.com": "gaming",
    "supercell.com": "gaming",
    "playtika.com": "gaming",
    "agora.io": "gaming",
    "photonengine.com": "gaming",
    # --- ad / tracking ---
    "doubleclick.net": "ad",
    "googletagmanager.com": "ad",
    "googlesyndication.com": "ad",
    "adnxs.com": "ad",
    "adsrvr.org": "ad",
    "rubiconproject.com": "ad",
    "openx.net": "ad",
    "pubmatic.com": "ad",
    "criteo.com": "ad",
    "taboola.com": "ad",
    "outbrain.com": "ad",
    "scorecardresearch.com": "ad",
    "quantserve.com": "ad",
    "moatads.com": "ad",
    "amazon-adsystem.com": "ad",
    "bing.com": "ad",
    "yahoo.com": "ad",
    "yandex.ru": "ad",
    "baidu.com": "ad",
    "hotjar.com": "ad",
    "segment.com": "ad",
    "mixpanel.com": "ad",
    "amplitude.com": "ad",
    "newrelic.com": "ad",
    "clarity.ms": "ad",
    "facebook.net": "ad",
    "facebook.com": "ad",
    "connect.facebook.net": "ad",
    "twitter.com": "ad",
    "analytics.google.com": "ad",
    "google-analytics.com": "ad",
    # --- payment ---
    "stripe.com": "payment",
    "paypal.com": "payment",
    "braintreegateway.com": "payment",
    "square.com": "payment",
    "adyen.com": "payment",
    "checkout.com": "payment",
    "klarna.com": "payment",
    "afterpay.com": "payment",
    "wise.com": "payment",
    "skrill.com": "payment",
    "neteller.com": "payment",
    "coinbase.com": "payment",
    "binance.com": "payment",
    "okx.com": "payment",
    "bitpay.com": "payment",
    "payu.com": "payment",
    "razorpay.com": "payment",
    "alipay.com": "payment",
    "wechat.com": "payment",
    # --- cdn / infrastructure ---
    "cloudflare.com": "cdn",
    "cloudflare.net": "cdn",
    "cloudfront.net": "cdn",
    "fastly.net": "cdn",
    "akamaihd.net": "cdn",
    "akamai.net": "cdn",
    "edgesuite.net": "cdn",
    "edgekey.net": "cdn",
    "jsdelivr.net": "cdn",
    "unpkg.com": "cdn",
    "cdnjs.cloudflare.com": "cdn",
    "googleapis.com": "cdn",
    "gstatic.com": "cdn",
    "bootstrapcdn.com": "cdn",
    "jquery.com": "cdn",
    "s3.amazonaws.com": "cdn",
    "amazonaws.com": "cdn",
    "azure.com": "cdn",
    "azureedge.net": "cdn",
    "msecnd.net": "cdn",
    "stackpathcdn.com": "cdn",
    "b-cdn.net": "cdn",
    "bunnycdn.com": "cdn",
    "twimg.com": "cdn",
    "fbcdn.net": "cdn",
    "instagram.com": "cdn",
    "wp.com": "cdn",
    "wordpress.com": "cdn",
}

KEYWORDS: dict[str, list[str]] = {
    "gambling": [
        "bet", "bets", "betting", "casino", "poker", "slots", "lottery",
        "lotto", "bingo", "wager", "odds", "sportsbook", "gambl",
        "jackpot", "roulette", "blackjack", "sportbet", "888",
    ],
    "gaming": [
        "game", "games", "gaming", "esport", "steam", "play", "gamer",
        "rpg", "mmo", "fps", "guild", "clan", "quest", "level",
    ],
    "ad": [
        "ads", "advert", "analytics", "tracker", "tracking", "pixel",
        "beacon", "metric", "stat", "measure", "tag", "click", "impression",
        "audience", "retarget", "dsp", "ssp", "rtb",
    ],
    "payment": [
        "pay", "payment", "cash", "wallet", "crypto", "coin", "finance",
        "fintech", "bank", "transfer", "checkout", "billing",
    ],
    "cdn": [
        "cdn", "static", "assets", "media", "cache", "edge", "deliver",
        "content", "storage", "bucket", "blob",
    ],
}


def _etld1(domain: str) -> str:
    parts = domain.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else domain


def classify_domain(domain: str) -> str:
    if not domain:
        return "other"

    # exact match
    if domain in KNOWN_DOMAINS:
        return KNOWN_DOMAINS[domain]

    # eTLD+1 match (e.g. "sub.bet365.com" → "bet365.com")
    base = _etld1(domain)
    if base in KNOWN_DOMAINS:
        return KNOWN_DOMAINS[base]

    # keyword scan on full domain string (lowercased, dots/hyphens as separators)
    lower = domain.lower()
    for category, keywords in KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return category

    return "other"


class DomainClassifier:
    """Thin wrapper kept for interface compatibility with main.py / aggregate.py."""

    def __init__(self, cache_path: str = "", **_kwargs):
        self.cache: dict[str, str] = {}

    def classify(self, domains: list[str]) -> dict[str, str]:
        for d in domains:
            if d not in self.cache:
                self.cache[d] = classify_domain(d)
        return {d: self.cache[d] for d in domains}
