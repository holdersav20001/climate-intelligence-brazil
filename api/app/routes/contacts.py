# api/app/routes/contacts.py
from fastapi import APIRouter, Query, Depends
from typing import Optional
from ..models import ContactOut, PaginatedResponse
from ..db import query
from ..auth import get_current_user, CurrentUser

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("", response_model=PaginatedResponse)
def list_contacts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    organisation_type: Optional[str] = None,
    min_influence: Optional[float] = None,
    current_user: CurrentUser = Depends(get_current_user),
):
    # Filter via contact_countries junction table
    filters = ["id IN (SELECT contact_id FROM contact_countries WHERE country_code = ANY(%s::text[]))"]
    params: list = [current_user.tenant_countries]

    if organisation_type:
        filters.append("organisation_type = %s")
        params.append(organisation_type)
    if min_influence is not None:
        filters.append("influence_score >= %s")
        params.append(min_influence)

    where = " AND ".join(filters)
    offset = (page - 1) * page_size

    total_rows = query(f"SELECT COUNT(*) AS n FROM contacts WHERE {where}", tuple(params))
    total = total_rows[0]["n"] if total_rows else 0

    rows = query(
        f"""
        SELECT id::text, name, role, organisation, organisation_type,
               decision_power, ngo_access, influence_score,
               profile_url, email, why_relevant, last_updated
        FROM contacts
        WHERE {where}
        ORDER BY influence_score DESC NULLS LAST, decision_power DESC NULLS LAST
        LIMIT %s OFFSET %s
        """,
        tuple(params) + (page_size, offset),
    )

    return PaginatedResponse(
        items=[ContactOut(**r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + page_size) < total,
    )
