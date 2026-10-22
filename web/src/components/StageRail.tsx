// The order as a ticket travelling along the pass: one pin per station, the current one under the heat lamp.
import { STAGES, STATUSES, useLang } from '../i18n'
import type { Order } from '../lib/api'
import { dateTime } from '../lib/format'

const FLOW = ['placed', 'confirmed', 'delivering', 'delivered', 'accepted'] as const
// Journal event type -> station it marks
const EVENT_STATION: Record<string, string> = {
  offer_made: 'negotiating',
  placed: 'placed',
  confirmed: 'confirmed',
  delivering: 'delivering',
  delivered: 'delivered',
  accepted: 'accepted',
  cancelled: 'cancelled',
  rejected: 'rejected',
}

export function StageRail({ order }: { order: Order }) {
  const lang = useLang()
  const at: Record<string, string> = {}
  for (const e of order.events) {
    const station = EVENT_STATION[e.type]
    if (station && !at[station]) at[station] = e.at
  }
  const stations: string[] = [...(order.negotiation ? ['negotiating'] : []), ...FLOW]
  const stopped = order.status === 'cancelled' || order.status === 'rejected'
  // A seller may skip "on the way" and mark delivered directly
  const visible = stations.filter((s) => s !== 'delivering' || at.delivering || order.status === 'delivering' || !at.delivered)
  const current = stopped ? null : order.status
  const currentIdx = current ? visible.indexOf(current) : -1
  const lastReached = stopped ? Math.max(...visible.map((s, i) => (at[s] ? i : -1))) : currentIdx

  return (
    <ol className="rail" aria-label={STATUSES[order.status][lang]}>
      {visible.map((s, i) => {
        const cls = stopped
          ? i <= lastReached
            ? 'station done'
            : i === lastReached + 1
              ? 'station stop'
              : 'station'
          : i < currentIdx
            ? 'station done'
            : i === currentIdx
              ? order.status === 'accepted'
                ? 'station done'
                : 'station now'
              : 'station'
        const label = stopped && i === lastReached + 1 ? STATUSES[order.status][lang] : STAGES[s][lang]
        const when = at[s] ?? (stopped && i === lastReached + 1 ? at[order.status] : undefined)
        return (
          <li key={s} className={cls}>
            <span className="pin" />
            <span>{label}</span>
            {when && <time dateTime={when}>{dateTime(when, lang)}</time>}
          </li>
        )
      })}
    </ol>
  )
}
