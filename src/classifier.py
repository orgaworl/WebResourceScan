"""
Rule-based domain classifier. No LLM required.

Matching order:
1. Exact domain match in KNOWN_DOMAINS
2. eTLD+1 match in KNOWN_DOMAINS
3. Keyword scan against the full domain string
4. Fallback: "other"

Categories:
  gambling  — betting / casino infrastructure
  gaming    — game engines, platforms, CDN
  ad        — advertising networks, real-time bidding
  analytics — analytics, A/B testing, heatmaps (distinct from ad)
  social    — social network SDKs and embeds
  payment   — payment gateways, crypto exchanges
  cdn       — content delivery, cloud storage, general infrastructure
  other     — unrecognised
"""

VALID_CATEGORIES = {"gambling", "gaming", "ad", "analytics", "social", "payment", "cdn", "other"}

KNOWN_DOMAINS: dict[str, str] = {
    # ── gambling ─────────────────────────────────────────────────────────────
    "bet365.com": "gambling",
    "betway.com": "gambling",
    "draftkings.com": "gambling",
    "fanduel.com": "gambling",
    "pokerstars.com": "gambling",
    "888casino.com": "gambling",
    "888holdings.com": "gambling",
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
    "coral.co.uk": "gambling",
    "paddypower.com": "gambling",
    "skybet.com": "gambling",
    "pointsbet.com": "gambling",
    "superbet.com": "gambling",
    "marathonbet.com": "gambling",
    "betmgm.com": "gambling",
    "caesarssportsbook.com": "gambling",
    "sportsbettingdime.com": "gambling",
    # ── gaming ────────────────────────────────────────────────────────────────
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
    "nexon.com": "gaming",
    "ncsoft.com": "gaming",
    "riot.com": "gaming",
    "riotgames.com": "gaming",
    "leagueoflegends.com": "gaming",
    "valvesoftware.com": "gaming",
    "activision.com": "gaming",
    "nintendo.com": "gaming",
    "xbox.com": "gaming",
    "playstation.com": "gaming",
    "gog.com": "gaming",
    "itch.io": "gaming",
    "playfab.com": "gaming",
    "gameliftstreaming.com": "gaming",
    # ── ad / real-time-bidding ────────────────────────────────────────────────
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
    "advertising.com": "ad",
    "media.net": "ad",
    "indexexchange.com": "ad",
    "appnexus.com": "ad",
    "smartadserver.com": "ad",
    "sovrn.com": "ad",
    "33across.com": "ad",
    "liveintent.com": "ad",
    "teads.tv": "ad",
    "tripadvisor.com": "ad",
    "sharethrough.com": "ad",
    "adroll.com": "ad",
    "zemanta.com": "ad",
    "bidswitch.net": "ad",
    "triplelift.com": "ad",
    "yieldmo.com": "ad",
    "spotxchange.com": "ad",
    "bing.com": "ad",
    "yahoo.com": "ad",
    "yandex.ru": "ad",
    "yandex.net": "ad",
    "baidu.com": "ad",
    # ── analytics / measurement ───────────────────────────────────────────────
    "google-analytics.com": "analytics",
    "analytics.google.com": "analytics",
    "hotjar.com": "analytics",
    "segment.com": "analytics",
    "mixpanel.com": "analytics",
    "amplitude.com": "analytics",
    "newrelic.com": "analytics",
    "clarity.ms": "analytics",
    "fullstory.com": "analytics",
    "heap.io": "analytics",
    "mouseflow.com": "analytics",
    "logrocket.com": "analytics",
    "contentsquare.com": "analytics",
    "dynatrace.com": "analytics",
    "pingdom.com": "analytics",
    "datadog-browser-agent.com": "analytics",
    "datadoghq.com": "analytics",
    "sentry.io": "analytics",
    "bugsnag.com": "analytics",
    "rollbar.com": "analytics",
    "optimizely.com": "analytics",
    "abtasty.com": "analytics",
    "vwo.com": "analytics",
    "crazyegg.com": "analytics",
    "chartbeat.com": "analytics",
    "parsely.com": "analytics",
    "intercom.io": "analytics",
    "pendo.io": "analytics",
    "appsflyer.com": "analytics",
    "adjust.com": "analytics",
    "branch.io": "analytics",
    "onesignal.com": "analytics",
    # ── social ────────────────────────────────────────────────────────────────
    "facebook.net": "social",
    "facebook.com": "social",
    "connect.facebook.net": "social",
    "fbcdn.net": "social",
    "instagram.com": "social",
    "twitter.com": "social",
    "twimg.com": "social",
    "t.co": "social",
    "linkedin.com": "social",
    "licdn.com": "social",
    "pinterest.com": "social",
    "pinimg.com": "social",
    "tiktok.com": "social",
    "tiktokcdn.com": "social",
    "snapchat.com": "social",
    "sc-cdn.net": "social",
    "reddit.com": "social",
    "redd.it": "social",
    "redditmedia.com": "social",
    "redditstatic.com": "social",
    "whatsapp.net": "social",
    "whatsapp.com": "social",
    "telegram.org": "social",
    "discord.com": "social",
    "discordapp.com": "social",
    "youtube.com": "social",
    "ytimg.com": "social",
    "googlevideo.com": "social",
    # ── payment ───────────────────────────────────────────────────────────────
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
    "revolut.com": "payment",
    "trustly.com": "payment",
    "paysafecard.com": "payment",
    "worldpay.com": "payment",
    "cybersource.com": "payment",
    "2checkout.com": "payment",
    "mollie.com": "payment",
    "paysafe.com": "payment",
    # ── cdn / infrastructure ──────────────────────────────────────────────────
    "cloudflare.com": "cdn",
    "cloudflare.net": "cdn",
    "cloudfront.net": "cdn",
    "fastly.net": "cdn",
    "fastlylb.net": "cdn",
    "akamaihd.net": "cdn",
    "akamai.net": "cdn",
    "akamaized.net": "cdn",
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
    "wp.com": "cdn",
    "wordpress.com": "cdn",
    "wp-rocket.me": "cdn",
    "imperva.com": "cdn",
    "incapdns.net": "cdn",
    "sucuri.net": "cdn",
    "edgecastcdn.net": "cdn",
    "llnwd.net": "cdn",
    "hwcdn.net": "cdn",
    "limelight.com": "cdn",
    "level3.net": "cdn",
    "vo.msecnd.net": "cdn",
    "cdn77.com": "cdn",
    "cdn77.org": "cdn",
    "digitaloceanspaces.com": "cdn",
    "storage.googleapis.com": "cdn",
    "r2.dev": "cdn",
    # ── consent / privacy management ─────────────────────────────────────────
    "onetrust.com": "analytics",
    "cookielaw.org": "analytics",
    "cookiebot.com": "analytics",
    "usercentrics.eu": "analytics",
    "usercentrics.de": "analytics",
    "privacymanager.io": "analytics",
    "consent.google.com": "analytics",
    "consentcdn.cookiebot.com": "analytics",
    # ── fonts / icon CDNs ─────────────────────────────────────────────────────
    "fontawesome.com": "cdn",
    "font-awesome.io": "cdn",
    "fonts.gstatic.com": "cdn",
    # ── identity / SSO ────────────────────────────────────────────────────────
    "accounts.google.com": "analytics",
    "appleid.apple.com": "analytics",
    "hcaptcha.com": "cdn",
    # ── Google general (search surface, maps, etc.) ───────────────────────────
    "google.com": "ad",
    # ── RTB / programmatic ad infrastructure ─────────────────────────────────
    "adform.net": "ad",
    "demdex.net": "ad",
    "3lift.com": "ad",
    "id5-sync.com": "ad",
    "eyeota.net": "ad",
    "crwdcntrl.net": "ad",
    "semasio.net": "ad",
    "casalemedia.com": "ad",
    "2mdn.net": "ad",
    "everesttech.net": "ad",
    "mxpnl.com": "analytics",
    "btloader.com": "ad",
    "dns-finder.com": "ad",
    # ── video / streaming CDN infrastructure ─────────────────────────────────
    "youtube-nocookie.com": "social",
    "bamgrid.com": "cdn",
    "speedysurfcdn.net": "cdn",
    "wknd.ai": "analytics",
    # ── error monitoring / APM ────────────────────────────────────────────────
    "bugsnag.net": "analytics",
    "newrelic.com": "analytics",
    "nr-data.net": "analytics",
    "datadog-browser-agent.com": "analytics",
    "browser-intake-datadoghq.com": "analytics",
}

