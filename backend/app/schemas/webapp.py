from pydantic import BaseModel, ConfigDict, model_validator
from datetime import datetime
from typing import Optional, List, Any

class WebAppBase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    target_audience: Optional[str] = None
    key_features: List[str] = []
    logo: Optional[str] = None
    is_active: bool = True
    brand_voice: Optional[str] = None
    market_location: Optional[str] = None
    content_goals: Optional[str] = None
    scraper_source_urls: Optional[List[str]] = None

class WebAppCreate(WebAppBase):
    @model_validator(mode="after")
    def validate_name_or_url(self):
        if not (self.name and self.name.strip()) and not (self.url and self.url.strip()):
            raise ValueError("Either name or url must be provided.")
        return self

class WebAppUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    target_audience: Optional[str] = None
    key_features: Optional[List[str]] = None
    logo: Optional[str] = None
    is_active: Optional[bool] = None
    brand_voice: Optional[str] = None
    market_location: Optional[str] = None
    content_goals: Optional[str] = None
    scraper_source_urls: Optional[List[str]] = None

class WebApp(WebAppBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    scraped_data: Optional[Any] = None
    media_assets: Optional[List[Any]] = None
    
    class Config:
        from_attributes = True
