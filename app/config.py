from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_DIR / ".env", env_file_encoding="utf-8")

    app_name: str = "Salebazzar"
    app_env: str = "development"
    contact_email: str = ""
    admin_password: str = ""
    database_url: str = f"sqlite:///{(PROJECT_DIR / '80off.db').as_posix()}"
    scan_interval_minutes: int = Field(default=1080, ge=1)
    run_scan_on_startup: bool = False
    request_timeout_seconds: float = Field(default=15, gt=0)
    max_results_per_category: int = Field(default=40, ge=1, le=100)
    max_deals_per_category: int = Field(default=50, ge=1)
    min_deal_quality_score: float = Field(default=48, ge=0)
    deal_retention_hours: int = Field(default=24, ge=1)
    categories: str = "Electronics,Fashion,Home & Kitchen,Beauty,Sports,Books"

    amazon_creators_api_enabled: bool = False
    amazon_creators_api_public_key: str = ""
    amazon_creators_api_private_key: str = ""
    amazon_creators_api_marketplace: str = "www.amazon.in"
    datayuge_enabled: bool = False
    datayuge_api_key: str = ""
    datayuge_search_url: str = ""
    pricesapi_enabled: bool = False
    pricesapi_api_key: str = ""
    pricesapi_search_url: str = ""

    amazon_affiliate_tag: str = ""
    flipkart_affiliate_tag: str = ""
    other_affiliate_template: str = ""
    other_affiliate_tag: str = ""

    @property
    def category_list(self) -> list[str]:
        return [item.strip() for item in self.categories.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
