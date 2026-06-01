from typing import Any

import httpx

from app.config import Settings
from app.providers.base import ProductCandidate, float_value


class RainforestProvider:
    """Licensed Amazon deal feed backed by Traject Data's Rainforest API."""

    name = "rainforest"

    def __init__(self, settings: Settings):
        self.settings = settings
        self._deals: list[dict[str, Any]] | None = None

    async def fetch(self, category: str) -> list[ProductCandidate]:
        if self._deals is None:
            params = {
                "api_key": self.settings.rainforest_api_key,
                "type": "deals",
                "amazon_domain": self.settings.rainforest_amazon_domain,
                "max_page": self.settings.rainforest_deals_max_page,
            }
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                response = await client.get("https://api.rainforestapi.com/request", params=params)
                response.raise_for_status()
                payload = response.json()
            if not payload.get("request_info", {}).get("success", False):
                raise RuntimeError(payload.get("request_info", {}).get("message", "Rainforest API request failed"))
            self._deals = payload.get("deals_results", [])
        return [self._map(item, category) for item in self._deals if self._category_matches(item, category)]

    def _map(self, item: dict[str, Any], category: str) -> ProductCandidate:
        return ProductCandidate(
            source=self.name,
            external_id=str(item.get("asin") or item.get("deal_id") or item.get("link", "")),
            category=category,
            name=str(item.get("title") or "Untitled Amazon deal"),
            image_url=str(item.get("image") or ""),
            current_price=self._price(item.get("deal_price") or item.get("current_price")),
            original_price=self._price(item.get("list_price")),
            store_name="Amazon India",
            product_url=str(item.get("link") or item.get("deals_link") or ""),
            rating=float_value(item.get("rating")) or 0,
            popularity=min(float_value(item.get("ratings_total")) or 0, 100),
        )

    @staticmethod
    def _price(value: Any) -> float | None:
        if isinstance(value, dict):
            return float_value(value.get("value"))
        return float_value(value)

    @staticmethod
    def _category_matches(item: dict[str, Any], category: str) -> bool:
        haystack = f"{item.get('title', '')} {item.get('description', '')}".lower()
        terms = {
            "Electronics": ("electronic", "phone", "laptop", "charger", "headphone", "speaker", "camera"),
            "Fashion": ("shirt", "dress", "shoe", "sandal", "jean", "jacket", "watch", "bag"),
            "Home & Kitchen": ("home", "kitchen", "cook", "mixer", "bottle", "storage", "furniture"),
            "Beauty": ("beauty", "skin", "hair", "makeup", "cream", "serum", "shampoo"),
            "Sports": ("sport", "fitness", "gym", "yoga", "cycle", "running"),
            "Books": ("book", "paperback", "hardcover", "novel"),
        }
        return any(term in haystack for term in terms.get(category, (category.lower(),)))
