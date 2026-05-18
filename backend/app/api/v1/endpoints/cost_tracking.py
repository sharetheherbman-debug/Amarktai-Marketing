"""
Cost Tracking Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.engagement import CostTracking
from app.models.user import User

router = APIRouter()

@router.get("/current")
async def get_current_costs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current billing period cost tracking."""
    
    # Get or create current period tracking
    current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    tracking = db.query(CostTracking).filter(
        CostTracking.user_id == current_user.id,
        CostTracking.billing_period_start == current_month_start
    ).first()
    
    if not tracking:
        # Create new tracking record
        from app.models.engagement import CostTracking
        import uuid
        
        next_month = current_month_start + timedelta(days=32)
        next_month_start = next_month.replace(day=1)
        
        tracking = CostTracking(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            billing_period_start=current_month_start,
            billing_period_end=next_month_start
        )
        db.add(tracking)
        db.commit()
    
    # Calculate remaining budget
    budget = float(current_user.api_cost_budget or "5.00")
    used = float(tracking.total_cost or "0.00")
    remaining = budget - used
    percent_used = (used / budget * 100) if budget > 0 else 0
    
    return {
        "billing_period": {
            "start": tracking.billing_period_start,
            "end": tracking.billing_period_end
        },
        "budget": {
            "total": budget,
            "used": round(used, 4),
            "remaining": round(remaining, 4),
            "percent_used": round(percent_used, 2)
        },
        "breakdown": {
            "llm": {
                "tokens": tracking.llm_tokens_used,
                "cost": float(tracking.llm_tokens_cost or "0.00")
            },
            "images": {
                "count": tracking.images_generated,
                "cost": float(tracking.images_cost or "0.00")
            },
            "videos": {
                "count": tracking.videos_generated,
                "cost": float(tracking.videos_cost or "0.00")
            },
            "audio": {
                "count": tracking.audio_generated,
                "cost": float(tracking.audio_cost or "0.00")
            }
        },
        "alerts": {
            "50_percent": tracking.alert_50_sent,
            "80_percent": tracking.alert_80_sent,
            "100_percent": tracking.alert_100_sent
        }
    }

