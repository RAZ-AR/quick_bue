import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { QtyStepper } from '../components/QtyStepper'
import { Tile } from '../components/ui'
import { useLang, useT } from '../i18n'
import { api, mediaUrl, type Category, type OrderListItem, type Product, type ProductPage } from '../lib/api'
import { useCart } from '../lib/cart'
import { useSession } from '../lib/session'
import { amd, date, qty, tr, unit } from '../lib/format'

export function Catalog({ canBuy, firstName }: { canBuy: boolean; firstName?: string }) {
  const t = useT()
  const lang = useLang()
  const { org, mode } = useSession()
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
    const id = setTimeout(
      () => {
        api
          .products({ q: q.trim(), category_id: categoryId, offers_only: offersOnly, limit: 60 })
          .then(setPage, (e: Error) => setError(e.message))
      },
      q ? 250 : 0,
    )
    return () => clearTimeout(id)
  }, [q, categoryId, offersOnly])

  const slugOf = useMemo(() => Object.fromEntries(categories.map((c) => [c.id, c.slug])), [categories])
  const browsing = !q && !categoryId && !offersOnly

  return (
    <div className="catalog page">
      <h1 className="page-title">
        {canBuy && firstName ? `${t('hello')}, ${firstName}!` : t('tab_catalog')}
        {canBuy && <small>{t('what_today')}</small>}
      </h1>
      <div className="search-wrap">
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
          <label className="chip toggle">
            <input type="checkbox" checked={offersOnly} onChange={(e) => setOffersOnly(e.target.checked)} />
            {t('offers_only')}
          </label>
          {categories.map((c) => (
            <button key={c.id} className={c.id === categoryId ? 'chip on' : 'chip'} onClick={() => setCategoryId(c.id)}>
              {tr(c.name, lang)}
            </button>
          ))}
        </div>
      </div>

      {canBuy && browsing && org && mode === 'buyer' && <QuickReorder />}

      {error && <p className="error">{error}</p>}
      {page && <p className="muted count">{page.total ? `${t('found')}: ${page.total}` : t('nothing')}</p>}

      <ul className="grid">
        {page?.items.map((p) => (
          <ProductCard key={p.id} p={p} slug={p.category_id ? slugOf[p.category_id] : undefined} canBuy={canBuy} />
        ))}
      </ul>
    </div>
  )
}

/** P1 "faster than a phone call": the last orders, one tap back into the cart. */
function QuickReorder() {
  const t = useT()
  const lang = useLang()
  const navigate = useNavigate()
  const { refresh } = useCart()
  const [orders, setOrders] = useState<OrderListItem[]>([])
  const [busy, setBusy] = useState<string | null>(null)

  useEffect(() => {
    api.orders(['accepted', 'delivered', 'confirmed', 'placed', 'cancelled']).then(
      (p) => {
        // One card per supplier, newest first
        const seen = new Set<string>()
        setOrders(p.items.filter((o) => !seen.has(o.counterparty.id) && seen.add(o.counterparty.id)).slice(0, 6))
      },
      () => {},
    )
  }, [])

  if (orders.length === 0) return null
  return (
    <section>
      <h2 className="section-title">{t('quick_reorder')}</h2>
      <div className="reorder-strip">
        {orders.map((o) => (
          <button
            key={o.id}
            className="reorder-card"
            disabled={busy !== null}
            onClick={async () => {
              setBusy(o.id)
              try {
                await api.reorder(o.id)
                await refresh()
                navigate('/cart')
              } finally {
                setBusy(null)
              }
            }}
          >
            <span className="ibtn" aria-hidden>
              ↻
            </span>
            <strong>{o.counterparty.display_name}</strong>
            <span className="names">{o.preview.map((n) => tr(n, lang)).join(', ')}</span>
            <span className="big num">{amd(o.total_amd)}</span>
            <span className="go">
              {busy === o.id ? t('loading') : t('add_to_cart')} · {date(o.created_at, lang)}
            </span>
          </button>
        ))}
      </div>
    </section>
  )
}

function ProductCard({ p, slug, canBuy }: { p: Product; slug?: string; canBuy: boolean }) {
  const t = useT()
  const lang = useLang()
  const best = p.tiers.at(-1)
  const tierPct = best ? Math.round((1 - best.price_amd / p.base_price_amd) * 100) : 0
  const name = tr(p.name, lang)
  const navigate = useNavigate()
  // The whole card opens the product; its own links and buttons (cart, quantity) keep working as they are
  const open = (e: React.MouseEvent) => {
    if (!(e.target as HTMLElement).closest('a, button, input, label, select')) navigate(`/product/${p.id}`)
  }
  return (
    <li className={p.in_stock ? 'product clickable' : 'product out clickable'} onClick={open}>
      <Link to={`/product/${p.id}`} className="product-thumb" aria-label={name}>
        {p.images[0] ? <img src={mediaUrl(p.images[0].thumb)} alt="" loading="lazy" /> : <Tile slug={slug} name={name} />}
      </Link>
      <div>
        <h3>
          <Link to={`/product/${p.id}`} className="product-link">
            {name}
          </Link>
        </h3>
        <p className="seller">{p.seller ? p.seller.display_name : <span className="muted">🔒 {t('seller_hidden')}</span>}</p>
        <div className="price-row">
          <span className="price num">
            {amd(p.base_price_amd)}
            <span className="per"> / {unit(p.unit, lang)}</span>
          </span>
          {best && (
            <span className="tier num">
              −{tierPct}% {t('from')} {qty(best.min_qty)} {unit(p.unit, lang)}
            </span>
          )}
        </div>
        <div className="meta">
          {p.allow_offers && <span className="pill haggle">⇄ {t('haggle')}</span>}
          {p.has_documents && <span className="pill plain">📄 {t('has_certificate')}</span>}
          {p.pack_size && <span className="pill plain">{p.pack_size}</span>}
          {Number(p.min_qty) > 1 && (
            <span className="pill plain">
              {t('min')} {qty(p.min_qty)} {unit(p.unit, lang)}
            </span>
          )}
          {!p.in_stock && <span className="pill plain">{t('out_of_stock')}</span>}
        </div>
        {canBuy && p.in_stock && <BuyControl p={p} />}
      </div>
    </li>
  )
}

export function BuyControl({ p }: { p: Product }) {
  const t = useT()
  const lang = useLang()
  const { qtyOf, setItem, remove } = useCart()
  const [busy, setBusy] = useState(false)
  const current = qtyOf(p.id)

  async function change(next: string) {
    setBusy(true)
    try {
      if (Number(next) <= 0) await remove(p.id)
      else await setItem(p.id, next)
      navigator.vibrate?.(8)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="buy">
      {current ? (
        <QtyStepper value={current} min={p.min_qty} step={p.qty_step} unitLabel={unit(p.unit, lang)} onChange={change} disabled={busy} />
      ) : (
        <button className="add-btn" disabled={busy} onClick={() => change(p.min_qty)}>
          {t('add_to_cart')}
        </button>
      )}
    </div>
  )
}
