// Haggling helpers shared by the seller and buyer screens. The autopilot here mirrors
// backend/app/domain/negotiation.decide for percentage rules, so the seller sees what will really happen.

export interface PctRule {
  acceptBp: number // agree at once to a discount up to this
  maxBp: number | null // decline anything deeper
  autoCounter: boolean
}

export type Verdict = { kind: 'accept'; price: number } | { kind: 'counter'; price: number } | { kind: 'decline' } | { kind: 'manual' }

const round10 = (x: number) => Math.round(x / 10) * 10
// Nearest dram, like the server
const priceAt = (reference: number, discountBp: number) => Math.round((reference * (10_000 - discountBp)) / 10_000)

export function decide(proposed: number, reference: number, rule: PctRule): Verdict {
  const accept = priceAt(reference, rule.acceptBp)
  const floor = rule.maxBp === null ? 0 : priceAt(reference, rule.maxBp)
  if (proposed >= accept) return { kind: 'accept', price: proposed }
  if (proposed < floor) return { kind: 'decline' }
  if (!rule.autoCounter) return { kind: 'manual' }
  const counter = Math.max(accept, midpoint(proposed, reference))
  return counter >= reference ? { kind: 'decline' } : { kind: 'counter', price: counter }
}

/** Halfway between an offer and the other side's price, in tens of drams. */
export function midpoint(a: number, b: number): number {
  return round10((a + b) / 2)
}

/** Sample offers that hit every zone of a rule: accepted, countered, declined. */
export function sampleDiscounts(rule: PctRule): number[] {
  const a = rule.acceptBp
  const m = rule.maxBp ?? Math.min(5000, a + 1000)
  const snap = (bp: number) => Math.round(bp / 50) * 50
  const raw = [snap(a / 2), a, snap((a + m) / 2), m, rule.maxBp === null ? null : snap(m + 300)]
  return [...new Set(raw.filter((x): x is number => x !== null && x > 0 && x < 5000))].sort((x, y) => x - y)
}

export function discountBp(price: number, reference: number): number {
  return reference > 0 && price < reference ? Math.floor(((reference - price) * 10_000) / reference) : 0
}

/** 300 → "3", 571 → "5.7" */
export function pct(bp: number): string {
  return (Math.round(bp / 10) / 10).toString()
}

export function priceForDiscount(reference: number, bp: number): number {
  return priceAt(reference, bp)
}

/** Where a buyer's price falls against the seller's shared hint. */
export function zone(price: number, reference: number, hintBp: number | null): 'likely' | 'maybe' | null {
  if (hintBp === null) return null
  return price >= priceAt(reference, hintBp) ? 'likely' : 'maybe'
}
