# Phase 4 — Business Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Launch-ready platform — Stripe billing, subscriber onboarding, settings, usage metering, production monitoring, and pgvector semantic search.

**Architecture:** Stripe Checkout handles payment. Webhooks update tenant plan and limits in PostgreSQL. FastAPI enforces plan limits on every request. Grafana monitors agent health and API performance. pgvector enables semantic search alongside existing keyword search.

**Tech Stack:** Stripe API + webhooks, FastAPI, Grafana, pgvector + Claude embeddings, React (onboarding wizard + settings)

---

## Task Index

| ID | Task | Estimated Effort |
|---|---|---|
| T-401 | Stripe billing | 2 days |
| T-402 | Onboarding flow | 2 days |
| T-403 | Subscriber settings page | 1.5 days |
| T-404 | Usage metering | 1 day |
| T-405 | Production monitoring | 1.5 days |
| T-406 | pgvector semantic search | 2 days |

**Total estimate:** ~10 working days. Target completion: end of August 2026 ahead of September launch.

---

## T-401: Stripe Billing

### Overview

Create three Stripe subscription products, wire up a Checkout session endpoint, handle webhooks to keep tenant state in sync, and enforce plan limits at the API layer.

### Files to create / modify

| Action | Path |
|---|---|
| CREATE | `api/routers/billing.py` |
| CREATE | `api/routers/webhooks.py` |
| MODIFY | `api/main.py` — register routers |
| MODIFY | `api/db.py` — add `update_tenant_plan()` helper |
| MODIFY | `docker-compose.yml` — add env vars |
| MODIFY | `.env.example` — document new keys |

### Step 1 — Create Stripe products

In the Stripe Dashboard (or via CLI) create three products with monthly recurring prices:

```bash
# Install Stripe CLI first: https://stripe.com/docs/stripe-cli
stripe login

stripe products create --name="Starter" --description="1 country, daily digest, 3-month data"
stripe prices create \
  --unit-amount=19900 \
  --currency=gbp \
  --recurring[interval]=month \
  --product=<starter_product_id>

stripe products create --name="Pro" --description="5 countries, real-time alerts, findings tab"
stripe prices create \
  --unit-amount=49900 \
  --currency=gbp \
  --recurring[interval]=month \
  --product=<pro_product_id>

stripe products create --name="Enterprise" --description="Unlimited countries, API key, raw export"
stripe prices create \
  --unit-amount=149900 \
  --currency=gbp \
  --recurring[interval]=month \
  --product=<enterprise_product_id>
```

Record the three `price_*` IDs — add them to `.env` as `STRIPE_PRICE_STARTER`, `STRIPE_PRICE_PRO`, `STRIPE_PRICE_ENTERPRISE`.

### Step 2 — Environment variables

Add to `.env` (and `.env.example`):

```
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_STARTER=price_...
STRIPE_PRICE_PRO=price_...
STRIPE_PRICE_ENTERPRISE=price_...
FRONTEND_URL=http://localhost:3000
```

### Step 3 — Install Stripe Python SDK

```bash
pip install stripe
# Add to api/requirements.txt:
# stripe>=8.0.0
```

### Step 4 — Create `api/routers/billing.py`

```python
import os
import stripe
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend.auth import get_current_tenant  # existing JWT dependency

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

PRICE_MAP = {
    "starter": os.environ.get("STRIPE_PRICE_STARTER"),
    "pro": os.environ.get("STRIPE_PRICE_PRO"),
    "enterprise": os.environ.get("STRIPE_PRICE_ENTERPRISE"),
}

PLAN_LIMITS = {
    "starter": 1,
    "pro": 5,
    "enterprise": 9999,  # represents unlimited
}

router = APIRouter(prefix="/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    plan: str  # "starter" | "pro" | "enterprise"


@router.post("/create-checkout-session")
async def create_checkout_session(
    body: CheckoutRequest,
    tenant=Depends(get_current_tenant),
):
    plan = body.plan.lower()
    if plan not in PRICE_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {plan}")

    price_id = PRICE_MAP[plan]
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")

    session = stripe.checkout.Session.create(
        mode="subscription",
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        customer_email=tenant["email"],
        metadata={"tenant_id": str(tenant["id"]), "plan": plan},
        success_url=f"{frontend_url}/onboarding?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{frontend_url}/pricing",
    )
    return {"checkout_url": session.url}
```

### Step 5 — Create `api/routers/webhooks.py`

```python
import os
import stripe
from fastapi import APIRouter, Request, HTTPException
from backend.db import update_tenant_plan, deactivate_tenant

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
WEBHOOK_SECRET = os.environ["STRIPE_WEBHOOK_SECRET"]

PLAN_LIMITS = {"starter": 1, "pro": 5, "enterprise": 9999}

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    obj = event["data"]["object"]

    if event["type"] in ("customer.subscription.created", "customer.subscription.updated"):
        # Retrieve metadata from the subscription's checkout session
        tenant_id = obj["metadata"].get("tenant_id")
        plan = obj["metadata"].get("plan", "starter")
        customer_id = obj["customer"]
        active = obj["status"] in ("active", "trialing")

        if tenant_id:
            await update_tenant_plan(
                tenant_id=tenant_id,
                plan=plan,
                stripe_customer=customer_id,
                country_limit=PLAN_LIMITS.get(plan, 1),
                active=active,
            )

    elif event["type"] == "customer.subscription.deleted":
        customer_id = obj["customer"]
        await deactivate_tenant(stripe_customer=customer_id)

    return {"received": True}
```

### Step 6 — Add DB helpers to `api/db.py`

