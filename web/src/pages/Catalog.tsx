import { useContext, useEffect, useState } from 'react'
import { LangContext, useT } from '../i18n'
import { api, type Category, type ProductPage } from '../lib/api'
import { amd, qty, tr, unit } from '../lib/format'

export function Catalog() {
  const t = useT()
  const { lang } = useContext(LangContext)
  const [categories, setCategories] = useState<Category[]>([])
  const [q, setQ] = useState('')
  const [categoryId, setCategoryId] = useState<string | undefined>()
  const [offersOnly, setOffersOnly] = useState(false)
  const [page, setPage] = useState<ProductPage | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.categories().then(setCategories, (e: Error) => setError(e.message))
  }, [])

  useEffect(() => {
    // Debounce typing; filters apply at once
    const id = setTimeout(() => {
      api
        .products({ q: q.trim(), category_id: categoryId, offers_only: offersOnly, limit: 60 })
        .then(setPage, (e: Error) => setError(e.message))
    }, q ? 250 : 0)
    return () => clearTimeout(id)
  }, [q, categoryId, offersOnly])

  return (
    <div className="catalog">
      <input
        className="search"
        type="search"
        placeholder={t('search')}
        value={q}
        onChange={(e) => setQ(e.target.value)}
        aria-label={t('search')}
      />
      <div className="chips">
        <button className={!categoryId ? 'chip on' : 'chip'} onClick={() => setCategoryId(undefined)}>
          {t('all')}
        </button>
        {categories.map((c) => (
          <button key={c.id} className={c.id === categoryId ? 'chip on' : 'chip'} onClick={() => setCategoryId(c.id)}>
            {tr(c.name, lang)}
          </button>
        ))}
        <label className="chip toggle">
          <input type="checkbox" checked={offersOnly} onChange={(e) => setOffersOnly(e.target.checked)} />
          {t('offers_only')}
        </label>
      </div>

      {error && <p className="error">{error}</p>}
      {page && (
        <p className="muted count">
          {page.total ? `${t('found')}: ${page.total}` : t('nothing')}
        </p>
      )}

      <ul className="grid">
        {page?.items.map((p) => {
          const best = p.tiers.at(-1)
          return (
            <li key={p.id} className={p.in_stock ? 'product' : 'product out'}>
              <div className="product-head">
                <h3>{tr(p.name, lang)}</h3>
                {p.allow_offers && <span className="badge">{t('haggle')}</span>}
              </div>
              <p className="seller">{p.seller.display_name}</p>
              <p className="price">
                {amd(p.base_price_amd)}
                <span className="per">
                  {' '}
                  {t('per')} {unit(p.unit, lang)}
                </span>
              </p>
              {best && (
                <p className="tier">
                  {t('from')} {qty(best.min_qty)} {unit(p.unit, lang)}: {amd(best.price_amd)}
                </p>
              )}
              <p className="meta">
                {p.pack_size && <span>{p.pack_size}</span>}
                {Number(p.min_qty) > 1 && (
                  <span>
                    {t('min')} {qty(p.min_qty)} {unit(p.unit, lang)}
                  </span>
                )}
                {!p.in_stock && <span>{t('out_of_stock')}</span>}
              </p>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
