import os
import requests

USERNAME     = os.getenv("BOOKING_USERNAME")
PASSWORD     = os.getenv("BOOKING_PASSWORD")
AFFILIATE_ID = os.getenv("BOOKING_AFFILIATE_ID", "")
BASE_URL     = "https://distribution-xml.booking.com/2.0/json"


def search(destination: str, limit: int = 10) -> list:
    r = requests.get(
        f"{BASE_URL}/hotels",
        auth=(USERNAME, PASSWORD),
        params={
            "search_string": destination,
            "rows":          min(limit, 100),
            "languagecode":  "fr",
            "currency":      "EUR",
            "extras":        "hotel_info,hotel_photos",
        },
        timeout=15
    )
    r.raise_for_status()
    items = []
    for h in r.json().get("result", [])[:limit]:
        price = h.get("min_total_price", "")
        stars = h.get("stars", "")
        items.append({
            "title":     h.get("name", ""),
            "price":     str(price) if price else "",
            "currency":  "EUR",
            "image":     h.get("main_photo_url", ""),
            "url":       _affiliate(h.get("url", "")),
            "condition": f"{'⭐' * int(stars)} {stars} étoiles" if stars else "",
            "location":  h.get("city", ""),
        })
    return items


def _affiliate(url: str) -> str:
    if not url or not AFFILIATE_ID:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}aid={AFFILIATE_ID}"
