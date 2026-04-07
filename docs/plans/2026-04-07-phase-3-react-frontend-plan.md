# Phase 3 — React Frontend Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the frontend stub with a full React + TypeScript application — 6 tabs, D3 world map, real-time WebSocket alerts, and full-text search.

**Architecture:** Vite + TypeScript SPA served by nginx. React Query handles data fetching and caching. D3 renders the world map. Tailwind CSS provides styling. A WebSocket hook connects to Redis pub/sub for real-time alerts. Multi-stage Docker build keeps the final image small.

**Tech Stack:** React 18 + TypeScript, Vite, Tailwind CSS, React Query, D3, recharts, axios, nginx

---

## Prerequisites

- Phase 2 stack running: `docker compose up` starts all 6 services including the FastAPI backend on port 8000
- `VITE_API_URL` and `VITE_WS_URL` available as build-time env vars (set in `.env` and forwarded in `docker-compose.yml`)
- Node 20 available locally for running `npm install` / `npm run dev` during development
- Existing `frontend/` directory (stub) will be fully replaced — no existing code to preserve

---

## Task T-301: React App Scaffold

**Files to create/modify:**
- Delete: `frontend/index.html`, `frontend/Dockerfile` (the stub versions)
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/postcss.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/context/AuthContext.tsx`
- Create: `frontend/Dockerfile`
- Create: `frontend/nginx.conf`
- Modify: `docker-compose.yml` — add `VITE_API_URL` and `VITE_WS_URL` build args to frontend service

### Step 1: Create `frontend/package.json`

```json
{
  "name": "climate-intelligence-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "axios": "^1.7.2",
    "@tanstack/react-query": "^5.51.1",
    "d3": "^7.9.0",
    "recharts": "^2.12.7",
    "topojson-client": "^3.1.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@types/d3": "^7.4.3",
    "@types/topojson-client": "^3.1.4",
    "@vitejs/plugin-react": "^4.3.1",
    "typescript": "^5.5.3",
    "vite": "^5.3.4",
    "tailwindcss": "^3.4.6",
    "postcss": "^8.4.39",
    "autoprefixer": "^10.4.19"
  }
}
```

### Step 2: Create `frontend/vite.config.ts`

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL ?? 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
```

### Step 3: Create `frontend/tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"]
}
```

### Step 4: Create `frontend/tailwind.config.ts`

```typescript
import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#f0fdf4',
          500: '#22c55e',
          700: '#15803d',
          900: '#14532d',
        },
      },
    },
  },
  plugins: [],
} satisfies Config
```

### Step 5: Create `frontend/postcss.config.js`

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

### Step 6: Create `frontend/index.html`

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Climate Intelligence Platform</title>
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

### Step 7: Create `frontend/src/main.tsx`

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
)
```

### Step 8: Create `frontend/src/index.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  body {
    @apply bg-gray-950 text-gray-100 antialiased;
  }
}
```

### Step 9: Create `frontend/src/api/client.ts`

This module creates the axios instance and attaches the JWT on every request.

```typescript
import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: BASE_URL,
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Re-export a typed helper so components import from one place
export const get = <T>(url: string, params?: Record<string, unknown>) =>
  apiClient.get<T>(url, { params }).then((r) => r.data)

export const post = <T>(url: string, data?: unknown) =>
  apiClient.post<T>(url, data).then((r) => r.data)

export const patch = <T>(url: string, data?: unknown) =>
  apiClient.patch<T>(url, data).then((r) => r.data)
```

### Step 10: Create `frontend/src/context/AuthContext.tsx`

```typescript
import React, { createContext, useContext, useState, useCallback } from 'react'

interface AuthContextValue {
  token: string | null
  login: (token: string, subscriberName: string, plan: string) => void
  logout: () => void
  subscriberName: string
  plan: string
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(
    () => localStorage.getItem('access_token')
  )
  const [subscriberName, setSubscriberName] = useState(
    () => localStorage.getItem('subscriber_name') ?? 'Demo User'
  )
  const [plan, setPlan] = useState(
    () => localStorage.getItem('subscriber_plan') ?? 'starter'
  )

  const login = useCallback((t: string, name: string, p: string) => {
    localStorage.setItem('access_token', t)
    localStorage.setItem('subscriber_name', name)
    localStorage.setItem('subscriber_plan', p)
    setToken(t)
    setSubscriberName(name)
    setPlan(p)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('subscriber_name')
    localStorage.removeItem('subscriber_plan')
    setToken(null)
    setSubscriberName('Demo User')
    setPlan('starter')
  }, [])

