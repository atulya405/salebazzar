from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import PROJECT_DIR, get_settings
from app.database import init_db
from app.routes import router
from app.services.scanner import run_scan_sync

settings = get_settings()
scheduler = BackgroundScheduler(timezone="UTC")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    scheduler.add_job(
        run_scan_sync,
        "interval",
        minutes=settings.scan_interval_minutes,
        id="product-scan",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    if settings.run_scan_on_startup:
        scheduler.add_job(run_scan_sync, id="startup-scan", replace_existing=True)
    yield
    scheduler.shutdown(wait=True)


app = FastAPI(title="Salebazzar", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=PROJECT_DIR / "app" / "static"), name="static")
app.include_router(router)
