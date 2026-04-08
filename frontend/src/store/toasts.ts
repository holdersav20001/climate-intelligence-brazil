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
