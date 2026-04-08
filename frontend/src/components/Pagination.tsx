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
