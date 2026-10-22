import type React from 'react'
import { useEffect, useState } from 'react'
import { Field } from '../components/Field'
import { problemText, useLang, useT } from '../i18n'
import { api, ApiError, type SellerSettings as Settings } from '../lib/api'

const DISTRICTS = ['Kentron', 'Arabkir', 'Ajapnyak', 'Davtashen', 'Nor Nork', 'Malatia-Sebastia', 'Shengavit', 'Erebuni', 'Kanaker-Zeytun', 'Avan', 'Nubarashen', 'Nork-Marash']
const DAYS: Record<'hy' | 'ru' | 'en', string[]> = {
  hy: ['Երկ', 'Երք', 'Չրք', 'Հնգ', 'Ուրբ', 'Շբթ', 'Կիր'],
  ru: ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'],
  en: ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'],
}

/** Seller cabinet: minimum order, cut-off, delivery fee, districts and weekdays. */
export function SellerSettings() {
  const t = useT()
  const lang = useLang()
  const [s, setS] = useState<Settings | null>(null)
  const [saved, setSaved] = useState(false)
  const [errors, setErrors] = useState<string[]>([])

  useEffect(() => {
    api.sellerSettings().then(setS)
  }, [])
  if (!s) return <p className="muted">{t('loading')}</p>
  const set = (patch: Partial<Settings>) => (setS({ ...s, ...patch }), setSaved(false))
  const num = (v: string) => (v === '' ? 0 : Number(v.replace(/\D/g, '')))
  const zoneOf = (d: string) => s.zones.find((z) => z.district === d)

  function toggleDay(district: string, day: number) {
    if (!s) return
    const z = zoneOf(district)
    const days = z ? (z.weekdays.includes(day) ? z.weekdays.filter((x) => x !== day) : [...z.weekdays, day]) : [day]
    const others = s.zones.filter((x) => x.district !== district)
    set({ zones: days.length ? [...others, { district, weekdays: days.sort() }] : others })
  }

  async function save(e: React.FormEvent) {
    e.preventDefault()
    setErrors([])
    try {
      setS(await api.saveSellerSettings(s!))
      setSaved(true)
    } catch (err) {
      const ex = err as ApiError
      setErrors(ex.problems?.length ? ex.problems.map((p) => problemText(p.code, lang)) : [problemText(ex.code, lang)])
    }
  }

  return (
    <form className="stack page" onSubmit={save}>
      <h1 className="page-title">{t('delivery_terms')}</h1>
      <section className="ticket form-grid">
        <Field label={t('min_order_label')} inputMode="numeric" value={s.min_order_amd || ''} onChange={(e) => set({ min_order_amd: num(e.target.value) })} />
        <Field label={t('cutoff')} type="time" value={s.cutoff_time.slice(0, 5)} onChange={(e) => set({ cutoff_time: e.target.value })} />
        <Field label={t('lead_days')} inputMode="numeric" value={s.lead_days} onChange={(e) => set({ lead_days: num(e.target.value) })} />
        <Field label={t('delivery_fee')} inputMode="numeric" value={s.delivery_fee_amd || ''} onChange={(e) => set({ delivery_fee_amd: num(e.target.value) })} />
        <Field
          label={t('free_from')}
          inputMode="numeric"
          value={s.free_delivery_from_amd ?? ''}
          onChange={(e) => set({ free_delivery_from_amd: e.target.value ? num(e.target.value) : null })}
        />
        <Field label={t('response_hours')} inputMode="numeric" value={s.offer_response_hours} onChange={(e) => set({ offer_response_hours: num(e.target.value) })} />
      </section>
      <section className="ticket">
        <header className="ticket-head">
          <h2>{t('zones')}</h2>
          <span className="muted small">{t('zones_hint')}</span>
        </header>
        <ul className="lines">
          {DISTRICTS.map((d) => {
            const z = zoneOf(d)
            return (
              <li key={d} className="line zone-row">
                <span className="line-name">{d}</span>
                <span className="days">
                  {DAYS[lang].map((label, i) => (
                    <button
                      type="button"
                      key={label}
                      className={z?.weekdays.includes(i + 1) ? 'day on' : 'day'}
                      aria-pressed={!!z?.weekdays.includes(i + 1)}
                      onClick={() => toggleDay(d, i + 1)}
                    >
                      {label}
                    </button>
                  ))}
                </span>
              </li>
            )
          })}
        </ul>
      </section>
      {errors.map((e) => (
        <p key={e} className="error">
          {e}
        </p>
      ))}
      <button className="btn primary block">{saved ? `✓ ${t('saved')}` : t('save')}</button>
    </form>
  )
}