KEYWORDS: dict[str, list[str]] = {
    "gambling": [
        "bet", "bets", "betting", "casino", "poker", "slots", "lottery",
        "lotto", "bingo", "wager", "odds", "sportsbook", "gambl",
        "jackpot", "roulette", "blackjack", "sportbet", "888",
    ],
    "gaming": [
        "game", "games", "gaming", "esport", "steam", "gamer",
        "rpg", "mmo", "fps", "guild", "clan", "quest",
    ],
    "ad": [
        "advert", "adserv", "adtech", "adexchange", "adnetwork",
        "rtb", "dsp", "ssp", "bidder", "prebid",
        "retarget", "impression", "adslot", "adsystem",
    ],
    "analytics": [
        "analytics", "tracker", "tracking", "pixel", "beacon",
        "metric", "stat", "measure", "tag", "telemetry",
        "heatmap", "session", "replay", "monitor", "apm",
        "audience", "insight", "intelligence",
    ],
    "social": [
        "social", "share", "tweet", "like", "comment", "follow",
        "login", "oauth", "auth", "connect",
    ],
    "payment": [
        "pay", "payment", "cash", "wallet", "crypto", "coin", "finance",
        "fintech", "bank", "transfer", "checkout", "billing",
    ],
    "cdn": [
        "cdn", "static", "assets", "cache", "edge", "deliver",
        "storage", "bucket", "blob", "origin", "s3", "gcs",
    ],
}


def _etld1(domain: str) -> str:
    parts = domain.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else domain


def classify_domain(domain: str) -> str:
    if not domain:
        return "other"

    if domain in KNOWN_DOMAINS:
        return KNOWN_DOMAINS[domain]

    base = _etld1(domain)
    if base in KNOWN_DOMAINS:
        return KNOWN_DOMAINS[base]

    lower = domain.lower()
    for category, keywords in KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return category

    return "other"


class DomainClassifier:
    """Thin wrapper for classify_domain with an optional cross-process shared cache."""

    def __init__(self, cache_path: str = "", shared_cache=None, **_kwargs):
        self.cache: dict = shared_cache if shared_cache is not None else {}

    def classify(self, domains: list[str]) -> dict[str, str]:
        for d in domains:
            if d not in self.cache:
                self.cache[d] = classify_domain(d)
        return {d: self.cache[d] for d in domains}
