from contextlib import asynccontextmanager
import asyncio
import logging
import os

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings
from app.api.v1.router import api_router
from app.api.v1.endpoints.amarktai_status import router as amarktai_status_router
from app.db.session import engine, Base

logger = logging.getLogger(__name__)

# Rate limiter — Redis-backed in production, in-memory in dev.
# Limits are deliberately generous because content generation runs on a schedule
# (every 6–8 hours via Celery Beat), not in real-time loops.  The 200/hour and
# 30/minute caps prevent scraper/bot abuse without impacting normal users.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL or "memory://",
    default_limits=["200/hour", "30/minute"],
)

async def _heartbeat_loop() -> None:
    """Periodic heartbeat task — runs every 5 minutes while the app is alive."""
    from app.services.integration import send_heartbeat
    from app.db.session import SessionLocal
    from sqlalchemy import text

    while True:
        try:
            db_ok = False
            try:
                db = SessionLocal()
                db.execute(text("SELECT 1"))
                db.close()
                db_ok = True
            except Exception:
                pass

            await send_heartbeat(db_ok=db_ok)
        except Exception as exc:
            logger.warning("Heartbeat loop error: %s", exc)

        await asyncio.sleep(300)  # 5 minutes


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up AmarktAI Marketing API (v%s)…", settings.APP_VERSION)

    # Initialize Sentry error tracking if DSN is configured
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk
            sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=0.1)
            logger.info("Sentry error tracking initialized.")
        except Exception as exc:
            logger.warning("Failed to initialize Sentry: %s", exc)

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified / created.")
    except Exception as exc:
        logger.warning("DB create_all failed (DB may not be ready): %s", exc)

    # Start the periodic heartbeat task if integration is enabled
    heartbeat_task = None
    if settings.AMARKTAI_INTEGRATION_ENABLED:
        heartbeat_task = asyncio.create_task(_heartbeat_loop())
        logger.info(
            "AmarktAI Network integration enabled — heartbeat active → %s",
            settings.AMARKTAI_DASHBOARD_URL,
        )

    yield

    if heartbeat_task:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass

    logger.info("Shutting down AmarktAI Marketing API…")


app = FastAPI(
    title="AmarktAI Marketing API",
    description="Autonomous AI Social Media Marketing Platform — AmarktAI Marketing",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ALLOWED_HOSTS enforcement — in production, reject requests whose Host header
# does not match any origin in CORS_ORIGINS.
if settings.APP_ENVIRONMENT == "production":
    from urllib.parse import urlparse

    _allowed_hosts: set[str] = set()
    for origin in settings.CORS_ORIGINS:
        parsed = urlparse(origin)
        if parsed.hostname:
            _allowed_hosts.add(parsed.hostname)
    _allowed_hosts.update({"127.0.0.1", "localhost"})

    @app.middleware("http")
    async def enforce_allowed_hosts(request: Request, call_next):
        host = request.headers.get("host", "").split(":")[0]
        if host not in _allowed_hosts:
            return PlainTextResponse("Invalid host header", status_code=400)
        return await call_next(request)

# API routes
app.include_router(api_router, prefix="/api/v1")

# Also expose the status endpoint at the canonical /api/amarktai/status path
# (in addition to /api/v1/amarktai/status) for AmarktAI Network pollers that
# use the short form.
app.include_router(amarktai_status_router, prefix="/api/amarktai", tags=["integration"])

# Serve uploaded brand media assets at /media/<user_id>/<webapp_id>/<filename>
# The directory is created on first upload; we create it here to avoid startup errors.
_media_dir = settings.MEDIA_UPLOAD_DIR or "/tmp/amarktai_media"
os.makedirs(_media_dir, exist_ok=True)
app.mount("/media", StaticFiles(directory=_media_dir), name="media")


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/api/v1/health")
async def health_v1():
    """Public health check endpoint for monitoring and deployment verification."""
    from sqlalchemy import text
    from app.db.session import SessionLocal

    db_ok = False
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_ok = True
    except Exception:
        pass

    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "version": settings.APP_VERSION,
    }


@app.get("/api/v1/health/workers")
async def health_workers():
    """Check whether the Celery worker pool is reachable."""
    from app.workers.celery_app import celery_app

    try:
        result = celery_app.control.ping(timeout=5)
        if result:
            return {"celery": "healthy"}
        return {"celery": "unreachable"}
    except Exception:
        return {"celery": "unreachable"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
