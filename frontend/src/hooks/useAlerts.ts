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
