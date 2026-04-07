# api/app/routes/sources.py
from fastapi import APIRouter, HTTPException
from ..models import SourceOut, PaginatedResponse
from ..db import query, execute

router = APIRouter(prefix="/sources", tags=["sources"])

DEV_TENANT_COUNTRIES = ["BR"]


@router.get("", response_model=PaginatedResponse)
def list_sources(page: int = 1, page_size: int = 50):
    filters = ["country_code = ANY(%s::text[])"]
    params: list = [DEV_TENANT_COUNTRIES]
    where = " AND ".join(filters)
    offset = (page - 1) * page_size

    total_rows = query(f"SELECT COUNT(*) AS n FROM sources WHERE {where}", tuple(params))
    total = total_rows[0]["n"] if total_rows else 0

    rows = query(
        f"""
        SELECT id::text, name, url, feed_url, source_type, country_code,
               language, active, status, last_fetched, created_at
        FROM sources WHERE {where}
        ORDER BY name ASC
        LIMIT %s OFFSET %s
        """,
        tuple(params) + (page_size, offset),
    )

    return PaginatedResponse(
        items=[SourceOut(**r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + page_size) < total,
    )


@router.post("/{source_id}/approve", status_code=200)
def approve_source(source_id: str):
    rows = query(
        "SELECT id FROM sources WHERE id = %s AND country_code = ANY(%s::text[])",
        (source_id, DEV_TENANT_COUNTRIES),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Source not found")

    execute(
        "UPDATE sources SET active = true, status = 'active' WHERE id = %s",
        (source_id,),
    )
    return {"id": source_id, "active": True, "status": "active"}


@router.post("/{source_id}/reject", status_code=200)
def reject_source(source_id: str):
    rows = query(
        "SELECT id FROM sources WHERE id = %s AND country_code = ANY(%s::text[])",
        (source_id, DEV_TENANT_COUNTRIES),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Source not found")

    execute(
        "UPDATE sources SET active = false, status = 'inactive' WHERE id = %s",
        (source_id,),
    )
    return {"id": source_id, "active": False, "status": "inactive"}
