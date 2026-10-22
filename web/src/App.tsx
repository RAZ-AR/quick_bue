import type React from 'react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, NavLink, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { Icon } from './components/ui'
import { LangContext, useT } from './i18n'
import { api, token, type Lang, type Me } from './lib/api'
import { CartProvider, useCart, useCartMaybe } from './lib/cart'
import { amd } from './lib/format'
import { CartPage } from './pages/Cart'
import { Catalog } from './pages/Catalog'
import { Company } from './pages/Company'
import { Moderation } from './pages/Moderation'
import { Onboarding } from './pages/Onboarding'
import { PrintDocument } from './pages/PrintDocument'
import { Login } from './pages/Login'
import { OrderDetail } from './pages/OrderDetail'
import { Orders } from './pages/Orders'

const LANG_KEY = 'qb.lang'
const LANGS: Lang[] = ['hy', 'ru', 'en']

function savedLang(): Lang {
  try {
    const v = localStorage.getItem(LANG_KEY)
    return LANGS.includes(v as Lang) ? (v as Lang) : 'hy'
  } catch {
    return 'hy'
  }
}

export function App() {
  const [lang, setLangState] = useState<Lang>(savedLang)
  const [me, setMe] = useState<Me | null>(null)
  const [checked, setChecked] = useState(false)

  const setLang = useCallback((l: Lang) => {
    setLangState(l)
    try {
      localStorage.setItem(LANG_KEY, l)
    } catch {
      /* private mode: language just isn't remembered */
    }
  }, [])

  const loadMe = useCallback(async () => {
    if (!token.get()) {
      setMe(null)
      setChecked(true)
      return
    }
    try {
      setMe(await api.me())
    } catch {
      setMe(null)
    } finally {
      setChecked(true)
    }
  }, [])

  useEffect(() => {
    void loadMe()
  }, [loadMe])

  useEffect(() => {
    document.documentElement.lang = lang
  }, [lang])

  const ctx = useMemo(() => ({ lang, setLang }), [lang, setLang])
  const signOut = useCallback(() => {
    token.clear()
    setMe(null)
  }, [])

  if (!checked) return null

  return (
    <LangContext.Provider value={ctx}>
      {me ? (
        <Routes>
          {/* A4 printout: no app chrome */}
          <Route path="/print/:id" element={<PrintDocument />} />
          <Route
            path="*"
            element={
              me.memberships.length === 0 && me.is_platform_admin ? (
                <AdminShell me={me} onSignOut={signOut} />
              ) : me.memberships.length === 0 ? (
                <Onboarding me={me} onDone={loadMe} onSignOut={signOut} />
              ) : (
                <Shell me={me} onSignOut={signOut} onOrgChanged={loadMe} />
              )
            }
          />
        </Routes>
      ) : (
        <Routes>
          <Route path="*" element={<Login onSignedIn={loadMe} />} />
        </Routes>
      )}
    </LangContext.Provider>
  )
}

function TopBar({ title, sub, onSignOut }: { title: string; sub: string; onSignOut: () => void }) {
  const t = useT()
  const navigate = useNavigate()
  return (
    <header className="topbar">
      <div className="brand">QB</div>
      <div className="who">
        <span>{title}</span>
        <small>{sub}</small>
      </div>
      <LangSwitch />
      <button
        className="link"
        onClick={() => {
          onSignOut()
          navigate('/')
        }}
      >
        {t('logout')}
      </button>
    </header>
  )
}

/** Platform operator: only the verification queue for now. */
function AdminShell({ me, onSignOut }: { me: Me; onSignOut: () => void }) {
  const t = useT()
  return (
    <div className="app">
      <TopBar title={t('tab_moderation')} sub={me.name} onSignOut={onSignOut} />
      <main>
        <Moderation />
      </main>
    </div>
  )
}