```python
async def update_tenant_plan(
    tenant_id: str,
    plan: str,
    stripe_customer: str,
    country_limit: int,
    active: bool,
):
    async with get_connection() as conn:
        await conn.execute(
            """
            UPDATE climate.tenants
            SET plan = $1,
                stripe_customer = $2,
                country_limit = $3,
                active = $4
            WHERE id = $5
            """,
            plan, stripe_customer, country_limit, active, tenant_id,
        )


async def deactivate_tenant(stripe_customer: str):
    async with get_connection() as conn:
        await conn.execute(
            "UPDATE climate.tenants SET active = false WHERE stripe_customer = $1",
            stripe_customer,
        )
```

### Step 7 — Register routers in `api/main.py`

```python
from backend.routers.billing import router as billing_router
from backend.routers.webhooks import router as webhooks_router

app.include_router(billing_router)
app.include_router(webhooks_router)
```

### Step 8 — Enforce plan limits in existing request handlers

In any endpoint that accepts a `countries` query parameter, add:

```python
async def enforce_country_limit(countries: list[str], tenant: dict):
    if len(countries) > tenant["country_limit"]:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Your {tenant['plan']} plan allows {tenant['country_limit']} "
                f"country/countries. Requested: {len(countries)}."
            ),
        )
```

Apply this check at the top of affected route handlers (e.g. `GET /articles`, `GET /reports`).

### How to test

```bash
# 1. Forward webhooks locally
stripe listen --forward-to localhost:8000/webhooks/stripe

# 2. Create a checkout session (swap in a real JWT)
curl -X POST http://localhost:8000/billing/create-checkout-session \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"plan": "pro"}'
# Expect: {"checkout_url": "https://checkout.stripe.com/..."}

# 3. Complete checkout in browser using Stripe test card 4242 4242 4242 4242
# Stripe CLI should show webhook delivered and 200 response

# 4. Verify DB update
psql $DATABASE_URL -c "SELECT plan, stripe_customer, country_limit, active FROM climate.tenants WHERE email='test@example.com';"

# 5. Test plan limit enforcement
curl "http://localhost:8000/articles?countries=CO,BR,AR" \
  -H "Authorization: Bearer <starter_jwt>"
# Expect: 403 with country limit message
```

### Commit

```bash
git add api/routers/billing.py api/routers/webhooks.py api/main.py api/db.py .env.example
git commit -m "feat(T-401): Stripe billing — checkout session, webhooks, plan enforcement"
```

---

## T-402: Onboarding Flow

### Overview

A 5-step React wizard that fires after first login when `tenant.countries` is empty. Integrates with the Stripe Checkout redirect so new subscribers land directly in the wizard after payment.

### Files to create / modify

| Action | Path |
|---|---|
| CREATE | `frontend/src/components/Onboarding/OnboardingWizard.tsx` |
| CREATE | `frontend/src/components/Onboarding/steps/WelcomeStep.tsx` |
| CREATE | `frontend/src/components/Onboarding/steps/CountriesStep.tsx` |
| CREATE | `frontend/src/components/Onboarding/steps/SectorsStep.tsx` |
| CREATE | `frontend/src/components/Onboarding/steps/EmailStep.tsx` |
| CREATE | `frontend/src/components/Onboarding/steps/ConfirmStep.tsx` |
| CREATE | `api/routers/onboarding.py` |
| MODIFY | `api/main.py` — register onboarding router |
| MODIFY | `frontend/src/App.tsx` — show wizard when `tenant.countries` is empty |

### Step 1 — FastAPI endpoint `POST /onboarding/complete`

Create `api/routers/onboarding.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List
from backend.auth import get_current_tenant
from backend.db import get_connection

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


class OnboardingPayload(BaseModel):
    countries: List[str]
    sectors: List[str]
    digest_email: EmailStr


@router.post("/complete")
async def complete_onboarding(
    body: OnboardingPayload,
    tenant=Depends(get_current_tenant),
):
    tenant_id = tenant["id"]
    country_limit = tenant["country_limit"]

    if len(body.countries) > country_limit:
        raise HTTPException(
            status_code=403,
            detail=f"Plan allows {country_limit} country/countries.",
        )

    async with get_connection() as conn:
        # Save country selections
        await conn.execute(
            "UPDATE climate.tenants SET countries = $1 WHERE id = $2",
            body.countries,
            tenant_id,
        )

        # Upsert tenant_filters row
        await conn.execute(
            """
            INSERT INTO climate.tenant_filters (tenant_id, sectors, digest_email)
            VALUES ($1, $2, $3)
            ON CONFLICT (tenant_id)
            DO UPDATE SET sectors = EXCLUDED.sectors,
                          digest_email = EXCLUDED.digest_email
            """,
            tenant_id,
            body.sectors,
            body.digest_email,
        )

    return {"status": "ok"}
```

> Note: the `tenant_filters` table must exist. Add migration if needed:
> ```sql
> CREATE TABLE IF NOT EXISTS climate.tenant_filters (
>     tenant_id UUID PRIMARY KEY REFERENCES climate.tenants(id),
>     sectors TEXT[] DEFAULT '{}',
>     digest_email TEXT
> );
> ```

### Step 2 — Onboarding wizard component

`frontend/src/components/Onboarding/OnboardingWizard.tsx`:

