import { useCallback, useEffect, useState } from 'react'
import { FILE_KINDS, FILE_STATUS, problemText, useLang, useT, VERIFICATION } from '../i18n'
import { api, ApiError, openFile, type Verification, type VerificationStatus } from '../lib/api'
import { dateTime } from '../lib/format'

const TABS: VerificationStatus[] = ['pending', 'rejected', 'verified']

/** Operator queue: check each company's documents against the registry, then let it trade. */
export function Moderation() {
  const t = useT()
  const lang = useLang()
  const [tab, setTab] = useState<VerificationStatus>('pending')
  const [items, setItems] = useState<Verification[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(
    () => api.adminQueue([tab]).then(setItems, (e: ApiError) => setError(problemText(e.code, lang))),
    [tab, lang],
  )
  useEffect(() => {
    void load()
  }, [load])

  return (
    <div className="stack page" style={{ maxWidth: 900 }}>
      <h1 className="page-title">{t('tab_moderation')}</h1>
      <div className="chips">
        {TABS.map((s) => (
          <button key={s} className={s === tab ? 'chip on' : 'chip'} onClick={() => setTab(s)}>
            {VERIFICATION[s][lang]}
          </button>
        ))}
      </div>
      {error && <p className="error">{error}</p>}
      {items?.length === 0 && <p className="col-empty">{t('queue_empty')}</p>}
      {items?.map((v) => <CompanyCard key={v.organization.id} v={v} reload={load} />)}
    </div>
  )
}

function CompanyCard({ v, reload }: { v: Verification; reload: () => Promise<void> }) {
  const t = useT()
  const lang = useLang()
  const o = v.organization
  const [note, setNote] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function run(p: Promise<unknown>) {
    setError(null)
    try {
      await p
      await reload()
    } catch (e) {
      const ex = e as ApiError
      setError(ex.problems?.length ? ex.problems.map((x) => problemText(x.code, lang)).join(' · ') : problemText(ex.code, lang))
    }
  }

  const rows: [string, string | null][] = [
    [t('tin'), o.tin],
    [t('legal_name'), o.legal_name],
    [t('legal_address'), o.legal_address],
    [t('director'), o.director_name],
    [t('reg_number'), o.registration_number],
    [t('tax_regime'), o.tax_regime ? t(`regime_${o.tax_regime}` as 'regime_vat') : null],
    [t('bank_account'), o.bank_account ? `${o.bank_name ?? ''} ${o.bank_account}` : null],
  ]
  return (
    <section className="ticket" style={{ display: 'grid', gap: 12 }}>
      <header className="ticket-head">
        <div>
          <h2>{o.display_name}</h2>
          <span className="muted small">
            {[o.is_buyer && t('role_buyer'), o.is_seller && t('role_seller')].filter(Boolean).join(' + ')} · {VERIFICATION[o.verification_status][lang]}
          </span>
        </div>
        <span className={o.registry_source === 'manual' ? 'pill lamp' : 'pill plain'}>
          {o.registry_source === 'manual' ? `✎ ${t('typed_by_hand')}` : `✓ ${o.registry_source}`}
        </span>
      </header>
      <dl className="sums">
        {rows.map(([k, val]) => (
          <div key={k} style={{ display: 'contents' }}>
            <dt>{k}</dt>
            <dd style={{ fontWeight: 500 }}>{val || '—'}</dd>
          </div>
        ))}
      </dl>
      <ul className="lines">
        {v.files.map((f) => (
          <li key={f.id} className="line">
            <div className="line-main">
              <div>
                <div className="line-name">{FILE_KINDS[f.kind][lang]}</div>
                <button className="link small" onClick={() => void openFile(`/files/${f.id}`)}>
                  📄 {f.file_name}
                </button>
                <div className="line-sub">{dateTime(f.created_at, lang)}</div>
              </div>
              <span className={f.status === 'approved' ? 'pill brand' : f.status === 'rejected' ? 'pill plain' : 'pill lamp'}>
                {FILE_STATUS[f.status][lang]}
              </span>
            </div>
            {f.status === 'pending' && (
              <div className="line-tools" style={{ justifyContent: 'flex-end' }}>
                <button className="btn ghost" style={{ minHeight: 40 }} onClick={() => run(api.reviewFile(f.id, false, note || undefined))}>
                  {t('reject')}
                </button>
                <button className="btn primary" style={{ minHeight: 40 }} onClick={() => run(api.reviewFile(f.id, true))}>
                  {t('approve')}
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
      <label className="field">
        <span>{t('note')}</span>
        <input value={note} onChange={(e) => setNote(e.target.value)} />
      </label>
      {error && <p className="error">{error}</p>}
      {o.verification_status !== 'verified' && (
        <div className="actions">
          <button className="btn ghost" onClick={() => run(api.reviewOrg(o.id, false, note || undefined))}>
            {t('reject')}
          </button>
          <button className="btn accent" onClick={() => run(api.reviewOrg(o.id, true, note || undefined))}>
            {t('approve_company')}
          </button>
        </div>
      )}
    </section>
  )
}
