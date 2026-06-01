from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_product_source_external"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(40), index=True)
    external_id: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(500))
    image_url: Mapped[str] = mapped_column(Text)
    original_price: Mapped[float] = mapped_column(Float)
    current_price: Mapped[float] = mapped_column(Float)
    savings_amount: Mapped[float] = mapped_column(Float)
    discount_percent: Mapped[float] = mapped_column(Float, index=True)
    rating: Mapped[float] = mapped_column(Float, default=0)
    popularity: Mapped[float] = mapped_column(Float, default=0)
    quality_score: Mapped[float] = mapped_column(Float, index=True)
    store_name: Mapped[str] = mapped_column(String(150), index=True)
    product_url: Mapped[str] = mapped_column(Text)
    affiliate_url: Mapped[str] = mapped_column(Text)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ScanRun(Base):
    __tablename__ = "scan_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="running")
    products_scanned: Mapped[int] = mapped_column(Integer, default=0)
    products_qualified: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(Text, default="")


class ApiUsage(Base):
    __tablename__ = "api_usage"

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_run_id: Mapped[int] = mapped_column(Integer, index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    category: Mapped[str] = mapped_column(String(80))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    success: Mapped[int] = mapped_column(Integer, default=1)
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(Text, default="")

