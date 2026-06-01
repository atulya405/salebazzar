from app.config import Settings
from app.database import Base
from app.models import ScanRun
from app.providers.base import ProductCandidate
from app.providers.rainforest import RainforestProvider
from app.services.affiliates import affiliate_url
from app.services.scanner import _scan_already_running, evaluate
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def candidate(current=20, original=100, rating=4.5, popularity=75):
    return ProductCandidate("test", "1", "Electronics", "Deal", "", current, original, "Store", "https://example.com/p", rating, popularity)


def test_accepts_discount_of_80_percent():
    result = evaluate(candidate(), Settings(min_deal_quality_score=0))
    assert result is not None
    assert result["discount_percent"] == 80
    assert result["savings_amount"] == 80


def test_rejects_missing_original_price_and_low_discount():
    assert evaluate(candidate(original=None), Settings(min_deal_quality_score=0)) is None
    assert evaluate(candidate(current=21), Settings(min_deal_quality_score=0)) is None


def test_rejects_suspicious_pricing():
    assert evaluate(candidate(current=0.5, original=200), Settings(min_deal_quality_score=0)) is None


def test_adds_amazon_affiliate_tag():
    settings = Settings(amazon_affiliate_tag="shop-21")
    assert affiliate_url("https://www.amazon.in/dp/123?ref=x", settings) == "https://www.amazon.in/dp/123?ref=x&tag=shop-21"


def test_scan_guard_blocks_duplicate_scan():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(ScanRun(status="running"))
        db.commit()
        assert _scan_already_running(db, Settings()) is True


def test_maps_rainforest_amazon_deal():
    provider = RainforestProvider(Settings())
    deal = provider._map(
        {
            "asin": "B012345678",
            "title": "Wireless headphones",
            "image": "https://example.com/image.jpg",
            "link": "https://www.amazon.in/dp/B012345678",
            "deal_price": {"value": 199},
            "list_price": {"value": 1000},
        },
        "Electronics",
    )
    assert deal.current_price == 199
    assert deal.original_price == 1000
    assert deal.store_name == "Amazon India"
