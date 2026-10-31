import { useState } from 'react'
import { Link } from 'react-router-dom'
import { problemText, useLang, useT } from '../i18n'
import { api, ApiError } from '../lib/api'
import { useSession } from '../lib/session'
import { Sheet } from './Sheet'

/** "I accept the offer and the privacy policy", with both documents opening in a new tab. */
export function ConsentText() {
  const t = useT()
  return (
    <>
      {t('consent_prefix')}{' '}
      <Link to="/legal/terms" target="_blank" rel="noopener">
        {t('legal_terms_link')}
      </Link>{' '}
      {t('consent_and')}{' '}
      <Link to="/legal/privacy" target="_blank" rel="noopener">
        {t('legal_privacy_link')}
      </Link>
    </>
  )
}

/**
 * Asks once more when the offer or the policy changed since the user signed up.
 * There is no way around it but to accept or to sign out.
 */
export function ConsentGate() {
  const t = useT()
  const lang = useLang()
  const { me, org, reload, signOut } = useSession()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  if (!me || !org || !me.missing_consents?.length) return null

  async function accept() {
    setBusy(true)
    setError(null)
    try {
      await api.acceptConsent()
      await reload()
    } catch (e) {
      setError(problemText((e as ApiError).code, lang))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Sheet onClose={() => undefined}>
      <div className="stack consent-gate">
        <p className="eyebrow">{t('consent_updated_eyebrow')}</p>
        <h2>{t('consent_updated_title')}</h2>
        <p className="muted">{t('consent_updated_text')}</p>
        <p>
          <ConsentText />
        </p>
        {error && <p className="error">{error}</p>}
        <button className="btn primary block" disabled={busy} onClick={accept}>
          {t('consent_accept')}
        </button>
        <button className="link" onClick={signOut}>
          {t('logout')}
        </button>
      </div>
    </Sheet>
  )
}