```tsx
import { useState } from "react";
import WelcomeStep from "./steps/WelcomeStep";
import CountriesStep from "./steps/CountriesStep";
import SectorsStep from "./steps/SectorsStep";
import EmailStep from "./steps/EmailStep";
import ConfirmStep from "./steps/ConfirmStep";
import { completeOnboarding } from "../../api/onboarding";

const STEPS = ["welcome", "countries", "sectors", "email", "confirm"] as const;

export default function OnboardingWizard({ tenant, onComplete }) {
  const [step, setStep] = useState(0);
  const [data, setData] = useState({
    countries: [] as string[],
    sectors: [] as string[],
    digestEmail: tenant.email,
  });

  const next = () => setStep((s) => Math.min(s + 1, STEPS.length - 1));
  const back = () => setStep((s) => Math.max(s - 1, 0));

  const handleFinish = async () => {
    await completeOnboarding({
      countries: data.countries,
      sectors: data.sectors,
      digest_email: data.digestEmail,
    });
    onComplete();
  };

  const stepProps = { tenant, data, setData, next, back };

  return (
    <div className="onboarding-overlay">
      <div className="onboarding-card">
        <div className="onboarding-progress">
          Step {step + 1} of {STEPS.length}
        </div>
        {step === 0 && <WelcomeStep {...stepProps} />}
        {step === 1 && <CountriesStep {...stepProps} />}
        {step === 2 && <SectorsStep {...stepProps} />}
        {step === 3 && <EmailStep {...stepProps} />}
        {step === 4 && <ConfirmStep {...stepProps} onFinish={handleFinish} />}
      </div>
    </div>
  );
}
```

Each step component follows the same pattern — display relevant UI, call `setData` to update shared state, call `next` to advance. See `CountriesStep` example:

```tsx
// frontend/src/components/Onboarding/steps/CountriesStep.tsx
import { AVAILABLE_COUNTRIES } from "../../../constants/countries";

export default function CountriesStep({ tenant, data, setData, next, back }) {
  const toggle = (code: string) => {
    setData((d) => {
      const sel = d.countries.includes(code)
        ? d.countries.filter((c) => c !== code)
        : d.countries.length < tenant.country_limit
        ? [...d.countries, code]
        : d.countries;
      return { ...d, countries: sel };
    });
  };

  return (
    <div>
      <h2>Choose your countries</h2>
      <p>Your plan allows up to {tenant.country_limit} country/countries.</p>
      <div className="country-grid">
        {AVAILABLE_COUNTRIES.map((c) => (
          <button
            key={c.code}
            className={data.countries.includes(c.code) ? "selected" : ""}
            onClick={() => toggle(c.code)}
          >
            {c.name}
          </button>
        ))}
      </div>
      <button onClick={back}>Back</button>
      <button disabled={data.countries.length === 0} onClick={next}>
        Next
      </button>
    </div>
  );
}
```

### Step 3 — Wire wizard into `App.tsx`

```tsx
// After auth resolves, check if onboarding is needed
const needsOnboarding = tenant && tenant.countries.length === 0;

if (needsOnboarding) {
  return (
    <OnboardingWizard
      tenant={tenant}
      onComplete={() => refetchTenant()}
    />
  );
}
```

### Step 4 — Stripe redirect integration

The Checkout `success_url` is set to `{FRONTEND_URL}/onboarding?session_id={CHECKOUT_SESSION_ID}`. On landing at `/onboarding`, the frontend should:
1. Verify the session (optional — Stripe webhooks already update the tenant).
2. Refetch tenant data so `country_limit` reflects the new plan.
3. Render `OnboardingWizard`.

### How to test

```bash
# 1. Create a test tenant with empty countries array
psql $DATABASE_URL -c "INSERT INTO climate.tenants (name, email, plan, country_limit) VALUES ('Test', 'onboard@test.com', 'pro', 5);"

# 2. Log in as that tenant — wizard should appear immediately

# 3. Complete the wizard, then verify
psql $DATABASE_URL -c "SELECT countries FROM climate.tenants WHERE email='onboard@test.com';"
psql $DATABASE_URL -c "SELECT * FROM climate.tenant_filters WHERE tenant_id=(SELECT id FROM climate.tenants WHERE email='onboard@test.com');"

# 4. Full Stripe flow: create checkout session → complete with test card → verify redirect to /onboarding
```

### Commit

```bash
git add frontend/src/components/Onboarding/ api/routers/onboarding.py api/main.py
git commit -m "feat(T-402): onboarding wizard — 5-step flow with country/sector selection"
```

---

## T-403: Subscriber Settings Page

### Overview

A settings modal (accessible from the header) lets tenants manage country preferences, email digest settings, plan upgrades, and API keys (Enterprise only).

### Files to create / modify

| Action | Path |
|---|---|
| CREATE | `frontend/src/components/Settings/SettingsModal.tsx` |
| CREATE | `frontend/src/components/Settings/tabs/CountrySettings.tsx` |
| CREATE | `frontend/src/components/Settings/tabs/EmailSettings.tsx` |
| CREATE | `frontend/src/components/Settings/tabs/PlanSettings.tsx` |
| CREATE | `frontend/src/components/Settings/tabs/ApiKeySettings.tsx` |
| CREATE | `api/routers/settings.py` |
| MODIFY | `api/main.py` — register settings router |
| MODIFY | `api/db.py` — add `api_key_hash` column migration |
| MODIFY | `frontend/src/components/Header.tsx` — add settings button |

### Step 1 — Database migration

```sql
-- Run against production/staging PostgreSQL
ALTER TABLE climate.tenants ADD COLUMN IF NOT EXISTS api_key_hash TEXT;
```

### Step 2 — FastAPI settings router `api/routers/settings.py`