  return (
    <AuthContext.Provider value={{ token, login, logout, subscriberName, plan }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
```

### Step 11: Create `frontend/src/App.tsx` (minimal shell — expanded in T-302)

```typescript
import { AuthProvider } from './context/AuthContext'
import Layout from './components/Layout'

export default function App() {
  return (
    <AuthProvider>
      <Layout />
    </AuthProvider>
  )
}
```

### Step 12: Create `frontend/Dockerfile` (multi-stage)

```dockerfile
# ── Stage 1: build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app

ARG VITE_API_URL
ARG VITE_WS_URL
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WS_URL=$VITE_WS_URL

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# ── Stage 2: serve ────────────────────────────────────────────────────────────
FROM nginx:alpine AS runner
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Step 13: Create `frontend/nginx.conf`

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    # All routes fall back to index.html (SPA)
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API calls to backend (only used if VITE_API_URL points to /api prefix)
    location /api/ {
        proxy_pass http://api:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Proxy WebSocket
    location /ws/ {
        proxy_pass http://api:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
}
```

### Step 14: Update `docker-compose.yml` frontend service

Find the `frontend:` service block and ensure it has:

```yaml
  frontend:
    build:
      context: ./frontend
      args:
        VITE_API_URL: ${VITE_API_URL:-http://localhost:8000}
        VITE_WS_URL: ${VITE_WS_URL:-ws://localhost:8000}
    ports:
      - "80:80"
    depends_on:
      - api
```

### Verification

```bash
cd frontend && npm install && npm run build
# Should complete with no TypeScript errors and output dist/ folder

docker compose build frontend
# Should produce a multi-stage build, final image < 50 MB

docker compose up frontend
# Browse http://localhost:80 — expect a blank page (no Layout yet) with no console errors
```

### Commit

```bash
git add frontend/
git commit -m "T-301: scaffold Vite+TypeScript React app with axios, React Query, Tailwind"
```

---

## Task T-302: Tab Navigation and Layout

**Files to create:**
- `frontend/src/components/Layout.tsx`
- `frontend/src/components/Header.tsx`
- `frontend/src/components/TabBar.tsx`
- `frontend/src/components/GlobalFilterBar.tsx`
- `frontend/src/context/FilterContext.tsx`
- `frontend/src/types/index.ts`

### Step 1: Create shared types in `frontend/src/types/index.ts`

```typescript
export type TabId =
  | 'dashboard'
  | 'worldmap'
  | 'findings'
  | 'contacts'
  | 'sources'
  | 'reports'

export interface GlobalFilter {
  country: string   // '' = all countries
  sector: string    // '' = all sectors
}

export interface StatsResponse {
  stories_today: number
  open_findings: number
  sentiment_today: number
  active_sources: number
}
```

### Step 2: Create `frontend/src/context/FilterContext.tsx`

```typescript
import React, { createContext, useContext, useState } from 'react'
import type { GlobalFilter } from '../types'

interface FilterContextValue {
  filter: GlobalFilter
  setFilter: React.Dispatch<React.SetStateAction<GlobalFilter>>
}

const FilterContext = createContext<FilterContextValue | null>(null)

export function FilterProvider({ children }: { children: React.ReactNode }) {
  const [filter, setFilter] = useState<GlobalFilter>({ country: '', sector: '' })
  return (
    <FilterContext.Provider value={{ filter, setFilter }}>
      {children}
    </FilterContext.Provider>
  )
}

export function useFilter() {
  const ctx = useContext(FilterContext)
  if (!ctx) throw new Error('useFilter must be used within FilterProvider')
  return ctx
}
```

### Step 3: Create `frontend/src/components/GlobalFilterBar.tsx`

```typescript
import { useFilter } from '../context/FilterContext'

const COUNTRIES = [
  { value: '',   label: 'All countries' },
  { value: 'BR', label: 'Brazil' },
  { value: 'AR', label: 'Argentina' },
  { value: 'CL', label: 'Chile' },
  { value: 'CO', label: 'Colombia' },
  { value: 'MX', label: 'Mexico' },
]

const SECTORS = [
  { value: '',       label: 'All sectors' },
  { value: 'solar',  label: 'Solar' },
  { value: 'wind',   label: 'Wind' },
  { value: 'hydro',  label: 'Hydro' },
  { value: 'policy', label: 'Policy' },
  { value: 'finance',label: 'Finance' },
]

export default function GlobalFilterBar() {
  const { filter, setFilter } = useFilter()

  return (
    <div className="flex gap-3 px-4 py-2 bg-gray-900 border-b border-gray-800">
      <select
        value={filter.country}
        onChange={(e) => setFilter((f) => ({ ...f, country: e.target.value }))}
        className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-500"
      >
        {COUNTRIES.map((c) => (
          <option key={c.value} value={c.value}>{c.label}</option>
        ))}
      </select>

      <select
        value={filter.sector}
        onChange={(e) => setFilter((f) => ({ ...f, sector: e.target.value }))}
        className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-500"
      >
        {SECTORS.map((s) => (
          <option key={s.value} value={s.value}>{s.label}</option>
        ))}
      </select>
    </div>
  )
}
```

### Step 4: Create `frontend/src/components/TabBar.tsx`

```typescript
import type { TabId } from '../types'

interface TabBarProps {
  active: TabId
  onChange: (tab: TabId) => void
}

const TABS: { id: TabId; label: string }[] = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'worldmap',  label: 'World Map' },
  { id: 'findings',  label: 'Findings' },
  { id: 'contacts',  label: 'Contacts' },
  { id: 'sources',   label: 'Sources' },
  { id: 'reports',   label: 'Reports' },
]

export default function TabBar({ active, onChange }: TabBarProps) {
  return (
    <nav className="flex gap-1 px-4 bg-gray-900 border-b border-gray-800 overflow-x-auto">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={[
            'px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors',
            active === tab.id
              ? 'text-brand-500 border-b-2 border-brand-500'
              : 'text-gray-400 hover:text-gray-100',
          ].join(' ')}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  )
}
```

### Step 5: Create `frontend/src/components/Header.tsx`

```typescript
import { useAuth } from '../context/AuthContext'
import { useAlertCount } from '../hooks/useAlerts'

interface HeaderProps {
  onSearchOpen: () => void
}

export default function Header({ onSearchOpen }: HeaderProps) {
  const { subscriberName, plan } = useAuth()
  const alertCount = useAlertCount()

  const planColour =
    plan === 'pro'      ? 'bg-blue-600' :
    plan === 'standard' ? 'bg-brand-700' :
                          'bg-gray-600'

  return (
    <header className="flex items-center justify-between px-4 py-3 bg-gray-950 border-b border-gray-800">
      <div className="flex items-center gap-3">
        <span className="text-brand-500 font-bold text-lg tracking-tight">
          Climate Intelligence
        </span>
        <span className="hidden sm:inline text-gray-500 text-sm">Brazil &amp; LatAm</span>
      </div>

      <div className="flex items-center gap-3">
        {/* Search trigger */}
        <button
          onClick={onSearchOpen}
          className="text-gray-400 hover:text-gray-100 p-1.5 rounded hover:bg-gray-800 transition-colors"
          aria-label="Open search"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </button>

        {/* Alert badge */}
        {alertCount > 0 && (
          <span className="relative flex h-5 w-5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-5 w-5 bg-red-500 text-white text-xs items-center justify-center font-bold">
              {alertCount > 9 ? '9+' : alertCount}
            </span>
          </span>
        )}

        {/* Subscriber info */}
        <span className="text-gray-300 text-sm hidden sm:block">{subscriberName}</span>
        <span className={`${planColour} text-white text-xs font-semibold px-2 py-0.5 rounded uppercase tracking-wider`}>
          {plan}
        </span>
      </div>
    </header>
  )
}
```

### Step 6: Create `frontend/src/components/Layout.tsx`

```typescript
import { useState } from 'react'
import { FilterProvider } from '../context/FilterContext'
import Header from './Header'
import TabBar from './TabBar'
import GlobalFilterBar from './GlobalFilterBar'
import DashboardTab from '../tabs/DashboardTab'
import WorldMapTab from '../tabs/WorldMapTab'
import FindingsTab from '../tabs/FindingsTab'
import ContactsTab from '../tabs/ContactsTab'
import SourcesTab from '../tabs/SourcesTab'
import ReportsTab from '../tabs/ReportsTab'
import SearchModal from './SearchModal'
import ToastContainer from './ToastContainer'
import type { TabId } from '../types'

export default function Layout() {
  const [activeTab, setActiveTab] = useState<TabId>('dashboard')
  const [searchOpen, setSearchOpen] = useState(false)

  return (
    <FilterProvider>
      <div className="flex flex-col h-screen overflow-hidden">
        <Header onSearchOpen={() => setSearchOpen(true)} />
        <TabBar active={activeTab} onChange={setActiveTab} />
        <GlobalFilterBar />

        <main className="flex-1 overflow-auto">
          {activeTab === 'dashboard' && <DashboardTab />}
          {activeTab === 'worldmap'  && <WorldMapTab />}
          {activeTab === 'findings'  && <FindingsTab />}
          {activeTab === 'contacts'  && <ContactsTab />}
          {activeTab === 'sources'   && <SourcesTab />}
          {activeTab === 'reports'   && <ReportsTab />}
        </main>
      </div>

      {searchOpen && <SearchModal onClose={() => setSearchOpen(false)} />}
      <ToastContainer />
    </FilterProvider>
  )
}
```

Also create stub tab files so TypeScript compiles now (full implementations come in T-303 through T-308):

- `frontend/src/tabs/DashboardTab.tsx` — `export default function DashboardTab() { return <div className="p-6 text-gray-400">Dashboard loading…</div> }`
- `frontend/src/tabs/WorldMapTab.tsx` — same pattern
- `frontend/src/tabs/FindingsTab.tsx` — same pattern
- `frontend/src/tabs/ContactsTab.tsx` — same pattern
- `frontend/src/tabs/SourcesTab.tsx` — same pattern
- `frontend/src/tabs/ReportsTab.tsx` — same pattern
- `frontend/src/components/SearchModal.tsx` — `export default function SearchModal({ onClose }: { onClose: () => void }) { return <div onClick={onClose} className="fixed inset-0 bg-black/60 z-50 flex items-start justify-center pt-20"><div className="bg-gray-900 rounded-xl p-6 w-full max-w-xl">Search coming in T-310</div></div> }`
- `frontend/src/components/ToastContainer.tsx` — `export default function ToastContainer() { return null }`
- `frontend/src/hooks/useAlerts.ts` — `export function useAlertCount() { return 0 }` (stub; full impl in T-309)

### Verification

```
npm run build  →  no TS errors
docker compose up frontend
Open http://localhost:80
Expected: header with "Climate Intelligence", 6 tabs, country/sector dropdowns
Click each tab → text "… loading…" appears with no errors
Resize to mobile width (< 640px) → tab bar scrolls horizontally, dropdowns stack
```

### Commit

```bash
git add frontend/src/
git commit -m "T-302: tab navigation, header, global filter bar, layout shell"
```

---

## Task T-303: Dashboard Tab

**Files to create/modify:**
- `frontend/src/tabs/DashboardTab.tsx` (replace stub)
- `frontend/src/components/MetricCard.tsx`
- `frontend/src/components/SignificanceBadge.tsx`
- `frontend/src/components/InfluenceDots.tsx`
- `frontend/src/api/queries.ts`

### Step 1: Create `frontend/src/api/queries.ts`

Centralise all React Query calls here so tabs import from one place.

```typescript
import { useQuery } from '@tanstack/react-query'
import { get } from './client'
import type { GlobalFilter } from '../types'

// ── Stats ────────────────────────────────────────────────────────────────────
export interface Stats {
  stories_today: number
  open_findings: number
  sentiment_today: number
  active_sources: number
}

export function useStats() {
  return useQuery({ queryKey: ['stats'], queryFn: () => get<Stats>('/stats') })
}

// ── Articles ─────────────────────────────────────────────────────────────────
export interface Article {
  id: string
  title: string
  source_domain: string
  significance: number
  fetched_at: string
  country: string
  sector: string
  summary: string
}

export function useArticles(filter: GlobalFilter, opts?: { limit?: number; q?: string }) {
  return useQuery({
    queryKey: ['articles', filter, opts],
    queryFn: () =>
      get<Article[]>('/articles', {
        country: filter.country || undefined,
        sector: filter.sector || undefined,
        limit: opts?.limit ?? 20,
        q: opts?.q || undefined,
      }),
  })
}

// ── Findings ─────────────────────────────────────────────────────────────────
export interface Finding {
  id: string
  title: string
  body: string
  priority: 'CRITICAL' | 'HIGH' | 'COALITION' | 'EVIDENCE' | 'FINANCE' | 'COP30'
  agent: string
  created_at: string
  deadline: string | null
  action_required: string | null
  source_url: string | null
  related_articles: Article[]
  related_contacts: Contact[]
}

export function useFindings(priority?: string) {
  return useQuery({
    queryKey: ['findings', priority],
    queryFn: () =>
      get<Finding[]>('/findings', priority ? { priority } : undefined),
  })
}

// ── Contacts ─────────────────────────────────────────────────────────────────
export interface Contact {
  id: string
  name: string
  role: string
  organisation: string
  organisation_category: 'government' | 'allied' | 'monitor' | 'opposition'
  influence_score: number
  decision_power: number
  why_relevant: string | null
  ngo_access: number | null
}

export function useContacts(sort?: string) {
  return useQuery({
    queryKey: ['contacts', sort],
    queryFn: () => get<Contact[]>('/contacts', sort ? { sort } : undefined),
  })
}

// ── Sources ──────────────────────────────────────────────────────────────────
export interface Source {
  id: string
  name: string
  url: string
  feed_url: string | null
  source_type: string
  country: string
  language: string
  reliability_score: number
  last_fetched: string | null
  fetch_frequency: string
  status: 'active' | 'candidate' | 'inactive'
}

export function useSources() {
  return useQuery({
    queryKey: ['sources'],
    queryFn: () => get<Source[]>('/sources'),
  })
}

// ── Reports ──────────────────────────────────────────────────────────────────
export interface Report {
  id: string
  title: string
  report_type: 'daily_digest' | 'brief' | 'submission'
  run_date: string
  email_status: 'sent' | 'pending' | 'failed'
  body: string
}

export function useReports() {
  return useQuery({
    queryKey: ['reports'],
    queryFn: () => get<Report[]>('/reports'),
  })
}
```

### Step 2: Create `frontend/src/components/MetricCard.tsx`

```typescript
interface MetricCardProps {
  label: string
  value: string | number
  colour?: 'default' | 'red' | 'amber' | 'green'
  loading?: boolean
}

const COLOUR_MAP = {
  default: 'border-gray-700',
  red:     'border-red-500',
  amber:   'border-amber-500',
  green:   'border-brand-500',
}

export default function MetricCard({ label, value, colour = 'default', loading }: MetricCardProps) {
  return (
    <div className={`bg-gray-900 border-l-4 ${COLOUR_MAP[colour]} rounded-r-lg p-4`}>
      <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</p>
      {loading ? (
        <div className="h-8 bg-gray-800 rounded animate-pulse w-16" />
      ) : (
        <p className="text-2xl font-bold text-gray-100">{value}</p>
      )}
    </div>
  )
}
```

### Step 3: Create `frontend/src/components/SignificanceBadge.tsx`

```typescript
interface Props { value: number }

export default function SignificanceBadge({ value }: Props) {
  const { label, classes } =
    value >= 0.8 ? { label: 'HIGH',   classes: 'bg-red-900/60 text-red-300 border border-red-700' } :
    value >= 0.5 ? { label: 'MED',    classes: 'bg-amber-900/60 text-amber-300 border border-amber-700' } :
                   { label: 'LOW',    classes: 'bg-gray-800 text-gray-400 border border-gray-700' }

  return (
    <span className={`text-xs font-semibold px-1.5 py-0.5 rounded ${classes}`}>
      {label} {value.toFixed(2)}
    </span>
  )
}
```

### Step 4: Create `frontend/src/components/InfluenceDots.tsx`

```typescript
interface Props { score: number; max?: number }

export default function InfluenceDots({ score, max = 5 }: Props) {
  return (
    <span className="flex gap-0.5">
      {Array.from({ length: max }).map((_, i) => (
        <span
          key={i}
          className={`w-2 h-2 rounded-full ${i < Math.round(score) ? 'bg-brand-500' : 'bg-gray-700'}`}
        />
      ))}
    </span>
  )
}
```

### Step 5: Replace `frontend/src/tabs/DashboardTab.tsx`

```typescript
import { useStats, useArticles, useContacts } from '../api/queries'
import { useFilter } from '../context/FilterContext'
import MetricCard from '../components/MetricCard'
import SignificanceBadge from '../components/SignificanceBadge'
import InfluenceDots from '../components/InfluenceDots'

function sentimentColour(s: number): 'red' | 'amber' | 'green' {
  return s < -0.2 ? 'red' : s > 0.2 ? 'green' : 'amber'
}

export default function DashboardTab() {
  const { filter } = useFilter()
  const { data: stats, isLoading: statsLoading } = useStats()
  const { data: articles, isLoading: articlesLoading } = useArticles(filter, { limit: 10 })
  const { data: contacts, isLoading: contactsLoading } = useContacts('influence')

  const topContacts = contacts?.slice(0, 8) ?? []

  return (
    <div className="p-4 grid grid-cols-1 lg:grid-cols-4 gap-4 h-full">

      {/* Metric cards — full width row */}
      <div className="lg:col-span-4 grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label="Stories Today"   value={stats?.stories_today  ?? '–'} loading={statsLoading} />
        <MetricCard label="Open Findings"   value={stats?.open_findings  ?? '–'} loading={statsLoading} colour="amber" />
        <MetricCard
          label="Sentiment Today"
          value={stats ? stats.sentiment_today.toFixed(2) : '–'}
          loading={statsLoading}
          colour={stats ? sentimentColour(stats.sentiment_today) : 'default'}
        />
        <MetricCard label="Active Sources"  value={stats?.active_sources ?? '–'} loading={statsLoading} colour="green" />
      </div>

      {/* Latest stories feed — 3 cols */}
      <div className="lg:col-span-3 bg-gray-900 rounded-xl p-4 overflow-auto">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Latest Stories</h2>
        {articlesLoading && (
          <div className="space-y-2">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-12 bg-gray-800 rounded animate-pulse" />
            ))}
          </div>
        )}
        {articles?.map((a) => (
          <div key={a.id} className="flex items-start gap-3 py-2.5 border-b border-gray-800 last:border-0">
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-200 truncate">{a.title}</p>
              <p className="text-xs text-gray-500 mt-0.5">
                {a.source_domain} · {new Date(a.fetched_at).toLocaleString()}
              </p>
            </div>
            <SignificanceBadge value={a.significance} />
          </div>
        ))}
        {articles?.length === 0 && (
          <p className="text-gray-500 text-sm">No stories match the current filter.</p>
        )}
      </div>

      {/* Top contacts sidebar — 1 col */}
      <div className="lg:col-span-1 bg-gray-900 rounded-xl p-4 overflow-auto">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Top Contacts</h2>
        {contactsLoading && (
          <div className="space-y-2">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-10 bg-gray-800 rounded animate-pulse" />
            ))}
          </div>
        )}
        {topContacts.map((c) => (
          <div key={c.id} className="py-2.5 border-b border-gray-800 last:border-0">
            <p className="text-sm text-gray-200">{c.name}</p>
            <p className="text-xs text-gray-500 truncate">{c.role}</p>
            <InfluenceDots score={c.influence_score} />
          </div>
        ))}
      </div>
    </div>
  )
}
```

### Verification

```
docker compose up
Open Dashboard tab
Expected:
  - 4 metric cards with live numbers from GET /stats
  - Stories list with significance badges (red/amber/green)
  - Contacts sidebar with influence dots
  - Changing country dropdown filters stories list (React Query refetches)
  - Sentiment card changes colour based on value
