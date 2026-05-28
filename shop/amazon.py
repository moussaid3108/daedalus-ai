import os
import paapi5_python_sdk as paapi

ACCESS_KEY  = os.getenv("AMAZON_ACCESS_KEY")
SECRET_KEY  = os.getenv("AMAZON_SECRET_KEY")
PARTNER_TAG = os.getenv("AMAZON_PARTNER_TAG")
HOST        = os.getenv("AMAZON_HOST", "webservices.amazon.fr")
REGION      = os.getenv("AMAZON_REGION", "eu-west-1")


def _api():
    cfg = paapi.Configuration()
    cfg.access_key = ACCESS_KEY
    cfg.secret_key = SECRET_KEY
    cfg.host = HOST
    cfg.region = REGION
    return paapi.DefaultApi(paapi.ApiClient(cfg))


def search(query: str, limit: int = 10) -> list:
    req = paapi.SearchItemsRequest(
        partner_tag=PARTNER_TAG,
        partner_type=paapi.PartnerType.ASSOCIATES,
        keywords=query,
        item_count=min(limit, 10),
        resources=[
            paapi.SearchItemsResource.ITEMINFO_TITLE,
            paapi.SearchItemsResource.IMAGES_PRIMARY_MEDIUM,
            paapi.SearchItemsResource.OFFERS_LISTINGS_PRICE,
        ]
    )
    resp = _api().search_items(req)
    items = []
    for it in (resp.search_result.items or []):
        price = ""
        if it.offers and it.offers.listings and it.offers.listings[0].price:
            price = it.offers.listings[0].price.display_amount or ""
        image = ""
        if it.images and it.images.primary and it.images.primary.medium:
            image = it.images.primary.medium.url or ""
        title = ""
        if it.item_info and it.item_info.title:
            title = it.item_info.title.display_value or ""
        items.append({
            "title":     title,
            "price":     price,
            "currency":  "EUR",
            "image":     image,
            "url":       it.detail_page_url or "",
            "condition": "Neuf",
        })
    return items
