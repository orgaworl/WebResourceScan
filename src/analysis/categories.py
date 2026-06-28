import re


def build_site_category_map(urls_path: str = "urls.txt") -> dict[str, str]:
    """Parse urls.txt and return a dict mapping eTLD+1 → site category."""
    result: dict[str, str] = {}
    current_cat = "unknown"
    cat_re = re.compile(r"#.*\((\w[\w-]*)\)")
    with open(urls_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            m = cat_re.search(line)
            if m:
                current_cat = m.group(1)
            elif line.startswith("https://"):
                host = line.split("//", 1)[1].split("/")[0]
                etld1 = ".".join(host.split(".")[-2:])
                if etld1 not in result:
                    result[etld1] = current_cat
    return result


def get_site_category(url: str, cat_map: dict[str, str]) -> str:
    """Return the site category for a URL, or 'unknown'."""
    host = url.split("//", 1)[-1].split("/")[0]
    etld1 = ".".join(host.split(".")[-2:])
    return cat_map.get(etld1, "unknown")