```

### Commit

```bash
git add frontend/src/
git commit -m "T-303: dashboard tab with metric cards, stories feed, contacts sidebar"
```

---

## Task T-304: World Map Tab

This is the most complex task. It is broken into 5 sub-steps. Each sub-step can be committed independently.

**Files to create/modify:**
- `frontend/src/tabs/WorldMapTab.tsx` (replace stub)
- `frontend/src/hooks/useWorldData.ts`
- `frontend/src/components/MapLegend.tsx`
- `frontend/src/index.css` (add pulse keyframe)

### Sub-step A: D3 Base Map

**Goal:** Render a GeoJSON world map inside a responsive SVG. No data yet — just grey country shapes.

```typescript
// frontend/src/tabs/WorldMapTab.tsx  — Sub-step A skeleton

import { useEffect, useRef } from 'react'
import * as d3 from 'd3'
import * as topojson from 'topojson-client'
import type { Topology, GeometryCollection } from 'topojson-specification'

const WORLD_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json'
const WIDTH = 960
const HEIGHT = 500

export default function WorldMapTab() {
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    if (!svgRef.current) return

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const projection = d3.geoNaturalEarth1()
      .scale(160)
      .translate([WIDTH / 2, HEIGHT / 2])

    const path = d3.geoPath().projection(projection)

    fetch(WORLD_URL)
      .then((r) => r.json())
      .then((world: Topology) => {
        const countries = topojson.feature(
          world,
          world.objects['countries'] as GeometryCollection
        )
        svg.append('g')
          .selectAll('path')
          .data((countries as GeoJSON.FeatureCollection).features)
          .join('path')
          .attr('d', path as unknown as string)
          .attr('fill', '#1f2937')
          .attr('stroke', '#374151')
          .attr('stroke-width', 0.5)
      })
  }, [])

  return (
    <div className="relative w-full h-full bg-gray-950 flex flex-col">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="w-full flex-1"
        preserveAspectRatio="xMidYMid meet"
      />
    </div>
  )
}
```

Verify: world map renders with dark-grey countries and slightly lighter borders.

### Sub-step B: Country Circles

**Goal:** Overlay SVG circles at country centroids, sized by story count, coloured by sentiment.

Create `frontend/src/hooks/useWorldData.ts`:

```typescript
import { useQuery } from '@tanstack/react-query'
import { get } from '../api/client'
import { useFilter } from '../context/FilterContext'

