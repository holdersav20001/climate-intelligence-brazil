# api/app/models.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date


class ArticleOut(BaseModel):
    id: str
    url: str
    title: str
    summary: Optional[str] = None
    source_name: Optional[str] = None
    domain: Optional[str] = None
    topic: Optional[str] = None
    significance: Optional[float] = None
    verified: bool = False
    sentiment_overall: Optional[float] = None
    sentiment_environmental: Optional[float] = None
    sentiment_economic: Optional[float] = None
    sentiment_political: Optional[float] = None
    sentiment_social: Optional[float] = None
    sentiment_framing: Optional[float] = None
    country_codes: list[str] = []
    tag_slugs: list[str] = []
    language: str = "en"
    fetched_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    run_date: Optional[date] = None


class FindingOut(BaseModel):
    id: str
    agent: str
    priority: str
    category: Optional[str] = None
    title: str
    body: str
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    action_required: Optional[str] = None
    deadline: Optional[date] = None
    coalition_opportunity: bool = False
    evidence_value: Optional[str] = None
    country_codes: list[str] = []
    tag_slugs: list[str] = []
    status: str = "open"
    run_date: Optional[date] = None
    created_at: Optional[datetime] = None


class ContactOut(BaseModel):
    id: str
    name: str
    role: str
    organisation: str
    organisation_type: Optional[str] = None
    decision_power: Optional[int] = None
    ngo_access: int = 1
    influence_score: Optional[float] = None
    profile_url: Optional[str] = None
    email: Optional[str] = None
    why_relevant: Optional[str] = None
    last_updated: Optional[datetime] = None


class SourceOut(BaseModel):
    id: str
    name: str
    url: str
    feed_url: Optional[str] = None
    source_type: Optional[str] = None
    country_code: Optional[str] = None
    language: str = "en"
    active: bool = True
    status: Optional[str] = None
    last_fetched: Optional[datetime] = None
    created_at: Optional[datetime] = None


class ReportOut(BaseModel):
    id: str
    title: str
    subject: Optional[str] = None
    body: str
    report_type: Optional[str] = None
    run_date: Optional[date] = None
    sent_at: Optional[datetime] = None
    email_status: str = "pending"
    recipient_count: int = 0
    created_at: Optional[datetime] = None


class StatsOut(BaseModel):
    articles: int
    findings: int
    contacts: int
    sources: int
    reports: int
    run_log: int
    as_of: datetime


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    has_more: bool
