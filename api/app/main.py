# api/app/main.py
"""
Climate Intelligence Platform — FastAPI application
Phase 1: Full REST endpoints with tenant filtering.
JWT auth (T-110) adds real tenant_id extraction from bearer tokens.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .routes import articles, findings, contacts, sources, reports, stats, ws

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Climate Intelligence Platform API",
    version="1.0.0",
    description="Tenant-filtered energy intelligence for NGOs, think tanks, journalists.",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://app.climateintel.br",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(articles.router)
app.include_router(findings.router)
app.include_router(contacts.router)
app.include_router(sources.router)
app.include_router(reports.router)
app.include_router(stats.router)
app.include_router(ws.router)


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/")
def root():
    return {
        "name": "Climate Intelligence Platform API",
        "version": "1.0.0",
        "docs": "/docs",
    }
