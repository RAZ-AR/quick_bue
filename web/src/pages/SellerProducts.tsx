import type React from 'react'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AutopilotEditor, DEFAULT_AUTOPILOT } from '../components/AutopilotEditor'
import { Field, SelectField } from '../components/Field'
import { DocManager, PhotoManager, SpecFields } from '../components/ProductParts'
import { Sheet } from '../components/Sheet'
import { Tile } from '../components/ui'
import { problemText, useLang, useT } from '../i18n'
import { api, ApiError, type Category, type ProductInput, type SellerProduct, type Unit } from '../lib/api'
import { amd, qty, tr, unit } from '../lib/format'
import { useSession } from '../lib/session'
import { useSpecDefs } from '../lib/specs'

const UNITS: Unit[] = ['kg', 'l', 'pcs', 'pack']

const EMPTY: ProductInput = {
  sku: null,
  category_id: null,
  name: {},
  description: null,
  unit: 'kg',
  pack_size: null,
  base_price_amd: 0,
  vat_included: true,
  min_qty: '1',
  qty_step: '1',
  in_stock: true,
  allow_offers: false,
  is_service: false,
  specs: {},
  tiers: [],
  autopilot: null,
}

/** Seller cabinet: the company's own products. Editing works before verification. */
export function SellerProducts() {
  const t = useT()
  const lang = useLang()
  const { canSell } = useSession()
  const [archived, setArchived] = useState(false)
  const [items, setItems] = useState<SellerProduct[] | null>(null)
  const [categories, setCategories] = useState<Category[]>([])
  const [editing, setEditing] = useState<SellerProduct | 'new' | null>(null)

  const load = useCallback(() => api.sellerProducts(archived).then(setItems), [archived])
  const close = useCallback(() => setEditing(null), [])
  useEffect(() => {
    void load()
  }, [load])
  useEffect(() => {
    api.categories().then(setCategories)
  }, [])
  const slugOf = Object.fromEntries(categories.map((c) => [c.id, c.slug]))

  return (
    <div className="page" style={{ display: 'grid', gap: 12 }}>
      <div className="page-head">
        <h1 className="page-title">{t('tab_products')}</h1>
        <div className="actions">
          <Link className="btn ghost" to="/seller/import">
            ↑ {t('import_button')}
          </Link>
          <button className="btn primary" onClick={() => setEditing('new')}>
            + {t('new_product')}
          </button>
        </div>
      </div>
      {!canSell && <p className="notice">{t('products_hidden_until_verified')}</p>}
      <div className="chips" style={{ paddingTop: 0 }}>
        <button className={!archived ? 'chip on' : 'chip'} onClick={() => setArchived(false)}>
          {t('active_products')}
        </button>
        <button className={archived ? 'chip on' : 'chip'} onClick={() => setArchived(true)}>
          {t('archived')}
        </button>
      </div>
      {items?.length === 0 && <p className="col-empty">{t('no_products')}</p>}
      <ul className="grid">
        {items?.map((p) => {
          const name = tr(p.name, lang)
          return (
            <li key={p.id} className={p.in_stock ? 'product' : 'product out'}>
              <Tile slug={p.category_id ? slugOf[p.category_id] : undefined} name={name} />
              <div>
                <h3>{name}</h3>
                <p className="seller">{[p.sku, p.pack_size].filter(Boolean).join(' · ') || '\u00a0'}</p>
                <div className="price-row">
                  <span className="price num">
                    {amd(p.base_price_amd)}
                    <span className="per"> / {unit(p.unit, lang)}</span>
                  </span>
                  {p.tiers.at(-1) && (
                    <span className="tier num">
                      {qty(p.tiers.at(-1)!.min_qty)}+ : {amd(p.tiers.at(-1)!.price_amd)}
                    </span>
                  )}
                </div>
                <div className="meta">
                  {p.allow_offers && <span className="pill haggle">⇄ {t('haggle')}</span>}
                  {p.is_service && <span className="pill plain">{t('service_badge')}</span>}
                  {p.autopilot?.enabled && <span className="pill saving">⚡ {t('autopilot')}</span>}
                  {!p.in_stock && <span className="pill plain">{t('out_of_stock')}</span>}
                </div>
                <div className="buy" style={{ gap: 8 }}>
                  <button className="btn ghost" style={{ minHeight: 40 }} onClick={() => api.archiveProduct(p.id, !p.archived).then(load)}>
                    {p.archived ? t('restore') : t('to_archive')}
                  </button>
                  <button className="btn primary" style={{ minHeight: 40 }} onClick={() => setEditing(p)}>
                    {t('edit')}
                  </button>
                </div>
              </div>
            </li>
          )
        })}
      </ul>
      {editing && (
        <ProductEditor
          product={editing === 'new' ? null : editing}
          categories={categories}
          onClose={async () => (close(), await load())}
          onSaved={async () => (setEditing(null), await load())}
          onCreated={async (p) => (setEditing(p), await load())}
        />
      )}
    </div>
  )
}

