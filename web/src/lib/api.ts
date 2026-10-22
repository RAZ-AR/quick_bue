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

export type VerificationStatus = 'none' | 'pending' | 'verified' | 'rejected'
export type Mode = 'buyer' | 'seller'
export interface Org {
  id: string; display_name: string; is_buyer: boolean; is_seller: boolean
  status: 'pending' | 'active' | 'blocked'; verification_status: VerificationStatus
}
export interface Brief { id: string; display_name: string }
export interface Me {
  id: string; name: string; email: string | null; locale: Lang; is_platform_admin: boolean
  memberships: { role: 'owner' | 'manager' | 'buyer_staff'; organization: Org; buyer_ready: boolean }[]
}
export interface Category { id: string; parent_id: string | null; slug: string; name: I18nText }
export interface Product {
  id: string; seller: Brief | null; category_id: string | null
  name: I18nText; unit: Unit; pack_size: string | null; base_price_amd: number; vat_included: boolean
  min_qty: string; qty_step: string; in_stock: boolean; allow_offers: boolean; images: string[]
  tiers: { min_qty: string; price_amd: number }[]
}
export interface ProductPage { items: Product[]; total: number; guest?: boolean }
export interface PublicConfig {
  dev_login: boolean; email_login: boolean; google_client_id: string | null; telegram_bot_username: string | null
}

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
export type TaxRegime = 'vat' | 'turnover' | 'micro'
export type FileKind =
  | 'state_registration' | 'food_safety_registration' | 'conformity' | 'veterinary'
  | 'phytosanitary' | 'haccp' | 'alcohol_license' | 'other'
export interface Company {
  tin: string; legal_name: string; registration_number: string | null; legal_address: string | null
  director_name: string | null; tax_regime: TaxRegime | null; active: boolean
}
export interface Lookup { tin: string; found: boolean; already_registered: boolean; provider: string; company: Company | null }
export interface OrgDetail {
  id: string; is_buyer: boolean; is_seller: boolean; status: 'pending' | 'active' | 'blocked'; legal_name: string
  display_name: string; tin: string | null; tax_regime: TaxRegime | null; registration_number: string | null
  legal_address: string | null; director_name: string | null; bank_name: string | null; bank_account: string | null
  phone: string | null; email: string | null; venue_type: string | null; registry_source: string | null
  verification_status: VerificationStatus; verified_at: string | null; review_note: string | null
}
export interface OrgFile {
  id: string; kind: FileKind; file_name: string; content_type: string; size_bytes: number
  status: 'pending' | 'approved' | 'rejected'; expires_on: string | null; review_note: string | null; created_at: string
}
export interface Verification { organization: OrgDetail; required: FileKind[]; recommended: FileKind[]; files: OrgFile[] }
export type DocKind = 'invoice' | 'delivery_note' | 'acceptance_act' | 'tax_invoice' | 'waybill'
export interface DocLine {
  n: number; name: I18nText; unit: Unit; qty: string; qty_confirmed?: string; price_amd: number
  amount_amd: number; vat_rate_bp: number; vat_amd: number
}
export interface Party {
  legal_name: string; display_name: string; tin: string | null; registration_number: string | null
  legal_address: string | null; director_name: string | null; bank_name: string | null; bank_account: string | null
  phone: string | null; vat_payer: boolean
}
export interface DocPayload {
  kind: DocKind; title: I18nText; number?: string; date?: string; order_number?: string; delivery_date?: string | null
  seller?: Party; buyer?: Party; delivery_address?: string | null; lines?: DocLine[]
  totals?: { subtotal_amd: number; discount_amd: number; delivery_fee_amd: number; total_amd: number; vat_amd: number }
  vat_note?: string | null; transport?: { from: string | null; to: string | null; vehicle: string | null; driver: string | null }
  external_id?: string
}
export interface QDocument {
  id: string; kind: DocKind; number: string | null; external_id: string | null
  status: 'draft' | 'issued' | 'failed' | 'cancelled'; issued_at: string | null; payload: DocPayload | null
}
export interface NewOrg {
  roles: Mode[]; tin: string; legal_name: string; display_name?: string; tax_regime?: TaxRegime | null
  registration_number?: string | null; legal_address?: string | null; director_name?: string | null
  bank_name?: string | null; bank_account?: string | null; phone?: string | null; email?: string | null
  venue_type?: string | null; delivery_address?: string | null; district?: string | null
}

export interface LineAnswer { order_line_id: string; decision: Decision; price_amd?: number }

export interface Tier { min_qty: string; price_amd: number }
export interface Autopilot {
  enabled: boolean; floor_price_amd: number | null; accept_price_amd: number | null
  auto_counter: boolean; min_line_amd: number | null
}
export interface SellerProduct {
  id: string; sku: string | null; category_id: string | null; name: I18nText; description: I18nText | null
  unit: Unit; pack_size: string | null; base_price_amd: number; vat_included: boolean; vat_rate_bp: number
  min_qty: string; qty_step: string; in_stock: boolean; allow_offers: boolean; archived: boolean
  tiers: Tier[]; autopilot: Autopilot | null
}
export type ProductInput = Omit<SellerProduct, 'id' | 'archived' | 'vat_rate_bp'>
export interface SellerSettings {
  min_order_amd: number; cutoff_time: string; lead_days: number; delivery_fee_amd: number
  free_delivery_from_amd: number | null; offer_response_hours: number
  zones: { district: string; weekdays: number[] }[]
}

