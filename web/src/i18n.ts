import { createContext, useContext } from 'react'
import type { Lang } from './lib/api'

export const TEXTS = {
  tagline: {
    hy: 'Բոլոր մատակարարները մեկ զամբյուղում։ Կարող եք սակարկել։',
    ru: 'Все поставщики в одной корзине. Можно торговаться.',
    en: 'All your suppliers in one cart. Haggling allowed.',
  },
  login_title: { hy: 'Մուտք', ru: 'Вход', en: 'Sign in' },
  login_dev_note: {
    hy: 'Թեստային մուտք դեմո օգտատերերով (DEV_LOGIN)։',
    ru: 'Тестовый вход под демо-пользователями (DEV_LOGIN).',
    en: 'Test sign-in as demo users (DEV_LOGIN).',
  },
  login_unavailable: {
    hy: 'Մուտքը դեռ կարգավորված չէ։',
    ru: 'Вход ещё не настроен.',
    en: 'Sign-in is not configured yet.',
  },
  logout: { hy: 'Ելք', ru: 'Выйти', en: 'Sign out' },
  search: { hy: 'Որոնում՝ պանիր, сыр, panir…', ru: 'Поиск: сыр, պանիր, panir…', en: 'Search: cheese, պանիր, сыр…' },
  all: { hy: 'Բոլորը', ru: 'Все', en: 'All' },
  offers_only: { hy: 'Սակարկելի', ru: 'Можно торговаться', en: 'Open to offers' },
  haggle: { hy: 'Սակարկում', ru: 'Торг', en: 'Offers' },
  from: { hy: 'սկսած', ru: 'от', en: 'from' },
  per: { hy: '/', ru: '/', en: '/' },
  found: { hy: 'Գտնվել է', ru: 'Найдено', en: 'Found' },
  nothing: { hy: 'Ոչինչ չգտնվեց', ru: 'Ничего не нашли', en: 'Nothing found' },
  out_of_stock: { hy: 'Առկա չէ', ru: 'Нет в наличии', en: 'Out of stock' },
  min: { hy: 'նվազ.', ru: 'мин.', en: 'min' },
  loading: { hy: 'Բեռնվում է…', ru: 'Загрузка…', en: 'Loading…' },
} satisfies Record<string, Record<Lang, string>>

export type TextKey = keyof typeof TEXTS

export const LangContext = createContext<{ lang: Lang; setLang: (l: Lang) => void }>({
  lang: 'hy',
  setLang: () => {},
})

export function useT() {
  const { lang } = useContext(LangContext)
  return (key: TextKey) => TEXTS[key][lang]
}
