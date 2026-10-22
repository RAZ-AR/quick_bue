// Thin typed client over the FastAPI backend (served under /api by the Vite proxy and nginx).

export type Lang = 'hy' | 'ru' | 'en'
export type I18nText = Partial<Record<Lang, string>>
export type Unit = 'kg' | 'l' | 'pcs' | 'pack'
export type PriceSource = 'list' | 'tier' | 'agreement' | 'negotiated'
export type OrderStatus =
  | 'negotiating' | 'placed' | 'confirmed' | 'rejected' | 'cancelled'
  | 'delivering' | 'delivered' | 'disputed' | 'accepted'
export type Decision = 'accepted' | 'declined' | 'countered'
export type NextStep = 'answer_offer' | 'answer_counter' | 'confirm' | 'deliver' | 'accept_delivery' | 'mark_paid'

export interface Org { id: string; kind: 'buyer' | 'seller'; display_name: string }
export interface Brief { id: string; display_name: string }
export interface Me {
  id: string; name: string; email: string | null; locale: Lang; is_platform_admin: boolean
  memberships: { role: 'owner' | 'manager' | 'buyer_staff'; organization: Org }[]
}
export interface Category { id: string; parent_id: string | null; slug: string; name: I18nText }
export interface Product {
  id: string; seller: Brief; category_id: string | null
  name: I18nText; unit: Unit; pack_size: string | null; base_price_amd: number; vat_included: boolean
  min_qty: string; qty_step: string; in_stock: boolean; allow_offers: boolean; images: string[]
  tiers: { min_qty: string; price_amd: number }[]
}
export interface ProductPage { items: Product[]; total: number }
export interface PublicConfig { dev_login: boolean; telegram_bot_username: string }

export interface Address { id: string; label: string; text: string; district: string | null }
export interface CartLine {
  product_id: string; name: I18nText; unit: Unit; qty: string; min_qty: string; qty_step: string
  base_price_amd: number; unit_price_amd: number; price_source: PriceSource; line_total_amd: number
  offer_price_amd: number | null; offers_allowed: boolean; offer_min_line_amd: number; problems: string[]
}
export interface CartGroup {
  seller: Brief; lines: CartLine[]; subtotal_amd: number; delivery_fee_amd: number; total_amd: number
  min_order_amd: number; missing_amd: number; free_delivery_from_amd: number | null
  delivery_date: string | null; problems: string[]
}
export interface Cart {
  groups: CartGroup[]; total_amd: number; address: Address | null
  problems: { code: string; product_id?: string; seller_id?: string }[]; can_negotiate: boolean
}

export interface OrderLine {
  id: string; product_id: string | null; name_snapshot: I18nText; unit: Unit
  qty_ordered: string; qty_confirmed: string | null; qty_received: string | null
  list_price_amd: number; final_price_amd: number | null; price_source: PriceSource; line_total_amd: number | null
}
export interface Offer {
  id: string; from_side: 'buyer' | 'seller'; is_auto: boolean; kind: 'price' | 'percent' | 'order_total'
  percent_bp: number | null; message: string | null
  response: 'accepted' | 'countered' | 'declined' | 'expired' | 'superseded' | null
  created_at: string; lines: { order_line_id: string; proposed_price_amd: number; decision: Decision | null }[]
}
export interface Negotiation {
  status: 'awaiting_seller' | 'awaiting_buyer' | 'agreed' | 'declined' | 'expired'
  scope: 'lines' | 'order'; round: number; expires_at: string; my_turn: boolean; rounds_left: number
  offers: Offer[]
}
export interface Order {
  id: string; number: string; status: OrderStatus; my_side: 'buyer' | 'seller'; buyer: Brief; seller: Brief
  delivery_date: string | null; subtotal_amd: number; discount_amd: number; delivery_fee_amd: number
  total_amd: number; payment_status: 'unpaid' | 'paid'; cancel_reason: string | null
  buyer_note: string | null; seller_note: string | null; created_at: string
  lines: OrderLine[]; negotiation: Negotiation | null; allowed_actions: string[]; address: Address | null
  next_step: NextStep | null; deadline: string | null; saving_amd: number
  events: { type: string; at: string; auto: boolean }[]
}
export interface OrderListItem {
  id: string; number: string; status: OrderStatus; counterparty: Brief; total_amd: number
  delivery_date: string | null; created_at: string; lines_count: number; payment_status: 'unpaid' | 'paid'
  my_side: 'buyer' | 'seller'; next_step: NextStep | null; deadline: string | null; saving_amd: number
  preview: I18nText[]
}
export interface LineAnswer { order_line_id: string; decision: Decision; price_amd?: number }

const TOKEN_KEY = 'qb.token'
const BASE = '/api'

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    public problems: { code: string; [k: string]: unknown }[] = [],
  ) {
    super(code)
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
    const body = await res.json().catch(() => ({}))
    // Domain errors: {code, message, details: {problems}}; framework errors: {detail}
    const code = body.code ?? (typeof body.detail === 'string' ? body.detail : res.statusText)
    throw new ApiError(res.status, code, body.details?.problems ?? [])
  }
  return res.json() as Promise<T>
}

const post = <T>(path: string, body?: unknown, headers?: HeadersInit) =>
  request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body), headers })

export const api = {
  config: () => request<PublicConfig>('/config'),
  devLogin: (email: string) => post<{ access_token: string }>('/auth/dev-login', { email }),
  me: () => request<Me>('/me'),
  categories: () => request<Category[]>('/categories'),
  products: (params: { q?: string; category_id?: string; offers_only?: boolean; limit?: number }) => {
    const qs = new URLSearchParams()
    for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== '' && v !== false) qs.set(k, String(v))
    return request<ProductPage>(`/products?${qs}`)
  },

  cart: () => request<Cart>('/cart'),
  addresses: () => request<Address[]>('/addresses'),
  setCartItem: (productId: string, qty: string, offerPrice: number | null = null) =>
    request<Cart>(`/cart/items/${productId}`, {
      method: 'PUT',
      body: JSON.stringify({ qty, offer_price_amd: offerPrice }),
    }),
  removeCartItem: (productId: string) => request<Cart>(`/cart/items/${productId}`, { method: 'DELETE' }),
  checkout: (body: { address_id?: string; order_offers?: { seller_id: string; percent_bp: number }[] }, key: string) =>
    post<{ orders: Order[] }>('/checkout', body, { 'Idempotency-Key': key }),

  orders: (status?: OrderStatus[]) => {
    const qs = new URLSearchParams()
    for (const s of status ?? []) qs.append('status', s)
    return request<{ items: OrderListItem[]; total: number }>(`/orders?${qs}`)
  },
  order: (id: string) => request<Order>(`/orders/${id}`),
  confirm: (id: string, lines: { order_line_id: string; qty: string }[]) =>
    post<Order>(`/orders/${id}/confirm`, { lines }),
  accept: (id: string) => post<Order>(`/orders/${id}/accept`, {}),
  action: (id: string, action: 'cancel' | 'reject' | 'ship' | 'deliver' | 'mark_paid') =>
    post<Order>(`/orders/${id}/${action}`),
  respond: (id: string, body: { lines?: LineAnswer[]; order?: { decision: Decision; percent_bp?: number } }) =>
    post<Order>(`/orders/${id}/negotiation/respond`, body, { 'Idempotency-Key': crypto.randomUUID() }),
  reorder: (id: string) => post<{ added: number }>(`/orders/${id}/reorder`),
  createAgreement: (orderLineId: string, days = 30) =>
    post<{ id: string }>('/agreements', { order_line_id: orderLineId, days }),
}