export interface CountryMapData {
  iso_num: string        // ISO 3166-1 numeric, matches TopoJSON id
  country_code: string   // ISO 3166-1 alpha-2
  story_count: number
  sentiment_avg: number | null
  top_story_title: string | null
  critical_findings: number
  has_subscription: boolean
}

export function useWorldData(date?: string) {
  const { filter } = useFilter()
  return useQuery({
    queryKey: ['world-data', date, filter.sector],
    queryFn: () =>
      get<CountryMapData[]>('/stats/world', {
        date: date || undefined,
        sector: filter.sector || undefined,
      }),
    staleTime: 60_000,
  })
}
```

> **Backend note:** `GET /stats/world` does not exist yet — it must be added in the FastAPI layer before this hook is useful. The endpoint should aggregate `articles` by country and join with findings. The hook gracefully returns an empty array on 404 so the map still renders.

Extend `WorldMapTab.tsx` to overlay circles after the base map renders:

```typescript
// Add to WorldMapTab.tsx after the base-map effect

// Country centroid lookup (ISO numeric → [lon, lat])
// A subset is hardcoded here for the countries we care about most.
// Full list can be generated from the same world-atlas data.
const CENTROIDS: Record<string, [number, number]> = {
  '076': [-51.9, -14.2],  // Brazil
  '032': [-63.6, -38.4],  // Argentina
  '152': [-71.5, -35.7],  // Chile
  '170': [-74.3,   4.5],  // Colombia
  '484': [-102.5, 23.6],  // Mexico
  '858': [-55.8, -32.5],  // Uruguay
  '068': [-64.9, -16.3],  // Bolivia
  '600': [-58.4, -23.4],  // Paraguay
  '218': [-78.1,  -1.8],  // Ecuador
  '604': [-75.0, -10.0],  // Peru
}

// Inside the component, add a second useEffect that runs when worldData changes:
useEffect(() => {
  if (!svgRef.current || !worldData) return
  const svg = d3.select(svgRef.current)
  // Remove previous circles
  svg.selectAll('circle.country-bubble').remove()

  const projection = d3.geoNaturalEarth1()
    .scale(160)
    .translate([WIDTH / 2, HEIGHT / 2])

  const maxCount = Math.max(...worldData.map((d) => d.story_count), 1)
  const rScale = d3.scaleSqrt().domain([0, maxCount]).range([5, 40])

  worldData.forEach((d) => {
    const centroid = CENTROIDS[d.iso_num]
    if (!centroid) return
    const [x, y] = projection(centroid) ?? [0, 0]

    const fill =
      !d.has_subscription          ? '#6b7280' :
      d.sentiment_avg === null      ? '#6b7280' :
      d.sentiment_avg < -0.2        ? '#ef4444' :
      d.sentiment_avg <= 0.2        ? '#f59e0b' :
                                      '#22c55e'

    svg.append('circle')
      .attr('class', `country-bubble country-${d.iso_num}`)
      .attr('cx', x)
      .attr('cy', y)
      .attr('r', rScale(d.story_count))
      .attr('fill', fill)
      .attr('fill-opacity', 0.75)
      .attr('stroke', '#fff')
      .attr('stroke-width', 0.8)
      .style('cursor', 'pointer')
  })
}, [worldData])
```

Verify: circles appear over Brazil, Argentina, Chile, Mexico, Colombia in correct sizes and colours.

### Sub-step C: Click-to-Popup Handler

Add a popup component and click handler.

Create `frontend/src/components/MapPopup.tsx`:

```typescript
import type { CountryMapData } from '../hooks/useWorldData'

interface Props {
  data: CountryMapData
  x: number
  y: number
  onClose: () => void
  onViewAll: (countryCode: string) => void
}

export default function MapPopup({ data, x, y, onClose, onViewAll }: Props) {
  const sentiment =
    data.sentiment_avg === null ? 'No data' :
    data.sentiment_avg < -0.2   ? '🔴 Negative' :
    data.sentiment_avg <= 0.2   ? '🟡 Neutral'  :
                                   '🟢 Positive'

  return (
    <div
      style={{ left: x, top: y }}
      className="absolute z-20 bg-gray-800 border border-gray-600 rounded-xl shadow-2xl p-4 w-64 text-sm"
    >
      <button
        onClick={onClose}
        className="absolute top-2 right-2 text-gray-400 hover:text-gray-100"
        aria-label="Close popup"
      >✕</button>

      <p className="font-semibold text-gray-100 mb-2">{data.country_code}</p>
      <div className="space-y-1 text-gray-300">
        <p>Stories (24h): <span className="text-white font-medium">{data.story_count}</span></p>
        <p>Sentiment: {sentiment}</p>
        <p>Critical findings: <span className="text-red-400 font-medium">{data.critical_findings}</span></p>
        {data.top_story_title && (
          <p className="text-gray-400 italic text-xs mt-1 line-clamp-2">{data.top_story_title}</p>
        )}
      </div>
      {!data.has_subscription && (
        <p className="mt-2 text-xs text-gray-500">🔒 Upgrade to see full data for this country</p>
      )}
      <button
        onClick={() => onViewAll(data.country_code)}
        className="mt-3 w-full text-center text-xs text-brand-500 hover:text-brand-400 font-medium"
      >
        View all articles →
      </button>
    </div>
  )
}
```

In `WorldMapTab.tsx` add click event to the circles:

```typescript
// After appending the circle, chain .on('click', ...):
.on('click', (event: MouseEvent, _datum) => {
  const rect = svgRef.current!.getBoundingClientRect()
  setPopup({ data: d, x: event.clientX - rect.left + 12, y: event.clientY - rect.top + 12 })
})
```

Add `useState<{ data: CountryMapData; x: number; y: number } | null>(null)` for `popup` and render `<MapPopup>` inside the wrapper div when it is set.

Verify: clicking a country bubble opens a popup with story count and sentiment. Clicking ✕ closes it.

### Sub-step D: Pulse Animation

When a CRITICAL alert arrives via WebSocket, the relevant country circle should pulse.

Add to `frontend/src/index.css`:

```css
@keyframes pulse-ring {
  0%   { r: var(--base-r); opacity: 0.8; }
  50%  { r: calc(var(--base-r) * 1.5); opacity: 0.3; }
  100% { r: var(--base-r); opacity: 0.8; }
}

.country-pulse {
  animation: pulse-ring 1s ease-in-out 3;
}
```

In `WorldMapTab.tsx`, subscribe to alert events:

```typescript
// Accept pulseCountry prop from parent via a custom event or context
useEffect(() => {
  function handleAlert(e: Event) {
    const { isoNum } = (e as CustomEvent).detail as { isoNum: string }
    const circle = svgRef.current?.querySelector(`.country-${isoNum}`)
    if (circle) {
      circle.classList.remove('country-pulse')
      // Force reflow to restart animation
      void (circle as SVGCircleElement).getBoundingClientRect()
      circle.classList.add('country-pulse')
    }
  }
  window.addEventListener('climate:alert', handleAlert)
  return () => window.removeEventListener('climate:alert', handleAlert)
}, [])
```

In `useAlerts.ts` (T-309), when a CRITICAL alert arrives, dispatch:
```typescript
window.dispatchEvent(new CustomEvent('climate:alert', { detail: { isoNum: alert.iso_num } }))
```

Verify: to test without a live WebSocket, open the browser console and run:
```javascript
window.dispatchEvent(new CustomEvent('climate:alert', { detail: { isoNum: '076' } }))
```
Brazil's circle should pulse 3 times and stop.

### Sub-step E: Time Slider

Add a 30-day lookback slider below the map.

```typescript
// Add to WorldMapTab.tsx state:
const [sliderDays, setSliderDays] = useState(0)  // 0 = today, 30 = 30 days ago

// Compute date string from slider:
const mapDate = sliderDays === 0
  ? undefined
  : new Date(Date.now() - sliderDays * 86_400_000).toISOString().slice(0, 10)

// Pass mapDate to useWorldData:
const { data: worldData } = useWorldData(mapDate)

// Render slider below the SVG:
```

```tsx
<div className="px-6 pb-4 flex items-center gap-4">
  <span className="text-xs text-gray-500 whitespace-nowrap">30 days ago</span>
  <input
    type="range"
    min={0}
    max={30}
    step={1}
    value={sliderDays}
    onChange={(e) => setSliderDays(Number(e.target.value))}
    className="flex-1 accent-brand-500"
  />
  <span className="text-xs text-gray-500 whitespace-nowrap">
    {sliderDays === 0 ? 'Today' : mapDate}
  </span>
