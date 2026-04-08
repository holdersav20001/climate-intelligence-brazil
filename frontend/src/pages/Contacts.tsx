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
