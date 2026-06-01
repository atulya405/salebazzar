import hashlib

import httpx

from app.config import Settings
from app.providers.base import ProductCandidate, first, float_value, list_payload


class GenericCatalogProvider:
    name = "generic"
    api_key_param = "api_key"

    def __init__(self, settings: Settings, api_key: str, search_url: str):
        self.settings = settings
        self.api_key = api_key
        self.search_url = search_url

    async def fetch(self, category: str) -> list[ProductCandidate]:
        params = {"query": category, self.api_key_param: self.api_key}
        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            response = await client.get(self.search_url, params=params)
            response.raise_for_status()
            items = list_payload(response.json())
        return [self._map(item, category) for item in items[: self.settings.max_results_per_category]]

    def _map(self, item: dict, category: str) -> ProductCandidate:
        url = str(first(item, "product_url", "url", "link"))
        external_id = str(first(item, "id", "product_id", "sku", default=""))
        if not external_id:
            external_id = hashlib.sha256(f"{self.name}:{url}".encode()).hexdigest()
        return ProductCandidate(
            source=self.name,
            external_id=external_id,
            category=category,
            name=str(first(item, "name", "title", "product_name", default="Untitled product")),
            image_url=str(first(item, "image", "image_url", "thumbnail")),
            current_price=float_value(first(item, "current_price", "price", "sale_price")),
            original_price=float_value(first(item, "original_price", "mrp", "list_price")),
            store_name=str(first(item, "store", "store_name", "merchant", default="Unknown store")),
            product_url=url,
            rating=float_value(first(item, "rating")) or 0,
            popularity=min(float_value(first(item, "popularity", "reviews", "review_count")) or 0, 100),
        )

