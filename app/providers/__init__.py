from app.config import Settings
from app.providers.base import ProductCandidate, ProductProvider
from app.providers.datayuge import DataYugeProvider
from app.providers.pricesapi import PricesApiProvider


def configured_providers(settings: Settings) -> list[ProductProvider]:
    providers: list[ProductProvider] = []
    if settings.datayuge_enabled and settings.datayuge_api_key and settings.datayuge_search_url:
        providers.append(DataYugeProvider(settings))
    if settings.pricesapi_enabled and settings.pricesapi_api_key and settings.pricesapi_search_url:
        providers.append(PricesApiProvider(settings))
    return providers


__all__ = ["ProductCandidate", "ProductProvider", "configured_providers"]
