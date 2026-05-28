import os
import requests
from datetime import datetime, timedelta

API_KEY      = os.getenv("SKYSCANNER_API_KEY")
PARTNER_ID   = os.getenv("SKYSCANNER_PARTNER_ID", "")
BASE_URL     = "https://partners.api.skyscanner.net/apiservices/v3"
DEFAULT_FROM = os.getenv("SKYSCANNER_DEFAULT_ORIGIN", "CDG")


def _iata(place: str) -> str:
    if len(place) == 3 and place.isalpha():
        return place.upper()
    r = requests.post(
        f"{BASE_URL}/autosuggest/flights",
        headers={"x-api-key": API_KEY, "Content-Type": "application/json"},
        json={
            "query": {
                "market": "FR", "locale": "fr-FR",
                "searchTerm": place,
                "includedEntityTypes": ["PLACE_TYPE_AIRPORT", "PLACE_TYPE_CITY"],
            }
        },
        timeout=10
    )
    r.raise_for_status()
    places = r.json().get("places", [])
    return places[0].get("iataCode", "") if places else ""


def search(destination: str, limit: int = 10) -> list:
    dest = _iata(destination)
    if not dest:
        return []

    depart = datetime.now() + timedelta(days=30)
    r = requests.post(
        f"{BASE_URL}/flights/live/search/create",
        headers={"x-api-key": API_KEY, "Content-Type": "application/json"},
        json={
            "query": {
                "market": "FR", "locale": "fr-FR", "currency": "EUR",
                "queryLegs": [{
                    "originPlaceId":      {"iata": DEFAULT_FROM},
                    "destinationPlaceId": {"iata": dest},
                    "date": {
                        "year":  depart.year,
                        "month": depart.month,
                        "day":   depart.day,
                    },
                }],
                "adults": 1,
                "cabinClass": "CABIN_CLASS_ECONOMY",
            }
        },
        timeout=15
    )
    r.raise_for_status()
    token = r.json().get("sessionToken", "")
    if not token:
        return []

    poll = requests.get(
        f"{BASE_URL}/flights/live/search/poll/{token}",
        headers={"x-api-key": API_KEY},
        timeout=15
    )
    poll.raise_for_status()
    content  = poll.json().get("content", {}).get("results", {})
    legs     = content.get("legs", {})
    carriers = content.get("carriers", {})

    items = []
    for itin in list(content.get("itineraries", {}).values())[:limit]:
        pricing     = (itin.get("pricingOptions") or [{}])[0]
        price_minor = pricing.get("price", {}).get("amount", "")
        price_eur   = str(int(int(price_minor) / 100)) if price_minor else ""
        deeplink    = (pricing.get("items") or [{}])[0].get("deeplink", "")

        leg_id  = (itin.get("legIds") or [""])[0]
        leg     = legs.get(leg_id, {})
        dur     = leg.get("durationInMinutes", 0)
        stops   = leg.get("stopCount", 0)
        cid     = (leg.get("marketingCarrierIds") or [""])[0]
        carrier = carriers.get(cid, {})

        items.append({
            "title":     f"{DEFAULT_FROM} -> {dest}  .  {carrier.get('name', '')}",
            "price":     price_eur,
            "currency":  "EUR",
            "image":     carrier.get("logoUrl", ""),
            "url":       _affiliate(deeplink),
            "condition": f"{dur // 60}h{dur % 60:02d}  .  {'Direct' if not stops else f'{stops} escale(s)'}",
        })
    return items


def _affiliate(url: str) -> str:
    if not url or not PARTNER_ID:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}associateid={PARTNER_ID}"
