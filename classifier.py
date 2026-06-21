import json
import anthropic

VALID_CATEGORIES = {"gambling", "gaming", "ad", "payment", "cdn", "other"}
BATCH_SIZE = 50

_PROMPT_TEMPLATE = """Classify each domain into exactly one of these categories: gambling, gaming, ad, payment, cdn, other.

"gambling" = online betting, casinos, lottery sites
"gaming" = video games, game engines, game SDKs, esports
"ad" = advertising networks, tracking pixels, analytics
"payment" = payment gateways, fintech, crypto exchanges
"cdn" = CDN providers, cloud infrastructure, hosting
"other" = anything that doesn't fit the above

Respond with ONLY a JSON object mapping each domain to its category. No explanation. Example:
{{"bet365.com": "gambling", "unity3d.com": "gaming", "doubleclick.net": "ad"}}

Domains to classify:
{domains}"""


class DomainClassifier:
    def __init__(self, cache_path: str):
        self.cache_path = cache_path
        self.cache: dict[str, str] = {}
        self.client = anthropic.Anthropic()
        self._load_cache()

    def _load_cache(self):
        try:
            with open(self.cache_path) as f:
                self.cache = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.cache = {}

    def _save_cache(self):
        with open(self.cache_path, "w") as f:
            json.dump(self.cache, f, indent=2)

    def _call_llm(self, domains: list[str]) -> dict[str, str]:
        prompt = _PROMPT_TEMPLATE.format(domains="\n".join(domains))
        for attempt in range(2):
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            try:
                result = json.loads(text)
                return {
                    d: (v if v in VALID_CATEGORIES else "other")
                    for d, v in result.items()
                }
            except (json.JSONDecodeError, AttributeError):
                if attempt == 1:
                    return {d: "other" for d in domains}
        return {d: "other" for d in domains}

    def classify(self, domains: list[str]) -> dict[str, str]:
        uncached = [d for d in domains if d not in self.cache]
        for i in range(0, len(uncached), BATCH_SIZE):
            batch = uncached[i : i + BATCH_SIZE]
            result = self._call_llm(batch)
            self.cache.update(result)
            self._save_cache()
        return {d: self.cache.get(d, "other") for d in domains}
