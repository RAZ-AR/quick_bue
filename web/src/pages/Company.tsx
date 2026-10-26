import type React from 'react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { AddressField } from '../components/AddressField'
import { ContactField } from '../components/ContactField'
import { DeliveryAddresses } from '../components/DeliveryAddresses'
import { Field, SelectField } from '../components/Field'
import { FILE_KINDS, FILE_STATUS, problemText, useLang, useT, VERIFICATION } from '../i18n'
import { api, ApiError, openFile, type FileKind, type OrgDetail, type OrgFile, type TaxRegime, type Verification } from '../lib/api'
import { date } from '../lib/format'
import { useSession } from '../lib/session'

/** The company profile: requisites printed on documents, and the verification checklist. */
export function Company() {
  const { reload: onChanged } = useSession()
  const t = useT()
  const lang = useLang()
  const [v, setV] = useState<Verification | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => api.verification().then(setV, (e: ApiError) => setError(problemText(e.code, lang))), [lang])
  useEffect(() => {
    void load()
  }, [load])

  // Links like /company#addresses (from the cart) land on that section once it is there
  useEffect(() => {
    if (v && window.location.hash) document.getElementById(window.location.hash.slice(1))?.scrollIntoView({ block: 'start' })
  }, [v])

  if (!v) return error ? <p className="error">{error}</p> : <p className="muted">{t('loading')}</p>
  const org = v.organization

  return (
    <div className="stack page">
      <h1 className="page-title">
        {org.display_name}
        <small>
          {t('tin')}: <span className="num">{org.tin}</span>
        </small>
      </h1>
      {/* The phone tab bar has no room for these: reach them from the company page */}
      <nav className="quick-links">
        <Link to="/documents" className="next calm">
          <strong>{t('tab_documents')}</strong>
          <span className="clock">→</span>
        </Link>
        <Link to="/notifications" className="next calm">
          <strong>{t('tab_notifications')}</strong>
          <span className="clock">→</span>
        </Link>
      </nav>
      <VerificationBlock v={v} reload={load} onChanged={onChanged} />
      <Roles org={org} onChanged={async () => (await load(), await onChanged())} />
      {org.is_buyer && <DeliveryAddresses />}
      <Requisites org={org} onSaved={load} />
    </div>
  )
}

function VerificationBlock({ v, reload, onChanged }: { v: Verification; reload: () => Promise<void>; onChanged: () => Promise<void> }) {
  const t = useT()
  const lang = useLang()
  const org = v.organization
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const status = org.verification_status
  const tone = status === 'verified' ? 'ticket dark' : status === 'pending' || status === 'none' ? 'ticket accent' : 'ticket'

  async function submit() {
    setBusy(true)
    setError(null)
    try {
      await api.submitVerification()
      await reload()
      await onChanged()
    } catch (e) {
      const ex = e as ApiError
      setError(ex.problems?.length ? ex.problems.map((p) => problemText(p.code, lang)).join(' · ') : problemText(ex.code, lang))
    } finally {
      setBusy(false)
    }
  }

  const kinds: { kind: FileKind; required: boolean }[] = [
    ...v.required.map((k) => ({ kind: k, required: true })),
    ...v.recommended.map((k) => ({ kind: k, required: false })),
  ]
  return (
    <>
      <section className={tone}>
        <header className="ticket-head">
          <h2>{t('verification')}</h2>
          <span className="pill brand">{VERIFICATION[status][lang]}</span>
        </header>
        {status === 'verified' && org.verified_at && <p style={{ margin: '10px 0 0' }}>✓ {date(org.verified_at, lang)}</p>}
        {org.review_note && <p style={{ margin: '10px 0 0' }}>💬 {org.review_note}</p>}
        {org.is_seller && status !== 'verified' && (
          <p style={{ margin: '10px 0 0' }}>{status === 'pending' ? t('pending_seller_banner') : t('upload_to_sell')}</p>
        )}
      </section>

      <section className="ticket">
        <p className="muted small" style={{ marginTop: 0 }}>
          {t('files_hint')}
        </p>
        <ul className="lines">
          {kinds.map(({ kind, required }) => (
            <FileSlot key={kind} kind={kind} required={required} files={v.files.filter((f) => f.kind === kind)} reload={reload} />
          ))}
        </ul>
        {error && <p className="error">{error}</p>}
        {status !== 'verified' && status !== 'pending' && (
          <button className="btn primary block" disabled={busy} onClick={submit}>
            {t('submit_review')} →
          </button>
        )}
      </section>
    </>
  )
}

function FileSlot({ kind, required, files, reload }: { kind: FileKind; required: boolean; files: OrgFile[]; reload: () => Promise<void> }) {
  const t = useT()
  const lang = useLang()
  const input = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function pick(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setBusy(true)
    setError(null)
    try {
      await api.uploadFile(kind, file)
      await reload()
    } catch (err) {
      const ex = err as ApiError
      setError(problemText(ex.problems?.[0]?.code ?? ex.code, lang))
    } finally {
      setBusy(false)
    }
  }

  return (
    <li className="line">
      <div className="line-main">
        <div>
          <div className="line-name">{FILE_KINDS[kind][lang]}</div>
          <div className="line-sub">{required ? t('required') : t('recommended')}</div>
        </div>
        <button className={files.length ? 'ibtn' : 'ibtn dark'} disabled={busy} onClick={() => input.current?.click()} aria-label={t('upload')} title={t('upload')}>
          {busy ? '…' : '+'}
        </button>
        <input ref={input} type="file" accept="application/pdf,image/*" hidden onChange={pick} />
      </div>
      {files.map((f) => (
        <div key={f.id} className="line-tools">
          <button className="link small" onClick={() => void openFile(`/files/${f.id}`)}>
            📄 {f.file_name}
          </button>
          <span style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <span className={f.status === 'approved' ? 'pill brand' : f.status === 'rejected' ? 'pill plain' : 'pill lamp'}>
              {FILE_STATUS[f.status][lang]}
            </span>
            {f.status !== 'approved' && (
              <button className="link" onClick={async () => (await api.deleteFile(f.id), await reload())} aria-label={t('remove')}>
                ✕
              </button>
            )}
          </span>
          {f.review_note && <span className="muted small" style={{ flexBasis: '100%' }}>💬 {f.review_note}</span>}
        </div>
      ))}
      {error && <p className="error small">{error}</p>}
    </li>
  )
}