```python
import os
import secrets
import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from backend.auth import get_current_tenant
from backend.db import get_connection

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
async def get_settings(tenant=Depends(get_current_tenant)):
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT t.plan, t.country_limit, t.countries,
                   tf.sectors, tf.digest_email,
                   (t.api_key_hash IS NOT NULL) AS has_api_key
            FROM climate.tenants t
            LEFT JOIN climate.tenant_filters tf ON tf.tenant_id = t.id
            WHERE t.id = $1
            """,
            tenant["id"],
        )
    return dict(row)


class CountriesUpdate(BaseModel):
    countries: List[str]


@router.patch("/countries")
async def update_countries(
    body: CountriesUpdate,
    tenant=Depends(get_current_tenant),
):
    if len(body.countries) > tenant["country_limit"]:
        raise HTTPException(
            status_code=403,
            detail=f"Plan allows {tenant['country_limit']} country/countries.",
        )
    async with get_connection() as conn:
        await conn.execute(
            "UPDATE climate.tenants SET countries = $1 WHERE id = $2",
            body.countries,
            tenant["id"],
        )
    return {"status": "ok"}


class EmailUpdate(BaseModel):
    digest_email: Optional[EmailStr] = None
    digest_time: Optional[str] = None  # e.g. "07:00"


@router.patch("/email")
async def update_email(body: EmailUpdate, tenant=Depends(get_current_tenant)):
    async with get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO climate.tenant_filters (tenant_id, digest_email, digest_time)
            VALUES ($1, $2, $3)
            ON CONFLICT (tenant_id) DO UPDATE
              SET digest_email = COALESCE(EXCLUDED.digest_email, tenant_filters.digest_email),
                  digest_time  = COALESCE(EXCLUDED.digest_time,  tenant_filters.digest_time)
            """,
            tenant["id"],
            body.digest_email,
            body.digest_time,
        )
    return {"status": "ok"}


@router.post("/api-key")
async def generate_api_key(tenant=Depends(get_current_tenant)):
    if tenant["plan"] != "enterprise":
        raise HTTPException(status_code=403, detail="API keys are Enterprise-only.")

    raw_key = "cib_" + secrets.token_urlsafe(32)
    hashed = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()

    async with get_connection() as conn:
        await conn.execute(
            "UPDATE climate.tenants SET api_key_hash = $1 WHERE id = $2",
            hashed,
            tenant["id"],
        )

    # Return raw key once — never stored in plaintext
    return {"api_key": raw_key, "warning": "Store this key securely. It will not be shown again."}


@router.delete("/api-key")
async def revoke_api_key(tenant=Depends(get_current_tenant)):
    async with get_connection() as conn:
        await conn.execute(
            "UPDATE climate.tenants SET api_key_hash = NULL WHERE id = $1",
            tenant["id"],
        )
    return {"status": "revoked"}
```

### Step 3 — Settings modal component

`frontend/src/components/Settings/SettingsModal.tsx`:

```tsx
import { useState } from "react";
import CountrySettings from "./tabs/CountrySettings";
import EmailSettings from "./tabs/EmailSettings";
import PlanSettings from "./tabs/PlanSettings";
import ApiKeySettings from "./tabs/ApiKeySettings";

const TABS = ["Countries", "Email", "Plan", "API Key"];

export default function SettingsModal({ tenant, onClose }) {
  const [activeTab, setActiveTab] = useState(0);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Account Settings</h2>
          <button onClick={onClose}>×</button>
        </div>
        <div className="modal-tabs">
          {TABS.map((tab, i) => (
            <button
              key={tab}
              className={activeTab === i ? "active" : ""}
              onClick={() => setActiveTab(i)}
              // Hide API Key tab for non-Enterprise
              style={{ display: tab === "API Key" && tenant.plan !== "enterprise" ? "none" : undefined }}
            >
              {tab}
            </button>
          ))}
        </div>
        <div className="modal-body">
          {activeTab === 0 && <CountrySettings tenant={tenant} />}
          {activeTab === 1 && <EmailSettings tenant={tenant} />}
          {activeTab === 2 && <PlanSettings tenant={tenant} />}
          {activeTab === 3 && <ApiKeySettings tenant={tenant} />}
        </div>
      </div>
    </div>
  );
}
```

### Step 4 — Add settings button to Header

```tsx
// In frontend/src/components/Header.tsx
import { useState } from "react";
import SettingsModal from "./Settings/SettingsModal";

// Inside component:
const [showSettings, setShowSettings] = useState(false);

// In JSX:
<button onClick={() => setShowSettings(true)}>Settings</button>
{showSettings && (
  <SettingsModal tenant={tenant} onClose={() => setShowSettings(false)} />
)}
```

### How to test

```bash
# Test GET settings
curl http://localhost:8000/settings -H "Authorization: Bearer <jwt>"

# Test country update
curl -X PATCH http://localhost:8000/settings/countries \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"countries": ["BR", "CO"]}'

# Test API key generation (Enterprise JWT)
curl -X POST http://localhost:8000/settings/api-key \
  -H "Authorization: Bearer <enterprise_jwt>"
# Expect: {"api_key": "cib_...", "warning": "..."}

# Test API key revoke
curl -X DELETE http://localhost:8000/settings/api-key \
  -H "Authorization: Bearer <enterprise_jwt>"

# Verify hash in DB
psql $DATABASE_URL -c "SELECT api_key_hash IS NOT NULL FROM climate.tenants WHERE plan='enterprise' LIMIT 1;"
```

### Commit

```bash
git add frontend/src/components/Settings/ api/routers/settings.py api/main.py
git commit -m "feat(T-403): subscriber settings — countries, email, plan, API key management"
```

---

## T-404: Usage Metering

### Overview

Track API calls per tenant per month. Enforce monthly quotas. Alert at 80% usage.

### Files to create / modify

| Action | Path |
|---|---|
| CREATE | `api/middleware/usage_metering.py` |
| CREATE | `db/migrations/004_api_usage.sql` |
| MODIFY | `api/main.py` — add middleware |
| MODIFY | `api/routers/settings.py` — expose usage stats |

### Step 1 — Database migration

Create `db/migrations/004_api_usage.sql`:

```sql
CREATE TABLE IF NOT EXISTS climate.api_usage (
    tenant_id UUID REFERENCES climate.tenants(id),
    month DATE,
    request_count INTEGER DEFAULT 0,
    PRIMARY KEY (tenant_id, month)
);

CREATE INDEX IF NOT EXISTS api_usage_tenant_month_idx
    ON climate.api_usage (tenant_id, month);
```

Run:

```bash
psql $DATABASE_URL -f db/migrations/004_api_usage.sql
```

