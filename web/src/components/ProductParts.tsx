import { useRef, useState } from 'react'
import { problemText, useLang, useT } from '../i18n'
import { api, ApiError, mediaUrl, type ProductDoc, type SellerProduct, type SpecDefs, type SpecValue } from '../lib/api'
import { fullDate, tr } from '../lib/format'
import { filledGroups, specsFor, specText } from '../lib/specs'
import { Field, SelectField } from './Field'

function problemOf(err: unknown, lang: 'hy' | 'ru' | 'en'): string {
  const ex = err as ApiError
  return problemText(ex.problems?.[0]?.code ?? ex.code, lang)
}

/** Seller form: the characteristics of this category, grouped (origin, product, storage, packaging). */
export function SpecFields({
  defs,
  category,
  isService,
  value,
  onChange,
}: {
  defs: SpecDefs
  category: string | null | undefined
  isService: boolean
  value: Record<string, SpecValue>
  onChange: (next: Record<string, SpecValue>) => void
}) {
  const t = useT()
  const lang = useLang()
  const list = specsFor(defs, category, isService)
  if (!list.length) return null
  const set = (code: string, v: SpecValue | null) => {
    const next = { ...value }
    if (v === null || v === '' || v === false) delete next[code]
    else next[code] = v
    onChange(next)
  }
  return (
    <fieldset className="box">
      <legend>{t('specs_title')}</legend>
      {!category && <p className="muted small">{t('specs_pick_category')}</p>}
      {Object.keys(defs.groups).map((group) => {
        const fields = list.filter((s) => s.group === group)
        if (!fields.length) return null
        return (
          <div key={group} className="spec-group">
            <span className="eyebrow">{tr(defs.groups[group], lang)}</span>
            <div className="form-grid tight">
              {fields.map((s) => {
                const label = s.unit ? `${tr(s.label, lang)}, ${tr(s.unit, lang)}` : tr(s.label, lang)
                const v = value[s.code]
                if (s.kind === 'flag')
                  return (
                    <label key={s.code} className="check">
                      <input type="checkbox" checked={!!v} onChange={(e) => set(s.code, e.target.checked)} /> {label}
                    </label>
                  )
                if (s.kind === 'choice')
                  return (
                    <SelectField
                      key={s.code}
                      label={label}
                      value={v === undefined ? '' : String(v)}
                      onChange={(e) => set(s.code, e.target.value || null)}
                      options={[{ value: '', label: '—' }, ...Object.entries(s.options).map(([k, o]) => ({ value: k, label: tr(o, lang) }))]}
                    />
                  )
                return (
                  <Field
                    key={s.code}
                    label={label}
                    inputMode={s.kind === 'number' ? 'decimal' : undefined}
                    value={v === undefined ? '' : String(v)}
                    onChange={(e) => set(s.code, s.kind === 'number' ? e.target.value.replace(/[^\d.,]/g, '') : e.target.value)}
                  />
                )
              })}
            </div>
          </div>
        )
      })}
    </fieldset>
  )
}

/** Seller form: photos (the first is the main one), re-encoded by the server. */
export function PhotoManager({ product, onChange }: { product: SellerProduct; onChange: (p: SellerProduct) => void }) {
  const t = useT()
  const lang = useLang()
  const input = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function run(job: () => Promise<SellerProduct>) {
    setBusy(true)
    setError(null)
    try {
      onChange(await job())
    } catch (err) {
      setError(problemOf(err, lang))
    } finally {
      setBusy(false)
    }
  }

  async function upload(files: FileList | null) {
    if (!files) return
    for (const file of Array.from(files)) await run(() => api.addProductImage(product.id, file))
  }

  return (
    <fieldset className="box">
      <legend>{t('photos_title')}</legend>
      <p className="muted small">{t('photos_hint')}</p>
      <ul className="photo-grid">
        {product.images.map((img, i) => (
          <li key={img.url} className={i === 0 ? 'main' : img.shown === false ? 'hidden' : ''}>
            <img src={mediaUrl(img.thumb)} alt="" loading="lazy" />
            {i > 0 && (
              <button
                type="button"
                className={img.shown === false ? 'photo-eye off' : 'photo-eye'}
                title={img.shown === false ? t('photo_show') : t('photo_hide')}
                aria-label={img.shown === false ? t('photo_show') : t('photo_hide')}
                aria-pressed={img.shown !== false}
                disabled={busy}
                onClick={() => void run(() => api.showProductImage(product.id, i, img.shown === false))}
              >
                👁
              </button>
            )}
            {img.shown === false && <span className="photo-hidden">{t('photo_hidden')}</span>}
            {i === 0 ? (
              <span className="photo-main">{t('photo_main')}</span>
            ) : (
              <button
                type="button"
                className="photo-star"
                title={t('photo_make_main')}
                aria-label={t('photo_make_main')}
                disabled={busy}
                onClick={() => void run(() => api.mainProductImage(product.id, i))}
              >
                ★
              </button>
            )}
            <button type="button" className="ibtn photo-x" aria-label={t('remove')} disabled={busy} onClick={() => void run(() => api.removeProductImage(product.id, i))}>
              ✕
            </button>
          </li>
        ))}
        {product.images.length < 6 && (
          <li>
            <button type="button" className="photo-add" disabled={busy} onClick={() => input.current?.click()}>
              {busy ? '…' : '+'}
            </button>
          </li>
        )}
      </ul>
      <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" multiple hidden onChange={(e) => void upload(e.target.files)} />
      {error && <p className="error small">{error}</p>}
    </fieldset>
  )
}

