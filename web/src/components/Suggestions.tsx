import { useState } from 'react'
import { useLang, useT } from '../i18n'
import type { Suggestion } from '../lib/api'
import { useCart } from '../lib/cart'
import { amd, qty as fmtQty, tr, unit } from '../lib/format'

/** One suggested product with a one-tap add. */
function Pick({ s, note }: { s: Suggestion; note?: string }) {
  const lang = useLang()
  const { setItem } = useCart()
  const [busy, setBusy] = useState(false)
  return (
    <li className="pick">
      <div className="pick-main">
        <span className="pick-name">{tr(s.name, lang)}</span>
        <span className="muted small num">
          {amd(s.price_amd)} / {unit(s.unit, lang)}
          {note && ` · ${note}`}
        </span>
      </div>
      <button
        type="button"
        className="ibtn add"
        disabled={busy}
        aria-label={`+ ${tr(s.name, lang)}`}
        onClick={async () => {
          setBusy(true)
          try {
            await setItem(s.product_id, s.qty)
          } finally {
            setBusy(false)
          }
        }}
      >
        +
      </button>
    </li>
  )
}

/** Inside a seller's ticket: what closes the gap to the minimum or free delivery, and the seller's services. */
export function SellerSuggestions({ items }: { items: Suggestion[] }) {
  const t = useT()
  const lang = useLang()
  const fill = items.filter((s) => s.kind === 'fill_min' || s.kind === 'fill_free_delivery')
  const services = items.filter((s) => s.kind === 'service')
  if (!fill.length && !services.length) return null
  return (
    <div className="suggest">
      {fill.length > 0 && (
        <>
          <p className="suggest-title">
            {fill[0].kind === 'fill_min' ? t('fill_min') : t('fill_free_delivery')}{' '}
            <b className="num">{amd(fill[0].gap_amd ?? 0)}</b> — {t('add_one_of')}
          </p>
          <ul className="picks">
            {fill.map((s) => (
              <Pick key={s.product_id} s={s} note={`${t('from')} ${fmtQty(s.qty)} ${unit(s.unit, lang)}`} />
            ))}
          </ul>
        </>
      )}
      {services.length > 0 && (
        <>
          <p className="suggest-title">{t('seller_services')}</p>
          <ul className="picks">
            {services.map((s) => (
              <Pick key={s.product_id} s={s} />
            ))}
          </ul>
        </>
      )}
    </div>
  )
}

/** Under a cart line: the next volume price. */
export function TierHint({ s, currentQty }: { s: Suggestion; currentQty: string }) {
  const t = useT()
  const lang = useLang()
  const { setItem } = useCart()
  const extra = Number(s.qty) - Number(currentQty)
  return (
    <div className="tier-hint">
      <span>
        {t('tier_more')} {fmtQty(String(extra))} {unit(s.unit, lang)} — {amd(s.price_amd)} / {unit(s.unit, lang)},{' '}
        {t('you_save').toLowerCase()} <b className="num">{amd(s.saving_amd ?? 0)}</b>
      </span>
      <button type="button" className="pill haggle" onClick={() => void setItem(s.product_id, s.qty)}>
        {t('take')} {fmtQty(s.qty)} {unit(s.unit, lang)}
      </button>
    </div>
  )
}

/** After the tickets: what the venue usually buys, and what goes with the order from other sellers. */
export function CartSuggestions({ items }: { items: Suggestion[] }) {
  const t = useT()
  const lang = useLang()
  const usual = items.filter((s) => s.kind === 'usual')
  const complement = items.filter((s) => s.kind === 'complement')
  if (!usual.length && !complement.length) return null
  return (
    <section className="ticket suggest-block">
      {usual.length > 0 && (
        <>
          <h2>{t('usually_buy')}</h2>
          <ul className="picks">
            {usual.map((s) => (
              <Pick key={s.product_id} s={s} note={`${s.seller.display_name} · ${t('last_time')} ${fmtQty(s.last_qty ?? s.qty)} ${unit(s.unit, lang)}`} />
            ))}
          </ul>
        </>
      )}
      {complement.length > 0 && (
        <>
          <h2>{t('goes_with_order')}</h2>
          <ul className="picks">
            {complement.map((s) => (
              <Pick key={s.product_id} s={s} note={s.seller.display_name} />
            ))}
          </ul>
        </>
      )}
    </section>
  )
}
