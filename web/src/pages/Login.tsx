import { useEffect, useState } from 'react'
import { LangSwitch } from '../App'
import { useT } from '../i18n'
import { api, token, type PublicConfig } from '../lib/api'

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
    </div>
  )
}