/** Seller form: certificates and declarations of the product. */
export function DocManager({ product, defs, onChange }: { product: SellerProduct; defs: SpecDefs; onChange: (p: SellerProduct) => void }) {
  const t = useT()
  const lang = useLang()
  const input = useRef<HTMLInputElement>(null)
  const [kind, setKind] = useState('declaration')
  const [number, setNumber] = useState('')
  const [validUntil, setValidUntil] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function upload(file: File | undefined) {
    if (!file) return
    setBusy(true)
    setError(null)
    try {
      onChange(await api.addProductDocument(product.id, file, kind, number, validUntil))
      setNumber('')
      setValidUntil('')
    } catch (err) {
      setError(problemOf(err, lang))
    } finally {
      setBusy(false)
      if (input.current) input.current.value = ''
    }
  }

  return (
    <fieldset className="box">
      <legend>{t('docs_title')}</legend>
      {product.documents.length > 0 && (
        <ul className="pdoc-list">
          {product.documents.map((d) => (
            <li key={d.id}>
              <DocLine d={d} defs={defs} />
              <button
                type="button"
                className="ibtn"
                aria-label={t('remove')}
                onClick={async () => onChange(await api.removeProductDocument(product.id, d.id))}
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="form-grid tight">
        <SelectField
          label={t('doc_kind')}
          value={kind}
          onChange={(e) => setKind(e.target.value)}
          options={Object.entries(defs.doc_kinds).map(([k, v]) => ({ value: k, label: tr(v, lang) }))}
        />
        <Field label={t('doc_number')} value={number} onChange={(e) => setNumber(e.target.value)} />
        <Field label={t('doc_valid_until')} type="date" value={validUntil} onChange={(e) => setValidUntil(e.target.value)} />
      </div>
      <button type="button" className="btn ghost" disabled={busy} onClick={() => input.current?.click()}>
        {busy ? t('loading') : `↑ ${t('doc_upload')}`}
      </button>
      <input ref={input} type="file" accept="application/pdf,image/jpeg,image/png,image/webp" hidden onChange={(e) => void upload(e.target.files?.[0])} />
      {error && <p className="error small">{error}</p>}
    </fieldset>
  )
}

export function DocLine({ d, defs }: { d: ProductDoc; defs: SpecDefs }) {
  const t = useT()
  const lang = useLang()
  const expired = d.valid_until !== null && d.valid_until < new Date().toISOString().slice(0, 10)
  return (
    <span className="doc-line">
      <strong>📄 {defs.doc_kinds[d.kind] ? tr(defs.doc_kinds[d.kind], lang) : d.kind}</strong>
      <span className="muted small">
        {[d.number, d.valid_until && `${t('doc_valid_until').toLowerCase()} ${fullDate(d.valid_until, lang)}`].filter(Boolean).join(' · ')}
        {expired && <b className="error"> · {t('doc_expired')}</b>}
      </span>
    </span>
  )
}

/** Product card: the filled characteristics, grouped. */
export function SpecTable({ defs, values }: { defs: SpecDefs; values: Record<string, SpecValue> }) {
  const t = useT()
  const lang = useLang()
  const groups = filledGroups(defs, values)
  if (!groups.length) return null
  return (
    <div className="spec-table">
      {groups.map(({ group, items }) => (
        <section key={group}>
          <span className="eyebrow">{tr(defs.groups[group], lang)}</span>
          <dl>
            {items.map(({ def, value }) => (
              <div key={def.code}>
                <dt>{tr(def.label, lang)}</dt>
                <dd>{specText(def, value, lang, t('yes'))}</dd>
              </div>
            ))}
          </dl>
        </section>
      ))}
    </div>
  )
}
