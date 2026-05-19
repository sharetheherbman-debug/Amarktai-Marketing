from pydantic import BaseModel
from datetime import date, datetime
from typing import Dict, List, Optional

class PlatformStats(BaseModel):
    posts: int = 0
    views: int = 0
    engagement: int = 0
    ctr: float = 0.0

class DailyStat(BaseModel):
    date: str
    posts: int = 0
    views: int = 0
    engagement: int = 0

class AnalyticsSummary(BaseModel):
    total_posts: int = 0
    total_views: int = 0
    total_engagement: int = 0
    avg_ctr: float = 0.0
    platform_breakdown: Dict[str, PlatformStats] = {}
    daily_stats: List[DailyStat] = []
    learning_active: bool = False
    metrics_records: int = 0

class Analytics(BaseModel):
    id: str
    user_id: str
    content_id: Optional[str] = None
    platform: str
    date: date
    posts: int = 0
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    clicks: int = 0
    ctr: float = 0.0
    created_at: datetime
    
    class Config:
        from_attributes = True
