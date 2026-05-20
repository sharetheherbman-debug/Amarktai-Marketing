from __future__ import annotations

from datetime import datetime
from typing import Any
import json
import logging
import re

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
import uuid

from app.db.base import get_db
from app.models.webapp import WebApp as WebAppModel, MAX_BUSINESSES_PER_USER
from app.models.user import User
from app.schemas.webapp import WebApp, WebAppCreate, WebAppUpdate
from app.api.deps import get_current_user, is_admin_user
from app.services.business_intelligence import analyze_business, normalize_url
from app.services.provider_catalog import resolve_user_api_key
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

_WEBAPPS_REQUIRED_COLUMNS: dict[str, str] = {
    "id": "VARCHAR(36) NOT NULL",
    "user_id": "VARCHAR(36) NOT NULL",
    "name": "VARCHAR(255) NOT NULL DEFAULT ''",
    "url": "VARCHAR(512) NOT NULL DEFAULT ''",
    "description": "TEXT NOT NULL",
    "category": "VARCHAR(128) NOT NULL DEFAULT ''",
    "target_audience": "VARCHAR(512) NOT NULL DEFAULT ''",
    "key_features": "JSON NULL",
    "logo": "VARCHAR(512) NULL",
    "is_active": "BOOLEAN DEFAULT TRUE",
    "brand_voice": "TEXT NULL",
    "market_location": "VARCHAR(255) NULL",
    "content_goals": "TEXT NULL",
    "scraped_data": "JSON NULL",
    "scraper_source_urls": "JSON NULL",
    "media_assets": "JSON NULL",
    "target_language": "VARCHAR(10) NULL DEFAULT 'en'",
    "created_at": "DATETIME NULL DEFAULT CURRENT_TIMESTAMP",
    "updated_at": "DATETIME NULL",
}

_WEBAPPS_JSON_FIELDS = {"key_features", "scraped_data", "scraper_source_urls", "media_assets"}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

async def _run_scrape(webapp_id: str) -> None:
    """Background task: scrape the webapp URL and store the results.

    Uses Firecrawl as the primary scraping provider when FIRECRAWL_API_KEY is
    configured; falls back to httpx + BeautifulSoup automatically.
    """
    from app.db.base import SessionLocal
    from app.services.business_intelligence import analyze_business

    db = SessionLocal()
    try:
        webapp = db.query(WebAppModel).filter(WebAppModel.id == webapp_id).first()
        if not webapp:
            return
        firecrawl_key = resolve_user_api_key(
            db,
            webapp.user_id,
            "FIRECRAWL_API_KEY",
            settings.FIRECRAWL_API_KEY,
        )
        intelligence = await analyze_business(
            url=webapp.url,
            name=webapp.name,
            description=webapp.description,
            firecrawl_api_key=firecrawl_key,
            timeout=25,
        )
        webapp.scraped_data = {
            "scraped_at": datetime.utcnow().isoformat(),
            **intelligence,
        }
        db.commit()
    except Exception as exc:
        logger.warning(
            "Background scrape failed for webapp %s: %s", webapp_id, exc
        )
    finally:
        db.close()


def _sanitize_message(value: Any) -> str:
    return str(value).replace("\n", " ").strip()[:300]


def _extract_db_table_column(exc: Exception) -> tuple[str | None, str | None]:
    messages: list[str] = []
    current: Any = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        messages.append(str(current))
        current = getattr(current, "orig", None) or getattr(current, "__cause__", None)
    blob = " | ".join(messages)

    patterns = [
        r"Unknown column '([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)'",
        r"no such column: ([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)",
        r"column \"([A-Za-z0-9_]+)\" of relation \"([A-Za-z0-9_]+)\" does not exist",
    ]
    for pattern in patterns:
        match = re.search(pattern, blob, flags=re.IGNORECASE)
        if not match:
            continue
        if "relation" in pattern:
            return match.group(2), match.group(1)
        return match.group(1), match.group(2)
    return None, None


