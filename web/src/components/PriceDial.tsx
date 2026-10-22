import { useEffect, useState } from 'react'
import { useT } from '../i18n'
import { amd } from '../lib/format'

const STEP = 10 // drams

const roundTo = (x: number) => Math.round(x / STEP) * STEP

/**
 * Haggling with the thumb: a bounded slider between "lowest sensible" and "just below the other side's price",
 * with quick presets and the money it means on this line. The number stays editable for exact prices.
 */
export function PriceDial({
  reference,
  qty,
  value,
  min,
  max,
  unitLabel,
  onCommit,
  presets = [3, 5, 7, 10],
  showSaving = true,
  autoCommit = false,
}: {
  reference: number // price the discount is measured from
  qty: number
  value: number | null
  min: number
  max: number
  unitLabel: string
  onCommit: (price: number) => void
  presets?: number[]
  showSaving?: boolean
  /** Treat the suggested starting price as chosen (answering an offer), instead of waiting for a touch */
  autoCommit?: boolean
}) {
  const t = useT()
  const lo = Math.ceil(min / STEP) * STEP
  const hi = Math.max(lo, Math.floor(max / STEP) * STEP)
  const start = value ?? Math.min(hi, Math.max(lo, roundTo(reference * 0.95)))
  const [price, setPrice] = useState(start)
  const [text, setText] = useState(String(start))

  useEffect(() => {
    if (autoCommit && value === null) onCommit(start)
    // only once, on open
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (value !== null) {
      setPrice(value)
      setText(String(value))
    }
  }, [value])

  const pct = reference ? Math.round(((reference - price) / reference) * 1000) / 10 : 0
  const saving = Math.max(0, Math.round((reference - price) * qty))
  const set = (p: number, commit = false) => {
    const v = Math.min(hi, Math.max(lo, p))
    setPrice(v)
    setText(String(v))
    if (commit) onCommit(v)
  }

  return (
    <div className="dial">
      <div className="dial-top">
        <div>
          <div className="muted small">
            {t('between')}, ֏ / {unitLabel}
          </div>
          <div className="dial-price">{amd(price)}</div>
        </div>
        <div className="dial-delta">
          −{pct}%
          {showSaving && (
            <div>
              −{amd(saving)} {t('per_line')}
            </div>
          )}
        </div>
      </div>
      <input
        type="range"
        min={lo}
        max={hi}
        step={STEP}
        value={price}
        aria-label={t('my_price')}
        onChange={(e) => set(Number(e.target.value))}
        onPointerUp={() => onCommit(price)}
        onKeyUp={() => onCommit(price)}
      />
      <div className="dial-scale">
        <span>{amd(lo)}</span>
        <span>
          {t('list_price')} {amd(reference)}
        </span>
      </div>
      <div className="dial-row">
        <div className="dial-presets">
          {presets
            .map((p) => ({ p, v: roundTo(reference * (1 - p / 100)) }))
            .filter(({ v }) => v >= lo && v <= hi)
            .map(({ p, v }) => (
              <button key={p} type="button" className={v === price ? 'on' : ''} onClick={() => set(v, true)}>
                −{p}%
              </button>
            ))}
        </div>
        <input
          className="dial-input"
          inputMode="numeric"
          aria-label={t('price')}
          value={text}
          onChange={(e) => setText(e.target.value.replace(/\D/g, ''))}
          onBlur={() => set(Number(text) || price, true)}
          onKeyDown={(e) => e.key === 'Enter' && set(Number(text) || price, true)}
        />
      </div>
    </div>
  )
}
