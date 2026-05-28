import os
import time
import base64
import requests

EBAY_CLIENT_ID     = os.getenv("EBAY_CLIENT_ID")
EBAY_CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET")
EPN_CAMPAIGN_ID    = os.getenv("EPN_CAMPAIGN_ID", "")
MARKETPLACE        = os.getenv("EBAY_MARKETPLACE", "EBAY_FR")

_cache = {"token": None, "expires_at": 0}


def get_token() -> str:
    if _cache["token"] and time.time() < _cache["expires_at"] - 60:
        return _cache["token"]
    creds = base64.b64encode(f"{EBAY_CLIENT_ID}:{EBAY_CLIENT_SECRET}".encode()).decode()
    r = requests.post(
        "https://api.ebay.com/identity/v1/oauth2/token",
        headers={
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data={
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope"
        },
        timeout=10
    )
    r.raise_for_status()
    data = r.json()
    _cache["token"] = data["access_token"]
    _cache["expires_at"] = time.time() + data["expires_in"]
    return _cache["token"]


def search(query: str, limit: int = 24) -> list:
    r = requests.get(
        "https://api.ebay.com/buy/browse/v1/item_summary/search",
        headers={
            "Authorization": f"Bearer {get_token()}",
            "X-EBAY-C-MARKETPLACE-ID": MARKETPLACE,
            "X-EBAY-C-ENDUSERCTX": f"affiliateCampaignId={EPN_CAMPAIGN_ID}",
        },
        params={"q": query, "limit": limit, "sort": "bestMatch"},
        timeout=10
    )
    r.raise_for_status()
    items = []
    for it in r.json().get("itemSummaries", []):
        price = it.get("price", {})
        items.append({
            "title":     it.get("title", ""),
            "price":     price.get("value", ""),
            "currency":  price.get("currency", "EUR"),
            "image":     it.get("image", {}).get("imageUrl", ""),
            "url":       _affiliate(it.get("itemWebUrl", "")),
            "condition": it.get("condition", ""),
        })
    return items


def _affiliate(url: str) -> str:
    if not url or not EPN_CAMPAIGN_ID:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}mkcid=1&mkrid=709-53476-19255-0&siteid=71&campid={EPN_CAMPAIGN_ID}&toolid=10001&mkevt=1"
