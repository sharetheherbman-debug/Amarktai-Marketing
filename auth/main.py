"""AMarkTAI JWT Authentication Service"""
import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from pymongo import MongoClient
from jose import jwt, JWTError
from passlib.context import CryptContext
import redis

# Config
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://amarktai:amarktai_db_pass@mongodb:27017/amarktai_mkt")
JWT_SECRET = os.getenv("JWT_SECRET", "amarktai_jwt_secret_change_in_production")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

# Init
app = FastAPI(title="AMarkTAI Auth", version="1.0.0")
mongo = MongoClient(MONGODB_URL)
db = mongo["amarktai_mkt"]
users_col = db["users"]
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
r = redis.from_url(REDIS_URL, decode_responses=True)

# Pricing tiers
TIERS = {
    "starter": {"name": "Starter", "price_zar": 349, "campaigns_month": 3, "posts_month": 75},
    "growth": {"name": "Growth", "price_zar": 699, "campaigns_month": 8, "posts_month": 200},
    "pro": {"name": "Pro", "price_zar": 1299, "campaigns_month": 20, "posts_month": 500},
    "agency": {"name": "Agency", "price_zar": 2499, "campaigns_month": 50, "posts_month": 1250},
}


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    tier: str = "starter"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserInfo(BaseModel):
    id: str
    email: str
    name: str
    tier: str
    campaigns_used: int
    campaigns_limit: int
    credits_used: float
    created_at: str


def create_token(user_id: str, email: str, tier: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": user_id, "email": email, "tier": tier, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        user = users_col.find_one({"_id": payload["sub"]})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.post("/auth/register", response_model=TokenResponse)
async def register(req: RegisterRequest):
    if req.tier not in TIERS:
        raise HTTPException(status_code=400, detail=f"Invalid tier. Choose: {list(TIERS.keys())}")
    if users_col.find_one({"email": req.email}):
        raise HTTPException(status_code=409, detail="Email already registered")
    
    user_doc = {
        "email": req.email,
        "password_hash": pwd_ctx.hash(req.password),
        "name": req.name,
        "tier": req.tier,
        "campaigns_used": 0,
        "credits_used": 0.0,
        "created_at": datetime.utcnow().isoformat(),
        "is_active": True,
    }
    result = users_col.insert_one(user_doc)
    user_id = str(result.inserted_id)
    token = create_token(user_id, req.email, req.tier)
    
    return TokenResponse(
        access_token=token,
        user={"id": user_id, "email": req.email, "name": req.name, "tier": req.tier}
    )


@app.post("/auth/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    user = users_col.find_one({"email": req.email})
    if not user or not pwd_ctx.verify(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account disabled")
    
    token = create_token(str(user["_id"]), user["email"], user["tier"])
    return TokenResponse(
        access_token=token,
        user={"id": str(user["_id"]), "email": user["email"], "name": user["name"], "tier": user["tier"]}
    )


@app.get("/auth/me", response_model=UserInfo)
async def get_me(user=Depends(verify_token)):
    tier_info = TIERS.get(user["tier"], TIERS["starter"])
    return UserInfo(
        id=str(user["_id"]),
        email=user["email"],
        name=user["name"],
        tier=user["tier"],
        campaigns_used=user.get("campaigns_used", 0),
        campaigns_limit=tier_info["campaigns_month"],
        credits_used=user.get("credits_used", 0.0),
        created_at=user.get("created_at", ""),
    )


@app.get("/auth/tiers")
async def get_tiers():
    return TIERS


@app.post("/auth/check-quota")
async def check_quota(user=Depends(verify_token)):
    """Check if user can run another campaign"""
    tier_info = TIERS.get(user["tier"], TIERS["starter"])
    used = user.get("campaigns_used", 0)
    limit = tier_info["campaigns_month"]
    if used >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Campaign limit reached ({used}/{limit}). Upgrade your plan."
        )
    return {"allowed": True, "remaining": limit - used, "tier": user["tier"]}


@app.post("/auth/increment-usage")
async def increment_usage(
    credits_used: float = 0.0,
    user=Depends(verify_token)
):
    """Increment campaign count and credits after successful generation"""
    users_col.update_one(
        {"_id": user["_id"]},
        {"$inc": {"campaigns_used": 1, "credits_used": credits_used}}
    )
    return {"status": "updated"}


@app.get("/health")
async def health():
    try:
        db.command("ping")
        r.ping()
        return {"status": "ok", "mongodb": "connected", "redis": "connected"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
