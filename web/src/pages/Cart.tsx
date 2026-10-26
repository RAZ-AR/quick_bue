import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { HaggleHowTo, howToSeen } from '../components/HaggleHowTo'
import { PriceDial } from '../components/PriceDial'
import { QtyStepper } from '../components/QtyStepper'
import { OrderMeter } from '../components/ui'
import { fill, problemText, SOURCES, useLang, useT } from '../i18n'
import { api, ApiError, type Address, type CartGroup, type CartLine, type Product } from '../lib/api'
import { useCart } from '../lib/cart'
import { amd, date, tr, unit } from '../lib/format'
import { pct, priceForDiscount } from '../lib/haggle'
import { useSession } from '../lib/session'

const DISCOUNTS = [3, 5, 7, 10]

/** What the buyer saves if every offer in the cart is accepted. */
function potentialSaving(groups: CartGroup[], discounts: Record<string, number>): number {
  let won = 0
  for (const g of groups) {
    for (const l of g.lines) {
      if (l.offer_price_amd !== null) won += Math.max(0, (l.unit_price_amd - l.offer_price_amd) * Number(l.qty))
    }
    won += Math.round((g.subtotal_amd * (discounts[g.seller.id] ?? 0)) / 100)
  }
  return Math.round(won)
}

export function CartPage() {
  const { guest } = useCart()
  return guest ? <GuestCart /> : <ServerCart />
}

/** Catalog price for a quantity: the deepest volume tier reached, else the list price. */
function listPrice(p: Product, q: number): number {
  let price = p.base_price_amd
  for (const tier of p.tiers) if (q >= Number(tier.min_qty)) price = Math.min(price, tier.price_amd)
  return price
}

/**
 * Cart before the company exists: kept in the browser, priced from the public catalog.
 * Sellers are hidden for guests, so lines are not grouped; ordering asks to sign in or register first.
 */
function GuestCart() {
  const t = useT()
  const lang = useLang()
  const { me } = useSession()
  const { local, setItem, remove } = useCart()
  const [products, setProducts] = useState<Product[] | null>(null)
  const ids = Object.keys(local)
  const key = ids.sort().join(',')

  useEffect(() => {
    if (!key) return setProducts([])
    api.products({ ids: key.split(','), limit: 100 }).then((r) => setProducts(r.items), () => setProducts([]))
  }, [key])

  if (!products) return <p className="muted">{t('loading')}</p>
  const lines = products.filter((p) => local[p.id])
  if (lines.length === 0) {
    return (
      <div className="empty page">
        <div className="big">🧾</div>
        <p>{t('cart_empty')}</p>
        <Link className="btn primary" to="/">
          {t('tab_catalog')}
        </Link>
      </div>
    )
  }
  const total = lines.reduce((s, p) => s + Math.round(listPrice(p, Number(local[p.id])) * Number(local[p.id])), 0)

  return (
    <div className="stack page">
      <h1 className="page-title">{t('tab_cart')}</h1>
      <section className="ticket">
        <ul className="lines">
          {lines.map((p) => {
            const q = local[p.id]
            const price = listPrice(p, Number(q))
            return (
              <li key={p.id} className="line">
                <div className="line-main">
                  <div>
                    <div className="line-name">{tr(p.name, lang)}</div>
                    <div className="line-sub num">
                      {price !== p.base_price_amd && <span className="strike">{amd(p.base_price_amd)}</span>} {amd(price)} /{' '}
                      {unit(p.unit, lang)}
                    </div>
                  </div>
                  <div className="line-total num">{amd(Math.round(price * Number(q)))}</div>
                </div>
                <div className="line-tools">
                  <QtyStepper
                    value={q}
                    min={p.min_qty}
                    step={p.qty_step}
                    unitLabel={unit(p.unit, lang)}
                    onChange={(next) => void (Number(next) <= 0 ? remove(p.id) : setItem(p.id, next))}
                  />
                </div>
              </li>
            )
          })}
        </ul>
      </section>
      <section className="ticket checkout">
        <div className="total-row">
          <span>{t('total')}</span>
          <strong className="num">≈ {amd(total)}</strong>
        </div>
        <p className="muted small" style={{ margin: 0 }}>
          {t('guest_hint')}
        </p>
        <Link className="btn primary block" to={me ? '/onboarding' : '/login'}>
          {me ? t('register_to_order') : t('sign_in_to_order')} →
        </Link>
      </section>
    </div>
  )
}

