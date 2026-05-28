import os
import requests

API_KEY    = os.getenv("FNAC_API_KEY")
PARTNER_ID = os.getenv("FNAC_PARTNER_ID", "")
BASE_URL   = "https://api.fnac.com/v1"


def search(query: str, limit: int = 24) -> list:
    r = requests.get(
        f"{BASE_URL}/products/search",
        headers={"Authorization": f"Bearer {API_KEY}"},
        params={"q": query, "limit": limit, "lang": "fr", "currency": "EUR"},
        timeout=10
    )
    r.raise_for_status()
    items = []
    for it in r.json().get("products", []):
        items.append({
            "title":     it.get("title", ""),
            "price":     str(it.get("price", "")),
            "currency":  "EUR",
            "image":     it.get("imageUrl", ""),
            "url":       _affiliate(it.get("url", "")),
            "condition": it.get("category", ""),
        })
    return items


def _affiliate(url: str) -> str:
    if not url or not PARTNER_ID:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}Origin={PARTNER_ID}"
