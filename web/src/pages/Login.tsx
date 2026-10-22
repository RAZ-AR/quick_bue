import type React from 'react'
import { useEffect, useState } from 'react'
import { LangSwitch } from '../App'
import { problemText, useLang, useT } from '../i18n'
import { api, ApiError, token, type PublicConfig } from '../lib/api'

// Seeded by `python -m app.seed` (backend/app/seed.py)
const DEMO_USERS: { group: 'buyers' | 'sellers' | 'platform'; email: string; label: string }[] = [
  { group: 'buyers', email: 'arax@qb.local', label: 'Cafe Arax — owner' },
  { group: 'buyers', email: 'chef@qb.local', label: 'Cafe Arax — chef' },
  { group: 'buyers', email: 'nova@qb.local', label: 'Bar Nova — owner' },
  { group: 'sellers', email: 'lori@qb.local', label: 'Լոռի Պանիր — seller' },
  { group: 'sellers', email: 'pack@qb.local', label: 'Yerevan Pack — seller' },
  { group: 'sellers', email: 'farm@qb.local', label: 'Green Valley — seller' },
  { group: 'platform', email: 'admin@qb.local', label: 'QB operator' },
]

export function Login({ onSignedIn }: { onSignedIn: () => Promise<void> }) {
  const t = useT()
  const lang = useLang()
  const [config, setConfig] = useState<PublicConfig | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.config().then(setConfig, (e: Error) => setError(e.message))
  }, [])

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')

  async function register(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      const { access_token } = await api.devRegister(name, email)
      token.set(access_token)
      await onSignedIn()
    } catch (err) {
      setError(problemText((err as ApiError).code, lang))
    }
  }

  async function signIn(email: string) {
    setError(null)
    try {
      const { access_token } = await api.devLogin(email)
      token.set(access_token)
      await onSignedIn()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <div className="login page">
      <div className="login-top">
        <LangSwitch />
      </div>
      <div className="logo">QB</div>
      <p className="tagline">{t('tagline')}</p>
      <section className="ticket perf">
        <h1>{t('login_title')}</h1>
        {config === null && !error && <p className="muted">{t('loading')}</p>}
        {config && !config.dev_login && <p className="muted">{t('login_unavailable')}</p>}
        {config?.dev_login && (
          <>
            <p className="muted">{t('login_dev_note')}</p>
            {(['buyers', 'sellers', 'platform'] as const).map((g) => (
              <div key={g}>
                <h2 className="section-title">{t(g)}</h2>
                <ul className="demo-users">
                  {DEMO_USERS.filter((u) => u.group === g).map((u) => (
                    <li key={u.email}>
                      <button onClick={() => signIn(u.email)}>
                        <span>{u.label}</span>
                        <small>{u.email}</small>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </>
        )}
        {error && <p className="error">{error}</p>}
      </section>
      {config?.dev_login && (
        <form className="ticket" style={{ marginTop: 12, display: 'grid', gap: 10 }} onSubmit={register}>
          <h2 style={{ margin: 0 }}>{t('register')}</h2>
          <input className="search" style={{ background: 'var(--sunken)', paddingLeft: 18 }} placeholder={t('your_name')}
            value={name} onChange={(e) => setName(e.target.value)} required />
          <input className="search" style={{ background: 'var(--sunken)', paddingLeft: 18 }} placeholder={t('email')}
            type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <button className="btn primary block">{t('register')} →</button>
        </form>
      )}
    </div>
  )
}
