import type { I18nText, Lang, Unit } from './api'

/** 3500 -> "3 500 ֏" (narrow no-break space as thousands separator, like Armenian receipts). */
export function amd(value: number): string {
  const digits = Math.round(value).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
  return `${digits} ֏`
}

/** Text in the user's language, falling back to Armenian, Russian, English. */
export function tr(text: I18nText, lang: Lang): string {
  return text[lang] || text.hy || text.ru || text.en || ''
}

/** "20.000" -> "20", "0.500" -> "0.5" */
export function qty(value: string | number): string {
  return Number(value).toString()
}

const UNITS: Record<Unit, Record<Lang, string>> = {
  kg: { hy: 'կգ', ru: 'кг', en: 'kg' },
  l: { hy: 'լ', ru: 'л', en: 'l' },
  pcs: { hy: 'հատ', ru: 'шт', en: 'pcs' },
  pack: { hy: 'տուփ', ru: 'уп', en: 'pack' },
}

export function unit(u: Unit, lang: Lang): string {
  return UNITS[u][lang]
}