/** Which company and which side the user acts for: sent with every request. */
export const context: { orgId: string | null; mode: Mode | null } = { orgId: null, mode: null }

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
  if (t && context.orgId) headers.set('X-Org-Id', context.orgId)
  if (t && context.mode) headers.set('X-Mode', context.mode)
  if (typeof init.body === 'string') headers.set('Content-Type', 'application/json')
  const res = await fetch(BASE + path, { ...init, headers })
  if (!res.ok) {
    if (res.status === 401) token.clear()
    const body = await res.json().catch(() => ({}))
    // Domain errors: {code, message, details: {problems}}; framework errors: {detail}
    const code = body.code ?? (typeof body.detail === 'string' ? body.detail : res.statusText)
    throw new ApiError(res.status, code, body.details?.problems ?? [])
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

/** Files need the auth header, so they are fetched as blobs and opened from an object URL. */
export async function openFile(path: string): Promise<void> {
  const t = token.get()
  const res = await fetch(BASE + path, { headers: t ? { Authorization: `Bearer ${t}` } : {} })
  if (!res.ok) throw new ApiError(res.status, 'file_not_found')
  const url = URL.createObjectURL(await res.blob())
  window.open(url, '_blank', 'noopener')
  setTimeout(() => URL.revokeObjectURL(url), 60_000)
}

const post = <T>(path: string, body?: unknown, headers?: HeadersInit) =>
  request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body), headers })

export const api = {
  config: () => request<PublicConfig>('/config'),
  devLogin: (email: string) => post<{ access_token: string }>('/auth/dev-login', { email }),
  me: () => request<Me>('/me'),
  categories: () => request<Category[]>('/categories'),
  products: (params: { q?: string; category_id?: string; offers_only?: boolean; limit?: number; ids?: string[] }) => {
    const qs = new URLSearchParams()
    for (const [k, v] of Object.entries(params)) {
      if (Array.isArray(v)) v.forEach((x) => qs.append(k, x))
      else if (v !== undefined && v !== '' && v !== false) qs.set(k, String(v))
    }
    return request<ProductPage>(`/products?${qs}`)
  },

  // sign-in
  emailStart: (email: string, lang: Lang) => post<{ sent: boolean; dev_code: string | null }>('/auth/email/start', { email, lang }),
  emailVerify: (email: string, code: string) => post<{ access_token: string }>('/auth/email/verify', { email, code }),
  google: (credential: string) => post<{ access_token: string }>('/auth/google', { credential }),
  telegram: (payload: Record<string, unknown>) => post<{ access_token: string }>('/auth/telegram', payload),
  addRole: (role: Mode, delivery_address?: string, district?: string) =>
    post<OrgDetail>('/organizations/me/roles', { role, delivery_address, district }),

  // seller cabinet
  sellerProducts: (archived = false) => request<SellerProduct[]>(`/seller/products?archived=${archived}`),
  createProduct: (body: ProductInput) => post<SellerProduct>('/seller/products', body),
  updateProduct: (id: string, body: ProductInput) =>
    request<SellerProduct>(`/seller/products/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  archiveProduct: (id: string, archived: boolean) =>
    post<SellerProduct>(`/seller/products/${id}/${archived ? 'archive' : 'restore'}`),
  sellerSettings: () => request<SellerSettings>('/seller/settings'),
  saveSellerSettings: (body: SellerSettings) =>
    request<SellerSettings>('/seller/settings', { method: 'PUT', body: JSON.stringify(body) }),

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

  // sign-up and verification
  devRegister: (name: string, email: string) => post<{ access_token: string }>('/auth/dev-register', { name, email }),
  lookup: (tin: string) => request<Lookup>(`/registry/lookup?tin=${encodeURIComponent(tin)}`),
  createOrg: (body: NewOrg) => post<OrgDetail>('/organizations', body),
  updateOrg: (body: Partial<OrgDetail>) =>
    request<OrgDetail>('/organizations/me', { method: 'PATCH', body: JSON.stringify(body) }),
  verification: () => request<Verification>('/verification'),
  uploadFile: (kind: FileKind, file: File, expiresOn?: string) => {
    const form = new FormData()
    form.append('kind', kind)
    form.append('file', file)
    if (expiresOn) form.append('expires_on', expiresOn)
    return request<OrgFile>('/verification/files', { method: 'POST', body: form })
  },
  deleteFile: (id: string) => request<void>(`/verification/files/${id}`, { method: 'DELETE' }),
  submitVerification: () => post<Verification>('/verification/submit'),
  adminQueue: (status: VerificationStatus[] = ['pending']) =>
    request<Verification[]>(`/admin/verification?${status.map((s) => `status=${s}`).join('&')}`),
  reviewFile: (id: string, approve: boolean, note?: string) => post<OrgFile>(`/admin/files/${id}/review`, { approve, note }),
  reviewOrg: (id: string, approve: boolean, note?: string) =>
    post<OrgDetail>(`/admin/organizations/${id}/review`, { approve, note }),

  // order documents
  documents: (orderId: string) => request<QDocument[]>(`/orders/${orderId}/documents`),
  issueDocuments: (orderId: string) => post<QDocument[]>(`/orders/${orderId}/documents`),
  srcNumber: (orderId: string, kind: 'tax_invoice' | 'waybill', number: string) =>
    post<QDocument>(`/orders/${orderId}/documents/src`, { kind, number }),
  document: (id: string) => request<QDocument>(`/documents/${id}`),
}