function ProductEditor({
  product,
  categories,
  onClose,
  onSaved,
  onCreated,
}: {
  product: SellerProduct | null
  categories: Category[]
  onClose: () => void
  onSaved: () => Promise<void>
  /** A new product was saved: keep the form open on it, so photos and documents can be added */
  onCreated: (p: SellerProduct) => Promise<void>
}) {
  const t = useT()
  const lang = useLang()
  const [f, setF] = useState<ProductInput>(() => (product ? { ...product } : { ...EMPTY, name: {} }))
  const [current, setCurrent] = useState<SellerProduct | null>(product)
  const defs = useSpecDefs()
  const categorySlug = categories.find((c) => c.id === f.category_id)?.slug
  const [busy, setBusy] = useState(false)
  const [errors, setErrors] = useState<string[]>([])
  const set = (patch: Partial<ProductInput>) => setF((x) => ({ ...x, ...patch }))
  const num = (v: string) => (v === '' ? 0 : Number(v.replace(/\D/g, '')))

  async function save(e: React.FormEvent) {
    e.preventDefault()
    setErrors([])
    // Every volume price needs both a quantity and a price; the server would only say "invalid"
    if (f.tiers.some((x) => !Number(x.min_qty) || !x.price_amd)) {
      setErrors([problemText('bad_tier', lang)])
      return
    }
    setBusy(true)
    try {
      const body = { ...f, autopilot: f.allow_offers ? f.autopilot : null }
      if (product) {
        await api.updateProduct(product.id, body)
        await onSaved()
      } else await onCreated(await api.createProduct(body))
    } catch (err) {
      const ex = err as ApiError
      setErrors(ex.problems?.length ? ex.problems.map((p) => problemText(p.code, lang)) : [problemText(ex.code, lang)])
    } finally {
      setBusy(false)
    }
  }

  return (
    <Sheet onClose={onClose}>
      <form className="sheet-form" onSubmit={save}>
        <header className="ticket-head">
          <h2>{product ? t('edit') : t('new_product')}</h2>
          <button type="button" className="ibtn" onClick={onClose} aria-label={t('cancel_edit')}>
            ✕
          </button>
        </header>
        <Field label={t('name_hy')} value={f.name.hy ?? ''} onChange={(e) => set({ name: { ...f.name, hy: e.target.value } })} />
        <Field label={t('name_ru')} value={f.name.ru ?? ''} onChange={(e) => set({ name: { ...f.name, ru: e.target.value } })} />
        <Field label={t('name_en')} value={f.name.en ?? ''} onChange={(e) => set({ name: { ...f.name, en: e.target.value } })} />
        <div className="form-grid">
          <SelectField
            label={t('category')}
            value={f.category_id ?? ''}
            onChange={(e) => set({ category_id: e.target.value || null })}
            options={[{ value: '', label: '—' }, ...categories.map((c) => ({ value: c.id, label: tr(c.name, lang) }))]}
          />
          <SelectField
            label={t('unit_label')}
            value={f.unit}
            onChange={(e) => set({ unit: e.target.value as Unit })}
            options={UNITS.map((u) => ({ value: u, label: unit(u, lang) }))}
          />
          <Field label={t('price_per_unit')} inputMode="numeric" value={f.base_price_amd || ''} onChange={(e) => set({ base_price_amd: num(e.target.value) })} />
          <Field label={t('pack_size')} value={f.pack_size ?? ''} onChange={(e) => set({ pack_size: e.target.value })} />
          <Field label={t('min_qty_label')} inputMode="decimal" value={f.min_qty} onChange={(e) => set({ min_qty: e.target.value.replace(',', '.') })} />
          <Field label={t('qty_step_label')} inputMode="decimal" value={f.qty_step} onChange={(e) => set({ qty_step: e.target.value.replace(',', '.') })} />
          <Field label={t('sku')} value={f.sku ?? ''} onChange={(e) => set({ sku: e.target.value })} />
        </div>
        <label className="check">
          <input type="checkbox" checked={f.in_stock} onChange={(e) => set({ in_stock: e.target.checked })} /> {t('in_stock')}
        </label>

        <label className="field">
          <span>{t('description')}</span>
          <textarea
            rows={3}
            value={f.description?.[lang] ?? ''}
            onChange={(e) => set({ description: { ...(f.description ?? {}), [lang]: e.target.value } })}
          />
        </label>
        {defs && (
          <SpecFields defs={defs} category={categorySlug} isService={f.is_service} value={f.specs ?? {}} onChange={(specs) => set({ specs })} />
        )}
        {current ? (
          <>
            <PhotoManager product={current} onChange={setCurrent} />
            {defs && <DocManager product={current} defs={defs} onChange={setCurrent} />}
          </>
        ) : (
          <p className="notice">{t('save_first_for_photos')}</p>
        )}
        <fieldset className="box">
          <legend>{t('volume_prices')}</legend>
          {f.tiers.map((tier, i) => (
            <div key={i} className="form-grid tight">
              <Field label={t('from_qty')} inputMode="decimal" value={tier.min_qty} onChange={(e) => set({ tiers: f.tiers.map((x, j) => (j === i ? { ...x, min_qty: e.target.value.replace(',', '.') } : x)) })} />
              <Field label={t('price')} inputMode="numeric" value={tier.price_amd || ''} onChange={(e) => set({ tiers: f.tiers.map((x, j) => (j === i ? { ...x, price_amd: num(e.target.value) } : x)) })} />
              <button type="button" className="ibtn" style={{ alignSelf: 'end', marginBottom: 4 }} onClick={() => set({ tiers: f.tiers.filter((_, j) => j !== i) })}>
                ✕
              </button>
            </div>
          ))}
          <button type="button" className="link small" onClick={() => set({ tiers: [...f.tiers, { min_qty: '', price_amd: 0 }] })}>
            + {t('add_tier')}
          </button>
        </fieldset>

        <label className="check">
          <input type="checkbox" checked={f.is_service} onChange={(e) => set({ is_service: e.target.checked, allow_offers: e.target.checked ? false : f.allow_offers })} />{' '}
          {t('is_service_label')}
        </label>
        {f.is_service && <p className="muted small">{t('is_service_hint')}</p>}
        <label className="check">
          <input type="checkbox" disabled={f.is_service} checked={f.allow_offers} onChange={(e) => set({ allow_offers: e.target.checked, autopilot: e.target.checked ? (f.autopilot ?? DEFAULT_AUTOPILOT) : null })} />{' '}
          ⇄ {t('allow_offers_label')}
        </label>
        {f.allow_offers && (
          <>
            <label className="check">
              <input type="checkbox" checked={!!f.autopilot} onChange={(e) => set({ autopilot: e.target.checked ? DEFAULT_AUTOPILOT : null })} /> ⚡{' '}
              {t('autopilot_title')}
            </label>
            {f.autopilot ? (
              <AutopilotEditor value={f.autopilot} basePrice={f.base_price_amd} unitLabel={unit(f.unit, lang)} onChange={(next) => set({ autopilot: next })} />
            ) : (
              <p className="muted small">{t('ap_off')}</p>
            )}
          </>
        )}
        {errors.map((e) => (
          <p key={e} className="error small">
            {e}
          </p>
        ))}
        <div className="actions">
          <button type="button" className="btn ghost" onClick={onClose}>
            {t('cancel_edit')}
          </button>
          <button className="btn primary" disabled={busy}>
            {t('save')}
          </button>
        </div>
      </form>
    </Sheet>
  )
}
