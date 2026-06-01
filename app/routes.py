from collections import defaultdict
import hashlib
import hmac
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import PROJECT_DIR, get_settings
from app.database import get_db
from app.models import ApiUsage, Product, ScanRun
from app.services.affiliates import affiliate_url
from app.services.bulk_import import import_authorized_messages

router = APIRouter()
templates = Jinja2Templates(directory=PROJECT_DIR / "app" / "templates")

PUBLIC_PAGES = {
    "about": {
        "title": "About Salebazzar",
        "heading": "A focused way to discover exceptional deals",
        "body": [
            "Salebazzar is an independent deal-discovery website. We index offers from permitted API-based sources and highlight products that are advertised at 50% or more below their original price.",
            "We do not sell products, process payments, or fulfil orders. When you choose a deal, you continue to the original merchant website to review the final price, delivery terms, returns policy, and availability before purchasing.",
        ],
    },
    "privacy": {
        "title": "Privacy Policy",
        "heading": "Privacy Policy",
        "body": [
            "Salebazzar does not currently require user accounts and does not collect payment information. The website may receive standard technical request data from its hosting provider, such as IP addresses, browser details, and access logs.",
            "When you follow a product link, the destination merchant or affiliate network may apply its own cookies and privacy policy. Review the destination website before completing a purchase.",
            "This policy may be updated as Salebazzar adds new features. The effective date of this policy is June 1, 2026.",
        ],
    },
    "disclosure": {
        "title": "Affiliate Disclosure",
        "heading": "Affiliate Disclosure",
        "body": [
            "Salebazzar may use affiliate links. If you click an eligible product link and complete a purchase on the original merchant website, Salebazzar may receive a commission at no additional cost to you.",
            "Affiliate relationships do not change our minimum-discount rule. Product prices, stock, and eligibility can change after an offer is indexed, so always verify the final details with the merchant.",
        ],
    },
}


def discount_band(discount: float) -> str:
    if discount >= 95:
        return "95%+ OFF"
    if discount >= 90:
        return "90% to 95%"
    if discount >= 80:
        return "80% to 90%"
    if discount >= 70:
        return "70% to 80%"
    if discount >= 60:
        return "60% to 70%"
    return "50% to 60%"


@router.get("/", response_class=HTMLResponse)
def homepage(
    request: Request,
    search: str = "",
    category: str = "",
    store: str = "",
    sort: str = Query(default="discount", pattern="^(discount|savings|quality)$"),
    db: Session = Depends(get_db),
):
    query = select(Product)
    if search:
        query = query.where(Product.name.ilike(f"%{search}%"))
    if category:
        query = query.where(Product.category == category)
    if store:
        query = query.where(Product.store_name == store)
    sort_column = {
        "discount": Product.discount_percent,
        "savings": Product.savings_amount,
        "quality": Product.quality_score,
    }[sort]
    products = db.scalars(query.order_by(sort_column.desc(), Product.quality_score.desc())).all()
    grouped = defaultdict(list)
    for product in products:
        grouped[discount_band(product.discount_percent)].append(product)
    settings = get_settings()
    stores = db.scalars(select(Product.store_name).distinct().order_by(Product.store_name)).all()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "groups": grouped,
            "bands": ["95%+ OFF", "90% to 95%", "80% to 90%", "70% to 80%", "60% to 70%", "50% to 60%"],
            "categories": settings.category_list,
            "stores": stores,
            "product_count": len(products),
            "filters": {"search": search, "category": category, "store": store, "sort": sort},
        },
    )


def _info_page(request: Request, page_name: str):
    return templates.TemplateResponse(request, "info.html", {"page": PUBLIC_PAGES[page_name]})


@router.get("/about", response_class=HTMLResponse)
def about(request: Request):
    return _info_page(request, "about")


@router.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request):
    return _info_page(request, "privacy")


@router.get("/disclosure", response_class=HTMLResponse)
def disclosure(request: Request):
    return _info_page(request, "disclosure")


@router.get("/contact", response_class=HTMLResponse)
def contact(request: Request):
    settings = get_settings()
    return templates.TemplateResponse(request, "contact.html", {"contact_email": settings.contact_email})


