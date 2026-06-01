from app.config import Settings
from app.providers.generic import GenericCatalogProvider


class PricesApiProvider(GenericCatalogProvider):
    name = "pricesapi"

    def __init__(self, settings: Settings):
        super().__init__(settings, settings.pricesapi_api_key, settings.pricesapi_search_url)

