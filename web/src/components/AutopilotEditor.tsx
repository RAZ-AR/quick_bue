import { useEffect, useState } from 'react'
import { useT } from '../i18n'
import type { Autopilot } from '../lib/api'
import { amd } from '../lib/format'
import { decide, pct, priceForDiscount, sampleDiscounts, type PctRule } from '../lib/haggle'

const ACCEPT_PRESETS = [200, 300, 500, 700, 1000]
const MAX_PRESETS = [500, 800, 1000, 1500, 2000]

export const DEFAULT_AUTOPILOT: Autopilot = {
  enabled: true,
  accept_discount_bp: 300,
  max_discount_bp: 1000,
  auto_counter: true,
  min_line_amd: null,
  share_hint: false,
}

/**
 * The seller autopilot in plain words: "agree at once up to 3%", "decline beyond 10%", "counter halfway
 * in between", and a live table of what will happen to sample offers at this product's price.
 */
export function AutopilotEditor({
  value,
  basePrice,
  unitLabel,
  onChange,
}: {
  value: Autopilot
  basePrice: number
  unitLabel: string
  onChange: (next: Autopilot) => void
}) {
  const t = useT()
  const set = (patch: Partial<Autopilot>) => onChange({ ...value, ...patch })
  const rule: PctRule | null =
    value.accept_discount_bp !== null
      ? { acceptBp: value.accept_discount_bp, maxBp: value.max_discount_bp, autoCounter: value.auto_counter }
      : null

  return (
    <fieldset className="box autopilot">
      <p className="muted small">{t('autopilot_hint')}</p>

      <PctRow
        id="ap-accept"
        label={t('ap_accept')}
        value={value.accept_discount_bp}
        presets={ACCEPT_PRESETS}
        basePrice={basePrice}
        onChange={(bp) => set({ accept_discount_bp: bp })}
      />
      <PctRow
        id="ap-max"
        label={t('ap_max')}
        value={value.max_discount_bp}
        presets={MAX_PRESETS}
        basePrice={basePrice}
        noneLabel={t('ap_no_max')}
        onChange={(bp) => set({ max_discount_bp: bp })}
      />
      <label className="check">
        <input type="checkbox" checked={value.auto_counter} onChange={(e) => set({ auto_counter: e.target.checked })} /> {t('auto_counter')}
      </label>
      <label className="check">
        <input type="checkbox" checked={value.share_hint} onChange={(e) => set({ share_hint: e.target.checked })} /> {t('ap_share')}
      </label>
      {value.share_hint && <p className="muted small">{t('ap_share_note')}</p>}

      {rule && basePrice > 0 && (
        <div className="ap-examples">
          <div className="muted small">
            {t('ap_examples')} {amd(basePrice)} / {unitLabel}
          </div>
          <ul>
            {sampleDiscounts(rule).map((bp) => {
              const offer = priceForDiscount(basePrice, bp)
              const v = decide(offer, basePrice, rule)
              return (
                <li key={bp} className={`ap-row ${v.kind}`}>
                  <span className="num">
                    {t('ap_offer')} −{pct(bp)}% · {amd(offer)}
                  </span>
                  <span className="ap-arrow" aria-hidden>
                    →
                  </span>
                  <span className="ap-verdict">
                    {v.kind === 'accept' && t('ap_will_accept')}
                    {v.kind === 'counter' && `${t('ap_will_counter')} ${amd(v.price)}`}
                    {v.kind === 'decline' && `${t('ap_will_decline')} ${amd(basePrice)}`}
                    {v.kind === 'manual' && t('ap_will_manual')}
                  </span>
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </fieldset>
  )
}

function PctRow({
  id,
  label,
  value,
  presets,
  basePrice,
  noneLabel,
  onChange,
}: {
  id: string
  label: string
  value: number | null
  presets: number[]
  basePrice: number
  noneLabel?: string
  onChange: (bp: number | null) => void
}) {
  const [text, setText] = useState(value === null ? '' : pct(value))
  useEffect(() => setText(value === null ? '' : pct(value)), [value])
  const commit = (raw: string) => {
    const n = Number(raw.replace(',', '.'))
    if (raw.trim() === '' || !Number.isFinite(n) || n <= 0) onChange(noneLabel ? null : value)
    else onChange(Math.round(n * 100))
  }
  return (
    <div className="ap-pct">
      <label htmlFor={id}>{label}</label>
      <div className="dial-row">
        <div className="dial-presets">
          {noneLabel && (
            <button type="button" className={value === null ? 'on' : ''} onClick={() => onChange(null)}>
              {noneLabel}
            </button>
          )}
          {presets.map((bp) => (
            <button key={bp} type="button" className={value === bp ? 'on' : ''} onClick={() => onChange(bp)}>
              {pct(bp)}%
            </button>
          ))}
        </div>
        <span className="ap-input">
          <input
            id={id}
            className="dial-input"
            inputMode="decimal"
            value={text}
            onChange={(e) => setText(e.target.value.replace(/[^\d.,]/g, ''))}
            onBlur={(e) => commit(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), commit(e.currentTarget.value))}
          />
          %
        </span>
      </div>
      {value !== null && basePrice > 0 && <div className="muted small num">= {amd(priceForDiscount(basePrice, value))}</div>}
    </div>
  )
}
