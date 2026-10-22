import { useEffect, useState } from 'react'
import { LangSwitch } from '../App'
import { useT } from '../i18n'
import { api, token, type PublicConfig } from '../lib/api'

// Seeded by `python -m app.seed` (backend/app/seed.py)
const DEMO_USERS = [
  { email: 'arax@qb.local', label: 'Cafe Arax — owner' },
  { email: 'chef@qb.local', label: 'Cafe Arax — chef' },
  { email: 'nova@qb.local', label: 'Bar Nova — owner' },
  { email: 'lori@qb.local', label: 'Լոռի Պանիր — seller' },
  { email: 'pack@qb.local', label: 'Yerevan Pack — seller' },
  { email: 'farm@qb.local', label: 'Green Valley — seller' },
  { email: 'admin@qb.local', label: 'QB operator' },
]

export function Login({ onSignedIn }: { onSignedIn: () => Promise<void> }) {
  const t = useT()
  const [config, setConfig] = useState<PublicConfig | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.config().then(setConfig, (e: Error) => setError(e.message))
  }, [])

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
    <div className="login">
      <div className="login-top">
        <LangSwitch />
      </div>
      <div className="logo">QB</div>
      <p className="tagline">{t('tagline')}</p>
      <section className="card">
        <h1>{t('login_title')}</h1>
        {config === null && !error && <p className="muted">{t('loading')}</p>}
        {config && !config.dev_login && <p className="muted">{t('login_unavailable')}</p>}
        {config?.dev_login && (
          <>
            <p className="muted">{t('login_dev_note')}</p>
            <ul className="demo-users">
              {DEMO_USERS.map((u) => (
                <li key={u.email}>
                  <button onClick={() => signIn(u.email)}>
                    <span>{u.label}</span>
                    <small>{u.email}</small>
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}
        {error && <p className="error">{error}</p>}
      </section>
    </div>
  )
}
