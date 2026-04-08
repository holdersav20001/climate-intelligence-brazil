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
