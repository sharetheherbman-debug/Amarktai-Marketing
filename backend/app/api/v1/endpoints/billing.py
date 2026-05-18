"""
Billing endpoints — Stripe checkout, portal, webhook, and status.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.user import PlanType, User

logger = logging.getLogger(__name__)
router = APIRouter()


class CheckoutRequest(BaseModel):
    plan: str


class CheckoutResponse(BaseModel):
    url: str


class PortalResponse(BaseModel):
    url: str


PLAN_DEFS: dict[PlanType, dict[str, Any]] = {
    PlanType.FREE: {
        "id": "free",
        "name": "Free",
        "price": 0,
        "interval": "month",
        "quota": 50,
        "features": ["1 web app", "3 platforms", "50 posts/month", "Basic analytics"],
        "stripe_price_id": None,
    },
    PlanType.PRO: {
        "id": "pro",
        "name": "Pro",
        "price": 29,
        "interval": "month",
        "quota": 500,
        "features": ["5 web apps", "All platforms", "500 posts/month", "Advanced analytics", "AI media generation", "Priority support"],
        "stripe_price_id": settings.STRIPE_PRICE_ID_PRO or None,
    },
    PlanType.BUSINESS: {
        "id": "business",
        "name": "Business",
        "price": 99,
        "interval": "month",
        "quota": 2000,
        "features": ["Unlimited web apps", "All platforms", "2000 posts/month", "Team access", "Custom branding", "API access"],
        "stripe_price_id": settings.STRIPE_PRICE_ID_BUSINESS or None,
    },
    PlanType.ENTERPRISE: {
        "id": "enterprise",
        "name": "Enterprise",
        "price": 299,
        "interval": "month",
        "quota": 99999,
        "features": ["Everything in Business", "Dedicated support", "Custom integrations", "SLA guarantee"],
        "stripe_price_id": settings.STRIPE_PRICE_ID_ENTERPRISE or None,
    },
}

PLAN_QUOTAS: dict[PlanType, int] = {p: int(d["quota"]) for p, d in PLAN_DEFS.items()}


def _stripe_configured() -> bool:
    return bool(settings.STRIPE_SECRET_KEY)


def _normalize_plan(raw: str | None) -> PlanType:
    value = (raw or "").strip().lower()
    try:
        return PlanType(value)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid plan '{raw}'. Must be one of: free, pro, business, enterprise.",
        )


def _get_stripe():
    if not _stripe_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not configured. Set STRIPE_SECRET_KEY in environment.",
        )
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def _set_user_plan(user: User, plan: PlanType) -> None:
    quota = PLAN_QUOTAS.get(plan, 50)
    user.plan = plan
    user.plan_tier = plan.value
    user.plan_quota_content = quota
    user.monthly_content_quota = quota


def _price_to_plan() -> dict[str, PlanType]:
    out: dict[str, PlanType] = {}
    for plan, cfg in PLAN_DEFS.items():
        pid = cfg.get("stripe_price_id")
        if pid:
            out[str(pid)] = plan
    return out


@router.get("/plans")
async def list_plans() -> dict[str, Any]:
    plans = [cfg for _, cfg in PLAN_DEFS.items()]
    return {"plans": plans, "stripe_configured": _stripe_configured()}


@router.post("/checkout-session", response_model=CheckoutResponse)
async def create_checkout_session(
    body: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CheckoutResponse:
    stripe = _get_stripe()
    plan = _normalize_plan(body.plan)
    if plan == PlanType.FREE:
        _set_user_plan(current_user, PlanType.FREE)
        db.commit()
        return CheckoutResponse(url=f"{settings.FRONTEND_URL}/dashboard/settings?billing=free")

    price_id = PLAN_DEFS[plan].get("stripe_price_id")
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Stripe price ID is not configured for plan '{plan.value}'.",
        )

    customer_id = getattr(current_user, "stripe_customer_id", None)
    if not customer_id:
        customer = stripe.Customer.create(
            email=current_user.email,
            metadata={"user_id": current_user.id},
        )
        customer_id = customer.id
        current_user.stripe_customer_id = customer_id
        db.commit()

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{settings.FRONTEND_URL}/dashboard/settings?billing=success",
        cancel_url=f"{settings.FRONTEND_URL}/pricing?billing=cancelled",
        metadata={"user_id": current_user.id, "plan": plan.value},
    )
    return CheckoutResponse(url=session.url)


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session_alias(
    body: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CheckoutResponse:
    return await create_checkout_session(body, current_user, db)


@router.post("/portal-session", response_model=PortalResponse)
async def create_portal_session(
    current_user: User = Depends(get_current_user),
) -> PortalResponse:
    stripe = _get_stripe()
    customer_id = getattr(current_user, "stripe_customer_id", None)
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing account found. Please subscribe first.",
        )
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{settings.FRONTEND_URL}/dashboard/settings",
    )
    return PortalResponse(url=session.url)


@router.post("/portal", response_model=PortalResponse)
async def create_portal_session_alias(
    current_user: User = Depends(get_current_user),
) -> PortalResponse:
    return await create_portal_session(current_user)


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(None, alias="stripe-signature"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    stripe = _get_stripe()
    payload = await request.body()

    if settings.STRIPE_WEBHOOK_SECRET and stripe_signature:
        try:
            event = stripe.Webhook.construct_event(
                payload,
                stripe_signature,
                settings.STRIPE_WEBHOOK_SECRET,
            )
        except Exception as exc:
            logger.warning("Stripe webhook signature verification failed: %s", exc)
            raise HTTPException(status_code=400, detail="Invalid Stripe signature")
    else:
        event = json.loads(payload.decode("utf-8"))

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data, db)
    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(data, db)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(data, db)
    else:
        logger.info("Unhandled Stripe event: %s", event_type)

    return {"received": True}


def _handle_checkout_completed(data: dict[str, Any], db: Session) -> None:
    user_id = (data.get("metadata") or {}).get("user_id")
    plan_raw = (data.get("metadata") or {}).get("plan")
    if not user_id:
        return
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return
    customer_id = data.get("customer")
    if customer_id:
        user.stripe_customer_id = customer_id
    try:
        plan = _normalize_plan(plan_raw or "pro")
    except HTTPException:
        plan = PlanType.PRO
    _set_user_plan(user, plan)
    db.commit()


def _handle_subscription_updated(data: dict[str, Any], db: Session) -> None:
    customer_id = data.get("customer")
    if not customer_id:
        return
    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if not user:
        return

    status_value = str(data.get("status", "")).lower()
    if status_value in {"canceled", "incomplete_expired", "unpaid"}:
        _set_user_plan(user, PlanType.FREE)
        db.commit()
        return

    items = (data.get("items") or {}).get("data") or []
    price_id = ""
    if items and isinstance(items, list):
        price_id = str((items[0].get("price") or {}).get("id") or "")
    mapping = _price_to_plan()
    plan = mapping.get(price_id, PlanType.FREE)
    _set_user_plan(user, plan)
    db.commit()


def _handle_subscription_deleted(data: dict[str, Any], db: Session) -> None:
    customer_id = data.get("customer")
    if not customer_id:
        return
    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if not user:
        return
    _set_user_plan(user, PlanType.FREE)
    db.commit()


@router.get("/status")
async def billing_status(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    raw_plan = getattr(current_user, "plan", PlanType.FREE)
    if isinstance(raw_plan, PlanType):
        plan = raw_plan
    else:
        try:
            plan = _normalize_plan(str(raw_plan))
        except HTTPException:
            plan = PlanType.FREE
    quota_used = int(getattr(current_user, "monthly_content_used", 0) or 0)
    cfg = PLAN_DEFS.get(plan, PLAN_DEFS[PlanType.FREE])
    limit = int(cfg["quota"])

    return {
        "plan_tier": plan.value,
        "plan_name": cfg["name"],
        "price": cfg["price"],
        "quota_used": quota_used,
        "quota_limit": limit,
        "quota_remaining": max(0, limit - quota_used),
        "features": cfg["features"],
        "stripe_configured": _stripe_configured(),
        "has_billing_account": bool(getattr(current_user, "stripe_customer_id", None)),
    }
