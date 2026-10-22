import { useCallback, useEffect, useMemo, useState } from 'react'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { LangContext, useT } from './i18n'
import { api, token, type Lang, type Me } from './lib/api'
import { Catalog } from './pages/Catalog'
import { Login } from './pages/Login'

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

  if (!checked) return null

  return (
    <LangContext.Provider value={ctx}>
      <Routes>
        <Route path="/login" element={me ? <Navigate to="/" replace /> : <Login onSignedIn={loadMe} />} />
        <Route
          path="/"
          element={me ? <Shell me={me} onSignOut={() => { token.clear(); setMe(null) }} /> : <Navigate to="/login" replace />}
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </LangContext.Provider>
  )
}

function Shell({ me, onSignOut }: { me: Me; onSignOut: () => void }) {
  const t = useT()
  const navigate = useNavigate()
  const org = me.memberships[0]?.organization
  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">QB</div>
        <div className="who">
          <span>{org?.display_name ?? me.name}</span>
          <small>{me.name}</small>
        </div>
        <LangSwitch />
        <button
          className="link"
          onClick={() => {
            onSignOut()
            navigate('/login')
          }}
        >
          {t('logout')}
        </button>
      </header>
      <main>
        <Catalog />
      </main>
    </div>
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
