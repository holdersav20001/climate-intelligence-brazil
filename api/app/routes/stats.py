# api/app/routes/stats.py
from fastapi import APIRouter, Depends
from datetime import datetime
from ..models import StatsOut
from ..db import query
from ..auth import get_current_user, CurrentUser

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsOut)
def get_stats(current_user: CurrentUser = Depends(get_current_user)):
    def count(table: str, where: str = "TRUE", params: tuple = ()) -> int:
        rows = query(f"SELECT COUNT(*) AS n FROM {table} WHERE {where}", params)
        return rows[0]["n"] if rows else 0

    return StatsOut(
        articles=count("articles", "country_codes && %s::text[]", (current_user.tenant_countries,)),
        findings=count("findings", "country_codes && %s::text[]", (current_user.tenant_countries,)),
        contacts=count("contacts", "id IN (SELECT contact_id FROM contact_countries WHERE country_code = ANY(%s::text[]))", (current_user.tenant_countries,)),
        sources=count("sources", "country_code = ANY(%s::text[])", (current_user.tenant_countries,)),
        reports=count("reports"),
        run_log=count("run_log"),
        as_of=datetime.utcnow(),
    )
