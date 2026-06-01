import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Product
from app.services.affiliates import affiliate_url

URL_RE = re.compile(r"https?://[^\s<>()]+", re.IGNORECASE)
DISCOUNT_RE = re.compile(r"(?<!\d)(\d{1,2}(?:\.\d+)?)\s*%\s*(?:off)?", re.IGNORECASE)
PRICE_RE = re.compile(r"(?:₹|rs\.?|inr)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)", re.IGNORECASE)


@dataclass(slots=True)
class ParsedDeal:
    name: str
    product_url: str
    discount_percent: float
    category: str
    store_name: str
    original_price: float
    current_price: float


@dataclass(slots=True)
class ImportSummary:
    parsed: int = 0
    published: int = 0
    skipped_incomplete: int = 0
    skipped_below_threshold: int = 0
    skipped_unsupported_store: int = 0


def import_authorized_messages(db: Session, text: str, settings: Settings) -> ImportSummary:
    summary = ImportSummary()
    for block in _message_blocks(text):
        parsed = _parse_block(block)
        if parsed is None:
            summary.skipped_incomplete += 1
            continue
        summary.parsed += 1
        if parsed.discount_percent < settings.min_discount_percent:
            summary.skipped_below_threshold += 1
            continue
        if parsed.store_name == "Unknown store":
            summary.skipped_unsupported_store += 1
            continue
        _upsert(db, parsed, settings)
        summary.published += 1
    db.commit()
    return summary


def _message_blocks(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return []
    return [block.strip() for block in re.split(r"\n\s*\n+", normalized) if block.strip()]


def _parse_block(block: str) -> ParsedDeal | None:
    url_match = URL_RE.search(block)
    discount_match = DISCOUNT_RE.search(block)
    if not url_match or not discount_match:
        return None
    url = url_match.group(0).rstrip(".,;")
    discount = float(discount_match.group(1))
    name = next((line.strip() for line in block.splitlines() if line.strip() and "http" not in line), "Imported deal")
    store = _store_name(url)
    category = _guess_category(name)
    prices = [float(value.replace(",", "")) for value in PRICE_RE.findall(name)]
    current = prices[-1] if prices else 0.0
    original = round(current / (1 - discount / 100), 2) if current > 0 and discount < 100 else 0.0
    return ParsedDeal(name, url, discount, category, store, original, current)


def _upsert(db: Session, deal: ParsedDeal, settings: Settings) -> None:
    external_id = hashlib.sha256(deal.product_url.encode()).hexdigest()
    product = db.scalar(select(Product).where(Product.source == "authorized_import", Product.external_id == external_id))
    if product is None:
        product = Product(source="authorized_import", external_id=external_id)
        db.add(product)
    product.category = deal.category
    product.name = deal.name
    product.image_url = ""
    product.original_price = deal.original_price
    product.current_price = deal.current_price
    product.savings_amount = round(max(0, deal.original_price - deal.current_price), 2)
    product.discount_percent = round(deal.discount_percent, 2)
    product.rating = 0
    product.popularity = 0
    product.quality_score = round(deal.discount_percent * 0.6, 2)
    product.store_name = deal.store_name
    product.product_url = deal.product_url
    product.affiliate_url = affiliate_url(deal.product_url, settings)
    product.last_updated = datetime.now(timezone.utc)


def _store_name(url: str) -> str:
    hostname = (urlparse(url).hostname or "").lower()
    if "amazon." in hostname or hostname.endswith("amzn.to"):
        return "Amazon India"
    if "flipkart." in hostname:
        return "Flipkart"
    if "myntr." in hostname or "myntra." in hostname:
        return "Myntra"
    if "ajio." in hostname:
        return "AJIO"
    return "Unknown store"


def _guess_category(name: str) -> str:
    text = name.lower()
    groups = {
        "Electronics": ("phone", "earbud", "headphone", "speaker", "laptop", "charger", "smartwatch"),
        "Fashion": ("shirt", "dress", "shoe", "sneaker", "jean", "chino", "jacket", "cap", "kurta"),
        "Home & Kitchen": ("kitchen", "cook", "bottle", "storage", "mixer", "furniture"),
        "Beauty": ("beauty", "skin", "hair", "makeup", "cream", "serum", "shampoo"),
        "Sports": ("sport", "fitness", "gym", "yoga", "cycle", "running"),
        "Books": ("book", "paperback", "hardcover", "novel"),
    }
    for category, terms in groups.items():
        if any(term in text for term in terms):
            return category
    return "Fashion"