### Step 2 — Middleware `api/middleware/usage_metering.py`

```python
import asyncio
from datetime import date
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from backend.db import get_connection
from backend.auth import decode_jwt_unsafe  # extracts tenant_id without raising

SKIP_PATHS = {"/health", "/webhooks/stripe", "/docs", "/openapi.json", "/redoc"}

MONTHLY_QUOTAS = {
    "starter": 10_000,
    "pro": 50_000,
    "enterprise": None,  # unlimited
}

RATE_LIMITS = {
    "starter": 100,
    "pro": 500,
    "enterprise": 2000,
}


class UsageMeteringMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip non-metered paths
        if any(path.startswith(p) for p in SKIP_PATHS):
            return await call_next(request)

        tenant = await decode_jwt_unsafe(request)
        if not tenant:
            return await call_next(request)

        tenant_id = tenant["id"]
        plan = tenant.get("plan", "starter")
        today = date.today().replace(day=1)  # first of month

        async with get_connection() as conn:
            # Upsert usage counter
            row = await conn.fetchrow(
                """
                INSERT INTO climate.api_usage (tenant_id, month, request_count)
                VALUES ($1, $2, 1)
                ON CONFLICT (tenant_id, month)
                DO UPDATE SET request_count = climate.api_usage.request_count + 1
                RETURNING request_count
                """,
                tenant_id,
                today,
            )
            count = row["request_count"]

        # Enforce monthly quota
        quota = MONTHLY_QUOTAS.get(plan)
        if quota and count > quota:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={"detail": f"Monthly quota of {quota} requests exceeded. Upgrade your plan."},
            )

        # Fire quota warning email at 80% (async, non-blocking)
        if quota and count == int(quota * 0.8):
            asyncio.create_task(send_quota_warning(tenant, count, quota))

        response = await call_next(request)
        return response


async def send_quota_warning(tenant: dict, count: int, quota: int):
    """Send email alert when tenant hits 80% of monthly quota."""
    from backend.email import send_email  # existing email utility
    await send_email(
        to=tenant["email"],
        subject="Climate Intelligence — 80% of monthly API quota used",
        body=(
            f"Hi {tenant['name']},\n\n"
            f"You have used {count} of your {quota} monthly API requests "
            f"({count/quota*100:.0f}%).\n\n"
            "To avoid service interruption, consider upgrading your plan.\n\n"
            "— Climate Intelligence Team"
        ),
    )
```

### Step 3 — Register middleware in `api/main.py`

```python
from backend.middleware.usage_metering import UsageMeteringMiddleware

app.add_middleware(UsageMeteringMiddleware)
```

### Step 4 — Expose usage stats in settings endpoint

Add to `GET /settings` response:

```python
usage_row = await conn.fetchrow(
    """
    SELECT request_count
    FROM climate.api_usage
    WHERE tenant_id = $1 AND month = date_trunc('month', NOW())::date
    """,
    tenant["id"],
)
current_usage = usage_row["request_count"] if usage_row else 0
```

Return `current_usage` and `monthly_quota` so the frontend can display a usage bar.

### Step 5 — Frontend usage banner

In the dashboard header, if `current_usage / monthly_quota > 0.8`, show:

```tsx
{usagePct >= 0.8 && (
  <div className="usage-warning-banner">
    You've used {Math.round(usagePct * 100)}% of your monthly API quota.{" "}
    <a href="/settings?tab=plan">Upgrade your plan</a>
  </div>
)}
```

### How to test

```bash
# 1. Make 5 API calls as a test tenant, then check counter
psql $DATABASE_URL -c "SELECT request_count FROM climate.api_usage WHERE month = date_trunc('month', NOW())::date;"

# 2. Manually set count near quota to trigger warning
psql $DATABASE_URL -c "UPDATE climate.api_usage SET request_count = 7999 WHERE tenant_id='<id>' AND month=date_trunc('month', NOW())::date;"
# Next request should trigger warning email

# 3. Exceed quota
psql $DATABASE_URL -c "UPDATE climate.api_usage SET request_count = 10001 WHERE tenant_id='<id>' AND month=date_trunc('month', NOW())::date;"
curl http://localhost:8000/articles -H "Authorization: Bearer <starter_jwt>"
# Expect: 429 with quota exceeded message
```

### Commit

```bash
git add api/middleware/usage_metering.py db/migrations/004_api_usage.sql api/main.py
git commit -m "feat(T-404): usage metering — per-tenant monthly quotas, 80% alert, 429 enforcement"
```

---

## T-405: Production Monitoring

### Overview

Self-hosted Grafana on the Hetzner VM with Prometheus metrics from FastAPI, PostgreSQL, and Redis. Alerts for agent failures, API latency, and queue depth.

### Files to create / modify

| Action | Path |
|---|---|
| CREATE | `monitoring/prometheus.yml` |
| CREATE | `monitoring/grafana/provisioning/datasources/prometheus.yaml` |
| CREATE | `monitoring/grafana/provisioning/dashboards/climate.json` |
| CREATE | `monitoring/alert_rules.yml` |
| CREATE | `api/middleware/prometheus_metrics.py` |
| MODIFY | `docker-compose.yml` — add Prometheus + Grafana services |
| MODIFY | `api/main.py` — add /metrics endpoint |

### Step 1 — Install Prometheus client

```bash
pip install prometheus-client
# Add to api/requirements.txt:
# prometheus-client>=0.20.0
```

### Step 2 — FastAPI Prometheus middleware `api/middleware/prometheus_metrics.py`

```python
import time
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0],
)

ACTIVE_SUBSCRIBERS = Gauge(
    "active_subscribers_total",
    "Number of active tenants",
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start

        endpoint = request.url.path
        REQUEST_COUNT.labels(request.method, endpoint, response.status_code).inc()
        REQUEST_LATENCY.labels(request.method, endpoint).observe(duration)

        return response


def metrics_endpoint():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

Register in `api/main.py`:

```python
from backend.middleware.prometheus_metrics import PrometheusMiddleware, metrics_endpoint

