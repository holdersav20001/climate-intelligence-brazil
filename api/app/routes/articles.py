# api/app/routes/articles.py
from fastapi import APIRouter, Query
from typing import Optional
from ..models import ArticleOut, PaginatedResponse
from ..db import query

router = APIRouter(prefix="/articles", tags=["articles"])

DEV_TENANT_COUNTRIES = ["BR"]


@router.get("", response_model=PaginatedResponse)
def list_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    domain: Optional[str] = None,
    min_significance: Optional[float] = None,
    topic: Optional[str] = None,
    verified: Optional[bool] = None,
    run_date: Optional[str] = None,
):
    filters = ["country_codes && %s::text[]"]
    params: list = [DEV_TENANT_COUNTRIES]

    if domain:
        filters.append("domain = %s")
        params.append(domain)
    if min_significance is not None:
        filters.append("significance >= %s")
        params.append(min_significance)
    if topic:
        filters.append("topic = %s")
        params.append(topic)
    if verified is not None:
        filters.append("verified = %s")
        params.append(verified)
    if run_date:
        filters.append("run_date = %s")
        params.append(run_date)

    where = " AND ".join(filters)
    offset = (page - 1) * page_size

    total_rows = query(f"SELECT COUNT(*) AS n FROM articles WHERE {where}", tuple(params))
    total = total_rows[0]["n"] if total_rows else 0

    rows = query(
        f"""
        SELECT id::text, url, title, summary, source_name, domain, topic,
               significance, verified,
               sentiment_overall, sentiment_environmental, sentiment_economic,
               sentiment_political, sentiment_social, sentiment_framing,
               country_codes, tag_slugs, language,
               fetched_at, published_at, run_date
        FROM articles
        WHERE {where}
        ORDER BY significance DESC NULLS LAST, fetched_at DESC
        LIMIT %s OFFSET %s
        """,
        tuple(params) + (page_size, offset),
    )

    return PaginatedResponse(
        items=[ArticleOut(**r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + page_size) < total,
    )


@router.get("/{article_id}", response_model=ArticleOut)
def get_article(article_id: str):
    rows = query(
        """
        SELECT id::text, url, title, summary, source_name, domain, topic,
               significance, verified,
               sentiment_overall, sentiment_environmental, sentiment_economic,
               sentiment_political, sentiment_social, sentiment_framing,
               country_codes, tag_slugs, language,
               fetched_at, published_at, run_date
        FROM articles WHERE id = %s AND country_codes && %s::text[]
        """,
        (article_id, DEV_TENANT_COUNTRIES),
    )
    if not rows:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Article not found")
    return ArticleOut(**rows[0])
