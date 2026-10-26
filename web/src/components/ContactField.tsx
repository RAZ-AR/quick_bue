import { useState } from 'react'
import { problemText, useLang, useT } from '../i18n'
import { checkContact, emailSuggestion, type ContactKey } from '../lib/contacts'
import { Field } from './Field'

const INPUT: Record<ContactKey, { type: string; inputMode: 'tel' | 'email' | 'numeric'; placeholder: string; autoComplete: string }> = {
  phone: { type: 'tel', inputMode: 'tel', placeholder: '+374 91 234 567', autoComplete: 'tel' },
  email: { type: 'email', inputMode: 'email', placeholder: 'name@company.am', autoComplete: 'email' },
  bank_account: { type: 'text', inputMode: 'numeric', placeholder: '1570 0000 0000 0000', autoComplete: 'off' },
}

/**
 * Phone, e-mail or bank account: checked when the field is left (a typo shows at once, not on submit),
 * the phone gets its +374 format, and a mistyped mail domain gets a one-tap fix.
 */
export function ContactField({
  kind,
  label,
  value,
  onChange,
  error,
}: {
  kind: ContactKey
  label: string
  value: string
  onChange: (value: string) => void
  error?: string
}) {
  const t = useT()
  const lang = useLang()
  const [problem, setProblem] = useState<string | null>(null)
  const suggestion = kind === 'email' && !problem && value ? emailSuggestion(value.trim().toLowerCase()) : null

  function blur() {
    const r = checkContact(kind, value)
    setProblem(r.problem)
    if (r.value && r.value !== value) onChange(r.value)
  }

  return (
    <div className="contact-field">
      <Field
        label={label}
        {...INPUT[kind]}
        value={value}
        onChange={(e) => (onChange(e.target.value), setProblem(null))}
        onBlur={blur}
        error={problem ? problemText(problem, lang) : error}
        aria-invalid={!!(problem || error)}
      />
      {suggestion && (
        <button type="button" className="link small" onClick={() => onChange(suggestion)}>
          {t('did_you_mean')} {suggestion}?
        </button>
      )}
    </div>
  )
}
