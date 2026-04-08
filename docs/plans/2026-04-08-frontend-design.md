# React Frontend Dashboard — Design

**Date:** 2026-04-08
**Status:** Approved

## Goal

Build the full Phase 3 React dashboard for the Climate Intelligence Platform — all 6 tabs, world map, real-time alerts, and Playwright e2e tests — wired to the existing FastAPI backend at port 8000.

## Architecture

```
frontend/
├── src/
│   ├── api/          # TanStack Query hooks (one file per resource)
│   ├── components/   # Shared UI (Badge, Card, Table, Spinner, Toast)
│   ├── pages/        # One component per tab
│   │   ├── Dashboard.tsx
│   │   ├── WorldMap.tsx
│   │   ├── Findings.tsx
│   │   ├── Contacts.tsx
│   │   ├── Sources.tsx
│   │   └── Reports.tsx
│   ├── hooks/        # useAlerts (WebSocket), useFilters (global state)
│   ├── App.tsx       # Tab router + global filter bar + alert toasts
│   └── main.tsx
├── tests/            # Playwright e2e (one spec per tab)
├── vite.config.ts    # Proxies /api → http://localhost:8000 in dev
├── Dockerfile        # node:20-alpine build → nginx:alpine serve
└── nginx.conf        # SPA routing + /api proxy to api:8000
```

## Tech Stack

| Concern | Library |
|---|---|
| Framework | React 18 + TypeScript |
| Build | Vite |
| Styling | Tailwind CSS |
| Data fetching | TanStack Query v5 |
| Routing | React Router v6 |
| Global state | Zustand (filters) |
| Charts | Recharts |
| World map | react-simple-maps |
| E2E tests | Playwright |

## Auth

Dev mode: API returns `DEV_USER` (Brazil tenant) when `ENVIRONMENT=development` and no auth token. No login screen needed — dashboard loads directly.

## Tab Designs

### Dashboard
- Stat cards row: Articles · Findings · Contacts · Sources · Reports (from `/stats`)
- Two-column: latest 5 findings (priority badge + title + agent + age) + latest 10 articles (title + source + significance bar)
- Recharts sparkline for findings-per-day over last 7 days

### World Map
- Full-width react-simple-maps Robinson projection
- Country circles: size = article count (24h), colour = avg sentiment (green/amber/red/grey)
- Click country → slide-out panel: top 3 findings + story count
- 30-day time slider below map
- CSS pulse animation on countries with CRITICAL findings

### Findings
- Paginated list, priority badges colour-coded (CRITICAL=red, HIGH=orange, COALITION=purple, EVIDENCE=blue, MEDIUM=yellow, LOW=grey)
- Filters: priority, agent, status
- Click row → drawer: full body, source URL, linked articles, action required, deadline countdown

### Contacts
- Two-column split: Government (left) · NGO & Allies (right)
- Cards: name + role + org + influence score bar + decision power dots
- Sorted by influence DESC; filter by org type and min influence

### Sources
- Two in-page tabs: Active (paginated table) · Pending (approve/reject buttons)
- Approve/Reject wired to `/sources/{id}/approve` and `/sources/{id}/reject`

### Reports
- List: type badge + date + subject line
- Click → full body rendered as markdown
- Email status chip (pending / sent)

## Global Filter Bar

- Country multi-select + tag/sector multi-select
- State in Zustand store — all TanStack Query hooks read from it
- Persists across tab navigation; "Clear all" resets

## Real-time Alerts

- `useAlerts` hook: WebSocket to `ws://localhost:8000/ws/alerts`
- Reconnects with 3s exponential backoff on drop
- CRITICAL finding → red toast (top-right), agent + title + "View" link, 10s auto-dismiss
- Non-CRITICAL → silently refetches findings query cache

## Docker / Build

- **Dev:** Vite dev server on port 5173, proxies `/api` → `http://localhost:8000`
- **Production:** Multi-stage Dockerfile — Vite build → nginx:alpine serving `dist/`
- `nginx.conf`: `try_files $uri /index.html` for SPA routing + `/api` proxy to `http://api:8000`
- Frontend stays on port 80 in Docker

## E2E Tests (Playwright)

One spec per tab, running against `http://localhost:5173` (Vite dev) or `http://localhost` (Docker):

| Spec | Assertions |
|---|---|
| `dashboard.spec.ts` | Stat cards render, counts > 0, findings list non-empty |
| `worldmap.spec.ts` | Map renders, Brazil circle visible, click opens panel |
| `findings.spec.ts` | List loads, priority filter works, drawer opens on click |
| `contacts.spec.ts` | Both columns render, influence scores visible |
| `sources.spec.ts` | Active list loads, approve/reject buttons present |
| `reports.spec.ts` | Report list loads, click renders body |
