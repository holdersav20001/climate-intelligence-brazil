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
