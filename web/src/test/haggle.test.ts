import { fill } from '../i18n'
import { decide, discountBp, midpoint, pct, priceForDiscount, sampleDiscounts, zone } from '../lib/haggle'

// Lori cheese from the demo data: list 3 500, auto-accept from 3 300 (-5.71%), floor 3 000 (-14.28%)
const LORI = { acceptBp: 571, maxBp: 1428, autoCounter: true }

describe('autopilot preview mirrors the server', () => {
  it('accepts, counters halfway and declines like backend decide()', () => {
    expect(decide(3300, 3500, LORI)).toEqual({ kind: 'accept', price: 3300 })
    expect(decide(3100, 3500, LORI)).toEqual({ kind: 'counter', price: 3300 })
    expect(decide(3200, 3500, LORI)).toEqual({ kind: 'counter', price: 3350 })
    expect(decide(2000, 3500, LORI)).toEqual({ kind: 'decline' })
    expect(decide(3100, 3500, { ...LORI, autoCounter: false })).toEqual({ kind: 'manual' })
    expect(decide(3100, 3500, { ...LORI, maxBp: null })).toEqual({ kind: 'counter', price: 3300 })
  })

  it('picks sample offers that show every outcome', () => {
    const rule = { acceptBp: 300, maxBp: 1000, autoCounter: true }
    const kinds = sampleDiscounts(rule).map((bp) => decide(priceForDiscount(4200, bp), 4200, rule).kind)
    expect(new Set(kinds)).toEqual(new Set(['accept', 'counter', 'decline']))
  })
})

describe('haggle helpers', () => {
  it('formats discounts and midpoints', () => {
    expect(pct(300)).toBe('3')
    expect(pct(571)).toBe('5.7')
    expect(midpoint(3100, 3500)).toBe(3300)
    expect(discountBp(3300, 3500)).toBe(571)
    expect(priceForDiscount(3500, 571)).toBe(3300)
  })

  it('tells the buyer which zone a price is in', () => {
    expect(zone(3300, 3500, 571)).toBe('likely')
    expect(zone(3200, 3500, 571)).toBe('maybe')
    expect(zone(3200, 3500, null)).toBeNull()
  })

  it('fills placeholders in texts', () => {
    expect(fill('up to {p}% in {h} h', { p: 3, h: 24 })).toBe('up to 3% in 24 h')
  })
})