function ServerCart() {
  const t = useT()
  const lang = useLang()
  const navigate = useNavigate()
  const { cart, refresh } = useCart()
  const [addresses, setAddresses] = useState<Address[]>([])
  const [addressId, setAddressId] = useState<string | undefined>()
  const [discounts, setDiscounts] = useState<Record<string, number>>({})
  const [sending, setSending] = useState(false)
  const [errors, setErrors] = useState<string[]>([])
  // One key per attempt: a double tap or a retry never creates the orders twice
  const attempt = useRef(crypto.randomUUID())

  useEffect(() => {
    void refresh().catch(() => {})
    api.addresses().then((list) => {
      setAddresses(list)
      setAddressId((id) => id ?? list[0]?.id)
    })
  }, [refresh])

  if (!cart) return <p className="muted">{t('loading')}</p>
  if (cart.groups.length === 0) {
    return (
      <div className="empty page">
        <div className="big">🧾</div>
        <p>{t('cart_empty')}</p>
        <Link className="btn primary" to="/">
          {t('tab_catalog')}
        </Link>
      </div>
    )
  }

  // An order discount only counts for sellers without line offers (the API accepts one kind per order)
  const effective = Object.fromEntries(
    cart.groups
      .filter((g) => !g.lines.some((l) => l.offer_price_amd !== null))
      .map((g) => [g.seller.id, discounts[g.seller.id] ?? 0]),
  )
  const saving = potentialSaving(cart.groups, effective)

  async function send() {
    setSending(true)
    setErrors([])
    try {
      const order_offers = Object.entries(effective)
        .filter(([, v]) => v > 0)
        .map(([seller_id, v]) => ({ seller_id, percent_bp: Math.round(v * 100) }))
      const { orders } = await api.checkout({ address_id: addressId, order_offers }, attempt.current)
      attempt.current = crypto.randomUUID()
      navigator.vibrate?.([10, 40, 10])
      await refresh()
      navigate(orders.length === 1 ? `/orders/${orders[0].id}` : '/orders', { state: { sent: true } })
    } catch (e) {
      const err = e as ApiError
      setErrors(err.problems?.length ? err.problems.map((p) => problemText(p.code, lang)) : [problemText(err.code, lang)])
      attempt.current = crypto.randomUUID()
      await refresh().catch(() => {})
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="stack page">
      <h1 className="page-title">{t('tab_cart')}</h1>
      {cart.groups.map((g) => (
        <SellerTicket
          key={g.seller.id}
          g={g}
          canNegotiate={cart.can_negotiate}
          rounds={cart.offer_max_rounds}
          discount={discounts[g.seller.id] ?? 0}
          onDiscount={(v) => setDiscounts((d) => ({ ...d, [g.seller.id]: v }))}
        />
      ))}

      <section className="ticket checkout">
        {addresses.length > 0 && (
          <label className="field">
            <span>{t('address')}</span>
            <select value={addressId} onChange={(e) => setAddressId(e.target.value)}>
              {addresses.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.label}: {a.text}
                </option>
              ))}
            </select>
          </label>
        )}
        <div className="total-row">
          <span>
            {t('total')}
            <span className="muted small">
              {' '}
              · {cart.groups.length} {t('suppliers')}
            </span>
          </span>
          <strong className="num">{amd(cart.total_amd)}</strong>
        </div>
        {saving > 0 && (
          <div className="total-row small">
            <span className="muted">{t('if_accepted')}</span>
            <span className="pill saving num">−{amd(saving)}</span>
          </div>
        )}
        {errors.map((e) => (
          <p key={e} className="error">
            {e}
          </p>
        ))}
        <button className="btn primary block" disabled={sending || cart.problems.length > 0} onClick={send}>
          {t('send_all')} <span className="sub num">· {amd(cart.total_amd)}</span>
        </button>
      </section>
    </div>
  )
}

