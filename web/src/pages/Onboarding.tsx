import type React from 'react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LangSwitch } from '../App'
import { Field, SelectField } from '../components/Field'
import { problemText, useLang, useT } from '../i18n'
import { api, ApiError, type Lookup, type Me, type NewOrg, type TaxRegime } from '../lib/api'

const DISTRICTS = ['Kentron', 'Arabkir', 'Ajapnyak', 'Davtashen', 'Nor Nork', 'Malatia-Sebastia', 'Shengavit', 'Erebuni']
const VENUES = ['cafe', 'restaurant', 'bar', 'bakery', 'hotel', 'catering', 'other']
const VENUE_LABEL: Record<string, Record<'hy' | 'ru' | 'en', string>> = {
  cafe: { hy: 'Սրճարան', ru: 'Кафе', en: 'Cafe' },
  restaurant: { hy: 'Ռեստորան', ru: 'Ресторан', en: 'Restaurant' },
  bar: { hy: 'Բար', ru: 'Бар', en: 'Bar' },
  bakery: { hy: 'Հացատուն', ru: 'Пекарня', en: 'Bakery' },
  hotel: { hy: 'Հյուրանոց', ru: 'Отель', en: 'Hotel' },
  catering: { hy: 'Քեյթրինգ', ru: 'Кейтеринг', en: 'Catering' },
  other: { hy: 'Այլ', ru: 'Другое', en: 'Other' },
}

type Step = 'role' | 'tin' | 'form'

