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
