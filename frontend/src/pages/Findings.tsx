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
