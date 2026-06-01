import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import SessionLocal
from app.models import ApiUsage, Product, ScanRun
from app.providers import ProductCandidate, configured_providers
from app.services.affiliates import affiliate_url


def evaluate(candidate: ProductCandidate, settings: Settings) -> dict | None:
    current = candidate.current_price
    original = candidate.original_price
    if not current or not original or current <= 0 or original <= 0 or current >= original:
        return None
    discount = ((original - current) / original) * 100
    # Very large price gaps paired with tiny prices are commonly malformed feeds.
    if discount < 80 or discount > 99.8 or (current < 1 and original > 100):
        return None
    popularity = max(0, min(candidate.popularity, 100))
    rating = max(0, min(candidate.rating, 5))
    quality_score = discount * 0.6 + rating * 0.2 + popularity * 0.2
    if quality_score < settings.min_deal_quality_score:
        return None
    return {
        "original_price": round(original, 2),
        "current_price": round(current, 2),
        "savings_amount": round(original - current, 2),
        "discount_percent": round(discount, 2),
        "rating": rating,
        "popularity": popularity,
        "quality_score": round(quality_score, 2),
    }


def _save_product(db: Session, candidate: ProductCandidate, values: dict, settings: Settings) -> None:
    product = db.scalar(
        select(Product).where(Product.source == candidate.source, Product.external_id == candidate.external_id)
    )
    if product is None:
        product = Product(source=candidate.source, external_id=candidate.external_id)
        db.add(product)
    for key, value in values.items():
        setattr(product, key, value)
    product.category = candidate.category
    product.name = candidate.name
    product.image_url = candidate.image_url
    product.store_name = candidate.store_name
    product.product_url = candidate.product_url
    product.affiliate_url = affiliate_url(candidate.product_url, settings)
    product.last_updated = datetime.now(timezone.utc)


async def run_scan(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    providers = configured_providers(settings)
    with SessionLocal() as db:
        if _scan_already_running(db, settings):
            return
        scan = ScanRun()
        db.add(scan)
        db.commit()
        db.refresh(scan)
        try:
            for provider in providers:
                for category in settings.category_list:
                    if provider.name == "serpapi" and serpapi_budget_remaining(db, settings) <= 0:
                        scan.status = "budget_limited"
                        scan.error_message = "SerpApi monthly search budget reached. Scans resume automatically next month."
                        break
                    await _scan_category(db, scan, provider, category, settings)
            cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.deal_retention_hours)
            db.execute(delete(Product).where(Product.last_updated < cutoff))
            _keep_top_deals(db, settings.max_deals_per_category)
            if scan.status == "running":
                scan.status = "completed"
        except Exception as exc:
            scan.status = "completed_with_errors"
            scan.error_message = str(exc)[:2000]
        finally:
            scan.completed_at = datetime.now(timezone.utc)
            db.commit()


def _scan_already_running(db: Session, settings: Settings) -> bool:
    now = datetime.now(timezone.utc)
    stale_before = now - timedelta(minutes=max(30, settings.request_timeout_seconds * len(settings.category_list) / 60 + 5))
    active_scans = db.scalars(select(ScanRun).where(ScanRun.status == "running")).all()
    has_active_scan = False
    for scan in active_scans:
        started_at = scan.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        if started_at < stale_before:
            scan.status = "interrupted"
            scan.completed_at = now
            scan.error_message = "Scan did not finish before the process stopped."
        else:
            has_active_scan = True
    db.commit()
    return has_active_scan


async def _scan_category(db: Session, scan: ScanRun, provider, category: str, settings: Settings) -> None:
    usage = ApiUsage(scan_run_id=scan.id, provider=provider.name, category=category)
    db.add(usage)
    try:
        candidates = await provider.fetch(category)
        usage.result_count = len(candidates)
        scan.products_scanned += len(candidates)
        for candidate in candidates:
            values = evaluate(candidate, settings)
            if values:
                _save_product(db, candidate, values, settings)
                scan.products_qualified += 1
    except Exception as exc:
        usage.success = 0
        usage.error_message = str(exc)[:1000]
    db.commit()


def _keep_top_deals(db: Session, limit: int) -> None:
    categories = db.scalars(select(Product.category).distinct()).all()
    for category in categories:
        ids_to_keep = db.scalars(
            select(Product.id)
            .where(Product.category == category)
            .order_by(Product.quality_score.desc(), Product.discount_percent.desc())
            .limit(limit)
        ).all()
        if ids_to_keep:
            db.execute(delete(Product).where(Product.category == category, Product.id.not_in(ids_to_keep)))


def serpapi_budget_remaining(db: Session, settings: Settings) -> int:
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    searches_used = db.scalar(
        select(func.count(ApiUsage.id)).where(
            ApiUsage.provider == "serpapi",
            ApiUsage.requested_at >= month_start,
        )
    ) or 0
    usable_limit = max(0, settings.serpapi_monthly_search_limit - settings.serpapi_monthly_search_reserve)
    return max(0, usable_limit - searches_used)


def run_scan_sync() -> None:
    asyncio.run(run_scan())