@router.get("/history")
async def get_cost_history(
    months: int = 6,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get cost history for past months."""
    
    from sqlalchemy import func
    
    # Get historical data
    history = db.query(CostTracking).filter(
        CostTracking.user_id == current_user.id
    ).order_by(
        CostTracking.billing_period_start.desc()
    ).limit(months).all()
    
    return [
        {
            "period": {
                "start": h.billing_period_start,
                "end": h.billing_period_end
            },
            "total_cost": float(h.total_cost or "0.00"),
            "breakdown": {
                "llm": float(h.llm_tokens_cost or "0.00"),
                "images": float(h.images_cost or "0.00"),
                "videos": float(h.videos_cost or "0.00"),
                "audio": float(h.audio_cost or "0.00")
            }
        }
        for h in history
    ]

@router.get("/content/{content_id}")
async def get_content_cost(
    content_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get cost breakdown for a specific content item."""
    
    from app.models.content import Content
    
    content = db.query(Content).filter(
        Content.id == content_id,
        Content.user_id == current_user.id
    ).first()
    
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    total_cost = (
        float(content.image_generation_cost or "0.00") +
        float(content.video_generation_cost or "0.00") +
        float(content.audio_generation_cost or "0.00")
    )
    
    # Estimate LLM cost (rough: $0.002 per 1K tokens)
    llm_cost = (content.llm_tokens_used or 0) * 0.000002
    total_cost += llm_cost
    
    return {
        "content_id": content_id,
        "title": content.title,
        "platform": content.platform,
        "generation_cost": {
            "image": float(content.image_generation_cost or "0.00"),
            "video": float(content.video_generation_cost or "0.00"),
            "audio": float(content.audio_generation_cost or "0.00"),
            "llm": round(llm_cost, 6),
            "total": round(total_cost, 4)
        },
        "tokens_used": content.llm_tokens_used or 0
    }

@router.get("/estimate")
async def estimate_generation_cost(
    platforms: List[str],
    include_images: bool = True,
    include_videos: bool = True,
    include_audio: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Estimate cost for generating content."""
    
    # Get user's API keys to determine which providers will be used
    from app.models.user_api_key import UserAPIKey
    
    user_keys = db.query(UserAPIKey).filter(
        UserAPIKey.user_id == current_user.id,
        UserAPIKey.is_active == True
    ).all()
    
    key_names = [k.key_name for k in user_keys]
    
    # Provider costs per unit
    provider_costs = {
        "image": {
            "genx": 0.01,
            "huggingface": 0.0,  # Free
            "replicate": 0.01,
            "fal": 0.02,
            "leonardo": 0.03,
            "openai": 0.04
        },
        "video": {
            "replicate": 0.05,
            "runway": 0.20,
            "heygen": 0.30
        },
        "audio": {
            "coqui": 0.0,  # Free
            "playht": 0.00005,  # Per char
            "elevenlabs": 0.0001  # Per char
        }
    }
    
    # Determine which providers will be used (cheapest available)
    def get_cheapest_provider(media_type, user_keys):
        costs = provider_costs.get(media_type, {})
        
        # Map key names to providers
        key_to_provider = {
            "GENX_API_KEY": "genx",
            "HUGGINGFACE_TOKEN": "huggingface",
            "REPLICATE_API_TOKEN": "replicate",
            "FAL_AI_KEY": "fal",
            "LEONARDO_API_KEY": "leonardo",
            "OPENAI_API_KEY": "openai",
            "RUNWAY_API_KEY": "runway",
            "HEYGEN_API_KEY": "heygen",
            "COQUI_API_KEY": "coqui",
            "PLAYHT_API_KEY": "playht",
            "ELEVENLABS_API_KEY": "elevenlabs"
        }
        
        available_providers = []
        for key in user_keys:
            provider = key_to_provider.get(key.key_name)
            if provider and provider in costs:
                available_providers.append((provider, costs[provider]))
        
        # Add free providers that don't need keys (if applicable)
        if media_type == "image" and "huggingface" not in [p[0] for p in available_providers]:
            available_providers.append(("huggingface", 0.0))
        
        if not available_providers:
            return None, 0
        
        # Return cheapest
        return min(available_providers, key=lambda x: x[1])
    
    # Calculate estimates
    estimates = {
        "platforms": len(platforms),
        "items": []
    }
    
    total_estimate = 0.0
    
    for platform in platforms:
        platform_cost = 0.0
        breakdown = {}
        
        # Images (1 per platform typically)
        if include_images:
            provider, cost = get_cheapest_provider("image", user_keys)
            if provider:
                platform_cost += cost
                breakdown["image"] = {"provider": provider, "cost": cost}
        
        # Videos (for video platforms)
        if include_videos and platform in ["youtube_shorts", "tiktok", "instagram_reels", "facebook_reels"]:
            provider, cost = get_cheapest_provider("video", user_keys)
            if provider:
                platform_cost += cost
                breakdown["video"] = {"provider": provider, "cost": cost}
        
        # Audio (for videos with voiceover)
        if include_audio and include_videos:
            provider, cost = get_cheapest_provider("audio", user_keys)
            if provider:
                # Estimate 500 chars per video
                estimated_chars = 500
                audio_cost = cost * estimated_chars
                platform_cost += audio_cost
                breakdown["audio"] = {"provider": provider, "cost": audio_cost, "chars": estimated_chars}
        
        # LLM tokens (rough estimate: 2K tokens per content piece)
        llm_tokens = 2000
        llm_cost = llm_tokens * 0.000002  # $0.002 per 1K tokens (GPT-3.5 rate)
        platform_cost += llm_cost
        breakdown["llm"] = {"tokens": llm_tokens, "cost": llm_cost}
        
        estimates["items"].append({
            "platform": platform,
            "estimated_cost": round(platform_cost, 4),
            "breakdown": breakdown
        })
        
        total_estimate += platform_cost
    
    estimates["total_estimate"] = round(total_estimate, 4)
    
    # Check against budget
    current_tracking = db.query(CostTracking).filter(
        CostTracking.user_id == current_user.id,
        CostTracking.billing_period_start == datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    ).first()
    
    current_spent = float(current_tracking.total_cost if current_tracking else "0.00")
    budget = float(current_user.api_cost_budget or "5.00")
    
    estimates["budget_check"] = {
        "current_spent": round(current_spent, 4),
        "budget": budget,
        "remaining": round(budget - current_spent, 4),
        "would_exceed_budget": (current_spent + total_estimate) > budget,
        "projected_total": round(current_spent + total_estimate, 4)
    }
    
    return estimates
