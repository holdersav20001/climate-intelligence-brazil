# api/app/auth.py
"""
JWT authentication for the Climate Intelligence Platform API.

Two modes (controlled by AUTH_PROVIDER env var):
- local: PyJWT with JWT_SECRET — no external service, for dev/test
- supabase: Supabase-issued JWTs verified with SUPABASE_JWT_SECRET

In ENVIRONMENT=development with AUTH_PROVIDER=local and no token provided,
a default dev user is returned (BR tenant). Remove before production.
"""
import os
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

AUTH_PROVIDER = os.environ.get("AUTH_PROVIDER", "local")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
JWT_SECRET = os.environ.get("JWT_SECRET", "")
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")
ALGORITHM = "HS256"

security = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    user_id: str
    email: Optional[str] = None
    tenant_id: str
    tenant_countries: list[str]
    is_dev: bool = False


DEV_USER = CurrentUser(
    user_id="dev-user",
    email="dev@climateintel.br",
    tenant_id="dev-tenant-br",
    tenant_countries=["BR"],
    is_dev=True,
)


def _decode_local(token: str) -> CurrentUser:
    """Verify and decode a locally-issued JWT."""
    import jwt
    if not JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT_SECRET not configured",
        )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(
        user_id=payload.get("sub", ""),
        email=payload.get("email"),
        tenant_id=payload.get("tenant_id", ""),
        tenant_countries=payload.get("countries", ["BR"]),
    )


def _decode_supabase(token: str) -> CurrentUser:
    """Verify and decode a Supabase-issued JWT."""
    from jose import jwt, JWTError
    if not SUPABASE_JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPABASE_JWT_SECRET not configured",
        )
    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=[ALGORITHM],
            options={"verify_aud": False},
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    app_metadata = payload.get("app_metadata", {})
    user_metadata = payload.get("user_metadata", {})
    tenant_id = app_metadata.get("tenant_id") or user_metadata.get("tenant_id")
    tenant_countries = app_metadata.get("countries") or user_metadata.get("countries", ["BR"])

    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenant_id in token")

    return CurrentUser(
        user_id=payload.get("sub", ""),
        email=payload.get("email"),
        tenant_id=tenant_id,
        tenant_countries=tenant_countries if isinstance(tenant_countries, list) else [tenant_countries],
    )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> CurrentUser:
    # Development shortcut: no token needed in local dev
    if ENVIRONMENT == "development" and not credentials:
        return DEV_USER

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    if AUTH_PROVIDER == "supabase":
        return _decode_supabase(token)
    else:
        return _decode_local(token)
