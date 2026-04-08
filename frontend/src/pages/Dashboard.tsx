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

  const chartData = PRIORITY_ORDER.map(p => ({
    priority: p,
    count: allFindings?.items.filter(f => f.priority === p).length ?? 0,
  })).filter(d => d.count > 0)

  return (
    <div className="p-6 space-y-6">
      <div className="flex gap-4 flex-wrap">
        <StatCard label="Articles" value={stats?.articles} />
        <StatCard label="Findings" value={stats?.findings} />
        <StatCard label="Contacts" value={stats?.contacts} />
        <StatCard label="Sources" value={stats?.sources} />
        <StatCard label="Reports" value={stats?.reports} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
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