/** First run without a company: pick a role, find the company by TIN, confirm the requisites. */
export function Onboarding({ me, onDone, onSignOut }: { me: Me; onDone: () => Promise<void>; onSignOut: () => void }) {
  const t = useT()
  const lang = useLang()
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>('role')
  const [form, setForm] = useState<NewOrg>({ kind: 'buyer', tin: '', legal_name: '', venue_type: 'cafe', district: 'Kentron' })
  const [lookup, setLookup] = useState<Lookup | null>(null)
  const [busy, setBusy] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)

  const set = (patch: Partial<NewOrg>) => setForm((f) => ({ ...f, ...patch }))
  const bind = (key: keyof NewOrg) => ({
    value: (form[key] as string | null | undefined) ?? '',
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => set({ [key]: e.target.value }),
    error: errors[key as string],
  })

  async function find() {
    setBusy(true)
    setError(null)
    try {
      const r = await api.lookup(form.tin)
      setLookup(r)
      const c = r.company
      set({
        tin: r.tin,
        ...(c && {
          legal_name: c.legal_name,
          display_name: c.legal_name.split('/').at(-1)?.trim(),
          registration_number: c.registration_number,
          legal_address: c.legal_address,
          director_name: c.director_name,
          tax_regime: c.tax_regime,
        }),
      })
      if (!r.already_registered && (!c || c.active)) setStep('form')
    } catch (e) {
      setError(problemText((e as ApiError).code === 'validation_failed' ? 'bad_tin' : (e as ApiError).code, lang))
    } finally {
      setBusy(false)
    }
  }

  async function create(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    setErrors({})
    try {
      await api.createOrg(form)
      await onDone()
      navigate(form.kind === 'seller' ? '/company' : '/', { replace: true })
    } catch (err) {
      const ex = err as ApiError
      const byField: Record<string, string> = {}
      for (const p of ex.problems ?? []) if (typeof p.field === 'string') byField[p.field] = problemText(p.code, lang)
      setErrors(byField)
      if (!Object.keys(byField).length) setError(problemText(ex.code, lang))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login page">
      <div className="login-top" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
        <span className="muted small">{me.name}</span>
        <span style={{ display: 'flex', gap: 8 }}>
          <LangSwitch />
          <button className="link" onClick={onSignOut}>
            {t('logout')}
          </button>
        </span>
      </div>
      <h1 className="tagline" style={{ marginTop: 24 }}>
        {t('onb_title')}
      </h1>

      {step === 'role' && (
        <div className="stack">
          <p className="section-title">{t('onb_role')}</p>
          <button className="reorder-card" style={{ width: '100%', padding: 24 }} onClick={() => (set({ kind: 'buyer' }), setStep('tin'))}>
            <span className="ibtn" aria-hidden>↗</span>
            <span className="big">{t('role_buyer')}</span>
            <span className="names">{t('role_buyer_sub')}</span>
          </button>
          <button className="reorder-card ticket dark" style={{ width: '100%', padding: 24 }} onClick={() => (set({ kind: 'seller' }), setStep('tin'))}>
            <span className="ibtn" aria-hidden>↗</span>
            <span className="big">{t('role_seller')}</span>
            <span className="names">{t('role_seller_sub')}</span>
          </button>
        </div>
      )}

      {step === 'tin' && (
        <section className="ticket" style={{ display: 'grid', gap: 12 }}>
          <span className="pill brand" style={{ justifySelf: 'start' }}>
            {form.kind === 'buyer' ? t('role_buyer') : t('role_seller')}
          </span>
          <Field
            label={t('tin')}
            hint={t('tin_hint')}
            inputMode="numeric"
            autoFocus
            placeholder="02744119"
            value={form.tin}
            onChange={(e) => set({ tin: e.target.value })}
            onKeyDown={(e) => e.key === 'Enter' && find()}
          />
          <button className="btn primary block" disabled={busy || form.tin.replace(/\D/g, '').length < 8} onClick={find}>
            {t('find')}
          </button>
          {lookup?.already_registered && <p className="warn">{t('already_on_qb')}</p>}
          {lookup?.company && !lookup.company.active && <p className="warn">{t('company_closed')}</p>}
          {lookup && !lookup.found && !lookup.already_registered && (
            <button className="link small" onClick={() => setStep('form')}>
              {t('not_found_manual')} →
            </button>
          )}
          {error && <p className="error">{error}</p>}
          <button className="link" onClick={() => setStep('role')}>
            ← {t('back_step')}
          </button>
        </section>
      )}

      {step === 'form' && (
        <form className="ticket" style={{ display: 'grid', gap: 12 }} onSubmit={create}>
          {lookup?.found ? (
            <div className="next" style={{ padding: 14 }}>
              <span>
                <strong style={{ fontSize: 15 }}>✓ {t('found_in')}</strong>
                {lookup.provider === 'demo' && <span className="muted small">{t('demo_data')}</span>}
              </span>
              <span className="clock">{form.tin}</span>
            </div>
          ) : (
            <p className="warn">{t('not_found_manual')}</p>
          )}
          <Field label={t('legal_name')} required {...bind('legal_name')} />
          <Field label={t('display_name')} {...bind('display_name')} />
          <SelectField
            label={t('tax_regime')}
            value={form.tax_regime ?? ''}
            onChange={(e) => set({ tax_regime: (e.target.value || null) as TaxRegime | null })}
            options={[
              { value: '', label: '—' },
              { value: 'vat', label: t('regime_vat') },
              { value: 'turnover', label: t('regime_turnover') },
              { value: 'micro', label: t('regime_micro') },
            ]}
          />
          <Field label={t('legal_address')} {...bind('legal_address')} />
          <Field label={t('director')} {...bind('director_name')} />
          <Field label={t('reg_number')} {...bind('registration_number')} />
          <Field label={t('phone')} inputMode="tel" {...bind('phone')} />
          {form.kind === 'buyer' ? (
            <>
              <SelectField
                label={t('venue_type')}
                value={form.venue_type ?? 'cafe'}
                onChange={(e) => set({ venue_type: e.target.value })}
                options={VENUES.map((v) => ({ value: v, label: VENUE_LABEL[v][lang] }))}
              />
              <Field label={t('delivery_address')} required {...bind('delivery_address')} />
              <SelectField
                label={t('district')}
                value={form.district ?? ''}
                onChange={(e) => set({ district: e.target.value })}
                options={DISTRICTS.map((d) => ({ value: d, label: d }))}
              />
            </>
          ) : (
            <>
              <Field label={t('bank_name')} {...bind('bank_name')} />
              <Field label={t('bank_account')} inputMode="numeric" {...bind('bank_account')} />
            </>
          )}
          {error && <p className="error">{error}</p>}
          <button className="btn primary block" disabled={busy}>
            {t('create_company')} →
          </button>
          <button type="button" className="link" onClick={() => setStep('tin')}>
            ← {t('back_step')}
          </button>
        </form>
      )}
    </div>
  )
}