function SellerTicket({
  g,
  canNegotiate,
  rounds,
  discount,
  onDiscount,
}: {
  g: CartGroup
  canNegotiate: boolean
  rounds: number
  discount: number
  onDiscount: (v: number) => void
}) {
  const t = useT()
  const lang = useLang()
  const hasLineOffers = g.lines.some((l) => l.offer_price_amd !== null)
  return (
    <section className="ticket perf">
      <header className="ticket-head">
        <h2>{g.seller.display_name}</h2>
        {g.delivery_date && <span className="pill plain">🚚 {date(g.delivery_date, lang)}</span>}
      </header>
      <OrderMeter subtotal={g.subtotal_amd} min={g.min_order_amd} freeFrom={g.free_delivery_from_amd} />
      <ul className="lines">
        {g.lines.map((l) => (
          <Line key={l.product_id} l={l} canNegotiate={canNegotiate} hours={g.offer_response_hours} rounds={rounds} />
        ))}
      </ul>
      <hr className="rule" />
      <dl className="sums">
        <dt>{t('subtotal')}</dt>
        <dd>{amd(g.subtotal_amd)}</dd>
        <dt>{t('delivery')}</dt>
        <dd>{g.delivery_fee_amd ? amd(g.delivery_fee_amd) : t('free')}</dd>
      </dl>
      {g.problems
        .filter((p) => p !== 'min_order_not_reached')
        .map((p) => (
          <p key={p} className="error small">
            {problemText(p, lang)}
          </p>
        ))}
      {canNegotiate && !hasLineOffers && (
        <div className="field" style={{ marginTop: 12 }}>
          <span>⇄ {t('discount_offer')}</span>
          <div className="dial-presets">
            {[0, ...DISCOUNTS].map((d) => (
              <button key={d} type="button" className={discount === d ? 'on' : ''} onClick={() => onDiscount(d)}>
                {d === 0 ? '—' : `−${d}%`}
              </button>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}

function Line({ l, canNegotiate, hours, rounds }: { l: CartLine; canNegotiate: boolean; hours: number; rounds: number }) {
  const t = useT()
  const lang = useLang()
  const { setItem, remove } = useCart()
  const [busy, setBusy] = useState(false)
  const [offerOpen, setOfferOpen] = useState(false)
  const [howTo, setHowTo] = useState(false)

  async function run(p: Promise<void>) {
    setBusy(true)
    try {
      await p
    } catch {
      /* the cart shows the problem */
    } finally {
      setBusy(false)
    }
  }

  const changeQty = (next: string) =>
    run(Number(next) <= 0 ? remove(l.product_id) : setItem(l.product_id, next, l.offer_price_amd))
  const canOffer = canNegotiate && l.offers_allowed
  const tooSmall = l.line_total_amd < l.offer_min_line_amd
  const offered = l.offer_price_amd

  return (
    <li className="line">
      <div className="line-main">
        <div>
          <div className="line-name">{tr(l.name, lang)}</div>
          <div className="line-sub num">
            {l.unit_price_amd !== l.base_price_amd && <span className="strike">{amd(l.base_price_amd)}</span>}{' '}
            {amd(l.unit_price_amd)} / {unit(l.unit, lang)}
            {l.price_source !== 'list' && <span style={{ color: 'var(--herb)' }}> · {SOURCES[l.price_source][lang]}</span>}
          </div>
        </div>
        <div className="line-total num">
          {offered !== null ? (
            <>
              <div className="strike small">{amd(l.line_total_amd)}</div>
              <div style={{ color: 'var(--brand)' }}>{amd(Math.round(offered * Number(l.qty)))}</div>
            </>
          ) : (
            amd(l.line_total_amd)
          )}
        </div>
      </div>
      <div className="line-tools">
        <QtyStepper value={l.qty} min={l.min_qty} step={l.qty_step} unitLabel={unit(l.unit, lang)} onChange={changeQty} disabled={busy} />
        {canOffer &&
          (offered !== null ? (
            <button className="pill brand" style={{ border: 0 }} onClick={() => setOfferOpen((o) => !o)}>
              ⇄ {amd(offered)} · −{Math.round((1 - offered / l.unit_price_amd) * 100)}%
            </button>
          ) : (
            <button
              className="link small"
              disabled={tooSmall}
              onClick={() => {
                setOfferOpen((o) => !o)
                if (!howToSeen()) setHowTo(true)
              }}
            >
              ⇄ {t('offer_price')}
            </button>
          ))}
      </div>
      {canOffer && tooSmall && offered === null && (
        <p className="muted small" style={{ margin: '6px 0 0' }}>
          {t('offer_hint')} {amd(l.offer_min_line_amd)}
        </p>
      )}
      {canOffer && offerOpen && !tooSmall && (
        <>
          {howTo && <HaggleHowTo hours={hours} rounds={rounds} onClose={() => setHowTo(false)} />}
          <div className="hint-row">
            <span className={l.offer_hint_bp ? 'hint strong' : 'hint muted'}>
              {l.offer_hint_bp ? fill(t('hint_seller_agrees'), { p: pct(l.offer_hint_bp) }) : t('hint_generic')}
            </span>
            {!howTo && (
              <button type="button" className="link small" onClick={() => setHowTo(true)}>
                {t('howto_link')}
              </button>
            )}
          </div>
          <PriceDial
            likelyFrom={l.offer_hint_bp ? priceForDiscount(l.unit_price_amd, l.offer_hint_bp) : null}
            reference={l.unit_price_amd}
            qty={Number(l.qty)}
            value={offered}
            min={Math.ceil(l.unit_price_amd * 0.5)}
            max={l.unit_price_amd - 10}
            unitLabel={unit(l.unit, lang)}
            onCommit={(p) => void run(setItem(l.product_id, l.qty, p))}
          />
          {offered !== null && (
            <button
              className="link small"
              onClick={() => {
                setOfferOpen(false)
                void run(setItem(l.product_id, l.qty, null))
              }}
            >
              {t('remove_offer')}
            </button>
          )}
        </>
      )}
      {l.problems.map((p) => (
        <p key={p} className="error small">
          {problemText(p, lang)}
        </p>
      ))}
    </li>
  )
}
