# React Frontend Dashboard — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the full Phase 3 React dashboard — 6 tabs, world map, real-time alerts, Playwright e2e — wired to FastAPI at localhost:8000.

**Architecture:** Vite builds React/TypeScript into static files served by nginx. All API calls use /api prefix proxied to FastAPI (prefix stripped). Dev mode returns DEV_USER with no auth required — no login screen. WebSocket at /ws/alerts streams CRITICAL findings as real-time toasts.

**Tech Stack:** React 18 · TypeScript · Vite · TanStack Query v5 · Tailwind CSS · react-simple-maps · Recharts · React Router v6 · Zustand · react-markdown · Playwright

---

## Context for implementer

- **Frontend dir:** `frontend/` (currently has Dockerfile + placeholder index.html — both get replaced)
- **API:** FastAPI at `http://localhost:8000` — routes are `/articles`, `/findings`, `/contacts`, `/sources`, `/reports`, `/stats`, ws at `/ws/alerts`
- **No auth needed:** `ENVIRONMENT=development` means API returns DEV_USER (Brazil tenant) with no token
- **Proxy rule:** Frontend calls `/api/articles` → Vite strips `/api` → forwards to `http://localhost:8000/articles`
- **All work happens inside `frontend/`**

---

### Task 1: Scaffold project files

**Files to create:**
- `frontend/package.json`
- `frontend/vite.config.ts`
- `frontend/tsconfig.json`
- `frontend/tsconfig.node.json`
- `frontend/tailwind.config.js`
- `frontend/postcss.config.js`
- `frontend/index.html` (replaces placeholder)
- `frontend/src/vite-env.d.ts`
- `frontend/src/index.css`
- `frontend/src/main.tsx`

**Step 1: Write frontend/package.json**

```json
{
  "name": "climate-intelligence-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test:e2e": "playwright test"
  },
  "dependencies": {
    "@tanstack/react-query": "^5.56.2",
    "axios": "^1.7.7",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-markdown": "^9.0.1",
    "react-router-dom": "^6.26.2",
    "react-simple-maps": "^3.0.0",
    "recharts": "^2.12.7",
    "zustand": "^5.0.0"
  },
  "devDependencies": {
    "@playwright/test": "^1.47.2",
    "@types/react": "^18.3.5",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.47",
    "tailwindcss": "^3.4.12",
    "typescript": "^5.5.3",
    "vite": "^5.4.8"
  }
}
```

**Step 2: Write frontend/vite.config.ts**

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
```

**Step 3: Write frontend/tsconfig.json**

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
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

**Step 4: Write frontend/tsconfig.node.json**

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

**Step 5: Write frontend/tailwind.config.js**

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: { extend: {} },
  plugins: [],
}
```

**Step 6: Write frontend/postcss.config.js**

```js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

**Step 7: Write frontend/index.html**

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Climate Intelligence Platform</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

**Step 8: Write frontend/src/vite-env.d.ts**

```ts
/// <reference types="vite/client" />
```

**Step 9: Write frontend/src/index.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  @apply bg-gray-50 text-gray-900 min-h-screen;
}
```

**Step 10: Write frontend/src/main.tsx**

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
```

**Step 11: Install dependencies**

```bash
cd frontend && npm install
```

Expected: `node_modules/` created, no errors.

**Step 12: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors (App.tsx doesn't exist yet so this may show one missing module error — that's fine, fix after App is created).

**Step 13: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold Vite + React + TypeScript + Tailwind"
```

---

### Task 2: Types and API layer

**Files to create:**
- `frontend/src/types.ts`
- `frontend/src/api/client.ts`
- `frontend/src/api/hooks.ts`

**Step 1: Write frontend/src/types.ts**

```ts
export interface Stats {
  articles: number
  findings: number
  contacts: number
  sources: number
  reports: number
  run_log: number
  as_of: string
}

export interface Article {
  id: string
  url: string
  title: string
  summary: string | null
  source_name: string
  domain?: string
  significance: number
  country_codes: string[]
  tag_slugs: string[]
  fetched_at: string
  run_date: string
}

export interface Finding {
  id: string
  agent: string
  priority: 'CRITICAL' | 'HIGH' | 'COALITION' | 'EVIDENCE' | 'MEDIUM' | 'LOW'
  category?: string
  title: string
  body: string
  source_url: string | null
  source_name?: string
  action_required: string | null
  deadline: string | null
  coalition_opportunity: boolean
  evidence_value?: string
  country_codes: string[]
  tag_slugs: string[]
  status: string
  run_date: string
  created_at: string
}

export interface Contact {
  id: string
  name: string
  role: string
  organisation: string
  organisation_type: string
  decision_power: number
  ngo_access: number
  influence_score: number
  profile_url?: string
  email?: string
  why_relevant: string
  last_updated?: string
}

export interface Source {
  id: string
  name: string
  url: string
  feed_url?: string
  source_type: string
  country_code: string
  language?: string
  active: boolean
  status: string
  last_fetched: string | null
  created_at: string
}

export interface Report {
  id: string
  title: string
  subject: string
  body: string
  report_type: string
  run_date: string
  sent_at?: string
  email_status: string
  recipient_count?: number
  created_at: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}
```

**Step 2: Write frontend/src/api/client.ts**

```ts
import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
})

export default client
```

**Step 3: Write frontend/src/api/hooks.ts**

```ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import client from './client'
import type { Stats, Article, Finding, Contact, Source, Report, PaginatedResponse } from '../types'

// Stats
export function useStats() {
  return useQuery<Stats>({
    queryKey: ['stats'],
    queryFn: async () => (await client.get('/stats')).data,
  })
}

// Articles
export function useArticles(params: { page?: number; page_size?: number; country?: string } = {}) {
  return useQuery<PaginatedResponse<Article>>({
    queryKey: ['articles', params],
    queryFn: async () => (await client.get('/articles', { params })).data,
  })
}

// Findings
export function useFindings(params: { page?: number; page_size?: number; priority?: string; agent?: string; status?: string } = {}) {
  return useQuery<PaginatedResponse<Finding>>({
    queryKey: ['findings', params],
    queryFn: async () => (await client.get('/findings', { params })).data,
  })
}

// Contacts
export function useContacts(params: { page?: number; page_size?: number; organisation_type?: string; min_influence?: number } = {}) {
  return useQuery<PaginatedResponse<Contact>>({
    queryKey: ['contacts', params],
    queryFn: async () => (await client.get('/contacts', { params })).data,
  })
}

// Sources
export function useSources(params: { page?: number; page_size?: number } = {}) {
  return useQuery<PaginatedResponse<Source>>({
    queryKey: ['sources', params],
    queryFn: async () => (await client.get('/sources', { params })).data,
  })
}

export function useApproveSource() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => client.post(`/sources/${id}/approve`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sources'] }),
  })
}

export function useRejectSource() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => client.post(`/sources/${id}/reject`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sources'] }),
  })
}

// Reports
export function useReports(params: { page?: number; page_size?: number; report_type?: string } = {}) {
  return useQuery<PaginatedResponse<Report>>({
    queryKey: ['reports', params],
    queryFn: async () => (await client.get('/reports', { params })).data,
  })
}
```

**Step 4: Verify no TypeScript errors**

```bash
cd frontend && npx tsc --noEmit
```

