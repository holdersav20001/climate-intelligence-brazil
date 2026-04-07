# api/app/routes/findings.py
from fastapi import APIRouter, Query, Depends
from typing import Optional
from ..models import FindingOut, PaginatedResponse
from ..db import query
from ..auth import get_current_user, CurrentUser

router = APIRouter(prefix="/findings", tags=["findings"])


@router.get("", response_model=PaginatedResponse)
def list_findings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    priority: Optional[str] = None,
    agent: Optional[str] = None,
    status: Optional[str] = None,
    coalition_opportunity: Optional[bool] = None,
    current_user: CurrentUser = Depends(get_current_user),
):
    filters = ["country_codes && %s::text[]"]
    params: list = [current_user.tenant_countries]

    if priority:
        filters.append("priority = %s")
        params.append(priority.upper())
    if agent:
        filters.append("agent = %s")
        params.append(agent)
    if status:
        filters.append("status = %s")
        params.append(status)
    if coalition_opportunity is not None:
        filters.append("coalition_opportunity = %s")
        params.append(coalition_opportunity)

    where = " AND ".join(filters)
    offset = (page - 1) * page_size

    total_rows = query(f"SELECT COUNT(*) AS n FROM findings WHERE {where}", tuple(params))
    total = total_rows[0]["n"] if total_rows else 0

    rows = query(
        f"""
        SELECT id::text, agent, priority, category, title, body,
               source_url, source_name, action_required, deadline,
               coalition_opportunity, evidence_value,
               country_codes, tag_slugs, status, run_date, created_at
        FROM findings
        WHERE {where}
        ORDER BY
          CASE priority
            WHEN 'CRITICAL' THEN 1
            WHEN 'HIGH' THEN 2
            WHEN 'COALITION' THEN 3
            WHEN 'EVIDENCE' THEN 4
            WHEN 'MEDIUM' THEN 5
            WHEN 'LOW' THEN 6
            ELSE 7
          END,
          created_at DESC
        LIMIT %s OFFSET %s
        """,
        tuple(params) + (page_size, offset),
    )

    return PaginatedResponse(
        items=[FindingOut(**r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + page_size) < total,
    )
