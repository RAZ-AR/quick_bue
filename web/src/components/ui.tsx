// Small shared pieces of the QB visual language: icons, product tiles, countdowns, the order-minimum meter.
import { useEffect, useState } from 'react'
import { useT } from '../i18n'
import { amd } from '../lib/format'

const stroke = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round' } as const

export const Icon = {
  catalog: () => (
    <svg viewBox="0 0 24 24" {...stroke}>
      <rect x="3.5" y="3.5" width="7" height="7" rx="2" />
      <rect x="13.5" y="3.5" width="7" height="7" rx="2" />
      <rect x="3.5" y="13.5" width="7" height="7" rx="2" />
      <rect x="13.5" y="13.5" width="7" height="7" rx="2" />
    </svg>
  ),
  cart: () => (
    <svg viewBox="0 0 24 24" {...stroke}>
      <path d="M3 4h2l2.2 10.2a2 2 0 0 0 2 1.6h7.6a2 2 0 0 0 2-1.5L20.5 8H6" />
      <circle cx="10" cy="20" r="1.3" />
      <circle cx="17" cy="20" r="1.3" />
    </svg>
  ),
  // a kitchen ticket: orders
  ticket: () => (
    <svg viewBox="0 0 24 24" {...stroke}>
      <path d="M6 3h12v18l-2-1.5L14 21l-2-1.5L10 21l-2-1.5L6 21z" />
      <path d="M9 8h6M9 12h6M9 16h3" />
    </svg>
  ),
  inbox: () => (
    <svg viewBox="0 0 24 24" {...stroke}>
      <path d="M4 13l2.5-8h11L20 13v6H4z" />
      <path d="M4 13h4.5l1 2h5l1-2H20" />
    </svg>
  ),
}

// Category tint: one stable hue per category, so a chef learns the shelf by colour
const HUES: Record<string, number> = {
  disposables: 210, cleaning: 190, grocery: 35, dairy: 48, meat: 0, produce: 120, coffee: 25, bakery: 30,
}

export function Tile({ slug, name }: { slug?: string; name: string }) {
  const hue = slug && slug in HUES ? HUES[slug] : 30
  return (
    <div className="tile" style={{ background: `hsl(${hue} 55% 88%)`, color: `hsl(${hue} 45% 28%)` }} aria-hidden>
      {name.trim().charAt(0).toUpperCase()}
    </div>
  )
}

/** Re-render every `ms` so countdowns stay true without a server push. */
export function useNow(ms = 30_000): number {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), ms)
    return () => clearInterval(id)
  }, [ms])
  return now
}

export function Countdown({ until }: { until: string }) {
  const t = useT()
  const now = useNow()
  const left = new Date(until).getTime() - now
  if (left <= 0) return <span className="clock">{t('overdue')}</span>
  const h = Math.floor(left / 3_600_000)
  const m = Math.floor((left % 3_600_000) / 60_000)
  return (
    <span className="clock">
      {h > 0 ? `${h} ${t('h')} ` : ''}
      {m} {t('m')}
    </span>
  )
}

/**
 * Progress towards the seller's minimum order and free delivery, on one track.
 * Amber until the minimum is reached, green after; the free-delivery threshold is a tick on the track.
 */
export function OrderMeter({
  subtotal,
  min,
  freeFrom,
}: {
  subtotal: number
  min: number
  freeFrom: number | null
}) {
  const t = useT()
  const end = Math.max(freeFrom ?? 0, min, subtotal, 1)
  const pct = (x: number) => `${Math.min(100, (x / end) * 100)}%`
  const belowMin = subtotal < min
  const toFree = freeFrom !== null ? freeFrom - subtotal : null
  return (
    <div className="meter" aria-label={t('to_min')}>
      <div className="meter-track">
        <div className={belowMin ? 'meter-fill' : 'meter-fill ok'} style={{ width: pct(subtotal) }} />
        {min > 0 && <div className="meter-mark" style={{ left: pct(min) }} title={`${t('min_order')} ${amd(min)}`} />}
        {freeFrom !== null && <div className="meter-mark" style={{ left: `calc(${pct(freeFrom)} - 2px)` }} />}
      </div>
      <div className="meter-legend">
        {belowMin ? (
          <span className="lamp">
            {t('to_min')}: {t('more')} {amd(min - subtotal)}
          </span>
        ) : toFree !== null && toFree > 0 ? (
          <span>
            {t('to_free')}: {t('more')} <b className="num">{amd(toFree)}</b>
          </span>
        ) : (
          <span className="herb">✓ {freeFrom !== null ? t('free_reached') : ''}</span>
        )}
        <span className="muted num">
          {t('min_order')} {amd(min)}
        </span>
      </div>
    </div>
  )
}
