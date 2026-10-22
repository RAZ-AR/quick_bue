import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { NOTICES, problemText, useLang, useT } from '../i18n'
import { api, ApiError, type Lang, type Notice, type NotifySettings } from '../lib/api'
import { dateTime } from '../lib/format'
import { useNotices } from '../lib/notices'

export function noticeText(n: Notice, lang: Lang): string {
  const tpl = NOTICES[n.type]?.[lang] ?? n.type
  return tpl.replace('{number}', n.payload?.number ?? '').replace('{counterparty}', n.payload?.counterparty ?? '')
}

/** The bell's page: what happened, newest first, plus where else to send it. */
export function Notifications() {
  const t = useT()
  const lang = useLang()
  const navigate = useNavigate()
  const { items, unread, markRead, refresh } = useNotices()

  useEffect(() => {
    void refresh()
  }, [refresh])

  async function open(n: Notice) {
    if (!n.read_at) await markRead([n.id])
    if (n.order_id) navigate(`/orders/${n.order_id}${n.type === 'message' ? '#chat' : ''}`)
  }

  return (
    <div className="stack page">
      <div className="page-head">
        <h1 className="page-title">{t('tab_notifications')}</h1>
        {unread > 0 && (
          <button className="btn ghost small-btn" onClick={() => void markRead()}>
            {t('mark_all_read')}
          </button>
        )}
      </div>
      {items.length === 0 && <p className="col-empty">{t('no_notifications')}</p>}
      <ul className="notices">
        {items.map((n) => (
          <li key={n.id}>
            <button className={n.read_at ? 'notice-row' : 'notice-row unread'} onClick={() => void open(n)}>
              <span className="notice-dot" aria-hidden />
              <span className="notice-body">
                <span className="notice-title">{noticeText(n, lang)}</span>
                {n.type === 'message' && n.payload?.text && <span className="notice-quote">«{n.payload.text}»</span>}
                <time className="muted small">{dateTime(n.created_at, lang)}</time>
              </span>
              <span className="ibtn" aria-hidden>
                ↗
              </span>
            </button>
          </li>
        ))}
      </ul>
      <ChannelSettings />
    </div>
  )
}

function ChannelSettings() {
  const t = useT()
  const lang = useLang()
  const [s, setS] = useState<NotifySettings | null>(null)
  const [link, setLink] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.notifySettings().then(setS, () => {})
  }, [])
  if (!s) return null

  async function run<T>(p: Promise<T>, then: (v: T) => void) {
    setError(null)
    try {
      then(await p)
    } catch (e) {
      setError(problemText((e as ApiError).code, lang))
    }
  }

  return (
    <section className="ticket" style={{ display: 'grid', gap: 12 }}>
      <h2 style={{ margin: 0, fontSize: 18 }}>{t('notify_settings')}</h2>
      <p className="muted small" style={{ margin: 0 }}>
        ✓ {t('notify_in_app')}
      </p>
      <label className="check">
        <input
          type="checkbox"
          checked={s.email}
          onChange={(e) => void run(api.saveNotifySettings(e.target.checked, s.telegram), setS)}
        />
        {t('notify_email')}
        {s.email_address && <span className="muted small"> · {s.email_address}</span>}
      </label>
      {s.telegram_linked ? (
        <div className="side-row">
          <label className="check">
            <input
              type="checkbox"
              checked={s.telegram}
              onChange={(e) => void run(api.saveNotifySettings(s.email, e.target.checked), setS)}
            />
            {t('notify_telegram')} ✓
          </label>
          <button className="link small" onClick={() => void run(api.telegramUnlink(), setS)}>
            {t('unlink_telegram')}
          </button>
        </div>
      ) : s.telegram_available ? (
        <div style={{ display: 'grid', gap: 6 }}>
          {link ? (
            <>
              <a className="btn primary" href={link} target="_blank" rel="noopener">
                {t('link_telegram')} ↗
              </a>
              <span className="muted small">{t('telegram_link_hint')}</span>
            </>
          ) : (
            <button className="btn ghost" onClick={() => void run(api.telegramLink(), (r) => setLink(r.url))}>
              {t('link_telegram')}
            </button>
          )}
        </div>
      ) : (
        <p className="muted small" style={{ margin: 0 }}>
          {t('notify_telegram')}: {t('telegram_unavailable')}
        </p>
      )}
      {error && <p className="error small">{error}</p>}
    </section>
  )
}
