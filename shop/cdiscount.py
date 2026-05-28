import os
import requests

API_KEY    = os.getenv("CDISCOUNT_API_KEY")
PARTNER_ID = os.getenv("CDISCOUNT_PARTNER_ID")
BASE_URL   = "https://partners.api.cdiscount.com/v1"


def search(query: str, limit: int = 24) -> list:
    r = requests.get(
        f"{BASE_URL}/products",
        headers={"Authorization": f"Bearer {API_KEY}"},
        params={"q": query, "limit": limit, "lang": "fr"},
        timeout=10
    )
    r.raise_for_status()
    items = []
    for it in r.json().get("products", []):
        items.append({
            "title":     it.get("name", ""),
            "price":     str(it.get("price", "")),
            "currency":  "EUR",
            "image":     it.get("imageUrl", ""),
            "url":       _affiliate(it.get("url", "")),
            "condition": it.get("condition", "Neuf"),
        })
    return items


def _affiliate(url: str) -> str:
    if not url or not PARTNER_ID:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}cm_mmc=affi-_-{PARTNER_ID}-_-SC"