</div>
```

Verify: dragging slider left changes the date string, React Query refetches `/stats/world?date=YYYY-MM-DD`, map circles update sizes and colours.

### Step: Add `MapLegend`

Create `frontend/src/components/MapLegend.tsx`:

```typescript
export default function MapLegend() {
  return (
    <div className="absolute bottom-12 left-4 bg-gray-900/80 rounded-lg p-3 text-xs text-gray-300 space-y-1.5">
      <p className="font-semibold text-gray-200 mb-1">Sentiment</p>
      {[
        { colour: '#ef4444', label: 'Negative (< −0.2)' },
        { colour: '#f59e0b', label: 'Neutral (−0.2 to +0.2)' },
        { colour: '#22c55e', label: 'Positive (> +0.2)' },
        { colour: '#6b7280', label: 'No data / locked' },
      ].map(({ colour, label }) => (
        <div key={label} className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: colour }} />
          {label}
        </div>
      ))}
      <p className="font-semibold text-gray-200 mt-2 mb-1">Circle size</p>
      <p className="text-gray-400">Proportional to story count (last 24h)</p>
    </div>
  )
}
```

Add `<MapLegend />` inside the wrapper div.

### Commit after all sub-steps

```bash
git add frontend/src/
git commit -m "T-304: D3 world map with country bubbles, popup, pulse animation, time slider"
```

---

## Task T-305: Findings Tab

**Files to create/modify:**
- `frontend/src/tabs/FindingsTab.tsx` (replace stub)
- `frontend/src/components/FindingCard.tsx`
- `frontend/src/components/PriorityBadge.tsx`

### Step 1: Create `frontend/src/components/PriorityBadge.tsx`

```typescript
import type { Finding } from '../api/queries'

const STYLES: Record<Finding['priority'], string> = {
  CRITICAL:  'bg-red-900/60 text-red-300 border border-red-700',
  HIGH:      'bg-amber-900/60 text-amber-300 border border-amber-700',
  COALITION: 'bg-brand-900/60 text-brand-300 border border-brand-700',
  EVIDENCE:  'bg-blue-900/60 text-blue-300 border border-blue-700',
  FINANCE:   'bg-purple-900/60 text-purple-300 border border-purple-700',
  COP30:     'bg-teal-900/60 text-teal-300 border border-teal-700',
}

export default function PriorityBadge({ priority }: { priority: Finding['priority'] }) {
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded ${STYLES[priority]}`}>
      {priority}
    </span>
  )
}
```

### Step 2: Create `frontend/src/components/FindingCard.tsx`

```typescript
import { useState } from 'react'
import type { Finding } from '../api/queries'
import PriorityBadge from './PriorityBadge'

const BORDER_COLOURS: Record<Finding['priority'], string> = {
  CRITICAL:  'border-red-500',
  HIGH:      'border-amber-500',
  COALITION: 'border-brand-500',
  EVIDENCE:  'border-blue-500',
  FINANCE:   'border-purple-500',
  COP30:     'border-teal-500',
}

function deadlineCountdown(deadline: string): string {
  const diff = new Date(deadline).getTime() - Date.now()
  if (diff < 0) return 'Overdue'
  const days = Math.floor(diff / 86_400_000)
  return days === 0 ? 'Due today' : `${days}d remaining`
}

export default function FindingCard({ finding }: { finding: Finding }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div
      className={`bg-gray-900 border-l-4 ${BORDER_COLOURS[finding.priority]} rounded-r-xl mb-3 cursor-pointer`}
      onClick={() => setExpanded((e) => !e)}
    >
      {/* Header row */}
      <div className="flex items-start gap-3 p-4">
        <PriorityBadge priority={finding.priority} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-100">{finding.title}</p>
          <p className="text-xs text-gray-500 mt-0.5">
            {finding.agent} · {new Date(finding.created_at).toLocaleDateString()}
            {finding.deadline && (
              <span className="ml-2 text-amber-400">{deadlineCountdown(finding.deadline)}</span>
            )}
          </p>
        </div>
        <span className="text-gray-600 text-xs">{expanded ? '▲' : '▼'}</span>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="px-4 pb-4 border-t border-gray-800 pt-3 space-y-3 text-sm text-gray-300">
          <p>{finding.body}</p>
          {finding.action_required && (
            <div className="bg-amber-950/40 border border-amber-800 rounded p-2">
              <p className="text-xs font-semibold text-amber-400 mb-1">Action required</p>
              <p className="text-xs">{finding.action_required}</p>
            </div>
          )}
          {finding.source_url && (
            <a href={finding.source_url} target="_blank" rel="noreferrer"
               className="text-xs text-blue-400 hover:underline block" onClick={(e) => e.stopPropagation()}>
              Source →
            </a>
          )}
          {finding.related_articles?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-400 mb-1">Related articles</p>
              <ul className="space-y-0.5">
                {finding.related_articles.map((a) => (
                  <li key={a.id} className="text-xs text-gray-400 truncate">• {a.title}</li>
                ))}
              </ul>
            </div>
          )}
          {finding.related_contacts?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-400 mb-1">Related contacts</p>
              <ul className="space-y-0.5">
                {finding.related_contacts.map((c) => (
                  <li key={c.id} className="text-xs text-gray-400">• {c.name} — {c.role}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
```

### Step 3: Replace `frontend/src/tabs/FindingsTab.tsx`

```typescript
import { useState } from 'react'
import { useFindings } from '../api/queries'
import type { Finding } from '../api/queries'
import FindingCard from '../components/FindingCard'

type Filter = 'ALL' | Finding['priority']

const FILTERS: Filter[] = ['ALL', 'CRITICAL', 'HIGH', 'COALITION', 'EVIDENCE', 'FINANCE', 'COP30']

export default function FindingsTab() {
  const [activeFilter, setActiveFilter] = useState<Filter>('ALL')
  const { data: findings, isLoading } = useFindings(
    activeFilter === 'ALL' ? undefined : activeFilter
  )

  return (
    <div className="p-4 max-w-4xl mx-auto">
      {/* Filter bar */}
      <div className="flex gap-2 mb-4 overflow-x-auto pb-1">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setActiveFilter(f)}
            className={[
              'px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors',
              activeFilter === f
                ? 'bg-brand-700 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700',
            ].join(' ')}
          >
            {f}
          </button>
        ))}
      </div>

      {isLoading && (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-16 bg-gray-900 rounded-xl animate-pulse" />
          ))}
        </div>
      )}

      {findings?.map((f) => (
        <FindingCard key={f.id} finding={f} />
      ))}

      {!isLoading && findings?.length === 0 && (
        <p className="text-gray-500 text-center py-12">No findings for this filter.</p>
      )}
    </div>
  )
}
```

### Verification

```
Open Findings tab
Expected:
  - Filter buttons across top: ALL CRITICAL HIGH COALITION EVIDENCE FINANCE COP30
  - Finding cards with colour-coded left borders
  - Click a card: expands body, action_required block (amber), related articles/contacts
  - CRITICAL filter: only red-bordered cards shown
  - Deadline countdown visible on findings with deadline field set
```

### Commit

```bash
git add frontend/src/
git commit -m "T-305: findings tab with priority filter, expandable cards, deadline countdown"
```

---

## Task T-306: Contacts Tab

**Files to create/modify:**
- `frontend/src/tabs/ContactsTab.tsx` (replace stub)
- `frontend/src/components/ContactCard.tsx`
- `frontend/src/components/ContactModal.tsx`

### Step 1: Create `frontend/src/components/ContactCard.tsx`

```typescript
import type { Contact } from '../api/queries'
import InfluenceDots from './InfluenceDots'

interface Props {
  contact: Contact
  onClick: () => void
}

export default function ContactCard({ contact, onClick }: Props) {
  return (
    <div
      onClick={onClick}
      className="bg-gray-900 rounded-xl p-3 cursor-pointer hover:bg-gray-800 transition-colors"
    >
      <p className="text-sm font-medium text-gray-100">{contact.name}</p>
      <p className="text-xs text-gray-400 truncate">{contact.role}</p>
      <p className="text-xs text-gray-500 truncate">{contact.organisation}</p>
      <div className="flex gap-4 mt-2">
        <div>
          <p className="text-xs text-gray-600 mb-0.5">Influence</p>
          <InfluenceDots score={contact.influence_score} />
        </div>
        <div>
          <p className="text-xs text-gray-600 mb-0.5">Decision</p>
          <InfluenceDots score={contact.decision_power} />
        </div>
      </div>
    </div>
  )
}
```

### Step 2: Create `frontend/src/components/ContactModal.tsx`

```typescript
import { useState } from 'react'
import type { Contact } from '../api/queries'
import InfluenceDots from './InfluenceDots'
import { patch } from '../api/client'
import { useQueryClient } from '@tanstack/react-query'

interface Props {
  contact: Contact
  onClose: () => void
}

export default function ContactModal({ contact, onClose }: Props) {
  const qc = useQueryClient()
  const [ngoAccess, setNgoAccess] = useState(contact.ngo_access ?? 0)
  const [saving, setSaving] = useState(false)

  async function saveAccess() {
    setSaving(true)
    await patch(`/contacts/${contact.id}/access`, { ngo_access: ngoAccess })
    qc.invalidateQueries({ queryKey: ['contacts'] })
    setSaving(false)
  }

  return (
    <div
      className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-gray-900 rounded-2xl shadow-2xl w-full max-w-lg p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-100">{contact.name}</h2>
            <p className="text-sm text-gray-400">{contact.role} · {contact.organisation}</p>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-200 text-xl">✕</button>
        </div>

        <div className="space-y-4 text-sm text-gray-300">
          <div className="flex gap-6">
            <div>
              <p className="text-xs text-gray-500 mb-1">Influence</p>
              <InfluenceDots score={contact.influence_score} />
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">Decision power</p>
              <InfluenceDots score={contact.decision_power} />
            </div>
          </div>

          {contact.why_relevant && (
            <div>
              <p className="text-xs text-gray-500 mb-1">Why relevant</p>
              <p>{contact.why_relevant}</p>
            </div>
          )}

          <div>
            <p className="text-xs text-gray-500 mb-1">NGO access score (editable)</p>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={0}
                max={5}
                step={1}
                value={ngoAccess}
                onChange={(e) => setNgoAccess(Number(e.target.value))}
                className="flex-1 accent-brand-500"
              />
              <span className="text-gray-300 w-4 text-center">{ngoAccess}</span>
              <button
                onClick={saveAccess}
                disabled={saving}
                className="text-xs bg-brand-700 hover:bg-brand-600 text-white px-3 py-1 rounded disabled:opacity-50"
              >
                {saving ? 'Saving…' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
```

### Step 3: Replace `frontend/src/tabs/ContactsTab.tsx`

```typescript
import { useState } from 'react'
import { useContacts } from '../api/queries'
import type { Contact } from '../api/queries'
import ContactCard from '../components/ContactCard'
import ContactModal from '../components/ContactModal'

export default function ContactsTab() {
  const { data: contacts, isLoading } = useContacts('influence')
  const [selected, setSelected] = useState<Contact | null>(null)

  const gov = contacts?.filter((c) => c.organisation_category === 'government')
    .sort((a, b) => b.decision_power - a.decision_power || b.influence_score - a.influence_score) ?? []

  const ngo = contacts?.filter((c) => c.organisation_category !== 'government')
    .sort((a, b) => {
      const order = { allied: 0, monitor: 1, opposition: 2 }
      return (order[a.organisation_category as keyof typeof order] ?? 3)
           - (order[b.organisation_category as keyof typeof order] ?? 3)
    }) ?? []

  if (isLoading) {
    return (
      <div className="p-4 grid grid-cols-2 gap-4">
        {[...Array(12)].map((_, i) => (
          <div key={i} className="h-20 bg-gray-900 rounded-xl animate-pulse" />
        ))}
      </div>
    )
  }

  return (
    <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4 h-full">
      {/* Government */}
      <div>
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
          Government ({gov.length})
        </h2>
        <div className="space-y-2 overflow-auto">
          {gov.map((c) => (
            <ContactCard key={c.id} contact={c} onClick={() => setSelected(c)} />
          ))}
        </div>
      </div>

      {/* NGO / Civil society */}
      <div>
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
          NGO &amp; Civil Society ({ngo.length})
        </h2>
        <div className="space-y-2 overflow-auto">
          {ngo.map((c) => (
            <ContactCard key={c.id} contact={c} onClick={() => setSelected(c)} />
          ))}
        </div>
      </div>

      {selected && (
        <ContactModal contact={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  )
}
```

### Verification

```
Open Contacts tab
Expected:
  - Left column: government contacts sorted by decision_power desc
  - Right column: NGO contacts — allied first, then monitor, then opposition
  - Click any card: modal opens showing name, scores, why_relevant, NGO access slider
  - Drag NGO access slider and click Save: PATCH /contacts/{id}/access fires (check Network tab)
  - Modal closes when clicking backdrop
```

### Commit

```bash
git add frontend/src/
git commit -m "T-306: contacts tab with split government/NGO view and editable access modal"
```

---

## Task T-307: Sources Tab

**Files to create/modify:**
- `frontend/src/tabs/SourcesTab.tsx` (replace stub)
- `frontend/src/components/ReliabilityBar.tsx`

### Step 1: Create `frontend/src/components/ReliabilityBar.tsx`

```typescript
export default function ReliabilityBar({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const colour = score >= 0.7 ? 'bg-brand-500' : score >= 0.4 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-700 rounded-full h-1.5">
        <div className={`${colour} h-1.5 rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-400 w-7 text-right">{pct}%</span>
    </div>
  )
}
```

### Step 2: Replace `frontend/src/tabs/SourcesTab.tsx`

```typescript
import { useState } from 'react'
import { useSources } from '../api/queries'
import type { Source } from '../api/queries'
import ReliabilityBar from '../components/ReliabilityBar'
import { post } from '../api/client'
import { useQueryClient } from '@tanstack/react-query'