app.add_middleware(PrometheusMiddleware)
app.add_route("/metrics", metrics_endpoint)
```

### Step 3 — `monitoring/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets: ["alertmanager:9093"]

scrape_configs:
  - job_name: "fastapi"
    static_configs:
      - targets: ["api:8000"]
    metrics_path: /metrics

  - job_name: "postgres"
    static_configs:
      - targets: ["postgres-exporter:9187"]

  - job_name: "redis"
    static_configs:
      - targets: ["redis-exporter:9121"]
```

### Step 4 — Alert rules `monitoring/alert_rules.yml`

```yaml
groups:
  - name: climate_intelligence
    rules:
      - alert: APIHighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API p95 latency > 2s"
          description: "95th percentile latency is {{ $value }}s"

      - alert: RedisQueueDepth
        expr: redis_list_length{key="bull:scout:waiting"} > 100
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Redis BullMQ queue depth > 100"

      - alert: ScoutAgentFailures
        expr: |
          increase(climate_agent_run_failed_total{agent="scout"}[30m]) >= 3
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "Scout Retrieval agent failed 3+ times in 30 minutes"
```

> For `ScoutAgentFailures`: add a `climate_agent_run_failed_total` counter to the Scout agent run loop. Increment it on each failed run.

### Step 5 — Grafana dashboard JSON

Create `monitoring/grafana/provisioning/dashboards/climate.json`. Key panels:

```json
{
  "title": "Climate Intelligence Platform",
  "panels": [
    {
      "title": "API Request Rate",
      "type": "graph",
      "targets": [{"expr": "rate(http_requests_total[5m])"}]
    },
    {
      "title": "API p95 Latency",
      "type": "graph",
      "targets": [{"expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"}]
    },
    {
      "title": "Active Subscribers",
      "type": "stat",
      "targets": [{"expr": "active_subscribers_total"}]
    },
    {
      "title": "Agent Run Success Rate (last 24h)",
      "type": "stat",
      "targets": [{
        "expr": "rate(climate_agent_run_success_total[24h]) / (rate(climate_agent_run_success_total[24h]) + rate(climate_agent_run_failed_total[24h]))"
      }]
    },
    {
      "title": "Redis Queue Depth",
      "type": "graph",
      "targets": [{"expr": "redis_list_length{key=~\"bull:.*:waiting\"}"}]
    },
    {
      "title": "PostgreSQL Query Time (p95)",
      "type": "graph",
      "targets": [{"expr": "pg_stat_statements_mean_time_seconds"}]
    }
  ]
}
```

### Step 6 — Docker Compose additions

Add to `docker-compose.yml`:

```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/alert_rules.yml:/etc/prometheus/alert_rules.yml
    ports:
      - "9090:9090"
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
    volumes:
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
      - grafana_data:/var/lib/grafana
    ports:
      - "3001:3000"
    depends_on:
      - prometheus
    restart: unless-stopped

  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:latest
    environment:
      DATA_SOURCE_NAME: ${DATABASE_URL}
    restart: unless-stopped

  redis-exporter:
    image: oliver006/redis_exp:latest
    environment:
      REDIS_ADDR: redis:6379
    restart: unless-stopped

volumes:
  grafana_data:
```

Add `GRAFANA_ADMIN_PASSWORD` to `.env`.

### How to test

```bash
# 1. Start monitoring stack
docker-compose up -d prometheus grafana postgres-exporter redis-exporter

# 2. Check Prometheus targets
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[].health'
# All should be "up"

# 3. Verify metrics endpoint
curl http://localhost:8000/metrics | grep http_requests_total

# 4. Open Grafana at http://localhost:3001 (admin / $GRAFANA_ADMIN_PASSWORD)
# Import dashboard from monitoring/grafana/provisioning/dashboards/climate.json

# 5. Trigger test alert
# Temporarily lower latency threshold and make slow requests, verify alert fires in Prometheus UI at http://localhost:9090/alerts
```

### Commit

```bash
git add monitoring/ api/middleware/prometheus_metrics.py api/main.py docker-compose.yml
git commit -m "feat(T-405): production monitoring — Prometheus, Grafana, alert rules for latency/queue/agents"
```

---

## T-406: pgvector Semantic Search

### Overview

Add vector embeddings to articles. Generate embeddings on ingest using the OpenAI embeddings API. Expose a semantic search endpoint. Add a toggle in the React search UI.

### Files to create / modify

| Action | Path |
|---|---|
| CREATE | `db/migrations/005_pgvector.sql` |
| CREATE | `api/services/embeddings.py` |
| MODIFY | `api/routers/articles.py` — add semantic search mode |
| MODIFY | `agents/analyst/main.py` — generate embedding after analysis |
| CREATE | `scripts/backfill_embeddings.py` |
| MODIFY | `frontend/src/components/ArticleSearch.tsx` — mode toggle |

### Step 1 — Enable pgvector and add column

Create `db/migrations/005_pgvector.sql`:

```sql
-- Enable pgvector extension (requires PostgreSQL 14+ with pgvector installed)
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column to articles
ALTER TABLE climate.articles ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- Create HNSW index for fast approximate nearest-neighbour search
CREATE INDEX IF NOT EXISTS articles_embedding_idx
    ON climate.articles
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

Run:

```bash
psql $DATABASE_URL -f db/migrations/005_pgvector.sql
```

> If pgvector is not installed on the PostgreSQL server, install it first:
> ```bash
> # On Hetzner VM (Debian/Ubuntu):
> apt install postgresql-16-pgvector
> # Or from source: https://github.com/pgvector/pgvector
> ```

### Step 2 — Embeddings service `api/services/embeddings.py`

