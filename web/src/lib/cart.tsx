import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, type Cart } from './api'

interface CartState {
  cart: Cart | null
  count: number
  qtyOf: (productId: string) => string | null
  setItem: (productId: string, qty: string, offer?: number | null) => Promise<void>
  remove: (productId: string) => Promise<void>
  refresh: () => Promise<void>
  error: string | null
}

const CartContext = createContext<CartState | null>(null)

export function CartProvider({ enabled, children }: { enabled: boolean; children: ReactNode }) {
  const [cart, setCart] = useState<Cart | null>(null)
  const [error, setError] = useState<string | null>(null)

  const run = useCallback(async (p: Promise<Cart>) => {
    try {
      setCart(await p)
      setError(null)
    } catch (e) {
      setError((e as Error).message)
      throw e
    }
  }, [])

  const refresh = useCallback(() => run(api.cart()), [run])
  useEffect(() => {
    if (enabled) void refresh().catch(() => {})
  }, [enabled, refresh])

  const value = useMemo<CartState>(() => {
    const lines = cart?.groups.flatMap((g) => g.lines) ?? []
    return {
      cart,
      error,
      count: lines.length,
      qtyOf: (id) => lines.find((l) => l.product_id === id)?.qty ?? null,
      setItem: (id, qty, offer = null) => run(api.setCartItem(id, qty, offer)),
      remove: (id) => run(api.removeCartItem(id)),
      refresh,
    }
  }, [cart, error, run, refresh])

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>
}

export function useCart(): CartState {
  const ctx = useContext(CartContext)
  if (!ctx) throw new Error('useCart outside CartProvider')
  return ctx
}

/** Cart actions when available (buyers); null for sellers' screens that are shared with buyers. */
export function useCartMaybe(): CartState | null {
  return useContext(CartContext)
}