export default function SourcesTab() {
  const { data: sources, isLoading } = useSources()
  const qc = useQueryClient()
  const [actioning, setActioning] = useState<string | null>(null)

  const active     = sources?.filter((s) => s.status === 'active') ?? []
  const candidates = sources?.filter((s) => s.status === 'candidate') ?? []

  async function handleApprove(id: string) {
    setActioning(id)
    await post(`/sources/${id}/approve`)
    qc.invalidateQueries({ queryKey: ['sources'] })
    setActioning(null)
  }

  async function handleReject(id: string) {
    setActioning(id)
    await post(`/sources/${id}/reject`)
    qc.invalidateQueries({ queryKey: ['sources'] })
    setActioning(null)
  }

  const typeBadge = (t: string) => (
    <span className="text-xs px-1.5 py-0.5 rounded bg-gray-800 text-gray-400 border border-gray-700">{t}</span>
  )

  if (isLoading) {
    return <div className="p-4 text-gray-500">Loading sources…</div>
  }

  return (
    <div className="p-4 space-y-6 max-w-5xl mx-auto">

      {/* Candidate queue */}
      {candidates.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-amber-400 uppercase tracking-wider mb-3">
            Candidate sources ({candidates.length})
          </h2>
          <div className="space-y-2">
            {candidates.map((s) => (
              <div key={s.id} className="bg-gray-900 rounded-xl p-3 flex items-center gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-200 font-medium">{s.name}</p>
                  <p className="text-xs text-gray-500 truncate">{s.url}</p>
                </div>
                {typeBadge(s.source_type)}
                <button
                  onClick={() => handleApprove(s.id)}
                  disabled={actioning === s.id}
                  className="text-xs bg-brand-700 hover:bg-brand-600 text-white px-3 py-1 rounded disabled:opacity-40"
                >Approve</button>
                <button
                  onClick={() => handleReject(s.id)}
                  disabled={actioning === s.id}
                  className="text-xs bg-red-800 hover:bg-red-700 text-white px-3 py-1 rounded disabled:opacity-40"
                >Reject</button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Active sources table */}
      <div>
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
          Active sources ({active.length})
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-500 border-b border-gray-800">
                <th className="text-left pb-2 pr-4">Name</th>
                <th className="text-left pb-2 pr-4">Type</th>
                <th className="text-left pb-2 pr-4">Country</th>
                <th className="text-left pb-2 pr-4 w-32">Reliability</th>
                <th className="text-left pb-2 pr-4">Last fetched</th>
                <th className="text-left pb-2">Frequency</th>
              </tr>
            </thead>
            <tbody>
              {active.map((s) => (
                <tr key={s.id} className="border-b border-gray-800/50 hover:bg-gray-900/50">
                  <td className="py-2 pr-4">
                    <a href={s.url} target="_blank" rel="noreferrer"
                       className="text-gray-200 hover:text-brand-400">{s.name}</a>
                  </td>
                  <td className="py-2 pr-4">{typeBadge(s.source_type)}</td>
                  <td className="py-2 pr-4 text-gray-400">{s.country}</td>
                  <td className="py-2 pr-4"><ReliabilityBar score={s.reliability_score} /></td>
                  <td className="py-2 pr-4 text-gray-500 text-xs">
                    {s.last_fetched ? new Date(s.last_fetched).toLocaleString() : '—'}
                  </td>
                  <td className="py-2 text-gray-500 text-xs">{s.fetch_frequency}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
```

### Verification

```
Open Sources tab
Expected:
  - "Candidate sources" section (amber header) appears when candidates exist
  - Approve / Reject buttons POST to /sources/{id}/approve or /sources/{id}/reject
  - After action, source disappears from candidate list (React Query invalidation)
  - Active sources table with reliability bars (green ≥ 70%, amber 40–70%, red < 40%)
  - Clicking source name opens URL in new tab
```

### Commit

```bash
git add frontend/src/
git commit -m "T-307: sources tab with candidate queue approve/reject and active sources table"
```

---

## Task T-308: Reports Tab

**Files to create/modify:**
- `frontend/src/tabs/ReportsTab.tsx` (replace stub)
- `frontend/src/components/MarkdownRenderer.tsx`

### Step 1: Install `react-markdown` (add to `package.json` dependencies)

```json
"react-markdown": "^9.0.1"
```

### Step 2: Create `frontend/src/components/MarkdownRenderer.tsx`

```typescript
import ReactMarkdown from 'react-markdown'

export default function MarkdownRenderer({ content }: { content: string }) {
  return (
    <article className="prose prose-invert prose-sm max-w-none text-gray-300
                        prose-headings:text-gray-100 prose-a:text-blue-400
                        prose-strong:text-gray-200 prose-code:text-brand-400">
      <ReactMarkdown>{content}</ReactMarkdown>
    </article>
  )
}
```

Add Tailwind typography plugin: `npm install -D @tailwindcss/typography` and add `require('@tailwindcss/typography')` to `tailwind.config.ts` plugins.

### Step 3: Replace `frontend/src/tabs/ReportsTab.tsx`

```typescript
import { useState } from 'react'
import { useReports } from '../api/queries'
import type { Report } from '../api/queries'
import MarkdownRenderer from '../components/MarkdownRenderer'
import { post } from '../api/client'

type TypeFilter = 'all' | 'daily_digest' | 'brief' | 'submission'

const TYPE_LABELS: Record<TypeFilter, string> = {
  all:          'All',
  daily_digest: 'Digests',
  brief:        'Briefs',
  submission:   'Submissions',
}

const STATUS_BADGE: Record<Report['email_status'], string> = {
  sent:    'bg-brand-900/60 text-brand-300',
  pending: 'bg-amber-900/60 text-amber-300',
  failed:  'bg-red-900/60 text-red-300',
}

export default function ReportsTab() {
  const { data: reports, isLoading } = useReports()
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all')
  const [selected, setSelected] = useState<Report | null>(null)
  const [resending, setResending] = useState<string | null>(null)

  const filtered = reports?.filter(
    (r) => typeFilter === 'all' || r.report_type === typeFilter
  ) ?? []

  async function handleResend(id: string, e: React.MouseEvent) {
    e.stopPropagation()
    setResending(id)
    await post(`/reports/${id}/resend`)
    setResending(null)
  }

  function handlePrint(e: React.MouseEvent) {
    e.stopPropagation()
    window.print()
  }

  return (
    <div className="flex h-full">
      {/* List panel */}
      <div className="w-80 flex-shrink-0 border-r border-gray-800 flex flex-col">
        {/* Type filter */}
        <div className="flex gap-1 p-3 flex-wrap border-b border-gray-800">
          {(Object.keys(TYPE_LABELS) as TypeFilter[]).map((f) => (
            <button
              key={f}
              onClick={() => setTypeFilter(f)}
              className={[
                'px-2 py-1 rounded text-xs font-medium transition-colors',
                typeFilter === f
                  ? 'bg-brand-700 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700',
              ].join(' ')}
            >
              {TYPE_LABELS[f]}
            </button>
          ))}
        </div>

        {/* Report list */}
        <div className="flex-1 overflow-auto">
          {isLoading && (
            <div className="p-3 space-y-2">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-14 bg-gray-900 rounded animate-pulse" />
              ))}
            </div>
          )}
          {filtered.map((r) => (
            <div
              key={r.id}
              onClick={() => setSelected(r)}
              className={[
                'p-3 cursor-pointer border-b border-gray-800 hover:bg-gray-900/50',
                selected?.id === r.id ? 'bg-gray-900' : '',
              ].join(' ')}
            >
              <p className="text-sm text-gray-200 line-clamp-2">{r.title}</p>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs text-gray-500">{r.run_date}</span>
                <span className={`text-xs px-1.5 py-0.5 rounded ${STATUS_BADGE[r.email_status]}`}>
                  {r.email_status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Detail panel */}
      <div className="flex-1 overflow-auto p-6">
        {selected ? (
          <>
            <div className="flex items-start justify-between mb-4 gap-4">
              <h1 className="text-lg font-semibold text-gray-100">{selected.title}</h1>
              <div className="flex gap-2 flex-shrink-0">
                <button
                  onClick={(e) => handleResend(selected.id, e)}
                  disabled={resending === selected.id}
                  className="text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 px-3 py-1.5 rounded disabled:opacity-40"
                >
                  {resending === selected.id ? 'Sending…' : 'Resend'}
                </button>
                <button
                  onClick={handlePrint}
                  className="text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 px-3 py-1.5 rounded"
                >
                  Download PDF
                </button>
              </div>
            </div>
            <MarkdownRenderer content={selected.body} />
          </>
        ) : (
          <div className="h-full flex items-center justify-center text-gray-600">
            Select a report to read it
          </div>
        )}
      </div>
    </div>
  )
}
```

### Verification

```
Open Reports tab
Expected:
  - Left panel: list of reports with type badges, email status coloured badges
  - Type filter buttons filter list immediately (client-side, no refetch)
  - Click report: right panel renders full markdown body
  - Resend button POSTs to /reports/{id}/resend
  - Download PDF triggers browser print dialog
```

### Commit

```bash
git add frontend/src/
git commit -m "T-308: reports tab with markdown render, resend, print-to-PDF"
```

---

## Task T-309: Real-Time Alerts via WebSocket

**Files to create/modify:**
- `frontend/src/hooks/useAlerts.ts` (replace stub)
- `frontend/src/components/ToastContainer.tsx` (replace stub)

### Step 1: Replace `frontend/src/hooks/useAlerts.ts`

```typescript
import { useEffect, useRef, useState, useCallback } from 'react'

export interface AlertMessage {
  id: string
  title: string
  priority: 'CRITICAL' | string
  country_code: string
  iso_num: string
}

const WS_URL = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000'

// Shared alert state — module-level so multiple hooks read the same list
let _alerts: AlertMessage[] = []
const _listeners = new Set<() => void>()

function notify() {
  _listeners.forEach((fn) => fn())
}

let _ws: WebSocket | null = null

function getWs(token: string | null): WebSocket {
  if (_ws && _ws.readyState < 2) return _ws

  const url = token
    ? `${WS_URL}/ws/alerts?token=${token}`
    : `${WS_URL}/ws/alerts`

  _ws = new WebSocket(url)

  _ws.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data) as AlertMessage
      _alerts = [msg, ..._alerts].slice(0, 50) // keep last 50
      notify()

      // Trigger world map pulse
      if (msg.iso_num) {
        window.dispatchEvent(
          new CustomEvent('climate:alert', { detail: { isoNum: msg.iso_num } })
        )
      }

      // Show toast
      window.dispatchEvent(
        new CustomEvent('climate:toast', { detail: msg })
      )
    } catch {
      // non-JSON ping frames — ignore
    }
  }

  _ws.onclose = () => {
    // Reconnect after 5 seconds
    setTimeout(() => {
      const token = localStorage.getItem('access_token')
      getWs(token)
    }, 5_000)
  }

  return _ws
}

export function useAlerts() {
  const [, rerender] = useState(0)
  const token = localStorage.getItem('access_token')

  useEffect(() => {
    getWs(token)
    const listener = () => rerender((n) => n + 1)
    _listeners.add(listener)
    return () => { _listeners.delete(listener) }
  }, [token])

  const dismiss = useCallback((id: string) => {
    _alerts = _alerts.filter((a) => a.id !== id)
    notify()
  }, [])

  return { alerts: _alerts, dismiss }
}

export function useAlertCount() {
  const [count, setCount] = useState(0)
  useEffect(() => {
    const token = localStorage.getItem('access_token')
    getWs(token)
    const listener = () => setCount(_alerts.length)
    _listeners.add(listener)
    return () => { _listeners.delete(listener) }
  }, [])
  return count
}
```

### Step 2: Replace `frontend/src/components/ToastContainer.tsx`

```typescript
import { useEffect, useState } from 'react'
import type { AlertMessage } from '../hooks/useAlerts'
import PriorityBadge from './PriorityBadge'
import type { Finding } from '../api/queries'

interface Toast extends AlertMessage {
  toastId: number
}

let _toastId = 0

export default function ToastContainer() {
  const [toasts, setToasts] = useState<Toast[]>([])

  useEffect(() => {
    function handler(e: Event) {
      const msg = (e as CustomEvent).detail as AlertMessage
      const toast: Toast = { ...msg, toastId: ++_toastId }
      setToasts((prev) => [...prev, toast])

      // Auto-dismiss after 10 seconds
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.toastId !== toast.toastId))
      }, 10_000)
    }
    window.addEventListener('climate:toast', handler)
    return () => window.removeEventListener('climate:toast', handler)
  }, [])

  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full">
      {toasts.map((t) => (
        <div
          key={t.toastId}
          className="bg-gray-900 border border-red-700 rounded-xl p-4 shadow-2xl
                     flex items-start gap-3 animate-slide-in-right"
        >
          <PriorityBadge priority={t.priority as Finding['priority']} />
          <div className="flex-1 min-w-0">
            <p className="text-sm text-gray-100 font-medium">{t.title}</p>
            <p className="text-xs text-gray-500 mt-0.5">{t.country_code}</p>
          </div>
          <button
            onClick={() =>
              setToasts((prev) => prev.filter((x) => x.toastId !== t.toastId))
            }
            className="text-gray-500 hover:text-gray-200 text-sm"
          >✕</button>
        </div>
      ))}
    </div>
  )
}
```

Add the slide-in animation to `frontend/src/index.css`:

```css
@keyframes slide-in-right {
  from { transform: translateX(100%); opacity: 0; }
  to   { transform: translateX(0);    opacity: 1; }
}
.animate-slide-in-right {
  animation: slide-in-right 0.25s ease-out forwards;
}
```

### Verification

```
With backend running, open browser console
Send a test alert by running in the terminal (if Redis CLI is available):
  docker exec -it <redis-container> redis-cli PUBLISH alerts '{"id":"test-1","title":"Critical grid failure","priority":"CRITICAL","country_code":"BR","iso_num":"076"}'