```python
import os
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

EMBEDDING_MODEL = "text-embedding-3-small"  # 1536 dimensions, cost-effective


async def get_embedding(text: str) -> list[float]:
    """Generate a 1536-dimension embedding for the given text."""
    # Truncate to ~8000 tokens to avoid exceeding context window
    truncated = text[:32000]
    response = await client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=truncated,
    )
    return response.data[0].embedding


async def store_article_embedding(article_id: str, text: str, conn):
    """Generate embedding and store in the articles table."""
    embedding = await get_embedding(text)
    await conn.execute(
        "UPDATE climate.articles SET embedding = $1 WHERE id = $2",
        embedding,
        article_id,
    )
```

Add `OPENAI_API_KEY` to `.env` and `.env.example`.

### Step 3 — Generate embeddings on ingest in `agents/analyst/main.py`

After the Analyst agent saves analysis results, add:

```python
from backend.services.embeddings import store_article_embedding

# After article analysis is written to DB:
article_text = f"{article['title']} {article['summary']} {article['content']}"
await store_article_embedding(article["id"], article_text, conn)
```

### Step 4 — Semantic search endpoint in `api/routers/articles.py`

Add `mode` query parameter to the existing `GET /articles/search` endpoint:

```python
from backend.services.embeddings import get_embedding

@router.get("/articles/search")
async def search_articles(
    q: str,
    mode: str = "keyword",  # "keyword" | "semantic"
    limit: int = 10,
    tenant=Depends(get_current_tenant),
):
    async with get_connection() as conn:
        if mode == "semantic":
            embedding = await get_embedding(q)
            rows = await conn.fetch(
                """
                SELECT id, title, summary, published_at, country, url,
                       1 - (embedding <=> $1::vector) AS similarity
                FROM climate.articles
                WHERE embedding IS NOT NULL
                  AND country = ANY($2)
                ORDER BY embedding <=> $1::vector
                LIMIT $3
                """,
                embedding,
                tenant["countries"],
                limit,
            )
        else:
            # Existing keyword search (full-text or ILIKE)
            rows = await conn.fetch(
                """
                SELECT id, title, summary, published_at, country, url
                FROM climate.articles
                WHERE country = ANY($1)
                  AND (title ILIKE $2 OR summary ILIKE $2)
                ORDER BY published_at DESC
                LIMIT $3
                """,
                tenant["countries"],
                f"%{q}%",
                limit,
            )
    return [dict(r) for r in rows]
```

### Step 5 — Backfill existing articles

Create `scripts/backfill_embeddings.py`:

```python
"""
Batch job to generate embeddings for articles that don't have them yet.
Run with: python -m scripts.backfill_embeddings
"""
import asyncio
import os
from backend.db import get_connection
from backend.services.embeddings import store_article_embedding

BATCH_SIZE = 50  # OpenAI rate limits: adjust as needed


async def backfill():
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT id, title, summary, content
            FROM climate.articles
            WHERE embedding IS NULL
            ORDER BY published_at DESC
            """
        )

    print(f"Found {len(rows)} articles without embeddings.")

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        tasks = []
        for row in batch:
            text = f"{row['title']} {row['summary'] or ''} {row['content'] or ''}"
            tasks.append(store_article_embedding(str(row["id"]), text, None))

        # Note: store_article_embedding needs its own connection per call when conn=None
        # Adjust to open a connection per batch for production use
        await asyncio.gather(*tasks)
        print(f"Processed batch {i // BATCH_SIZE + 1} ({min(i + BATCH_SIZE, len(rows))}/{len(rows)})")

    print("Backfill complete.")


if __name__ == "__main__":
    asyncio.run(backfill())
```

Run backfill:

```bash
python -m scripts.backfill_embeddings
```

### Step 6 — React search UI toggle

In `frontend/src/components/ArticleSearch.tsx`, add a mode toggle:

```tsx
const [searchMode, setSearchMode] = useState<"keyword" | "semantic">("keyword");

// In the search form:
<div className="search-mode-toggle">
  <button
    className={searchMode === "keyword" ? "active" : ""}
    onClick={() => setSearchMode("keyword")}
  >
    Keyword
  </button>
  <button
    className={searchMode === "semantic" ? "active" : ""}
    onClick={() => setSearchMode("semantic")}
  >
    Semantic
  </button>
</div>

// Pass mode to API call:
const results = await api.get(`/articles/search?q=${q}&mode=${searchMode}`);
```

### How to test

```bash
# 1. Verify pgvector extension
psql $DATABASE_URL -c "SELECT extname FROM pg_extension WHERE extname='vector';"

# 2. Verify column exists
psql $DATABASE_URL -c "\d climate.articles" | grep embedding

# 3. Generate embedding for one article manually
python -c "
import asyncio
from backend.services.embeddings import get_embedding
emb = asyncio.run(get_embedding('energy transition coal policy Brazil'))
print(f'Embedding length: {len(emb)}, first value: {emb[0]:.4f}')
"

# 4. Test semantic search endpoint
curl "http://localhost:8000/articles/search?q=energy+job+losses&mode=semantic" \
  -H "Authorization: Bearer <jwt>"
# Expect: array of articles with similarity scores

# 5. Compare keyword vs semantic results for the same query
curl "http://localhost:8000/articles/search?q=offshore+wind&mode=keyword" -H "Authorization: Bearer <jwt>"
curl "http://localhost:8000/articles/search?q=offshore+wind&mode=semantic" -H "Authorization: Bearer <jwt>"

# 6. Run backfill and verify
python -m scripts.backfill_embeddings
psql $DATABASE_URL -c "SELECT COUNT(*) FROM climate.articles WHERE embedding IS NULL;"
# Should be 0 (or close to it)
```

### Commit