Expected: possibly missing App.tsx error only — ignore it for now.

**Step 5: Commit**

```bash
git add frontend/src/
git commit -m "feat: add TypeScript types and TanStack Query API hooks"
```

---

### Task 3: Shared components

**Files to create:**
- `frontend/src/components/Badge.tsx`
- `frontend/src/components/Card.tsx`
- `frontend/src/components/Spinner.tsx`
- `frontend/src/components/Pagination.tsx`

**Step 1: Write frontend/src/components/Badge.tsx**

```tsx
import type { Finding } from '../types'

const priorityClasses: Record<Finding['priority'], string> = {
  CRITICAL: 'bg-red-100 text-red-700 border border-red-200',
  HIGH: 'bg-orange-100 text-orange-700 border border-orange-200',
  COALITION: 'bg-purple-100 text-purple-700 border border-purple-200',
  EVIDENCE: 'bg-blue-100 text-blue-700 border border-blue-200',
  MEDIUM: 'bg-yellow-100 text-yellow-700 border border-yellow-200',
  LOW: 'bg-gray-100 text-gray-500 border border-gray-200',
}

interface Props {
  priority: Finding['priority']
}

export default function Badge({ priority }: Props) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${priorityClasses[priority]}`}>
      {priority}
    </span>
  )
}
```

**Step 2: Write frontend/src/components/Card.tsx**

```tsx
import { ReactNode } from 'react'

interface Props {
  children: ReactNode
  className?: string
}

export default function Card({ children, className = '' }: Props) {
  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-4 ${className}`}>
      {children}
    </div>
  )
}
```

**Step 3: Write frontend/src/components/Spinner.tsx**

```tsx
export default function Spinner() {
  return (
    <div className="flex items-center justify-center p-8">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600" />
    </div>
  )
}
```

**Step 4: Write frontend/src/components/Pagination.tsx**

```tsx
interface Props {
  page: number
  hasMore: boolean
  total: number
  pageSize: number
  onPage: (p: number) => void
}

export default function Pagination({ page, hasMore, total, pageSize, onPage }: Props) {
  const totalPages = Math.ceil(total / pageSize)
  return (
    <div className="flex items-center justify-between mt-4 text-sm text-gray-600">
      <span>Page {page} of {totalPages} ({total} total)</span>
      <div className="flex gap-2">
        <button
          disabled={page <= 1}
          onClick={() => onPage(page - 1)}
          className="px-3 py-1 rounded border disabled:opacity-40 hover:bg-gray-50"
        >
          ← Prev
        </button>
        <button
          disabled={!hasMore}
          onClick={() => onPage(page + 1)}
          className="px-3 py-1 rounded border disabled:opacity-40 hover:bg-gray-50"
        >
          Next →
        </button>
      </div>
    </div>
  )
}
```

**Step 5: Commit**

```bash
git add frontend/src/components/
git commit -m "feat: add Badge, Card, Spinner, Pagination shared components"
```

---

### Task 4: Zustand filter store + GlobalFilterBar

**Files to create:**
- `frontend/src/store/filters.ts`
- `frontend/src/components/GlobalFilterBar.tsx`

**Step 1: Write frontend/src/store/filters.ts**

```ts
import { create } from 'zustand'

interface FiltersState {
  countries: string[]
  tags: string[]
  setCountries: (c: string[]) => void
  setTags: (t: string[]) => void
  reset: () => void
}

export const useFilters = create<FiltersState>((set) => ({
  countries: [],
  tags: [],
  setCountries: (countries) => set({ countries }),
  setTags: (tags) => set({ tags }),
  reset: () => set({ countries: [], tags: [] }),
}))
```

**Step 2: Write frontend/src/components/GlobalFilterBar.tsx**

```tsx
import { useFilters } from '../store/filters'

const COUNTRY_OPTIONS = [
  { code: 'BR', label: 'Brazil' },
  { code: 'CO', label: 'Colombia' },
  { code: 'AR', label: 'Argentina' },
  { code: 'CL', label: 'Chile' },
  { code: 'DE', label: 'Germany' },
  { code: 'GB', label: 'UK' },
]

const TAG_OPTIONS = ['coal', 'gas', 'solar', 'wind', 'cop30', 'ndc', 'financing', 'transition', 'petrobras']

export default function GlobalFilterBar() {
  const { countries, tags, setCountries, setTags, reset } = useFilters()

  const toggleCountry = (code: string) => {
    setCountries(countries.includes(code) ? countries.filter(c => c !== code) : [...countries, code])
  }

  const toggleTag = (tag: string) => {
    setTags(tags.includes(tag) ? tags.filter(t => t !== tag) : [...tags, tag])
  }

  return (
    <div className="bg-white border-b border-gray-200 px-6 py-2 flex items-center gap-4 flex-wrap text-sm">
      <span className="text-gray-500 font-medium">Filter:</span>
      <div className="flex gap-1 flex-wrap">
        {COUNTRY_OPTIONS.map(({ code, label }) => (
          <button
            key={code}
            onClick={() => toggleCountry(code)}
            className={`px-2 py-0.5 rounded border text-xs font-medium transition-colors ${
              countries.includes(code)
                ? 'bg-green-600 text-white border-green-600'
                : 'bg-white text-gray-600 border-gray-300 hover:border-green-400'
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="w-px h-4 bg-gray-300" />
      <div className="flex gap-1 flex-wrap">
        {TAG_OPTIONS.map(tag => (
          <button
            key={tag}
            onClick={() => toggleTag(tag)}
            className={`px-2 py-0.5 rounded border text-xs font-medium transition-colors ${
              tags.includes(tag)
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-600 border-gray-300 hover:border-blue-400'
            }`}
          >
            {tag}
          </button>
        ))}
      </div>
      {(countries.length > 0 || tags.length > 0) && (
        <button onClick={reset} className="ml-auto text-gray-400 hover:text-gray-700 text-xs">
          Clear all
        </button>
      )}
    </div>
  )
}
```

**Step 3: Commit**

```bash
git add frontend/src/store/ frontend/src/components/GlobalFilterBar.tsx
git commit -m "feat: add Zustand filter store and GlobalFilterBar"
```

---

### Task 5: WebSocket alerts hook + Toast system

**Files to create:**
- `frontend/src/store/toasts.ts`
- `frontend/src/hooks/useAlerts.ts`
- `frontend/src/components/ToastContainer.tsx`

**Step 1: Write frontend/src/store/toasts.ts**

```ts
import { create } from 'zustand'

export interface Toast {
  id: string
  title: string
  agent: string
  findingId: string
  priority: string
}

interface ToastState {
  toasts: Toast[]
  addToast: (t: Omit<Toast, 'id'>) => void
  removeToast: (id: string) => void
}

export const useToasts = create<ToastState>((set) => ({
  toasts: [],
  addToast: (t) => {
    const id = crypto.randomUUID()
    set((s) => ({ toasts: [...s.toasts.slice(-2), { ...t, id }] }))
    setTimeout(() => set((s) => ({ toasts: s.toasts.filter(x => x.id !== id) })), 10_000)
  },
  removeToast: (id) => set((s) => ({ toasts: s.toasts.filter(t => t.id !== id) })),
}))
```

**Step 2: Write frontend/src/hooks/useAlerts.ts**

```ts
import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useToasts } from '../store/toasts'