Expected:
  - Toast slides in from bottom-right: shows "CRITICAL" badge and title
  - Header badge increments by 1
  - Brazil's circle on World Map tab pulses
  - Toast auto-dismisses after 10 seconds
  - Clicking ✕ dismisses immediately
  - WebSocket reconnects automatically if backend restarts (check console after docker restart api)
```

### Commit

```bash
git add frontend/src/
git commit -m "T-309: real-time WebSocket alerts with toast notifications and map pulse"
```

---

## Task T-310: Full-Text Search

**Files to create/modify:**
- `frontend/src/components/SearchModal.tsx` (replace stub)
- FastAPI: add `q` parameter to `GET /articles` with `tsvector` query (backend change)

### Step 1: Backend — add `q` query param to `GET /articles`

In the FastAPI articles endpoint, add:

```python
from typing import Optional

@router.get("/articles")
async def get_articles(
    country: Optional[str] = None,
    sector: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    q: Optional[str] = None,
    db = Depends(get_db),
):
    filters = ["1=1"]
    params: dict = {"limit": limit, "offset": offset}

    if country:
        filters.append("country = :country")
        params["country"] = country
    if sector:
        filters.append("sector = :sector")
        params["sector"] = sector
    if q:
        filters.append(
            "to_tsvector('english', title || ' ' || COALESCE(summary, '')) "
            "@@ plainto_tsquery('english', :q)"
        )
        params["q"] = q

    where = " AND ".join(filters)
    sql = f"""
        SELECT id, title, source_domain, significance, fetched_at,
               country, sector, summary
        FROM climate.articles
        WHERE {where}
        ORDER BY fetched_at DESC
        LIMIT :limit OFFSET :offset
    """
    rows = db.execute(text(sql), params).fetchall()
    return [dict(r._mapping) for r in rows]
