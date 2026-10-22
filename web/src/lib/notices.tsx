import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, type Notice } from './api'

interface NoticesState {
  items: Notice[]
  unread: number
  refresh: () => Promise<void>
  markRead: (ids?: string[]) => Promise<void>
}

const NoticesContext = createContext<NoticesState | null>(null)
const POLL_MS = 30_000

/** The bell: polls while the tab is visible (no push channel to the browser yet). */
export function NoticesProvider({ enabled, children }: { enabled: boolean; children: ReactNode }) {
  const [items, setItems] = useState<Notice[]>([])
  const [unread, setUnread] = useState(0)

  const refresh = useCallback(async () => {
    if (!enabled) return
    try {
      const page = await api.notifications()
      setItems(page.items)
      setUnread(page.unread)
    } catch {
      /* offline or signed out: keep what we have */
    }
  }, [enabled])

  useEffect(() => {
    if (!enabled) {
      setItems([])
      setUnread(0)
      return
    }
    void refresh()
    const timer = setInterval(() => document.visibilityState === 'visible' && void refresh(), POLL_MS)
    const onVisible = () => document.visibilityState === 'visible' && void refresh()
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      clearInterval(timer)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [enabled, refresh])

  const markRead = useCallback(
    async (ids?: string[]) => {
      await api.readNotifications(ids)
      await refresh()
    },
    [refresh],
  )

  const value = useMemo(() => ({ items, unread, refresh, markRead }), [items, unread, refresh, markRead])
  return <NoticesContext.Provider value={value}>{children}</NoticesContext.Provider>
}

export function useNotices(): NoticesState {
  const ctx = useContext(NoticesContext)
  if (!ctx) throw new Error('useNotices outside NoticesProvider')
  return ctx
}