def _log_route_exception(route: str, user_id: str | None, exc: Exception, failing_field: str | None = None) -> None:
    db_table, db_column = _extract_db_table_column(exc)
    logger.exception(
        "webapps route=%s user_id=%s db_table=%s db_column=%s failing_field=%s exc=%s message=%s",
        route,
        user_id or "unknown",
        db_table or "unknown",
        db_column or "unknown",
        failing_field or "none",
        type(exc).__name__,
        _sanitize_message(exc),
    )


def _get_webapps_columns(db: Session) -> set[str]:
    try:
        table_columns = inspect(db.bind).get_columns("webapps")
        return {col["name"] for col in table_columns}
    except Exception:
        return set()


def _parse_json_string(value: str) -> Any:
    try:
        return json.loads(value)
    except Exception:
        return value


def _normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        parsed = _parse_json_string(value.strip())
        if isinstance(parsed, list):
            return [str(v).strip() for v in parsed if str(v).strip()]
        if isinstance(parsed, str):
            tokenized = [v.strip() for v in parsed.replace("\n", ",").split(",") if v.strip()]
            return tokenized if tokenized else [parsed]
    if isinstance(value, (tuple, set)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [str(value).strip()] if str(value).strip() else []


def _normalize_dict(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        parsed = _parse_json_string(value.strip())
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list):
            return {"items": parsed}
        if parsed:
            return {"raw": str(parsed)}
    return {"raw": str(value)}


def _normalize_media_assets(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        assets: list[dict[str, Any]] = []
        for item in value:
            if isinstance(item, dict):
                assets.append(item)
            elif isinstance(item, str) and item.strip():
                assets.append({"url": item.strip()})
            elif item is not None:
                assets.append({"value": item})
        return assets
    if isinstance(value, str):
        parsed = _parse_json_string(value.strip())
        if isinstance(parsed, dict):
            return [parsed]
        if isinstance(parsed, list):
            return _normalize_media_assets(parsed)
        if parsed:
            return [{"url": str(parsed)}]
    return []


def _iso_datetime(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str) and value.strip():
        return value
    return None


def _coerce_content_goals(content_goals_value: Any) -> str:
    if isinstance(content_goals_value, list):
        content_goals_value = ", ".join([str(v).strip() for v in content_goals_value if str(v).strip()])
    elif isinstance(content_goals_value, str):
        parsed_goals = _parse_json_string(content_goals_value.strip())
        if isinstance(parsed_goals, list):
            content_goals_value = ", ".join([str(v).strip() for v in parsed_goals if str(v).strip()])
        else:
            content_goals_value = content_goals_value.strip()
    elif content_goals_value is None:
        content_goals_value = ""
    else:
        content_goals_value = str(content_goals_value)
    return content_goals_value


def _serialize_webapp_data(data: dict[str, Any], route: str, user_id: str | None) -> dict[str, Any]:
    serialized: dict[str, Any] = {}
    defaults: dict[str, Any] = {
        "id": "",
        "user_id": user_id or "",
        "name": "",
        "url": "",
        "description": "",
        "category": "",
        "target_audience": "",
        "key_features": [],
        "logo": None,
        "is_active": True,
        "scraped_data": None,
        "brand_voice": None,
        "market_location": None,
        "content_goals": "",
        "scraper_source_urls": [],
        "media_assets": [],
        "created_at": None,
        "updated_at": None,
    }
    builders: dict[str, Any] = {
        "id": lambda: str(data.get("id") or ""),
        "user_id": lambda: str(data.get("user_id") or user_id or ""),
        "name": lambda: str(data.get("name") or "").strip(),
        "url": lambda: str(data.get("url") or "").strip(),
        "description": lambda: str(data.get("description") or ""),
        "category": lambda: str(data.get("category") or ""),
        "target_audience": lambda: str(data.get("target_audience") or ""),
        "key_features": lambda: _normalize_string_list(data.get("key_features")),
        "logo": lambda: data.get("logo"),
        "is_active": lambda: bool(data.get("is_active")) if data.get("is_active") is not None else True,
        "scraped_data": lambda: _normalize_dict(data.get("scraped_data")),
        "brand_voice": lambda: data.get("brand_voice"),
        "market_location": lambda: data.get("market_location"),
        "content_goals": lambda: _coerce_content_goals(data.get("content_goals")),
        "scraper_source_urls": lambda: _normalize_string_list(data.get("scraper_source_urls")),
        "media_assets": lambda: _normalize_media_assets(data.get("media_assets")),
        "created_at": lambda: _iso_datetime(data.get("created_at")),
        "updated_at": lambda: _iso_datetime(data.get("updated_at")),
    }
    for field_name, builder in builders.items():
        try:
            serialized[field_name] = builder()
        except Exception as field_exc:
            _log_route_exception(route, user_id, field_exc, failing_field=field_name)
            serialized[field_name] = defaults[field_name]
    return serialized


def serialize_webapp(model: WebAppModel, route: str = "/api/v1/webapps/") -> dict[str, Any]:
    return _serialize_webapp_data(
        {
            "id": model.id,
            "user_id": model.user_id,
            "name": model.name,
            "url": model.url,
            "description": model.description,
            "category": model.category,
            "target_audience": model.target_audience,
            "key_features": model.key_features,
            "logo": model.logo,
            "is_active": model.is_active,
            "scraped_data": model.scraped_data,
            "brand_voice": model.brand_voice,
            "market_location": model.market_location,
            "content_goals": model.content_goals,
            "scraper_source_urls": model.scraper_source_urls,
            "media_assets": model.media_assets,
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        },
        route=route,
        user_id=model.user_id,
    )

def _serialize_webapp_row(row: dict[str, Any], route: str, user_id: str) -> dict[str, Any]:
    normalized_row = dict(row)
    for field_name in _WEBAPPS_JSON_FIELDS:
        value = normalized_row.get(field_name)
        if isinstance(value, str):
            normalized_row[field_name] = _parse_json_string(value)
    return _serialize_webapp_data(normalized_row, route=route, user_id=user_id)


def _list_webapps_resilient(db: Session, user_id: str, route: str) -> list[dict[str, Any]]:
    available_columns = _get_webapps_columns(db)
    if not available_columns:
        raise RuntimeError("Could not inspect webapps table columns")
    missing_columns = [col for col in _WEBAPPS_REQUIRED_COLUMNS if col not in available_columns]
    if missing_columns:
        logger.warning(
            "webapps route=%s user_id=%s schema_missing_columns=%s",
            route,
            user_id,
            ",".join(missing_columns),
        )
    select_columns = [col for col in _WEBAPPS_REQUIRED_COLUMNS if col in available_columns]
    if not select_columns:
        return []
    rows = db.execute(
        text(
            f"SELECT {', '.join(select_columns)} FROM webapps WHERE user_id = :user_id ORDER BY created_at DESC"
            if "created_at" in select_columns
            else f"SELECT {', '.join(select_columns)} FROM webapps WHERE user_id = :user_id"
        ),
        {"user_id": user_id},
    ).mappings().all()
    return [_serialize_webapp_row(dict(row), route=route, user_id=user_id) for row in rows]


def _get_webapp_resilient(db: Session, user_id: str, webapp_id: str, route: str) -> dict[str, Any] | None:
    available_columns = _get_webapps_columns(db)
    select_columns = [col for col in _WEBAPPS_REQUIRED_COLUMNS if col in available_columns]
    if not select_columns:
        return None
    row = db.execute(
        text(
            f"SELECT {', '.join(select_columns)} FROM webapps WHERE id = :webapp_id AND user_id = :user_id LIMIT 1"
        ),
        {"webapp_id": webapp_id, "user_id": user_id},
    ).mappings().first()
    if not row:
        return None
    return _serialize_webapp_row(dict(row), route=route, user_id=user_id)


def _coerce_json_payload(value: Any, fallback: Any) -> str:
    normalized = value if value is not None else fallback
    try:
        return json.dumps(normalized)
    except Exception:
        return json.dumps(fallback)


def _create_webapp_resilient(
    db: Session,
    route: str,
    user_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    available_columns = _get_webapps_columns(db)
    missing_columns = [col for col in _WEBAPPS_REQUIRED_COLUMNS if col not in available_columns]
    if missing_columns:
        logger.warning(
            "webapps route=%s user_id=%s schema_missing_columns=%s",
            route,
            user_id,
            ",".join(missing_columns),
        )

    insert_payload = dict(payload)
    insert_payload["key_features"] = _coerce_json_payload(insert_payload.get("key_features"), [])
    insert_payload["scraper_source_urls"] = _coerce_json_payload(insert_payload.get("scraper_source_urls"), [])
    insert_payload["media_assets"] = _coerce_json_payload(insert_payload.get("media_assets"), [])
    insert_payload["scraped_data"] = _coerce_json_payload(insert_payload.get("scraped_data"), None)

    insert_columns = [col for col in insert_payload if col in available_columns]
    if not insert_columns:
        raise RuntimeError("No insertable columns detected for webapps table")
    sql = text(
        f"INSERT INTO webapps ({', '.join(insert_columns)}) VALUES ({', '.join(f':{col}' for col in insert_columns)})"
    )
    db.execute(sql, {col: insert_payload[col] for col in insert_columns})
    db.commit()
    inserted = _get_webapp_resilient(db, user_id=user_id, webapp_id=str(payload["id"]), route=route)
    if not inserted:
        raise RuntimeError("Created business but failed to load it")
    return inserted


# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------

@router.get("/")
async def get_webapps(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all web apps for the current user."""
    route = "/api/v1/webapps/"
    try:
        webapps = db.query(WebAppModel).filter(WebAppModel.user_id == current_user.id).all()
        return [serialize_webapp(item, route=route) for item in webapps]
    except Exception as exc:
        _log_route_exception(route, current_user.id, exc)
        try:
            return _list_webapps_resilient(db, current_user.id, route=route)
        except Exception as fallback_exc:
            _log_route_exception(route, current_user.id, fallback_exc)
            raise HTTPException(status_code=500, detail="Failed to load businesses.")

@router.get("/{webapp_id}")
async def get_webapp(
    webapp_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific web app by ID."""
    route = f"/api/v1/webapps/{webapp_id}"
    try:
        webapp = db.query(WebAppModel).filter(
            WebAppModel.id == webapp_id,
            WebAppModel.user_id == current_user.id,
        ).first()
        if not webapp:
            raise HTTPException(status_code=404, detail="Web app not found")
        return serialize_webapp(webapp, route=route)
    except HTTPException:
        raise
    except Exception as exc:
        _log_route_exception(route, current_user.id, exc)
        try:
            webapp_fallback = _get_webapp_resilient(db, current_user.id, webapp_id, route=route)
            if webapp_fallback is None:
                raise HTTPException(status_code=404, detail="Web app not found")
            return webapp_fallback
        except HTTPException:
            raise
        except Exception as fallback_exc:
            _log_route_exception(route, current_user.id, fallback_exc)
            raise HTTPException(status_code=500, detail="Failed to load business.")

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_webapp(
    webapp: WebAppCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new web app / business (max 20 per user; unlimited for admin).

    Immediately queues a background scrape of the webapp URL so the AI has
    rich context before the first content generation run.
    """
    route = "/api/v1/webapps/"
    try:
        # Admin users bypass all limits
        if not is_admin_user(current_user):
            existing_count = db.query(WebAppModel).filter(
                WebAppModel.user_id == current_user.id,
            ).count()
            if existing_count >= MAX_BUSINESSES_PER_USER:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Maximum of {MAX_BUSINESSES_PER_USER} businesses per user reached.",
                )
        name = (webapp.name or "").strip()
        normalized_url = normalize_url(webapp.url)
        if not name and not normalized_url:
            raise HTTPException(status_code=422, detail="Either name or url must be provided.")

        firecrawl_key = resolve_user_api_key(
            db,
            current_user.id,
            "FIRECRAWL_API_KEY",
            settings.FIRECRAWL_API_KEY,
        )
        intelligence: dict[str, Any] = {}
        if normalized_url:
            try:
                intelligence = await analyze_business(
                    url=normalized_url,
                    name=name or None,
                    description=webapp.description,
                    firecrawl_api_key=firecrawl_key,
                    timeout=25,
                )
            except Exception as scrape_exc:
                intelligence = {
                    "source_provider": "manual",
                    "scrape_status": "failed",
                    "warnings": ["Website analysis failed; profile created from provided fields."],
                    "error": f"{type(scrape_exc).__name__}: {_sanitize_message(scrape_exc)}",
                }

        inferred_name = (
            intelligence.get("business_name")
            or name
            or ((normalized_url or "").split("://")[-1].split("/")[0] if normalized_url else "")
            or "Business Profile"
        )
        description = (webapp.description or intelligence.get("page_summary") or "").strip()
        category = (webapp.category or "").strip()
        target_audience = (webapp.target_audience or intelligence.get("target_audience_guess") or "").strip()
        key_features = [k.strip() for k in (webapp.key_features or intelligence.get("products_services") or []) if isinstance(k, str) and k.strip()][:20]

        db_webapp = WebAppModel(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            name=inferred_name,
            url=normalized_url or "",
            description=description,
            category=category,
            target_audience=target_audience,
            key_features=key_features,
            logo=webapp.logo,
            is_active=webapp.is_active if webapp.is_active is not None else True,
            brand_voice=webapp.brand_voice,
            market_location=webapp.market_location,
            content_goals=webapp.content_goals,
            scraper_source_urls=webapp.scraper_source_urls,
            scraped_data={
                "scraped_at": datetime.utcnow().isoformat(),
                **intelligence,
            } if intelligence else None,
        )
        db.add(db_webapp)
        db.commit()
        db.refresh(db_webapp)

        # Keep async refresh for richer data, but never block creation.
        if normalized_url:
            background_tasks.add_task(_run_scrape, db_webapp.id)

        return serialize_webapp(db_webapp, route=route)
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        _log_route_exception(route, current_user.id, exc)
        try:
            fallback_payload = {
                "id": str(uuid.uuid4()),
                "user_id": current_user.id,
                "name": inferred_name if "inferred_name" in locals() else (name if "name" in locals() else "Business Profile"),
                "url": normalized_url if "normalized_url" in locals() else "",
                "description": description if "description" in locals() else "",
                "category": category if "category" in locals() else "",
                "target_audience": target_audience if "target_audience" in locals() else "",
                "key_features": key_features if "key_features" in locals() else [],
                "logo": webapp.logo,
                "is_active": webapp.is_active if webapp.is_active is not None else True,
                "brand_voice": webapp.brand_voice,
                "market_location": webapp.market_location,
                "content_goals": webapp.content_goals,
                "scraper_source_urls": webapp.scraper_source_urls or [],
                "media_assets": [],
                "target_language": "en",
                "scraped_data": {
                    "scraped_at": datetime.utcnow().isoformat(),
                    **intelligence,
                } if "intelligence" in locals() and intelligence else None,
            }
            created = _create_webapp_resilient(
                db,
                route=route,
                user_id=current_user.id,
                payload=fallback_payload,
            )
            if created.get("url"):
                background_tasks.add_task(_run_scrape, created["id"])
            return created
        except Exception as fallback_exc:
            _log_route_exception(route, current_user.id, fallback_exc)
            raise HTTPException(status_code=500, detail="Failed to create business.")


class AnalyzeBusinessRequest(BaseModel):
    name: str | None = None
    url: str | None = None
    description: str | None = None


@router.post("/analyze")
async def analyze_business_profile(
    payload: AnalyzeBusinessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    if not (payload.name and payload.name.strip()) and not (payload.url and payload.url.strip()):
        raise HTTPException(status_code=422, detail="Either name or url must be provided.")
    firecrawl_key = resolve_user_api_key(
        db,
        current_user.id,
        "FIRECRAWL_API_KEY",
        settings.FIRECRAWL_API_KEY,
    )
    intelligence = await analyze_business(
        url=payload.url,
        name=payload.name,
        description=payload.description,
        firecrawl_api_key=firecrawl_key,
        timeout=25,
    )
    return intelligence

@router.post("/{webapp_id}/scrape")
async def scrape_webapp(
    webapp_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Scrape the webapp URL synchronously and store results.

    Uses Firecrawl as primary provider when FIRECRAWL_API_KEY is configured;
    falls back to httpx + BeautifulSoup.  Returns the scraped_data dict so
    the frontend can display insights immediately.
    """
    webapp = db.query(WebAppModel).filter(
        WebAppModel.id == webapp_id,
        WebAppModel.user_id == current_user.id,
    ).first()
    if not webapp:
        raise HTTPException(status_code=404, detail="Web app not found")

    firecrawl_key = resolve_user_api_key(
        db,
        current_user.id,
        "FIRECRAWL_API_KEY",
        settings.FIRECRAWL_API_KEY,
    )
    intelligence = await analyze_business(
        url=webapp.url,
        name=webapp.name,
        description=webapp.description,
        firecrawl_api_key=firecrawl_key,
        timeout=25,
    )
    scraped_data: dict[str, Any] = {
        "scraped_at": datetime.utcnow().isoformat(),
        **intelligence,
    }
    webapp.scraped_data = scraped_data
    db.commit()

    return {
        "message": "Scraped successfully" if intelligence.get("scrape_status") == "success" else "Scrape completed with warnings",
        "scraped_data": scraped_data,
    }


@router.post("/{webapp_id}/refresh-intelligence")
async def refresh_intelligence(
    webapp_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    webapp = db.query(WebAppModel).filter(
        WebAppModel.id == webapp_id,
        WebAppModel.user_id == current_user.id,
    ).first()
    if not webapp:
        raise HTTPException(status_code=404, detail="Web app not found")

    firecrawl_key = resolve_user_api_key(
        db,
        current_user.id,
        "FIRECRAWL_API_KEY",
        settings.FIRECRAWL_API_KEY,
    )
    intelligence = await analyze_business(
        url=webapp.url,
        name=webapp.name,
        description=webapp.description,
        firecrawl_api_key=firecrawl_key,
        timeout=25,
    )
    webapp.scraped_data = {
        "scraped_at": datetime.utcnow().isoformat(),
        **intelligence,
    }
    if not webapp.description and intelligence.get("page_summary"):
        webapp.description = str(intelligence["page_summary"])[:2000]
    if not webapp.target_audience and intelligence.get("target_audience_guess"):
        webapp.target_audience = str(intelligence["target_audience_guess"])[:512]
    if intelligence.get("products_services"):
        webapp.key_features = intelligence["products_services"][:20]
    db.commit()
    db.refresh(webapp)
    return {
        "ok": True,
        "webapp_id": webapp.id,
        "intelligence": webapp.scraped_data,
    }


@router.put("/{webapp_id}")
async def update_webapp(
    webapp_id: str,
    webapp_update: WebAppUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a web app."""
    try:
        db_webapp = db.query(WebAppModel).filter(
            WebAppModel.id == webapp_id,
            WebAppModel.user_id == current_user.id,
        ).first()
        if not db_webapp:
            raise HTTPException(status_code=404, detail="Web app not found")

        update_data = webapp_update.model_dump(exclude_unset=True)
        if "url" in update_data:
            update_data["url"] = normalize_url(update_data.get("url")) or ""
        for field, value in update_data.items():
            setattr(db_webapp, field, value)

        db.commit()
        db.refresh(db_webapp)
        return serialize_webapp(db_webapp)
    except HTTPException:
        raise
    except Exception as exc:
        _log_route_exception(f"/api/v1/webapps/{webapp_id}", current_user.id, exc)
        raise HTTPException(status_code=500, detail="Failed to update business.")

@router.delete("/{webapp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webapp(
    webapp_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a web app."""
    db_webapp = db.query(WebAppModel).filter(
        WebAppModel.id == webapp_id,
        WebAppModel.user_id == current_user.id,
    ).first()
    if not db_webapp:
        raise HTTPException(status_code=404, detail="Web app not found")

    db.delete(db_webapp)
    db.commit()
    return None


# ---------------------------------------------------------------------------
# Media upload
# ---------------------------------------------------------------------------

_ALLOWED_MEDIA_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml",
    "video/mp4", "video/webm", "video/quicktime",
    "application/pdf",
}
_MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


@router.post("/{webapp_id}/media")
async def upload_media(
    webapp_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Upload a brand media asset and attach it to the business/app.

    Accepts images, videos, and PDFs up to 50 MB.
    Files are stored under MEDIA_UPLOAD_DIR (default: /tmp/amarktai_media).
    Returns the stored asset metadata including a relative URL.
    """
    import os
    from app.core.config import settings

    webapp = db.query(WebAppModel).filter(
        WebAppModel.id == webapp_id,
        WebAppModel.user_id == current_user.id,
    ).first()
    if not webapp:
        raise HTTPException(status_code=404, detail="Web app not found")

    # Validate content type
    content_type = file.content_type or ""
    if content_type not in _ALLOWED_MEDIA_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{content_type}'. Allowed: images, videos, PDF.",
        )

    # Read and validate size
    data = await file.read()
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 50 MB limit.")

    # Determine storage directory
    upload_dir = settings.MEDIA_UPLOAD_DIR or "/tmp/amarktai_media"
    webapp_dir = os.path.join(upload_dir, current_user.id, webapp_id)
    os.makedirs(webapp_dir, exist_ok=True)

    # Build a unique filename preserving the extension
    ext = os.path.splitext(file.filename or "")[1] or ".bin"
    asset_id = str(uuid.uuid4())
    filename = f"{asset_id}{ext}"
    file_path = os.path.join(webapp_dir, filename)

    with open(file_path, "wb") as fh:
        fh.write(data)

    # Build relative URL served via static mount (or direct path for now)
    relative_url = f"/media/{current_user.id}/{webapp_id}/{filename}"

    # Append to media_assets JSON list
    asset_meta: dict[str, Any] = {
        "id": asset_id,
        "name": file.filename or filename,
        "url": relative_url,
        "type": content_type,
        "size": len(data),
        "uploaded_at": datetime.utcnow().isoformat(),
    }
    current_assets: list = list(webapp.media_assets or [])
    current_assets.append(asset_meta)
    webapp.media_assets = current_assets
    db.commit()

    return {"message": "Upload successful", "asset": asset_meta}


@router.delete("/{webapp_id}/media/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(
    webapp_id: str,
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Remove a previously uploaded media asset from the business/app."""
    import os
    from app.core.config import settings

    webapp = db.query(WebAppModel).filter(
        WebAppModel.id == webapp_id,
        WebAppModel.user_id == current_user.id,
    ).first()
    if not webapp:
        raise HTTPException(status_code=404, detail="Web app not found")

    current_assets: list = list(webapp.media_assets or [])
    asset = next((a for a in current_assets if a.get("id") == asset_id), None)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Try to delete the physical file (best-effort)
    try:
        upload_dir = settings.MEDIA_UPLOAD_DIR or "/tmp/amarktai_media"
        ext = os.path.splitext(asset.get("name", ""))[1] or ".bin"
        filename = f"{asset_id}{ext}"
        file_path = os.path.join(upload_dir, current_user.id, webapp_id, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass

    webapp.media_assets = [a for a in current_assets if a.get("id") != asset_id]
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
