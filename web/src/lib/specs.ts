// Product characteristics: the definitions come from the server (GET /product-specs, domain/product_specs.py).
import { useEffect, useState } from 'react'
import { api, type Lang, type SpecDef, type SpecDefs, type SpecValue } from './api'
import { tr } from './format'

export function useSpecDefs(): SpecDefs | null {
  const [defs, setDefs] = useState<SpecDefs | null>(null)
  useEffect(() => {
    void api.productSpecs().then(setDefs, () => setDefs(null))
  }, [])
  return defs
}

/** The characteristics a product of this category can have (services have none). */
export function specsFor(defs: SpecDefs, category: string | null | undefined, isService: boolean): SpecDef[] {
  if (isService) return []
  return defs.specs.filter((s) => !s.categories.length || (category != null && s.categories.includes(category)))
}

/** A value as text: an option label, a number with its unit, ✓ for a flag. */
export function specText(def: SpecDef, value: SpecValue, lang: Lang, yes: string): string {
  if (def.kind === 'flag') return value ? yes : ''
  if (def.kind === 'choice') return def.options[String(value)] ? tr(def.options[String(value)], lang) : String(value)
  if (def.kind === 'number') return def.unit ? `${value} ${tr(def.unit, lang)}` : String(value)
  return String(value)
}

/** Filled characteristics grouped for the card, in the order of the definitions. */
export function filledGroups(
  defs: SpecDefs,
  values: Record<string, SpecValue>,
): { group: string; items: { def: SpecDef; value: SpecValue }[] }[] {
  const out: { group: string; items: { def: SpecDef; value: SpecValue }[] }[] = []
  for (const group of Object.keys(defs.groups)) {
    const items = defs.specs
      .filter((s) => s.group === group && values[s.code] !== undefined && values[s.code] !== '' && values[s.code] !== false)
      .map((def) => ({ def, value: values[def.code] }))
    if (items.length) out.push({ group, items })
  }
  return out
}
