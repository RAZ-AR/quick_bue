import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { DocLine, SpecTable } from '../components/ProductParts'
import { Tile } from '../components/ui'
import { problemText, useLang, useT } from '../i18n'
import { api, ApiError, mediaUrl, openFile, type ProductDetail } from '../lib/api'
import { amd, qty, tr, unit } from '../lib/format'
import { useSession } from '../lib/session'
import { useSpecDefs } from '../lib/specs'
import { BuyControl } from './Catalog'

/** The product card: photos, price and volume prices, order terms, description, characteristics, documents. */
export function ProductCard({ canBuy }: { canBuy: boolean }) {
  const { id = '' } = useParams()
  const t = useT()
  const lang = useLang()
  const navigate = useNavigate()
  const { me } = useSession()
  const defs = useSpecDefs()
  const [p, setP] = useState<ProductDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [shown, setShown] = useState(0)

  useEffect(() => {
    setP(null)
    setShown(0)
    api.product(id).then(setP, (e: ApiError) => setError(problemText(e.code, lang)))
  }, [id, lang])

  if (error) return <p className="error page">{error}</p>
  if (!p) return <p className="muted page">{t('loading')}</p>
  const name = tr(p.name, lang)
  const u = unit(p.unit, lang)
  const photo = p.images[shown] ?? p.images[0]
  const description = p.description ? tr(p.description, lang) : ''

  return (
    <div className="page product-page">
      <button className="link small back" onClick={() => (history.length > 1 ? navigate(-1) : navigate('/'))}>
        ← {t('back')}
      </button>
      <div className="product-hero">
        <div className="gallery">
          <div className="gallery-main">
            {photo ? <img src={mediaUrl(photo.url)} alt={name} /> : <Tile slug={p.category ?? undefined} name={name} />}
          </div>
          {p.images.length > 1 && (
            <div className="gallery-thumbs">
              {p.images.map((img, i) => (
                <button key={img.url} className={i === shown ? 'on' : ''} onClick={() => setShown(i)} aria-label={`${i + 1}`}>
                  <img src={mediaUrl(img.thumb)} alt="" loading="lazy" />
                </button>
              ))}
            </div>
          )}
        </div>

        <section className="ticket product-buy">
          <h1>{name}</h1>
          <p className="seller">{p.seller ? p.seller.display_name : <span className="muted">🔒 {t('seller_hidden')}</span>}</p>
          <div className="product-price">
            <span className="num">{amd(p.base_price_amd)}</span>
            <span className="per"> / {u}</span>
            <span className="muted small"> · {p.vat_rate_bp ? t('vat_in_price') : t('no_vat')}</span>
          </div>
          {p.tiers.length > 0 && (
            <ul className="tier-list">
              {p.tiers.map((tier) => (
                <li key={tier.min_qty}>
                  <span>
                    {t('from')} {qty(tier.min_qty)} {u}
                  </span>
                  <b className="num">
                    {amd(tier.price_amd)} / {u}
                  </b>
                  <span className="pill saving num">−{Math.round((1 - tier.price_amd / p.base_price_amd) * 100)}%</span>
                </li>
              ))}
            </ul>
          )}
          <div className="meta">
            {p.allow_offers && <span className="pill haggle">⇄ {t('haggle')}</span>}
            {p.documents.length > 0 && <span className="pill plain">📄 {t('has_certificate')}</span>}
            <span className={p.in_stock ? 'pill plain' : 'pill plain muted'}>{p.in_stock ? `✓ ${t('in_stock')}` : t('out_of_stock')}</span>
          </div>
          <dl className="order-terms">
            <div>
              <dt>{t('min_batch')}</dt>
              <dd className="num">
                {qty(p.min_qty)} {u}
              </dd>
            </div>
            <div>
              <dt>{t('qty_step_short')}</dt>
              <dd className="num">
                {qty(p.qty_step)} {u}
              </dd>
            </div>
            {p.pack_size && (
              <div>
                <dt>{t('pack_size')}</dt>
                <dd>{p.pack_size}</dd>
              </div>
            )}
            {p.seller_min_order_amd !== null && p.seller_min_order_amd > 0 && (
              <div>
                <dt>{t('seller_min_order')}</dt>
                <dd className="num">{amd(p.seller_min_order_amd)}</dd>
              </div>
            )}
            {p.seller_lead_days !== null && (
              <div>
                <dt>{t('lead_time')}</dt>
                <dd>
                  {p.seller_lead_days} {t('lead_days_n')}
                </dd>
              </div>
            )}
          </dl>
          {canBuy && p.in_stock && <BuyControl p={p} />}
        </section>
      </div>

      {description && (
        <section className="ticket">
          <h2 className="section-title">{t('description')}</h2>
          <p className="product-desc">{description}</p>
        </section>
      )}
      {defs && Object.keys(p.specs).length > 0 && (
        <section className="ticket">
          <h2 className="section-title">{t('specs_title')}</h2>
          <SpecTable defs={defs} values={p.specs} />
        </section>
      )}
      {defs && p.documents.length > 0 && (
        <section className="ticket">
          <h2 className="section-title">{t('docs_title')}</h2>
          <ul className="pdoc-list">
            {p.documents.map((d) => (
              <li key={d.id}>
                <DocLine d={d} defs={defs} />
                {me ? (
                  <button className="btn small ghost" onClick={() => void openFile(`/products/${p.id}/documents/${d.id}`)}>
                    {t('doc_open')}
                  </button>
                ) : (
                  <Link className="link small" to="/login">
                    {t('doc_sign_in')}
                  </Link>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
