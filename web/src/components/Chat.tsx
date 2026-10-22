import type React from 'react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { problemText, useLang, useT } from '../i18n'
import { api, ApiError, type ChatMessage, type Order } from '../lib/api'
import { dateTime } from '../lib/format'
import { useNotices } from '../lib/notices'

const POLL_MS = 10_000

/** Buyer ↔ seller chat inside one order. Own messages on the right, black; the other side's on the left. */
export function OrderChat({ order }: { order: Order }) {
  const t = useT()
  const lang = useLang()
  const { refresh: refreshBell } = useNotices()
  const [messages, setMessages] = useState<ChatMessage[] | null>(null)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const listRef = useRef<HTMLDivElement>(null)

  const load = useCallback(async () => {
    try {
      setMessages(await api.messages(order.id))
    } catch {
      /* keep the last list */
    }
  }, [order.id])

  useEffect(() => {
    void load().then(() => refreshBell())
    const timer = setInterval(() => document.visibilityState === 'visible' && void load(), POLL_MS)
    return () => clearInterval(timer)
  }, [load, refreshBell])

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight })
  }, [messages?.length])

  // Opened from a message notification: bring the chat into view
  useEffect(() => {
    if (window.location.hash === '#chat') listRef.current?.closest('section')?.scrollIntoView({ block: 'center' })
  }, [])

  async function send(e: React.FormEvent) {
    e.preventDefault()
    if (!text.trim()) return
    setBusy(true)
    setError(null)
    try {
      const m = await api.sendMessage(order.id, text)
      setMessages((list) => [...(list ?? []), m])
      setText('')
    } catch (err) {
      const ex = err as ApiError
      setError(problemText(ex.problems?.[0]?.code ?? ex.code, lang))
    } finally {
      setBusy(false)
    }
  }

  const other = order.my_side === 'buyer' ? order.seller.display_name : order.buyer.display_name
  return (
    <section className="ticket chat">
      <header className="ticket-head">
        <h2>{t('chat')}</h2>
        <span className="muted small">{other}</span>
      </header>
      <div className="chat-list" ref={listRef}>
        {messages?.length === 0 && <p className="muted small chat-empty">{t('no_messages')}</p>}
        {messages?.map((m) => (
          <div key={m.id} className={m.mine ? 'bubble mine' : m.side === order.my_side ? 'bubble team' : 'bubble'}>
            <p>{m.text}</p>
            <time>{dateTime(m.at, lang)}</time>
          </div>
        ))}
      </div>
      <form className="chat-form" onSubmit={send}>
        <textarea
          rows={1}
          value={text}
          placeholder={t('chat_placeholder')}
          maxLength={2000}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              void send(e)
            }
          }}
        />
        <button className="ibtn dark" disabled={busy || !text.trim()} aria-label={t('send')} title={t('send')}>
          ↑
        </button>
      </form>
      {error && <p className="error small">{error}</p>}
    </section>
  )
}
