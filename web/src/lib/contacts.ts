// Contact checks as you type. Kept in step with backend/app/domain/contacts.py, which has the last word.

const COMMON_DOMAINS = [
  'gmail.com', 'mail.ru', 'yandex.ru', 'yahoo.com', 'outlook.com', 'hotmail.com',
  'icloud.com', 'inbox.ru', 'list.ru', 'bk.ru', 'rambler.ru', 'protonmail.com',
]

/** '091 23-45-67', '+37491234567' → '+374 91 234 567'; null if not an Armenian number. */
export function normalizePhone(raw: string): string | null {
  let d = raw.replace(/\D/g, '')
  if (d.startsWith('00374')) d = d.slice(5)
  else if (d.startsWith('374') && d.length === 11) d = d.slice(3)
  else if (d.startsWith('0') && d.length === 9) d = d.slice(1)
  if (!/^[1-9]\d{7}$/.test(d)) return null
  return `+374 ${d.slice(0, 2)} ${d.slice(2, 5)} ${d.slice(5)}`
}

export function normalizeEmail(raw: string): string | null {
  const e = raw.trim().toLowerCase()
  return /^[^@\s]+@[^@\s]+\.[a-z]{2,}$/.test(e) && e.length <= 320 ? e : null
}

function distance(a: string, b: string): number {
  let prev = Array.from({ length: b.length + 1 }, (_, i) => i)
  for (let i = 1; i <= a.length; i++) {
    const cur = [i]
    for (let j = 1; j <= b.length; j++) cur.push(Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1)))
    prev = cur
  }
  return prev[b.length]
}

/** 'ani@gmial.com' → 'ani@gmail.com'; null when the domain looks fine or unknown. */
export function emailSuggestion(email: string): string | null {
  const [local, domain] = email.split('@')
  if (!domain || COMMON_DOMAINS.includes(domain)) return null
  const best = COMMON_DOMAINS.reduce((a, b) => (distance(domain, a) <= distance(domain, b) ? a : b))
  return distance(domain, best) <= 2 ? `${local}@${best}` : null
}

/** Armenian bank accounts: 16 digits. */
export function normalizeBankAccount(raw: string): string | null {
  const d = raw.replace(/[\s-]/g, '')
  return /^\d{16}$/.test(d) ? d : null
}

export type ContactKey = 'phone' | 'email' | 'bank_account'

/** On leaving a field: the normalized value to put back, or the problem code to show. Empty is fine. */
export function checkContact(key: ContactKey, raw: string): { value: string | null; problem: string | null } {
  if (!raw.trim()) return { value: null, problem: null }
  const value = key === 'phone' ? normalizePhone(raw) : key === 'email' ? normalizeEmail(raw) : normalizeBankAccount(raw)
  return value ? { value, problem: null } : { value: null, problem: `bad_${key}` }
}
