import os
import hmac
import hashlib
import json
import requests
from datetime import datetime, timezone

ACCESS_KEY  = os.getenv("AMAZON_ACCESS_KEY", "")
SECRET_KEY  = os.getenv("AMAZON_SECRET_KEY", "")
PARTNER_TAG = os.getenv("AMAZON_PARTNER_TAG", "")
HOST        = os.getenv("AMAZON_HOST", "webservices.amazon.fr")
REGION      = os.getenv("AMAZON_REGION", "eu-west-1")
SERVICE     = "ProductAdvertisingAPI"
ENDPOINT    = f"https://{HOST}/paapi5/searchitems"


def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _signing_key(date_stamp: str) -> bytes:
    k = _sign(f"AWS4{SECRET_KEY}".encode("utf-8"), date_stamp)
    k = _sign(k, REGION)
    k = _sign(k, SERVICE)
    return _sign(k, "aws4_request")


def search(query: str, limit: int = 10) -> list:
    if not ACCESS_KEY or not SECRET_KEY or not PARTNER_TAG:
        return []

    now = datetime.now(timezone.utc)
    amz_date   = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")

    payload = {
        "Keywords":    query,
        "PartnerTag":  PARTNER_TAG,
        "PartnerType": "Associates",
        "Resources": [
            "ItemInfo.Title",
            "Images.Primary.Medium",
            "Offers.Listings.Price",
        ],
        "SearchIndex": "All",
        "ItemCount":   min(limit, 10),
    }
    body = json.dumps(payload, separators=(",", ":"))
    body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()

    canonical = "\n".join([
        "POST",
        "/paapi5/searchitems",
        "",
        "content-encoding:amz-1.0",
        "content-type:application/json; charset=utf-8",
        f"host:{HOST}",
        f"x-amz-date:{amz_date}",
        "x-amz-target:com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems",
        "",
        "content-encoding;content-type;host;x-amz-date;x-amz-target",
        body_hash,
    ])

    credential_scope = f"{date_stamp}/{REGION}/{SERVICE}/aws4_request"
    string_to_sign = "\n".join([
        "AWS4-HMAC-SHA256",
        amz_date,
        credential_scope,
        hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    ])

    sig = hmac.new(_signing_key(date_stamp), string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    auth = (
        f"AWS4-HMAC-SHA256 Credential={ACCESS_KEY}/{credential_scope}, "
        "SignedHeaders=content-encoding;content-type;host;x-amz-date;x-amz-target, "
        f"Signature={sig}"
    )

    headers = {
        "Content-Encoding": "amz-1.0",
        "Content-Type":     "application/json; charset=utf-8",
        "Host":             HOST,
        "X-Amz-Date":       amz_date,
        "X-Amz-Target":     "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems",
        "Authorization":    auth,
    }

    r = requests.post(ENDPOINT, headers=headers, data=body, timeout=15)
    r.raise_for_status()

    items = []
    for it in r.json().get("SearchResult", {}).get("Items", [])[:limit]:
        title = it.get("ItemInfo", {}).get("Title", {}).get("DisplayValue", "")
        url   = it.get("DetailPageURL", "")
        image = it.get("Images", {}).get("Primary", {}).get("Medium", {}).get("URL", "")
        price = ""
        listings = it.get("Offers", {}).get("Listings", [])
        if listings:
            price = listings[0].get("Price", {}).get("DisplayAmount", "")
        items.append({
            "title":     title,
            "price":     price,
            "currency":  "EUR",
            "image":     image,
            "url":       url,
            "condition": "Neuf",
        })
    return items