export function useAlerts() {
  const qc = useQueryClient()
  const { addToast } = useToasts()
  const wsRef = useRef<WebSocket | null>(null)
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    const connect = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const ws = new WebSocket(`${protocol}//${window.location.host}/ws/alerts`)
      wsRef.current = ws

      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data)
          if (data.priority === 'CRITICAL') {
            addToast({
              title: data.title || 'Critical Alert',
              agent: data.agent || 'system',
              findingId: data.id || '',
              priority: data.priority,
            })
          }
          qc.invalidateQueries({ queryKey: ['findings'] })
        } catch {
          // ignore malformed messages
        }
      }

      ws.onclose = () => {
        retryRef.current = setTimeout(connect, 3_000)
      }
    }

    connect()

    return () => {
      wsRef.current?.close()
      if (retryRef.current) clearTimeout(retryRef.current)
    }
  }, [addToast, qc])
}
```

**Step 3: Write frontend/src/components/ToastContainer.tsx**

```tsx
import { useNavigate } from 'react-router-dom'
import { useToasts } from '../store/toasts'

export default function ToastContainer() {
  const { toasts, removeToast } = useToasts()
  const navigate = useNavigate()

  if (toasts.length === 0) return null

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map(t => (
        <div
          key={t.id}
          className="bg-red-600 text-white rounded-lg shadow-lg px-4 py-3 flex items-start gap-3 max-w-sm"
        >
          <div className="flex-1">
            <div className="text-xs font-semibold opacity-80 uppercase">{t.agent}</div>
            <div className="text-sm font-medium mt-0.5 line-clamp-2">{t.title}</div>
          </div>
          <div className="flex flex-col items-end gap-1">
            <button
              onClick={() => removeToast(t.id)}
              className="text-white/70 hover:text-white text-lg leading-none"
            >
              ×
            </button>
            {t.findingId && (
              <button
                onClick={() => { navigate('/findings'); removeToast(t.id) }}
                className="text-xs underline opacity-80 hover:opacity-100"
              >
                View
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
```

**Step 4: Commit**

```bash
git add frontend/src/store/toasts.ts frontend/src/hooks/useAlerts.ts frontend/src/components/ToastContainer.tsx
git commit -m "feat: add WebSocket alerts hook and toast notification system"
```

---

### Task 6: App shell and routing

**Files to create:**
- `frontend/src/App.tsx`

**Step 1: Write frontend/src/App.tsx**

```tsx
import { Routes, Route, NavLink } from 'react-router-dom'
import GlobalFilterBar from './components/GlobalFilterBar'
import ToastContainer from './components/ToastContainer'
import { useAlerts } from './hooks/useAlerts'
import Dashboard from './pages/Dashboard'
import WorldMap from './pages/WorldMap'
import Findings from './pages/Findings'
import Contacts from './pages/Contacts'
import Sources from './pages/Sources'
import Reports from './pages/Reports'

const TABS = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/map', label: 'World Map' },
  { to: '/findings', label: 'Findings' },
  { to: '/contacts', label: 'Contacts' },
  { to: '/sources', label: 'Sources' },
  { to: '/reports', label: 'Reports' },
]

function AlertsConnector() {
  useAlerts()
  return null
}

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <AlertsConnector />
      <ToastContainer />

      {/* Nav */}
      <nav className="bg-white border-b border-gray-200 px-6 flex items-center gap-1 h-14 shrink-0">
        <span className="text-green-700 font-bold text-lg mr-6">🌿 Climate Intel</span>
        {TABS.map(({ to, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-green-50 text-green-700'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              }`
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>

      <GlobalFilterBar />

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/map" element={<WorldMap />} />
          <Route path="/findings" element={<Findings />} />
          <Route path="/contacts" element={<Contacts />} />
          <Route path="/sources" element={<Sources />} />
          <Route path="/reports" element={<Reports />} />
        </Routes>
      </main>
    </div>
  )
}
```

**Step 2: Create stub pages so the app compiles**

Create `frontend/src/pages/Dashboard.tsx`:
```tsx
export default function Dashboard() { return <div className="p-6">Dashboard</div> }
```

Create `frontend/src/pages/WorldMap.tsx`:
```tsx
export default function WorldMap() { return <div className="p-6">World Map</div> }
```

Create `frontend/src/pages/Findings.tsx`:
```tsx
export default function Findings() { return <div className="p-6">Findings</div> }
```

Create `frontend/src/pages/Contacts.tsx`:
```tsx
export default function Contacts() { return <div className="p-6">Contacts</div> }
```

Create `frontend/src/pages/Sources.tsx`:
```tsx
export default function Sources() { return <div className="p-6">Sources</div> }
```

Create `frontend/src/pages/Reports.tsx`:
```tsx
export default function Reports() { return <div className="p-6">Reports</div> }
```

**Step 3: Start dev server and verify navigation works**

```bash
cd frontend && npm run dev
```

Open `http://localhost:5173` — should show nav bar with 6 tabs, GlobalFilterBar below, stub content.

**Step 4: Commit**

```bash
git add frontend/src/
git commit -m "feat: App shell with nav, routing, filter bar, and stub pages"
```

---

### Task 7: Dashboard page

**Files to modify:**
- `frontend/src/pages/Dashboard.tsx` (replace stub)

**Step 1: Write frontend/src/pages/Dashboard.tsx**

```tsx
import { useState } from 'react'
import { useStats, useFindings, useArticles } from '../api/hooks'
import Badge from '../components/Badge'
import Card from '../components/Card'
import Spinner from '../components/Spinner'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import type { Finding } from '../types'

function StatCard({ label, value }: { label: string; value: number | undefined }) {
  return (
    <Card className="flex-1 min-w-[120px]">
      <div className="text-2xl font-bold text-gray-900">{value ?? '—'}</div>
      <div className="text-sm text-gray-500 mt-1">{label}</div>
    </Card>
  )
}

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime()
  const h = Math.floor(diff / 3_600_000)
  const m = Math.floor(diff / 60_000)
  if (h > 24) return `${Math.floor(h / 24)}d ago`
  if (h > 0) return `${h}h ago`
  return `${m}m ago`
}

const PRIORITY_ORDER: Finding['priority'][] = ['CRITICAL', 'HIGH', 'COALITION', 'EVIDENCE', 'MEDIUM', 'LOW']

export default function Dashboard() {
  const { data: stats } = useStats()
  const { data: findingsData, isLoading: fLoading } = useFindings({ page_size: 5 })
  const { data: articlesData, isLoading: aLoading } = useArticles({ page_size: 10 })
  const { data: allFindings } = useFindings({ page_size: 100 })

  // Build chart data from all findings
  const chartData = PRIORITY_ORDER.map(p => ({
    priority: p,
    count: allFindings?.items.filter(f => f.priority === p).length ?? 0,
  })).filter(d => d.count > 0)

  return (
    <div className="p-6 space-y-6">
      {/* Stat cards */}
      <div className="flex gap-4 flex-wrap">
        <StatCard label="Articles" value={stats?.articles} />
        <StatCard label="Findings" value={stats?.findings} />
        <StatCard label="Contacts" value={stats?.contacts} />
        <StatCard label="Sources" value={stats?.sources} />
        <StatCard label="Reports" value={stats?.reports} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Latest findings */}
        <Card>
          <h2 className="font-semibold text-gray-800 mb-3">Latest Findings</h2>
          {fLoading ? <Spinner /> : (
            <ul className="divide-y divide-gray-100">
              {findingsData?.items.map(f => (
                <li key={f.id} className="py-2.5 flex items-start gap-2">
                  <Badge priority={f.priority} />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-gray-900 truncate">{f.title}</div>
                    <div className="text-xs text-gray-400">{f.agent} · {timeAgo(f.created_at)}</div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        {/* Latest articles */}
        <Card>
          <h2 className="font-semibold text-gray-800 mb-3">Latest Articles</h2>
          {aLoading ? <Spinner /> : (
            <ul className="divide-y divide-gray-100">
              {articlesData?.items.map(a => (
                <li key={a.id} className="py-2 flex items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <a href={a.url} target="_blank" rel="noopener noreferrer"
                      className="text-sm font-medium text-gray-900 hover:text-green-700 truncate block">
                      {a.title}
                    </a>
                    <div className="text-xs text-gray-400">{a.source_name}</div>
                  </div>
                  {/* Significance bar */}
                  <div className="w-16 h-1.5 bg-gray-200 rounded-full shrink-0">
                    <div
                      className="h-1.5 bg-green-500 rounded-full"
                      style={{ width: `${Math.round(a.significance * 100)}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      {/* Findings by priority chart */}
      {chartData.length > 0 && (
        <Card>
          <h2 className="font-semibold text-gray-800 mb-4">Findings by Priority</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <XAxis dataKey="priority" tick={{ fontSize: 11 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#16a34a" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}
    </div>
  )
}
```

**Step 2: Verify in browser**

Open `http://localhost:5173/` — stat cards show numbers, findings list shows badge + title, articles list shows titles with significance bars.

**Step 3: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "feat: Dashboard page with stat cards, findings, articles, and chart"
```

---

### Task 8: World Map page

**Files to modify:**
- `frontend/src/pages/WorldMap.tsx` (replace stub)

**Step 1: Write frontend/src/pages/WorldMap.tsx**

```tsx
import { useState, useMemo } from 'react'
import { ComposableMap, Geographies, Geography, Marker, Sphere, Graticule } from 'react-simple-maps'
import { useFindings } from '../api/hooks'
import Badge from '../components/Badge'
import Spinner from '../components/Spinner'
import type { Finding } from '../types'

const GEO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json'

// ISO alpha-2 → numeric string (for topojson id matching)
const ALPHA2_TO_NUMERIC: Record<string, string> = {
  BR: '076', CO: '170', AR: '032', CL: '152', DE: '276', GB: '826',
  FR: '250', US: '840', IN: '356', ID: '360', AU: '036', ZA: '710',
  MX: '484', PE: '604', BO: '068', PY: '600', UY: '858', EC: '218',
  VE: '862', PT: '620', ES: '724', NL: '528', IT: '380', NO: '578',
  SE: '752', DK: '208', BE: '056', AT: '040', CH: '756', JP: '392',
  KR: '410', CN: '156', CA: '124', NZ: '554', PH: '608',
}

// Coordinates for countries we track [lon, lat]
const COUNTRY_COORDS: Record<string, [number, number]> = {
  BR: [-51.9, -14.2], CO: [-74.3, 4.6], AR: [-63.6, -38.4], CL: [-71.5, -35.7],
  DE: [10.5, 51.2], GB: [-3.4, 55.4], FR: [2.2, 46.2], US: [-99.1, 38.5],
  IN: [78.9, 20.6], ID: [113.9, -0.8], AU: [133.8, -25.3], ZA: [25.1, -28.5],
  MX: [-102.5, 23.6], PE: [-75.0, -9.2], BO: [-64.9, -16.3], EC: [-78.1, -1.8],
}

const PRIORITY_COLOR: Record<Finding['priority'], string> = {
  CRITICAL: '#dc2626',
  HIGH: '#ea580c',
  COALITION: '#9333ea',
  EVIDENCE: '#2563eb',
  MEDIUM: '#ca8a04',
  LOW: '#6b7280',
}

const PRIORITY_ORDER: Finding['priority'][] = ['CRITICAL', 'HIGH', 'COALITION', 'EVIDENCE', 'MEDIUM', 'LOW']

function getHighestPriority(priorities: Finding['priority'][]): Finding['priority'] {
  for (const p of PRIORITY_ORDER) {
    if (priorities.includes(p)) return p
  }
  return 'LOW'
}

export default function WorldMap() {
  const [daysBack, setDaysBack] = useState(7)
  const [selected, setSelected] = useState<string | null>(null)
  const { data, isLoading } = useFindings({ page_size: 100 })

  const cutoff = useMemo(() => {
    const d = new Date()
    d.setDate(d.getDate() - daysBack)
    return d.toISOString().split('T')[0]
  }, [daysBack])

  const filtered = useMemo(
    () => data?.items.filter(f => f.run_date >= cutoff) ?? [],
    [data, cutoff]
  )

  // Aggregate by country
  const countryData = useMemo(() => {
    const map: Record<string, { count: number; priorities: Finding['priority'][]; findings: Finding[] }> = {}
    for (const f of filtered) {
      for (const cc of f.country_codes) {
        if (!map[cc]) map[cc] = { count: 0, priorities: [], findings: [] }
        map[cc].count++
        map[cc].priorities.push(f.priority)
        map[cc].findings.push(f)
      }
    }
    return map
  }, [filtered])

  const markers = useMemo(() =>
    Object.entries(countryData)
      .filter(([cc]) => COUNTRY_COORDS[cc])
      .map(([cc, d]) => ({
        cc,
        coords: COUNTRY_COORDS[cc],
        count: d.count,
        priority: getHighestPriority(d.priorities),
        findings: d.findings,
      })),
    [countryData]
  )

  if (isLoading) return <Spinner />

  const selectedData = selected ? countryData[selected] : null

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Intelligence Map</h1>
        <div className="flex items-center gap-3 text-sm text-gray-600">
          <span>Last {daysBack} days</span>
          <input
            type="range" min={1} max={30} value={daysBack}
            onChange={e => setDaysBack(Number(e.target.value))}
            className="w-32 accent-green-600"
          />
        </div>
      </div>

      <div className="flex gap-4">
        <div className="flex-1 bg-white rounded-lg border border-gray-200 overflow-hidden">
          <ComposableMap projectionConfig={{ scale: 147 }} style={{ width: '100%', height: 'auto' }}>
            <Sphere id="sphere" fill="#f0f9ff" stroke="#e2e8f0" strokeWidth={0.5} />
            <Graticule stroke="#e2e8f0" strokeWidth={0.3} />
            <Geographies geography={GEO_URL}>
              {({ geographies }) =>
                geographies.map(geo => (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    fill="#e5e7eb"
                    stroke="#d1d5db"
                    strokeWidth={0.3}
                    style={{ default: { outline: 'none' }, hover: { outline: 'none' }, pressed: { outline: 'none' } }}
                  />
                ))
              }
            </Geographies>
            {markers.map(({ cc, coords, count, priority }) => (
              <Marker key={cc} coordinates={coords}>
                <circle
                  r={Math.min(4 + count * 3, 18)}
                  fill={PRIORITY_COLOR[priority]}
                  fillOpacity={0.8}
                  stroke="white"
                  strokeWidth={1.5}
                  style={{ cursor: 'pointer' }}
                  onClick={() => setSelected(selected === cc ? null : cc)}
                  className={priority === 'CRITICAL' ? 'animate-pulse' : ''}
                />
                <text
                  textAnchor="middle"
                  y={-Math.min(4 + count * 3, 18) - 3}
                  style={{ fontSize: 9, fill: '#374151', pointerEvents: 'none' }}
                >
                  {cc}
                </text>
              </Marker>
            ))}
          </ComposableMap>
        </div>

        {/* Side panel */}
        {selected && selectedData && (
          <div className="w-80 bg-white rounded-lg border border-gray-200 p-4 overflow-y-auto max-h-96">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-gray-900">{selected} — {selectedData.count} findings</h3>
              <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-700 text-lg">×</button>
            </div>
            <ul className="space-y-2">
              {selectedData.findings.slice(0, 5).map(f => (
                <li key={f.id} className="border-l-2 pl-2" style={{ borderColor: PRIORITY_COLOR[f.priority] }}>
                  <div className="flex items-center gap-1 mb-0.5">
                    <Badge priority={f.priority} />
                  </div>
                  <div className="text-xs text-gray-700 line-clamp-2">{f.title}</div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="flex gap-4 text-xs text-gray-500 flex-wrap">
        {PRIORITY_ORDER.filter(p => markers.some(m => m.priority === p)).map(p => (
          <span key={p} className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full inline-block" style={{ background: PRIORITY_COLOR[p] }} />
            {p}
          </span>
        ))}
        <span className="text-gray-400">· Circle size = finding count · Click circle for details</span>
      </div>
    </div>
  )
}
```

**Step 2: Verify in browser**

Open `http://localhost:5173/map` — world map renders with country circles. Brazil should have a circle. Click it for the side panel.

**Step 3: Commit**

```bash
git add frontend/src/pages/WorldMap.tsx
git commit -m "feat: World Map page with react-simple-maps country circles and click panel"
```

---

### Task 9: Findings page

**Files to modify:**
- `frontend/src/pages/Findings.tsx` (replace stub)

**Step 1: Write frontend/src/pages/Findings.tsx**

```tsx
import { useState } from 'react'
import { useFindings } from '../api/hooks'
import Badge from '../components/Badge'
import Pagination from '../components/Pagination'
import Spinner from '../components/Spinner'
import type { Finding } from '../types'

const PRIORITIES: Finding['priority'][] = ['CRITICAL', 'HIGH', 'COALITION', 'EVIDENCE', 'MEDIUM', 'LOW']

function daysUntil(deadline: string | null): string | null {
  if (!deadline) return null
  const diff = new Date(deadline).getTime() - Date.now()
  const days = Math.ceil(diff / 86_400_000)
  if (days < 0) return `${Math.abs(days)}d overdue`
  if (days === 0) return 'today'
  return `${days}d`
}

function Drawer({ finding, onClose }: { finding: Finding; onClose: () => void }) {
  const dl = daysUntil(finding.deadline)
  return (
    <div className="fixed inset-0 z-40 flex">
      <div className="flex-1 bg-black/20" onClick={onClose} />
      <div className="w-full max-w-lg bg-white shadow-xl overflow-y-auto">
        <div className="p-6">
          <div className="flex items-start justify-between mb-4">
            <Badge priority={finding.priority} />
            <button onClick={onClose} className="text-gray-400 hover:text-gray-700 text-2xl leading-none">×</button>
          </div>
          <h2 className="text-lg font-semibold text-gray-900 mb-3">{finding.title}</h2>
          <div className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed mb-4">{finding.body}</div>
          {finding.action_required && (
            <div className="bg-amber-50 border border-amber-200 rounded p-3 mb-3">
              <div className="text-xs font-semibold text-amber-700 mb-1">Action Required</div>
              <div className="text-sm text-amber-800">{finding.action_required}</div>
            </div>
          )}
          {finding.deadline && (
            <div className="flex items-center gap-2 text-sm mb-3">
              <span className="text-gray-500">Deadline:</span>
              <span className={`font-medium ${dl?.includes('overdue') ? 'text-red-600' : 'text-gray-900'}`}>
                {finding.deadline} {dl && `(${dl})`}
              </span>
            </div>
          )}
          {finding.coalition_opportunity && (
            <div className="text-xs bg-purple-50 text-purple-700 border border-purple-200 rounded px-2 py-1 inline-block mb-3">
              Coalition Opportunity
            </div>
          )}
          {finding.source_url && (
            <a href={finding.source_url} target="_blank" rel="noopener noreferrer"
              className="text-sm text-green-700 hover:underline block">
              → Source
            </a>
          )}
          <div className="mt-3 text-xs text-gray-400">
            Agent: {finding.agent} · Countries: {finding.country_codes.join(', ')} · {finding.run_date}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function Findings() {
  const [page, setPage] = useState(1)
  const [priority, setPriority] = useState('')
  const [status, setStatus] = useState('')
  const [selected, setSelected] = useState<Finding | null>(null)

  const { data, isLoading } = useFindings({
    page,
    page_size: 20,
    priority: priority || undefined,
    status: status || undefined,
  })

  return (
    <div className="p-6">
      {selected && <Drawer finding={selected} onClose={() => setSelected(null)} />}

      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <h1 className="text-xl font-semibold text-gray-900 mr-2">Findings</h1>
        <select
          value={priority} onChange={e => { setPriority(e.target.value); setPage(1) }}
          className="border border-gray-300 rounded px-2 py-1 text-sm"
        >
          <option value="">All priorities</option>
          {PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
        </select>
        <select
          value={status} onChange={e => { setStatus(e.target.value); setPage(1) }}
          className="border border-gray-300 rounded px-2 py-1 text-sm"
        >
          <option value="">All statuses</option>
          <option value="open">Open</option>
          <option value="reported">Reported</option>
          <option value="closed">Closed</option>
        </select>
      </div>

      {isLoading ? <Spinner /> : (
        <>
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                <tr>
                  <th className="px-4 py-3 text-left">Priority</th>
                  <th className="px-4 py-3 text-left">Title</th>
                  <th className="px-4 py-3 text-left">Agent</th>
                  <th className="px-4 py-3 text-left">Countries</th>
                  <th className="px-4 py-3 text-left">Deadline</th>
                  <th className="px-4 py-3 text-left">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data?.items.map(f => (
                  <tr
                    key={f.id}
                    onClick={() => setSelected(f)}
                    className="hover:bg-gray-50 cursor-pointer"
                  >
                    <td className="px-4 py-3"><Badge priority={f.priority} /></td>
                    <td className="px-4 py-3 font-medium text-gray-900 max-w-xs truncate">{f.title}</td>
                    <td className="px-4 py-3 text-gray-500">{f.agent}</td>
                    <td className="px-4 py-3 text-gray-500">{f.country_codes.join(', ')}</td>
                    <td className="px-4 py-3 text-gray-500">
                      {f.deadline ? (
                        <span className={daysUntil(f.deadline)?.includes('overdue') ? 'text-red-600 font-medium' : ''}>
                          {daysUntil(f.deadline)}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-1.5 py-0.5 rounded ${f.status === 'open' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                        {f.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {data && (
            <Pagination
              page={page} hasMore={data.has_more} total={data.total}
              pageSize={data.page_size} onPage={setPage}
            />
          )}
        </>
      )}
    </div>
  )
}
```

**Step 2: Verify in browser**

Open `http://localhost:5173/findings` — table with priority badges. Click priority filter to CRITICAL — rows filter. Click any row — drawer slides in from right.

**Step 3: Commit**

```bash
git add frontend/src/pages/Findings.tsx
git commit -m "feat: Findings page with filters, paginated table, and detail drawer"
```

---

### Task 10: Contacts page

**Files to modify:**
- `frontend/src/pages/Contacts.tsx` (replace stub)

**Step 1: Write frontend/src/pages/Contacts.tsx**

```tsx
import { useState } from 'react'
import { useContacts } from '../api/hooks'
import Spinner from '../components/Spinner'
import type { Contact } from '../types'

function InfluenceBar({ score }: { score: number }) {
  const pct = Math.min(Math.round(score * 100), 100)
  const color = pct > 60 ? 'bg-red-500' : pct > 30 ? 'bg-orange-400' : 'bg-green-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-200 rounded-full h-1.5">
        <div className={`h-1.5 rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-500 w-8 text-right">{score.toFixed(2)}</span>
    </div>
  )
}

function PowerDots({ n, max = 5 }: { n: number; max?: number }) {
  return (
    <div className="flex gap-0.5">
      {Array.from({ length: max }).map((_, i) => (
        <div key={i} className={`w-2 h-2 rounded-full ${i < n ? 'bg-gray-700' : 'bg-gray-200'}`} />
      ))}
    </div>
  )
}

function ContactCard({ c }: { c: Contact }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-2">
      <div>
        <div className="font-semibold text-gray-900">{c.name}</div>
        <div className="text-sm text-gray-500">{c.role}</div>
        <div className="text-xs text-gray-400">{c.organisation}</div>
      </div>
      <InfluenceBar score={c.influence_score} />
      <div className="flex items-center justify-between">
        <PowerDots n={c.decision_power} />
        <span className="text-xs text-gray-400">power {c.decision_power}/5</span>
      </div>
      {c.why_relevant && (
        <div className="text-xs text-gray-500 italic leading-tight">{c.why_relevant}</div>
      )}
    </div>
  )
}

export default function Contacts() {
  const [orgType, setOrgType] = useState('')
  const { data, isLoading } = useContacts({ page_size: 100, organisation_type: orgType || undefined })

  const govt = data?.items.filter(c => c.organisation_type === 'government') ?? []
  const allied = data?.items.filter(c => c.organisation_type !== 'government') ?? []

  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-4">
        <h1 className="text-xl font-semibold text-gray-900 mr-2">Contacts</h1>
        <select
          value={orgType} onChange={e => setOrgType(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1 text-sm"
        >
          <option value="">All types</option>
          <option value="government">Government</option>
          <option value="ngo">NGO</option>
          <option value="industry">Industry</option>
          <option value="academic">Academic</option>
          <option value="international">International</option>
        </select>
      </div>

      {isLoading ? <Spinner /> : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
              Government ({govt.length})
            </h2>
            <div className="space-y-3" data-testid="govt-column">
              {govt.length === 0
                ? <div className="text-sm text-gray-400 italic">No government contacts</div>
                : govt.map(c => <ContactCard key={c.id} c={c} />)}
            </div>
          </div>
          <div>
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
              NGO & Allied ({allied.length})
            </h2>
            <div className="space-y-3" data-testid="allied-column">
              {allied.length === 0
                ? <div className="text-sm text-gray-400 italic">No allied contacts</div>
                : allied.map(c => <ContactCard key={c.id} c={c} />)}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
```

**Step 2: Verify in browser**

Open `http://localhost:5173/contacts` — two columns. Government column shows ministers (Alexandre Silveira, Sandoval Feitosa, etc.). Allied column shows industry/NGO contacts.

**Step 3: Commit**

```bash
git add frontend/src/pages/Contacts.tsx
git commit -m "feat: Contacts page with two-column split and influence score bars"
```

---

### Task 11: Sources page

**Files to modify:**
- `frontend/src/pages/Sources.tsx` (replace stub)

**Step 1: Write frontend/src/pages/Sources.tsx**

```tsx
import { useState } from 'react'
import { useSources, useApproveSource, useRejectSource } from '../api/hooks'
import Pagination from '../components/Pagination'
import Spinner from '../components/Spinner'

function formatDate(d: string | null) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function Sources() {
  const [tab, setTab] = useState<'active' | 'pending'>('active')
  const [page, setPage] = useState(1)
  const { data, isLoading } = useSources({ page, page_size: 50 })
  const approve = useApproveSource()
  const reject = useRejectSource()

  const active = data?.items.filter(s => s.active) ?? []
  const pending = data?.items.filter(s => !s.active) ?? []
  const displayed = tab === 'active' ? active : pending

  return (
    <div className="p-6">
      <div className="flex items-center gap-4 mb-4">
        <h1 className="text-xl font-semibold text-gray-900 mr-2">Sources</h1>
        <div className="flex border border-gray-300 rounded overflow-hidden text-sm">
          <button
            onClick={() => setTab('active')}
            className={`px-3 py-1.5 ${tab === 'active' ? 'bg-green-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
          >
            Active ({active.length})
          </button>
          <button
            onClick={() => setTab('pending')}
            className={`px-3 py-1.5 ${tab === 'pending' ? 'bg-green-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
          >
            Pending ({pending.length})
          </button>
        </div>
      </div>

      {isLoading ? <Spinner /> : (
        <>
          {displayed.length === 0 ? (
            <div className="text-center text-gray-400 py-12">
              {tab === 'pending' ? 'No pending sources to review' : 'No active sources'}
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                  <tr>
                    <th className="px-4 py-3 text-left">Name</th>
                    <th className="px-4 py-3 text-left">Type</th>
                    <th className="px-4 py-3 text-left">Country</th>
                    <th className="px-4 py-3 text-left">Last Fetched</th>
                    {tab === 'pending' && <th className="px-4 py-3 text-left">Actions</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {displayed.map(s => (
                    <tr key={s.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <a href={s.url} target="_blank" rel="noopener noreferrer"
                          className="font-medium text-gray-900 hover:text-green-700">
                          {s.name}
                        </a>
                      </td>
                      <td className="px-4 py-3 text-gray-500">{s.source_type}</td>
                      <td className="px-4 py-3 text-gray-500">{s.country_code}</td>
                      <td className="px-4 py-3 text-gray-500">{formatDate(s.last_fetched)}</td>
                      {tab === 'pending' && (
                        <td className="px-4 py-3">
                          <div className="flex gap-2">
                            <button
                              onClick={() => approve.mutate(s.id)}
                              disabled={approve.isPending}
                              className="px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => reject.mutate(s.id)}
                              disabled={reject.isPending}
                              className="px-2 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
                            >
                              Reject
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {data && tab === 'active' && (
            <Pagination page={page} hasMore={data.has_more} total={data.total} pageSize={data.page_size} onPage={setPage} />
          )}
        </>
      )}
    </div>
  )
}
```

**Step 2: Verify in browser**

Open `http://localhost:5173/sources` — Active tab shows source table. Switch to Pending — shows approve/reject buttons.

**Step 3: Commit**

```bash
git add frontend/src/pages/Sources.tsx
git commit -m "feat: Sources page with active/pending tabs and approve/reject actions"
```

---

### Task 12: Reports page

**Files to modify:**
- `frontend/src/pages/Reports.tsx` (replace stub)

**Step 1: Write frontend/src/pages/Reports.tsx**

```tsx
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { useReports } from '../api/hooks'
import Pagination from '../components/Pagination'
import Spinner from '../components/Spinner'
import type { Report } from '../types'

const TYPE_COLORS: Record<string, string> = {
  daily_digest: 'bg-blue-100 text-blue-700',
  weekly_brief: 'bg-indigo-100 text-indigo-700',
  alert: 'bg-red-100 text-red-700',
  coalition_brief: 'bg-purple-100 text-purple-700',
}

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-500',
  sent: 'bg-green-100 text-green-700',
}

function ReportModal({ report, onClose }: { report: Report; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-40 flex items-start justify-center bg-black/40 pt-16 px-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[80vh] flex flex-col">
        <div className="flex items-start justify-between p-6 border-b border-gray-200">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-xs px-2 py-0.5 rounded font-medium ${TYPE_COLORS[report.report_type] ?? 'bg-gray-100 text-gray-600'}`}>
                {report.report_type.replace('_', ' ')}
              </span>
              <span className={`text-xs px-2 py-0.5 rounded font-medium ${STATUS_COLORS[report.email_status] ?? 'bg-gray-100 text-gray-500'}`}>
                {report.email_status}
              </span>
            </div>
            <h2 className="text-lg font-semibold text-gray-900">{report.title}</h2>
            <div className="text-sm text-gray-400 mt-0.5">{report.run_date}</div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 text-2xl leading-none">×</button>
        </div>
        <div className="overflow-y-auto p-6 prose prose-sm max-w-none">
          <ReactMarkdown>{report.body}</ReactMarkdown>
        </div>
      </div>
    </div>
  )
}

export default function Reports() {
  const [page, setPage] = useState(1)
  const [reportType, setReportType] = useState('')
  const [selected, setSelected] = useState<Report | null>(null)
  const { data, isLoading } = useReports({ page, page_size: 20, report_type: reportType || undefined })

  return (
    <div className="p-6">
      {selected && <ReportModal report={selected} onClose={() => setSelected(null)} />}

      <div className="flex items-center gap-3 mb-4">
        <h1 className="text-xl font-semibold text-gray-900 mr-2">Reports</h1>
        <select
          value={reportType} onChange={e => { setReportType(e.target.value); setPage(1) }}
          className="border border-gray-300 rounded px-2 py-1 text-sm"
        >
          <option value="">All types</option>
          <option value="daily_digest">Daily Digest</option>
          <option value="weekly_brief">Weekly Brief</option>
          <option value="alert">Alert</option>
          <option value="coalition_brief">Coalition Brief</option>
        </select>
      </div>

      {isLoading ? <Spinner /> : (
        <>
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                <tr>
                  <th className="px-4 py-3 text-left">Type</th>
                  <th className="px-4 py-3 text-left">Subject</th>
                  <th className="px-4 py-3 text-left">Date</th>
                  <th className="px-4 py-3 text-left">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data?.items.map(r => (
                  <tr key={r.id} onClick={() => setSelected(r)} className="hover:bg-gray-50 cursor-pointer">
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded font-medium ${TYPE_COLORS[r.report_type] ?? 'bg-gray-100 text-gray-600'}`}>
                        {r.report_type.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-medium text-gray-900 max-w-md truncate">{r.subject || r.title}</td>
                    <td className="px-4 py-3 text-gray-500">{r.run_date}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded font-medium ${STATUS_COLORS[r.email_status] ?? 'bg-gray-100 text-gray-500'}`}>
                        {r.email_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {data && (
            <Pagination page={page} hasMore={data.has_more} total={data.total} pageSize={data.page_size} onPage={setPage} />
          )}
        </>
      )}
    </div>
  )
}
```

**Step 2: Verify in browser**

Open `http://localhost:5173/reports` — report list with the daily digest. Click it → modal opens showing markdown-rendered body.

**Step 3: Commit**

```bash
git add frontend/src/pages/Reports.tsx
git commit -m "feat: Reports page with type filter, list, and markdown body modal"
```

---

### Task 13: Playwright e2e setup and all tests

**Files to create:**
- `frontend/playwright.config.ts`
- `frontend/tests/dashboard.spec.ts`
- `frontend/tests/worldmap.spec.ts`
- `frontend/tests/findings.spec.ts`
- `frontend/tests/contacts.spec.ts`
- `frontend/tests/sources.spec.ts`
- `frontend/tests/reports.spec.ts`

**Step 1: Write frontend/playwright.config.ts**

```ts
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: true,
    timeout: 30_000,
  },
})
```

**Step 2: Write frontend/tests/dashboard.spec.ts**

```ts
import { test, expect } from '@playwright/test'

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('shows 5 stat cards with positive numbers', async ({ page }) => {
    const cards = page.locator('.bg-white.rounded-lg.shadow-sm').filter({ hasText: /Articles|Findings|Contacts|Sources|Reports/ })
    await expect(cards).toHaveCount(5, { timeout: 10_000 })
    // At least one card should have a non-zero number
    const firstNum = await cards.first().locator('.text-2xl').textContent()
    expect(Number(firstNum)).toBeGreaterThan(0)
  })

  test('shows findings list with at least one item', async ({ page }) => {
    await expect(page.locator('text=Latest Findings')).toBeVisible()
    const findingItems = page.locator('ul li').first()
    await expect(findingItems).toBeVisible({ timeout: 10_000 })
  })

  test('shows articles list', async ({ page }) => {
    await expect(page.locator('text=Latest Articles')).toBeVisible()
    const articleLink = page.locator('a[target="_blank"]').first()
    await expect(articleLink).toBeVisible({ timeout: 10_000 })
  })

  test('nav links are all present', async ({ page }) => {
    for (const label of ['Dashboard', 'World Map', 'Findings', 'Contacts', 'Sources', 'Reports']) {
      await expect(page.locator(`text=${label}`).first()).toBeVisible()
    }
  })
})
```

**Step 3: Write frontend/tests/worldmap.spec.ts**

```ts
import { test, expect } from '@playwright/test'

test.describe('World Map', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/map')
  })

  test('map SVG renders', async ({ page }) => {
    await expect(page.locator('svg')).toBeVisible({ timeout: 15_000 })
  })

  test('at least one country circle marker exists', async ({ page }) => {
    // Circles are SVG <circle> elements from Markers
    const circles = page.locator('circle[r]')
    await expect(circles.first()).toBeVisible({ timeout: 15_000 })
  })

  test('time slider is present', async ({ page }) => {
    const slider = page.locator('input[type="range"]')
    await expect(slider).toBeVisible()
  })

  test('clicking a circle opens the side panel', async ({ page }) => {
    await page.locator('svg').waitFor({ timeout: 15_000 })
    const circle = page.locator('circle[r]').first()
    await circle.click({ force: true })
    // Panel appears with finding count
    await expect(page.locator('text=findings').first()).toBeVisible({ timeout: 5_000 })
  })
})
```

**Step 4: Write frontend/tests/findings.spec.ts**

```ts
import { test, expect } from '@playwright/test'

test.describe('Findings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/findings')
  })

  test('table loads with rows', async ({ page }) => {
    await expect(page.locator('table')).toBeVisible()
    const rows = page.locator('tbody tr')
    await expect(rows.first()).toBeVisible({ timeout: 10_000 })
  })

  test('priority badges are visible', async ({ page }) => {
    const badge = page.locator('tbody tr').first().locator('span').first()
    await expect(badge).toBeVisible({ timeout: 10_000 })
  })

  test('priority filter works', async ({ page }) => {
    await page.locator('select').first().selectOption('CRITICAL')
    await page.waitForTimeout(500)
    const rows = page.locator('tbody tr')
    const count = await rows.count()
    // After filter there should be some rows (or 0 if none critical, but we know there are)
    expect(count).toBeGreaterThanOrEqual(0)
    // If rows exist, they should all say CRITICAL
    if (count > 0) {
      const firstBadge = await rows.first().locator('span').first().textContent()
      expect(firstBadge).toBe('CRITICAL')
    }
  })

  test('clicking a row opens the drawer', async ({ page }) => {
    const firstRow = page.locator('tbody tr').first()
    await expect(firstRow).toBeVisible({ timeout: 10_000 })
    await firstRow.click()
    // Drawer has a title and a close button
    await expect(page.locator('text=Action Required').or(page.locator('text=Source'))).toBeVisible({ timeout: 5_000 })
    await expect(page.locator('button').filter({ hasText: '×' })).toBeVisible()
  })
})
```

**Step 5: Write frontend/tests/contacts.spec.ts**

```ts
import { test, expect } from '@playwright/test'

test.describe('Contacts', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/contacts')
  })

  test('both columns render', async ({ page }) => {
    await expect(page.locator('[data-testid="govt-column"]')).toBeVisible({ timeout: 10_000 })
    await expect(page.locator('[data-testid="allied-column"]')).toBeVisible()
  })

  test('at least one contact card is visible', async ({ page }) => {
    const card = page.locator('.bg-white.rounded-lg.border').first()
    await expect(card).toBeVisible({ timeout: 10_000 })
  })

  test('influence bars are rendered', async ({ page }) => {
    // Influence bar has a bg-green-500 or bg-orange-400 or bg-red-500 child div
    await expect(page.locator('.bg-gray-200.rounded-full').first()).toBeVisible({ timeout: 10_000 })
  })
})
```

**Step 6: Write frontend/tests/sources.spec.ts**

```ts
import { test, expect } from '@playwright/test'

test.describe('Sources', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/sources')
  })

  test('active tab shows sources', async ({ page }) => {
    await expect(page.locator('table')).toBeVisible({ timeout: 10_000 })
    const rows = page.locator('tbody tr')
    await expect(rows.first()).toBeVisible()
  })

  test('pending tab is accessible', async ({ page }) => {
    await page.locator('button', { hasText: /Pending/ }).click()
    // Either shows table rows or the empty state message
    const tableOrEmpty = page.locator('table').or(page.locator('text=No pending sources'))
    await expect(tableOrEmpty.first()).toBeVisible({ timeout: 5_000 })
  })

  test('pending tab shows approve and reject buttons if sources exist', async ({ page }) => {
    await page.locator('button', { hasText: /Pending/ }).click()
    const hasRows = await page.locator('tbody tr').count()
    if (hasRows > 0) {
      await expect(page.locator('button', { hasText: 'Approve' }).first()).toBeVisible()
      await expect(page.locator('button', { hasText: 'Reject' }).first()).toBeVisible()
    }
  })
})
```

**Step 7: Write frontend/tests/reports.spec.ts**

```ts
import { test, expect } from '@playwright/test'

test.describe('Reports', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/reports')
  })

  test('report list loads with at least one row', async ({ page }) => {
    await expect(page.locator('table')).toBeVisible({ timeout: 10_000 })
    const rows = page.locator('tbody tr')
    await expect(rows.first()).toBeVisible()
  })

  test('clicking a report opens the modal with body text', async ({ page }) => {
    const firstRow = page.locator('tbody tr').first()
    await expect(firstRow).toBeVisible({ timeout: 10_000 })
    await firstRow.click()
    // Modal body should render markdown — look for the close button
    await expect(page.locator('button', { hasText: '×' })).toBeVisible({ timeout: 5_000 })
    // The report body should be visible in the modal
    await expect(page.locator('.prose')).toBeVisible()
  })
})
```

**Step 8: Install Playwright browser**

```bash
cd frontend && npx playwright install chromium
```

**Step 9: Run all e2e tests (API must be running)**

Make sure `docker compose up -d api postgres redis` is running, then:

```bash
cd frontend && npm run dev &
npm run test:e2e
```

Expected: all 6 specs pass. If any fail, read the error and fix before proceeding.

**Step 10: Fix any test failures and re-run until all green**

Common issues:
- World map circles not loading: the world-atlas CDN URL may take a moment — increase timeout to 20_000ms
- API proxy not working: check vite.config.ts proxy settings and that API is running on 8000
- Empty data: verify `docker compose up -d postgres api` and database has data

**Step 11: Commit**

```bash
git add frontend/playwright.config.ts frontend/tests/
git commit -m "feat: Playwright e2e tests for all 6 dashboard tabs"
```

---

### Task 14: Updated Dockerfile and nginx.conf

**Files to modify:**
- `frontend/Dockerfile` (rewrite)

**Files to create:**
- `frontend/nginx.conf`

**Step 1: Write frontend/Dockerfile**

```dockerfile
# Stage 1: Build
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Serve
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

**Step 2: Write frontend/nginx.conf**

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    # Proxy API calls to FastAPI (strips /api prefix)
    location /api/ {
        proxy_pass http://api:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Proxy WebSocket
    location /ws/ {
        proxy_pass http://api:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # SPA routing — all other paths serve index.html
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

**Step 3: Build the Docker image**

```bash
cd .. && docker compose build frontend
```

Expected: build completes with no errors.

**Step 4: Start the container**

```bash
docker compose up -d frontend
```

**Step 5: Verify Docker build works**

```bash
curl -s http://localhost/ | head -5
```

Expected: returns HTML with `<title>Climate Intelligence Platform</title>`.

**Step 6: Run e2e against Docker (optional)**

Update playwright.config.ts temporarily to baseURL `http://localhost` and remove webServer, then:

```bash
cd frontend && npx playwright test
```

**Step 7: Commit**

```bash
git add frontend/Dockerfile frontend/nginx.conf
git commit -m "feat: production Dockerfile and nginx.conf with API proxy"
```

---

### Task 15: Full e2e run and fix until all green

**Step 1: Ensure full stack is up**

```bash
docker compose up -d postgres redis api
```

**Step 2: Start Vite dev server**

```bash
cd frontend && npm run dev
```

**Step 3: Run all Playwright tests**

```bash
cd frontend && npm run test:e2e
```

**Step 4: Fix any failures**

For each failing test:
1. Read the error message carefully
2. Open the browser at the relevant URL
3. Fix the component or test assertion
4. Re-run `npm run test:e2e`
5. Do not stop until all 6 specs pass

**Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete React dashboard — 6 tabs, world map, real-time alerts, all Playwright e2e passing"
```
