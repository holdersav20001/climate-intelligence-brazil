# api/app/routes/auth.py
"""
Auth endpoints.
- POST /auth/login — returns JWT (local: self-issued, supabase: proxied)
- POST /auth/signup — creates account
- POST /auth/refresh — refresh token
"""
import os
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
import httpx

router = APIRouter(prefix="/auth", tags=["auth"])

AUTH_PROVIDER = os.environ.get("AUTH_PROVIDER", "local")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
JWT_SECRET = os.environ.get("JWT_SECRET", "")
ALGORITHM = "HS256"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str = ""


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str = ""


class RefreshRequest(BaseModel):
    refresh_token: str


def _issue_local_token(email: str, tenant_id: str, countries: list[str]) -> str:
    """Issue a local JWT for development use."""
    import jwt
    payload = {
        "sub": email,
        "email": email,
        "tenant_id": tenant_id,
        "countries": countries,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=24),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    if AUTH_PROVIDER == "local":
        if ENVIRONMENT != "development":
            raise HTTPException(
                status_code=503,
                detail="Local auth is only available in development. Set AUTH_PROVIDER=supabase for production.",
            )
        # Local dev: look up tenant by email in the database
        from ..db import query
        rows = query(
            "SELECT id::text, countries FROM tenants WHERE email = %s AND active = true",
            (body.email,),
        )
        if not rows:
            raise HTTPException(status_code=401, detail="Invalid credentials or inactive account")

        tenant = rows[0]
        token = _issue_local_token(
            email=body.email,
            tenant_id=tenant["id"],
            countries=tenant["countries"] or ["BR"],
        )
        return TokenResponse(access_token=token, expires_in=86400)

    # Supabase provider
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(status_code=503, detail="Auth service not configured")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
            json={"email": body.email, "password": body.password},
            timeout=10,
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    data = resp.json()
    return TokenResponse(
        access_token=data["access_token"],
        expires_in=data.get("expires_in", 3600),
        refresh_token=data.get("refresh_token", ""),
    )


@router.post("/signup", status_code=201)
async def signup(body: SignupRequest):
    if AUTH_PROVIDER == "local":
        if ENVIRONMENT != "development":
            raise HTTPException(status_code=503, detail="Local auth is only available in development.")
        from ..db import query, execute
        existing = query("SELECT id FROM tenants WHERE email = %s", (body.email,))
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        execute(
            """
            INSERT INTO tenants (name, email, plan, countries, active)
            VALUES (%s, %s, 'starter', %s, true)
            """,
            (body.full_name or body.email.split("@")[0], body.email, ["BR"]),
        )
        return {"message": "Account created. You can now log in."}

    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(status_code=503, detail="Auth service not configured")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/auth/v1/signup",
            headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
            json={"email": body.email, "password": body.password, "data": {"full_name": body.full_name}},
            timeout=10,
        )

    if resp.status_code not in (200, 201):
        detail = resp.json().get("msg", "Signup failed")
        raise HTTPException(status_code=400, detail=detail)

    return {"message": "Account created. Check your email to confirm."}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest):
    if AUTH_PROVIDER == "local":
        raise HTTPException(status_code=400, detail="Local auth does not use refresh tokens. Call /auth/login again.")

    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(status_code=503, detail="Auth service not configured")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=refresh_token",
            headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
            json={"refresh_token": body.refresh_token},
            timeout=10,
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    data = resp.json()
    return TokenResponse(
        access_token=data["access_token"],
        expires_in=data.get("expires_in", 3600),
        refresh_token=data.get("refresh_token", ""),
    )