@router.get("/admin", response_class=HTMLResponse)
def admin(request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    latest_scan = db.scalar(select(ScanRun).order_by(ScanRun.started_at.desc()).limit(1))
    totals = {
        "products_scanned": db.scalar(select(func.coalesce(func.sum(ScanRun.products_scanned), 0))),
        "qualified": db.scalar(select(func.count(Product.id))),
        "api_calls": db.scalar(select(func.count(ApiUsage.id))),
        "failed_calls": db.scalar(select(func.count(ApiUsage.id)).where(ApiUsage.success == 0)),
        "amazon_api_status": "enabled" if settings.amazon_creators_api_enabled else "awaiting credentials",
    }
    usage = db.execute(
        select(ApiUsage.provider, func.count(ApiUsage.id), func.sum(ApiUsage.result_count))
        .group_by(ApiUsage.provider)
        .order_by(ApiUsage.provider)
    ).all()
    scans = db.scalars(select(ScanRun).order_by(ScanRun.started_at.desc()).limit(10)).all()
    return templates.TemplateResponse(
        request,
        "admin.html",
        {
            "latest_scan": latest_scan,
            "totals": totals,
            "usage": usage,
            "scans": scans,
            "message": request.query_params.get("message", ""),
            "error": request.query_params.get("error", ""),
            "categories": settings.category_list,
        },
    )


@router.post("/admin/deals")
def add_manual_amazon_deal(
    name: str = Form(),
    category: str = Form(),
    image_url: str = Form(default=""),
    product_url: str = Form(),
    original_price: float = Form(gt=0),
    current_price: float = Form(gt=0),
    admin_password: str = Form(),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    if not settings.admin_password:
        return _admin_redirect(error="Set ADMIN_PASSWORD before adding deals.")
    if not hmac.compare_digest(admin_password, settings.admin_password):
        return _admin_redirect(error="Incorrect admin password.")
    if category not in settings.category_list:
        return _admin_redirect(error="Choose a configured category.")
    hostname = (urlparse(product_url).hostname or "").lower()
    if hostname != "amazon.in" and not hostname.endswith(".amazon.in"):
        return _admin_redirect(error="Only Amazon.in product URLs are accepted.")
    if current_price >= original_price:
        return _admin_redirect(error="Sale price must be lower than MRP.")
    discount = ((original_price - current_price) / original_price) * 100
    if discount < settings.min_discount_percent or discount > 99.8:
        return _admin_redirect(error=f"Only credible Amazon deals discounted by {settings.min_discount_percent:.0f}% or more are accepted.")
    external_id = hashlib.sha256(product_url.encode()).hexdigest()
    product = db.scalar(select(Product).where(Product.source == "manual_amazon", Product.external_id == external_id))
    if product is None:
        product = Product(source="manual_amazon", external_id=external_id)
        db.add(product)
    product.category = category
    product.name = name.strip()
    product.image_url = image_url.strip()
    product.original_price = round(original_price, 2)
    product.current_price = round(current_price, 2)
    product.savings_amount = round(original_price - current_price, 2)
    product.discount_percent = round(discount, 2)
    product.rating = 0
    product.popularity = 0
    product.quality_score = round(discount * 0.6, 2)
    product.store_name = "Amazon India"
    product.product_url = product_url.strip()
    product.affiliate_url = affiliate_url(product_url.strip(), settings)
    product.last_updated = datetime.now(timezone.utc)
    db.commit()
    return _admin_redirect(message=f"Published Amazon deal at {product.discount_percent:.1f}% off.")


def _admin_redirect(**params: str) -> RedirectResponse:
    from urllib.parse import urlencode

    return RedirectResponse(url=f"/admin?{urlencode(params)}", status_code=303)


@router.post("/admin/import")
async def bulk_import(
    admin_password: str = Form(),
    messages: str = Form(default=""),
    export_file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    if not settings.admin_password:
        return _admin_redirect(error="Set ADMIN_PASSWORD before importing deals.")
    if not hmac.compare_digest(admin_password, settings.admin_password):
        return _admin_redirect(error="Incorrect admin password.")
    text = messages
    if export_file and export_file.filename:
        text = (await export_file.read()).decode("utf-8", errors="replace")
    if not text.strip():
        return _admin_redirect(error="Paste authorized messages or upload a text export.")
    summary = import_authorized_messages(db, text, settings)
    return _admin_redirect(
        message=(
            f"Import complete: {summary.published} published, "
            f"{summary.skipped_incomplete} incomplete, "
            f"{summary.skipped_below_threshold} below threshold, "
            f"{summary.skipped_unsupported_store} unsupported store."
        )
    )


@router.get("/health")
def health():
    return {"status": "ok", "service": "Salebazzar"}
