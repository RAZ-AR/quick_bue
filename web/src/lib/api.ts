// Thin typed client over the FastAPI backend (served under /api by the Vite proxy and nginx).

export type Lang = 'hy' | 'ru' | 'en'
export type I18nText = Partial<Record<Lang, string>>
export type Unit = 'kg' | 'l' | 'pcs' | 'pack'

export interface Org { id: string; kind: 'buyer' | 'seller'; display_name: string }
export interface Me {
  id: string; name: string; email: string | null; locale: Lang; is_platform_admin: boolean
  memberships: { role: 'owner' | 'manager' | 'buyer_staff'; organization: Org }[]
}
export interface Category { id: string; parent_id: string | null; slug: string; name: I18nText }
export interface Product {
  id: string; seller: { id: string; display_name: string }; category_id: string | null
  name: I18nText; unit: Unit; pack_size: string | null; base_price_amd: number; vat_included: boolean
  min_qty: string; qty_step: string; in_stock: boolean; allow_offers: boolean; images: string[]
  tiers: { min_qty: string; price_amd: number }[]
}
export interface ProductPage { items: Product[]; total: number }
export interface PublicConfig { dev_login: boolean; telegram_bot_username: string }

const TOKEN_KEY = 'qb.token'
const BASE = '/api'

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

export const token = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const t = token.get()
  if (t) headers.set('Authorization', `Bearer ${t}`)
  if (init.body) headers.set('Content-Type', 'application/json')
  const res = await fetch(BASE + path, { ...init, headers })
  if (!res.ok) {
    if (res.status === 401) token.clear()
    const detail = await res.json().then((b) => b.detail, () => res.statusText)
    throw new ApiError(res.status, typeof detail === 'string' ? detail : res.statusText)
  }
  return res.json() as Promise<T>
}

export const api = {
  config: () => request<PublicConfig>('/config'),
  devLogin: (email: string) =>
    request<{ access_token: string }>('/auth/dev-login', { method: 'POST', body: JSON.stringify({ email }) }),
  me: () => request<Me>('/me'),
  categories: () => request<Category[]>('/categories'),
  products: (params: { q?: string; category_id?: string; offers_only?: boolean; limit?: number }) => {
    const qs = new URLSearchParams()
    for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== '' && v !== false) qs.set(k, String(v))
    return request<ProductPage>(`/products?${qs}`)
  },
}
