# api/app/routes/reports.py
from fastapi import APIRouter, Query
from typing import Optional
from ..models import ReportOut, PaginatedResponse
from ..db import query

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=PaginatedResponse)
def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    report_type: Optional[str] = None,
):
    filters = ["TRUE"]
    params: list = []

    if report_type:
        filters.append("report_type = %s")
        params.append(report_type)

    where = " AND ".join(filters)
    offset = (page - 1) * page_size

    total_rows = query(f"SELECT COUNT(*) AS n FROM reports WHERE {where}", tuple(params))
    total = total_rows[0]["n"] if total_rows else 0

    rows = query(
        f"""
        SELECT id::text, title, subject, body, report_type, run_date,
               sent_at, email_status, recipient_count, created_at
        FROM reports WHERE {where}
        ORDER BY run_date DESC, created_at DESC
        LIMIT %s OFFSET %s
        """,
        tuple(params) + (page_size, offset),
    )

    return PaginatedResponse(
        items=[ReportOut(**r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + page_size) < total,
    )
