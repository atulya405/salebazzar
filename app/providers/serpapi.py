import hashlib

import httpx

from app.config import Settings
from app.providers.base import ProductCandidate, first, float_value


class SerpApiProvider:
    name = "serpapi"

    def __init__(self, settings: Settings):
        self.settings = settings

    async def fetch(self, category: str) -> list[ProductCandidate]:
        params = {
            "engine": "google_shopping",
            "q": f"{category} deals India",
            "api_key": self.settings.serpapi_key,
            "num": self.settings.max_results_per_category,
            "gl": self.settings.serpapi_country,
            "hl": self.settings.serpapi_language,
            "google_domain": self.settings.serpapi_google_domain,
        }
        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            response = await client.get("https://serpapi.com/search.json", params=params)
            response.raise_for_status()
            results = response.json().get("shopping_results", [])
        products = []
        for item in results:
            url = first(item, "product_link", "link")
            external_id = str(first(item, "product_id", default="")) or hashlib.sha256(url.encode()).hexdigest()
            products.append(
                ProductCandidate(
                    source=self.name,
                    external_id=external_id,
                    category=category,
                    name=str(first(item, "title", default="Untitled product")),
                    image_url=str(first(item, "thumbnail")),
                    current_price=float_value(first(item, "extracted_price", "price")),
                    original_price=float_value(first(item, "extracted_old_price", "old_price")),
                    store_name=str(first(item, "source", default="Unknown store")),
                    product_url=str(url),
                    rating=float_value(first(item, "rating")) or 0,
                    popularity=min(float_value(first(item, "reviews")) or 0, 100),
                )
            )
        return products
