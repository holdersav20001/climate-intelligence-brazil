# api/app/routes/stats.py
from fastapi import APIRouter
from datetime import datetime
from ..models import StatsOut
from ..db import query

router = APIRouter(prefix="/stats", tags=["stats"])

DEV_TENANT_COUNTRIES = ["BR"]


@router.get("", response_model=StatsOut)
def get_stats():
    def count(table: str, where: str = "TRUE", params: tuple = ()) -> int:
        rows = query(f"SELECT COUNT(*) AS n FROM {table} WHERE {where}", params)
        return rows[0]["n"] if rows else 0

    return StatsOut(
        articles=count("articles", "country_codes && %s::text[]", (DEV_TENANT_COUNTRIES,)),
        findings=count("findings", "country_codes && %s::text[]", (DEV_TENANT_COUNTRIES,)),
        contacts=count("contacts", "id IN (SELECT contact_id FROM contact_countries WHERE country_code = ANY(%s::text[]))", (DEV_TENANT_COUNTRIES,)),
        sources=count("sources", "country_code = ANY(%s::text[])", (DEV_TENANT_COUNTRIES,)),
        reports=count("reports"),
        run_log=count("run_log"),
        as_of=datetime.utcnow(),
    )