function Shell({ me, onSignOut, onOrgChanged }: { me: Me; onSignOut: () => void; onOrgChanged: () => Promise<void> }) {
  const t = useT()
  const membership = me.memberships[0]
  const org = membership?.organization
  const isBuyer = org?.kind === 'buyer'
  const { pathname } = useLocation()
  const pendingSeller = org?.kind === 'seller' && org.status === 'pending' && pathname !== '/company'
  const awaitingReview = org?.verification_status === 'pending'
  return (
    <CartProvider enabled={isBuyer}>
      <Frame isBuyer={isBuyer}>
        <TopBar title={org?.display_name ?? me.name} sub={me.name} onSignOut={onSignOut} />
        <main>
          {pendingSeller && (
            <Link to="/company" className="next" style={{ marginBottom: 12, textDecoration: 'none' }}>
              <strong>{awaitingReview ? t('pending_seller_banner') : t('upload_to_sell')}</strong>
              <span className="clock">→</span>
            </Link>
          )}
          <Routes>
            <Route path="/company" element={<Company onChanged={onOrgChanged} />} />
            {isBuyer ? (
              <>
                <Route path="/" element={<Catalog canBuy firstName={me.name.split(' ')[0]} />} />
                <Route path="/cart" element={<CartPage />} />
                <Route path="/orders" element={<Orders />} />
              </>
            ) : (
              <>
                <Route path="/" element={<Orders inbox />} />
                <Route path="/orders" element={<Orders />} />
                <Route path="/catalog" element={<Catalog canBuy={false} />} />
              </>
            )}
            <Route path="/orders/:id" element={<OrderDetail />} />
            <Route path="/login" element={<Navigate to="/" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <TabBar isBuyer={isBuyer} />
      </Frame>
    </CartProvider>
  )
}

/** Page frame; on the buyer's catalog a cart bar floats above the tabs while the cart has something in it. */
function Frame({ isBuyer, children }: { isBuyer: boolean; children: React.ReactNode }) {
  const cart = useCartMaybe()
  const { pathname } = useLocation()
  const showBar = isBuyer && pathname === '/' && (cart?.count ?? 0) > 0
  return (
    <div className={`app ${isBuyer ? 'buyer' : 'seller'}${showBar ? ' has-cartbar' : ''}`}>
      {children}
      {showBar && <CartBar />}
    </div>
  )
}

function CartBar() {
  const t = useT()
  const { cart, count } = useCart()
  if (!cart) return null
  const suppliers = cart.groups.length
  return (
    <Link to="/cart" className="cartbar">
      <div className="info">
        <span key={cart.total_amd} className="sum num bump">
          {amd(cart.total_amd)}
        </span>
        <small>
          {count} {t('items')} · {suppliers} {t('suppliers')}
        </small>
      </div>
      <span className="go">{t('go_cart')} →</span>
    </Link>
  )
}

function Tab({ to, icon, label, badge }: { to: string; icon: () => React.ReactNode; label: string; badge?: number }) {
  return (
    <NavLink to={to} end={to === '/'} aria-label={label} title={label}>
      <span className="tab-icon">
        {icon()}
        {badge ? <span className="dot">{badge}</span> : null}
      </span>
      <span className="tab-label">{label}</span>
    </NavLink>
  )
}

function TabBar({ isBuyer }: { isBuyer: boolean }) {
  const t = useT()
  if (!isBuyer) {
    return (
      <nav className="tabbar">
        <Tab to="/" icon={Icon.inbox} label={t('tab_inbox')} />
        <Tab to="/orders" icon={Icon.ticket} label={t('tab_orders')} />
        <Tab to="/catalog" icon={Icon.catalog} label={t('tab_catalog')} />
        <Tab to="/company" icon={Icon.company} label={t('tab_company')} />
      </nav>
    )
  }
  return <BuyerTabs />
}

function BuyerTabs() {
  const t = useT()
  const { count } = useCart()
  return (
    <nav className="tabbar">
      <Tab to="/" icon={Icon.catalog} label={t('tab_catalog')} />
      <Tab to="/cart" icon={Icon.cart} label={t('tab_cart')} badge={count} />
      <Tab to="/orders" icon={Icon.ticket} label={t('tab_orders')} />
      <Tab to="/company" icon={Icon.company} label={t('tab_company')} />
    </nav>
  )
}

export function LangSwitch() {
  return (
    <LangContext.Consumer>
      {({ lang, setLang }) => (
        <div className="lang" role="group" aria-label="Language">
          {LANGS.map((l) => (
            <button key={l} className={l === lang ? 'on' : ''} onClick={() => setLang(l)} aria-pressed={l === lang}>
              {l === 'hy' ? 'Հայ' : l === 'ru' ? 'Рус' : 'Eng'}
            </button>
          ))}
        </div>
      )}
    </LangContext.Consumer>
  )
}