function Requisites({ org, onSaved }: { org: OrgDetail; onSaved: () => Promise<void> }) {
  const t = useT()
  const [form, setForm] = useState(org)
  const [saved, setSaved] = useState(false)
  const [busy, setBusy] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const lang = useLang()
  const setValue = (key: keyof OrgDetail, value: string) => (setForm((f) => ({ ...f, [key]: value })), setSaved(false))
  const bind = (key: keyof OrgDetail) => ({
    value: (form[key] as string | null) ?? '',
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => setValue(key, e.target.value),
  })

  async function save(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setErrors({})
    try {
      const { display_name, legal_address, director_name, bank_name, bank_account, phone, email, registration_number, tax_regime } = form
      await api.updateOrg({ display_name, legal_address, director_name, bank_name, bank_account, phone, email, registration_number, tax_regime })
      await onSaved()
      setSaved(true)
    } catch (err) {
      const byField: Record<string, string> = {}
      for (const p of (err as ApiError).problems ?? []) if (typeof p.field === 'string') byField[p.field] = problemText(p.code, lang)
      setErrors(byField)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="ticket" style={{ display: 'grid', gap: 12 }} onSubmit={save}>
      <header className="ticket-head">
        <h2>{t('requisites')}</h2>
        {org.registry_source && <span className="pill plain">{org.registry_source === 'manual' ? '✎' : '✓'} {org.registry_source}</span>}
      </header>
      <p className="muted small" style={{ margin: 0 }}>
        {t('requisites_hint')}
      </p>
      <Field label={t('legal_name')} value={org.legal_name} disabled />
      <Field label={t('display_name')} {...bind('display_name')} />
      <SelectField
        label={t('tax_regime')}
        value={form.tax_regime ?? ''}
        onChange={(e) => (setForm((f) => ({ ...f, tax_regime: (e.target.value || null) as TaxRegime | null })), setSaved(false))}
        options={[
          { value: '', label: '—' },
          { value: 'vat', label: t('regime_vat') },
          { value: 'turnover', label: t('regime_turnover') },
          { value: 'micro', label: t('regime_micro') },
        ]}
      />
      <AddressField label={t('legal_address')} value={form.legal_address ?? ''} onChange={(v) => setValue('legal_address', v)} />
      <Field label={t('director')} {...bind('director_name')} />
      <Field label={t('reg_number')} {...bind('registration_number')} />
      <Field label={t('bank_name')} {...bind('bank_name')} />
      <ContactField kind="bank_account" label={t('bank_account')} value={form.bank_account ?? ''} onChange={(v) => setValue('bank_account', v)} error={errors.bank_account} />
      <ContactField kind="phone" label={t('phone')} value={form.phone ?? ''} onChange={(v) => setValue('phone', v)} error={errors.phone} />
      <ContactField kind="email" label={t('email')} value={form.email ?? ''} onChange={(v) => setValue('email', v)} error={errors.email} />
      <button className="btn primary block" disabled={busy}>
        {saved ? `✓ ${t('saved')}` : t('save')}
      </button>
    </form>
  )
}

/** One company may buy and sell; selling opens after verification. */
function Roles({ org, onChanged }: { org: OrgDetail; onChanged: () => Promise<void> }) {
  const t = useT()
  const lang = useLang()
  const [address, setAddress] = useState('')
  const [asking, setAsking] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function add(role: 'buyer' | 'seller') {
    setError(null)
    try {
      await api.addRole(role, role === 'buyer' ? address : undefined)
      setAsking(false)
      await onChanged()
    } catch (e) {
      const ex = e as ApiError
      setError(problemText(ex.problems?.[0]?.code ?? ex.code, lang))
    }
  }

  return (
    <section className="ticket" style={{ display: 'grid', gap: 10 }}>
      <header className="ticket-head">
        <h2>{t('roles')}</h2>
        <span style={{ display: 'flex', gap: 6 }}>
          {org.is_buyer && <span className="pill brand">{t('mode_buy')}</span>}
          {org.is_seller && <span className="pill brand">{t('mode_sell')}</span>}
        </span>
      </header>
      {!org.is_seller && (
        <button className="btn block" onClick={() => add('seller')}>
          + {t('add_seller_role')}
        </button>
      )}
      {!org.is_buyer &&
        (asking ? (
          <div className="dial-row">
            <label className="field" style={{ flex: 1 }}>
              <span>{t('delivery_address')}</span>
              <input value={address} onChange={(e) => setAddress(e.target.value)} />
            </label>
            <button className="ibtn dark" style={{ alignSelf: 'end', marginBottom: 4 }} disabled={!address.trim()} onClick={() => add('buyer')}>
              ✓
            </button>
          </div>
        ) : (
          <button className="btn block" onClick={() => setAsking(true)}>
            + {t('add_buyer_role')}
          </button>
        ))}
      {error && <p className="error small">{error}</p>}
    </section>
  )
}