```bash
git add db/migrations/005_pgvector.sql api/services/embeddings.py api/routers/articles.py agents/analyst/main.py scripts/backfill_embeddings.py frontend/src/components/ArticleSearch.tsx
git commit -m "feat(T-406): pgvector semantic search — embeddings on ingest, search endpoint, backfill script"
```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Stripe webhook returns 400 "Invalid signature" | Wrong `STRIPE_WEBHOOK_SECRET` — test mode and live mode use different secrets | Use `stripe listen` output secret for local dev; set production secret from Stripe Dashboard → Webhooks |
| Tenant plan not updating after checkout | Subscription metadata not set on the Stripe Session | Confirm `metadata={"tenant_id": ..., "plan": ...}` is passed in `create_checkout_session` |
| `customer.subscription.created` not firing | Using Stripe test mode but listening for live events | Run `stripe listen --forward-to localhost:8000/webhooks/stripe` and use test cards |
| Onboarding wizard not appearing after payment | `tenant.countries` already non-empty from previous test data | Clear countries: `UPDATE climate.tenants SET countries='{}' WHERE id='...'` |
| `POST /onboarding/complete` 500 — `tenant_filters` table missing | Migration not run | Run `psql $DATABASE_URL -c "CREATE TABLE IF NOT EXISTS climate.tenant_filters (...)"` |
| Usage counter not incrementing | JWT not parsed by `decode_jwt_unsafe` — path not matched | Add debug logging to middleware; confirm `Authorization` header is present |
| 429 on first request | Test data left `request_count` at limit | `UPDATE climate.api_usage SET request_count=0 WHERE tenant_id='...'` |
| Prometheus target shows "down" | FastAPI `/metrics` endpoint not registered | Confirm `app.add_route("/metrics", metrics_endpoint)` is present in `main.py` |
| Grafana cannot connect to Prometheus | Wrong Prometheus URL in datasource provisioning | Set `url: http://prometheus:9090` (Docker internal DNS) |
| pgvector extension missing | PostgreSQL server doesn't have the extension installed | `apt install postgresql-16-pgvector` on the VM and reconnect |
| `embedding <=> $1::vector` type error | asyncpg doesn't know how to encode a Python list as `vector` | Register pgvector codec: `await conn.execute("SET search_path = climate, public")` and use `pgvector.asyncpg` adapter |
| Semantic search returns unrelated results | Backfill not run yet — articles have `NULL` embedding | Run `python -m scripts.backfill_embeddings` |
| OpenAI embeddings API rate limit during backfill | Sending too many requests simultaneously | Reduce `BATCH_SIZE` in backfill script and add `asyncio.sleep(1)` between batches |
| API key verify fails | Comparing raw key against hash incorrectly | Use `bcrypt.checkpw(raw_key.encode(), stored_hash.encode())` |
| Settings modal not showing for Enterprise user | `tenant.plan` not refreshed after upgrade | Call `refetchTenant()` after Stripe webhook updates plan |

---

## Pre-Launch Checklist

### Stripe & Billing

- [ ] Three Stripe products created and price IDs saved in `.env`
- [ ] Stripe webhook endpoint registered in Stripe Dashboard with correct URL (`https://api.yourdomain.com/webhooks/stripe`)
- [ ] `STRIPE_WEBHOOK_SECRET` set to live mode secret (not test mode)
- [ ] Test full checkout flow end-to-end with real card in live mode (use £1 test transaction if needed)
- [ ] Verify `customer.subscription.deleted` correctly deactivates tenant
- [ ] Plan limit enforcement tested: Starter tenant blocked from accessing >1 country

### Onboarding

- [ ] Wizard appears on first login for all new tenants
- [ ] Wizard does not reappear after `countries` is populated
- [ ] Stripe → onboarding redirect works: payment success lands on wizard with correct `country_limit`
- [ ] `tenant_filters` row created on wizard completion
- [ ] First digest email arrives the morning after onboarding (test with digest agent in staging)

### Settings

- [ ] Country updates are reflected immediately in article queries
- [ ] Email settings changes are picked up by digest agent
- [ ] API key generation works for Enterprise tenants only
- [ ] API key hash stored, raw key never persisted
- [ ] API key revocation tested

### Usage Metering

- [ ] `api_usage` table populated after test API calls
- [ ] 80% quota warning email received in staging
- [ ] 429 response returned when quota exceeded
- [ ] Usage bar displayed in frontend dashboard

### Monitoring

- [ ] All Prometheus targets show "up" in production
- [ ] Grafana dashboard loads all six panels without errors
- [ ] Test alert for API latency fires and delivers notification
- [ ] Scout agent failure alert tested by temporarily disabling Scout
- [ ] Redis queue depth alert tested
- [ ] Grafana admin password rotated from default

### Semantic Search

- [ ] pgvector extension enabled on production PostgreSQL
- [ ] HNSW index created and confirmed with `\d climate.articles`
- [ ] Backfill script completed — zero articles with `NULL` embedding
- [ ] Semantic search returns relevant results for test queries
- [ ] Keyword and semantic modes both work in frontend toggle
- [ ] Embedding generation tested in Analyst agent on a fresh article ingest

### General

- [ ] All new environment variables documented in `.env.example`
- [ ] All new DB migrations committed to `db/migrations/`
- [ ] `docker-compose.yml` tested with `docker-compose up --build` from scratch on a clean VM
- [ ] API documentation at `/docs` updated and reflects all new endpoints
- [ ] Rate limits tested: Starter at 100 req/min, Pro at 500 req/min
- [ ] GDPR: confirm tenant data deletion removes `api_usage`, `tenant_filters`, and `tenants` rows
- [ ] Security: `/metrics` endpoint is not publicly accessible (add IP allowlist or basic auth in nginx)
- [ ] Staging environment smoke-tested with representative NGO and journalist accounts
- [ ] Rollback plan documented: steps to disable billing and revert to static access if Stripe is unreachable
