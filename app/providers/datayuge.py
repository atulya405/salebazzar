from app.config import Settings
from app.providers.generic import GenericCatalogProvider


class DataYugeProvider(GenericCatalogProvider):
    name = "datayuge"

    def __init__(self, settings: Settings):
        super().__init__(settings, settings.datayuge_api_key, settings.datayuge_search_url)