```

### Step 2: Replace `frontend/src/components/SearchModal.tsx`

```typescript
import { useState, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { get } from '../api/client'
import type { Article } from '../api/queries'
import { useFilter } from '../context/FilterContext'
import SignificanceBadge from './SignificanceBadge'

interface Props { onClose: () => void }

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debounced
}

export default function SearchModal({ onClose }: Props) {
  const [query, setQuery] = useState('')
  const debouncedQuery = useDebounce(query, 300)
  const { filter } = useFilter()
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => { inputRef.current?.focus() }, [])

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const { data: results, isFetching } = useQuery({
    queryKey: ['search', debouncedQuery, filter],
    queryFn: () =>
      get<Article[]>('/articles', {
        q: debouncedQuery,
        country: filter.country || undefined,
        sector:  filter.sector  || undefined,
        limit: 20,
      }),
    enabled: debouncedQuery.trim().length >= 2,
  })

  return (
    <div
      className="fixed inset-0 bg-black/70 z-50 flex items-start justify-center pt-16 px-4"
      onClick={onClose}
    >
      <div
        className="bg-gray-900 rounded-2xl shadow-2xl w-full max-w-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search input */}
        <div className="flex items-center gap-3 p-4 border-b border-gray-800">
          <svg className="w-5 h-5 text-gray-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search articles… (min 2 characters)"
            className="flex-1 bg-transparent text-gray-100 placeholder-gray-500 outline-none text-sm"
          />
          {isFetching && (
            <span className="text-xs text-gray-500 animate-pulse">Searching…</span>
          )}
          <button onClick={onClose} className="text-gray-500 hover:text-gray-200">✕</button>
        </div>

        {/* Results */}
        <div className="max-h-[60vh] overflow-auto divide-y divide-gray-800">
          {results?.length === 0 && debouncedQuery.length >= 2 && !isFetching && (
            <p className="p-4 text-gray-500 text-sm text-center">
              No results for "{debouncedQuery}"
            </p>
          )}
          {results?.map((a) => (
            <div key={a.id} className="p-4 hover:bg-gray-800/50 transition-colors">
              <div className="flex items-start gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-100 font-medium">{a.title}</p>
                  {a.summary && (
                    <p className="text-xs text-gray-400 mt-0.5 line-clamp-2">{a.summary}</p>
                  )}
                  <p className="text-xs text-gray-600 mt-1">
                    {a.source_domain} · {new Date(a.fetched_at).toLocaleDateString()}
                  </p>
                </div>
                <SignificanceBadge value={a.significance} />
              </div>
            </div>
          ))}
        </div>

        {debouncedQuery.length < 2 && (
          <p className="p-4 text-gray-600 text-xs text-center">Type at least 2 characters to search</p>
        )}
      </div>
    </div>
  )
}
```

### Verification

```
Click the search icon in the header
Expected:
  - Modal opens, input focused immediately
  - Type "solar" — after 300ms debounce, GET /articles?q=solar fires (check Network tab)
  - Results appear: title, snippet, source domain, significance badge
  - Type faster than 300ms: only one request fires (debounce works)
  - Press Escape or click backdrop: modal closes
  - Change country filter while modal open: new search fires with country param
  - No results found: "No results for X" message shown
```

### Commit

```bash
git add frontend/src/ api/  # adjust path to your FastAPI module
git commit -m "T-310: full-text search modal with debounce and tsvector backend support"
```

---

## Final Integration and Docker Verification

After all tasks are committed, verify the full stack:

```bash
# 1. Verify frontend builds cleanly
cd /c/Users/Holde/development/climate-intelligence-brazil/frontend
npm install
npm run build
# Expected: no TypeScript errors, dist/ created

# 2. Build production Docker image
cd /c/Users/Holde/development/climate-intelligence-brazil
docker compose build frontend
# Expected: two-stage build, final image size < 60 MB

# 3. Start full stack
docker compose up
# Wait for all 6 services healthy

# 4. Smoke test each tab
open http://localhost

# Dashboard:  metric cards load, stories feed visible
# World Map:  countries render, circles appear (if /stats/world implemented)
# Findings:   cards load with priority filter working
# Contacts:   split gov/NGO columns visible
# Sources:    active table and candidate queue visible
# Reports:    left-panel list, right-panel markdown render
# Search:     magnifying glass opens modal, search returns results
# Alerts:     PUBLISH to Redis → toast appears, badge increments
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `npm run build` fails with TS error `Cannot find module 'd3'` | Type declarations missing | `npm install -D @types/d3 @types/topojson-client` |
| `npm run build` fails with `noUnusedLocals` | Stub files have unused imports | Remove unused imports or set `"noUnusedLocals": false` in tsconfig temporarily |
| World map SVG renders but no circles | `/stats/world` endpoint not yet implemented | Check Network tab for 404; stub endpoint returns `[]`, circles have nothing to render — expected until backend is built |
| Circles appear but all grey | `has_subscription` field returns `false` for all | Confirm subscription data in `climate.contacts` / auth layer; for local dev set `has_subscription: true` in the stub response |
| WebSocket connection fails immediately | `VITE_WS_URL` not set or backend not started | Check `.env` has `VITE_WS_URL=ws://localhost:8000`; confirm `docker compose ps` shows `api` healthy |
| Toast appears but map pulse does not | World Map tab not mounted when alert fires | Navigate to World Map tab first; the `useEffect` that registers the event listener only runs while the tab is mounted |
| `axios` requests return 401 | JWT not in localStorage | Open browser console: `localStorage.setItem('access_token', '<token from Supabase>')` |
| `axios` requests return 422 | Query param type mismatch | Ensure `country: filter.country || undefined` — passing `country: ''` causes FastAPI validation error |
| Tailwind classes not applying | `content` glob missing `src/**/*.tsx` | Verify `tailwind.config.ts` content array includes `'./src/**/*.{ts,tsx}'` |
| Docker image build fails at `npm ci` | `package-lock.json` missing | Run `npm install` locally first to generate `package-lock.json`, then commit it |
| nginx 404 on page refresh | SPA fallback not configured | Verify `nginx.conf` has `try_files $uri $uri/ /index.html;` in the location block |
| `react-markdown` not found | Not installed | `npm install react-markdown` and `npm install -D @tailwindcss/typography` |
| Resend button has no effect | `/reports/{id}/resend` endpoint missing | Implement the endpoint in FastAPI; until then the button silently fails |
| Contact NGO access PATCH returns 405 | Endpoint not implemented | Add `PATCH /contacts/{id}/access` to FastAPI accepting `{ ngo_access: int }` |
| D3 map projection off-centre on narrow screens | `viewBox` not set | Confirm `viewBox={`0 0 ${WIDTH} ${HEIGHT}`}` and `preserveAspectRatio="xMidYMid meet"` on the SVG |
| Time slider has no effect on circles | `/stats/world?date=` not supported | Implement `date` filter in the backend endpoint; slider UI works independently |
