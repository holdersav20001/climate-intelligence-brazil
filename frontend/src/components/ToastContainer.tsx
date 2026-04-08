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
