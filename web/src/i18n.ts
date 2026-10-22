import { createContext, useContext } from 'react'
import type { Lang } from './lib/api'

type T3 = Record<Lang, string>

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
  login_unavailable: { hy: 'Մուտքը դեռ կարգավորված չէ։', ru: 'Вход ещё не настроен.', en: 'Sign-in is not configured yet.' },
  logout: { hy: 'Ելք', ru: 'Выйти', en: 'Sign out' },
  loading: { hy: 'Բեռնվում է…', ru: 'Загрузка…', en: 'Loading…' },
  error: { hy: 'Սխալ', ru: 'Ошибка', en: 'Error' },

  // tabs
  tab_catalog: { hy: 'Կատալոգ', ru: 'Каталог', en: 'Catalog' },
  tab_cart: { hy: 'Զամբյուղ', ru: 'Корзина', en: 'Cart' },
  tab_orders: { hy: 'Պատվերներ', ru: 'Заказы', en: 'Orders' },
  tab_inbox: { hy: 'Մուտքային', ru: 'Входящие', en: 'Inbox' },

  // catalog
  search: { hy: 'Որոնում՝ պանիր, сыр, panir…', ru: 'Поиск: сыр, պանիր, panir…', en: 'Search: cheese, պանիր, сыр…' },
  all: { hy: 'Բոլորը', ru: 'Все', en: 'All' },
  offers_only: { hy: 'Սակարկելի', ru: 'Можно торговаться', en: 'Open to offers' },
  haggle: { hy: 'Սակարկում', ru: 'Торг', en: 'Offers' },
  from: { hy: 'սկսած', ru: 'от', en: 'from' },
  found: { hy: 'Գտնվել է', ru: 'Найдено', en: 'Found' },
  nothing: { hy: 'Ոչինչ չգտնվեց', ru: 'Ничего не нашли', en: 'Nothing found' },
  out_of_stock: { hy: 'Առկա չէ', ru: 'Нет в наличии', en: 'Out of stock' },
  min: { hy: 'նվազ.', ru: 'мин.', en: 'min' },
  add_to_cart: { hy: 'Զամբյուղ', ru: 'В корзину', en: 'Add' },
  in_cart: { hy: 'Զամբյուղում', ru: 'В корзине', en: 'In cart' },

  // cart
  cart_empty: { hy: 'Զամբյուղը դատարկ է', ru: 'Корзина пуста', en: 'Your cart is empty' },
  my_price: { hy: 'Իմ գինը', ru: 'Моя цена', en: 'My price' },
  offer_price: { hy: 'Առաջարկել գին', ru: 'Предложить цену', en: 'Offer a price' },
  remove_offer: { hy: 'Հեռացնել առաջարկը', ru: 'Убрать предложение', en: 'Remove offer' },
  offer_hint: {
    hy: 'Սակարկում՝ տողի գումարը սկսած',
    ru: 'Торг возможен при сумме строки от',
    en: 'Offers possible from a line total of',
  },
  subtotal: { hy: 'Ապրանքներ', ru: 'Товары', en: 'Goods' },
  discount: { hy: 'Զեղչ', ru: 'Скидка', en: 'Discount' },
  delivery: { hy: 'Առաքում', ru: 'Доставка', en: 'Delivery' },
  free: { hy: 'անվճար', ru: 'бесплатно', en: 'free' },
  total: { hy: 'Ընդամենը', ru: 'Итого', en: 'Total' },
  delivery_on: { hy: 'Առաքում', ru: 'Доставка', en: 'Delivery' },
  missing_to_min: { hy: 'Մինչև նվազագույն պատվերը պակասում է', ru: 'До минимального заказа не хватает', en: 'Below minimum order by' },
  address: { hy: 'Հասցե', ru: 'Адрес', en: 'Address' },
  send_all: { hy: 'Ուղարկել բոլոր պատվերները', ru: 'Отправить все заказы', en: 'Send all orders' },
  sent: { hy: 'Պատվերներն ուղարկված են', ru: 'Заказы отправлены', en: 'Orders sent' },

  // orders
  orders_empty: { hy: 'Պատվերներ դեռ չկան', ru: 'Заказов пока нет', en: 'No orders yet' },
  inbox_empty: { hy: 'Ամեն ինչ արված է', ru: 'Всё обработано', en: 'All caught up' },
  needs_you: { hy: 'Սպասում է ձեզ', ru: 'Ждёт вас', en: 'Waiting for you' },
  back: { hy: 'Հետ', ru: 'Назад', en: 'Back' },
  qty: { hy: 'Քանակ', ru: 'Кол-во', en: 'Qty' },
  price: { hy: 'Գին', ru: 'Цена', en: 'Price' },
  sum: { hy: 'Գումար', ru: 'Сумма', en: 'Amount' },
  paid: { hy: 'Վճարված', ru: 'Оплачен', en: 'Paid' },
  unpaid: { hy: 'Չվճարված', ru: 'Не оплачен', en: 'Unpaid' },
  negotiation: { hy: 'Սակարկում', ru: 'Торг', en: 'Negotiation' },
  your_turn: { hy: 'Ձեր հերթն է', ru: 'Ваш ход', en: 'Your turn' },
  their_turn: { hy: 'Սպասում ենք պատասխանի', ru: 'Ждём ответа', en: 'Waiting for the other side' },
  answer_until: { hy: 'Պատասխանել մինչև', ru: 'Ответить до', en: 'Answer by' },
  rounds_left: { hy: 'Մնացած քայլեր', ru: 'Осталось ходов', en: 'Rounds left' },
  side_buyer: { hy: 'Գնորդ', ru: 'Покупатель', en: 'Buyer' },
  side_seller: { hy: 'Վաճառող', ru: 'Продавец', en: 'Seller' },
  autopilot: { hy: 'Վաճառողի ավտոպատասխան', ru: 'Автоответ продавца', en: 'Seller autopilot' },
  accept: { hy: 'Ընդունել', ru: 'Принять', en: 'Accept' },
  decline: { hy: 'Մերժել', ru: 'Отклонить', en: 'Decline' },
  counter: { hy: 'Հակաառաջարկ', ru: 'Встречная', en: 'Counter' },
  send_answer: { hy: 'Ուղարկել պատասխանը', ru: 'Отправить ответ', en: 'Send answer' },
  discount_offer: { hy: 'Զեղչ ամբողջ պատվերի վրա', ru: 'Скидка на весь заказ', en: 'Discount on the whole order' },
  fix_price: { hy: 'Ամրագրել գինը 30 օրով', ru: 'Закрепить цену на 30 дней', en: 'Fix price for 30 days' },
  price_fixed: { hy: 'Գինն ամրագրված է', ru: 'Цена закреплена', en: 'Price fixed' },
  confirmed_qty: { hy: 'Հաստատված', ru: 'Подтверждено', en: 'Confirmed' },
  reorder_done: { hy: 'Ապրանքները զամբյուղում են', ru: 'Товары добавлены в корзину', en: 'Items added to the cart' },
  cancel_reason_offer_expired: {
    hy: 'Առաջարկին ժամանակին չպատասխանեցին',
    ru: 'На предложение не ответили вовремя',
    en: 'The offer was not answered in time',
  },

  // redesign: informative states
  suppliers: { hy: 'մատակարար', ru: 'поставщ.', en: 'suppliers' },
  items: { hy: 'ապրանք', ru: 'поз.', en: 'items' },
  go_cart: { hy: 'Զամբյուղ', ru: 'В корзину', en: 'Cart' },
  quick_reorder: { hy: 'Արագ կրկնել', ru: 'Быстрый повтор', en: 'Quick reorder' },
  to_min: { hy: 'Մինչև նվազագույնը', ru: 'До минимума', en: 'To minimum' },
  to_free: { hy: 'Մինչև անվճար առաքում', ru: 'До бесплатной доставки', en: 'To free delivery' },
  free_reached: { hy: 'Առաքումն անվճար է', ru: 'Доставка бесплатно', en: 'Free delivery' },
  min_order: { hy: 'նվազ.', ru: 'мин.', en: 'min' },
  saving: { hy: 'Սակարկված', ru: 'Выторговано', en: 'Saved' },
  buyer_discount: { hy: 'Զեղչ գնորդին', ru: 'Скидка покупателю', en: 'Discount given' },
  if_accepted: { hy: 'Եթե ընդունեն', ru: 'Если примут', en: 'If accepted' },
  per_line: { hy: 'տողի վրա', ru: 'на строке', en: 'on the line' },
  list_price: { hy: 'Ցուցակային', ru: 'Каталог', en: 'List' },
  you: { hy: 'Դուք', ru: 'Вы', en: 'You' },
  them_seller: { hy: 'Վաճառող', ru: 'Продавец', en: 'Seller' },
  them_buyer: { hy: 'Գնորդ', ru: 'Покупатель', en: 'Buyer' },
  agreed_at: { hy: 'Համաձայնեցին', ru: 'Сошлись на', en: 'Agreed at' },
  left: { hy: 'մնաց', ru: 'осталось', en: 'left' },
  overdue: { hy: 'ժամկետն անցել է', ru: 'срок вышел', en: 'overdue' },
  h: { hy: 'ժ', ru: 'ч', en: 'h' },
  m: { hy: 'ր', ru: 'мин', en: 'm' },
  today_orders: { hy: 'Պատվերներ', ru: 'Заказов', en: 'Orders' },
  turnover: { hy: 'Գումար', ru: 'На сумму', en: 'Value' },
  waiting_you: { hy: 'Սպասում են ձեզ', ru: 'Ждут вас', en: 'Waiting for you' },
  sec_answer: { hy: 'Պատասխանել սակարկմանը', ru: 'Ответить на торг', en: 'Answer offers' },
  sec_confirm: { hy: 'Հաստատել', ru: 'Подтвердить', en: 'To confirm' },
  sec_deliver: { hy: 'Առաքել', ru: 'Отгрузить', en: 'To deliver' },
  sec_paid: { hy: 'Սպասում են վճարման', ru: 'Ждут оплаты', en: 'Awaiting payment' },
  sec_action: { hy: 'Սպասում են ձեզ', ru: 'Требуют действия', en: 'Needs you' },
  sec_active: { hy: 'Ընթացքում', ru: 'В работе', en: 'In progress' },
  sec_done: { hy: 'Ավարտված', ru: 'Завершённые', en: 'Finished' },
  buyers: { hy: 'Գնորդներ', ru: 'Покупатели', en: 'Buyers' },
  sellers: { hy: 'Վաճառողներ', ru: 'Продавцы', en: 'Sellers' },
  platform: { hy: 'Հարթակ', ru: 'Платформа', en: 'Platform' },
  offer_sent_hint: {
    hy: 'Վաճառողը կպատասխանի մինչև',
    ru: 'Продавец ответит до',
    en: 'The seller answers by',
  },
  between: { hy: 'Ձեր գինը', ru: 'Ваша цена', en: 'Your price' },
  more: { hy: 'ևս', ru: 'ещё', en: 'more' },
} satisfies Record<string, T3>

export const ACTIONS: Record<string, T3> = {
  confirm: { hy: 'Հաստատել', ru: 'Подтвердить', en: 'Confirm' },
  reject: { hy: 'Մերժել', ru: 'Отклонить', en: 'Reject' },
  ship: { hy: 'Ճանապարհին է', ru: 'Отправлен', en: 'Shipped' },
  deliver: { hy: 'Առաքված է', ru: 'Доставлен', en: 'Delivered' },
  accept: { hy: 'Ընդունել առաքումը', ru: 'Принять поставку', en: 'Accept delivery' },
  cancel: { hy: 'Չեղարկել', ru: 'Отменить', en: 'Cancel' },
  mark_paid: { hy: 'Վճարված է', ru: 'Оплачен', en: 'Mark paid' },
  reorder: { hy: 'Կրկնել պատվերը', ru: 'Повторить заказ', en: 'Reorder' },
}

export const SOURCES: Record<string, T3> = {
  tier: { hy: 'մեծածախ', ru: 'опт', en: 'volume' },
  agreement: { hy: 'պայմանագրային', ru: 'по контракту', en: 'contract' },
  negotiated: { hy: 'սակարկված', ru: 'после торга', en: 'negotiated' },
}

// What to do next (next_step from the API): label + whether it is urgent
export const STEPS: Record<string, T3> = {
  answer_offer: { hy: 'Պատասխանել առաջարկին', ru: 'Ответьте на предложение цены', en: 'Answer the price offer' },
  answer_counter: { hy: 'Վաճառողն առաջարկել է իր գինը', ru: 'Продавец предложил свою цену', en: 'The seller countered' },
  confirm: { hy: 'Հաստատեք պատվերը', ru: 'Подтвердите заказ', en: 'Confirm the order' },
  deliver: { hy: 'Առաքեք պատվերը', ru: 'Отгрузите заказ', en: 'Deliver the order' },
  accept_delivery: { hy: 'Ստուգեք և ընդունեք առաքումը', ru: 'Проверьте и примите поставку', en: 'Check and accept the delivery' },
  mark_paid: { hy: 'Նշեք վճարումը', ru: 'Отметьте оплату', en: 'Mark the payment' },
}

export const STAGES: Record<string, T3> = {
  negotiating: { hy: 'Սակարկում', ru: 'Торг', en: 'Offer' },
  placed: { hy: 'Ուղարկված', ru: 'Отправлен', en: 'Sent' },
  confirmed: { hy: 'Հաստատված', ru: 'Подтверждён', en: 'Confirmed' },
  delivering: { hy: 'Ճանապարհին', ru: 'В пути', en: 'On the way' },
  delivered: { hy: 'Առաքված', ru: 'Доставлен', en: 'Delivered' },
  accepted: { hy: 'Ընդունված', ru: 'Принят', en: 'Accepted' },
}

export const STATUSES: Record<string, T3> = {
  negotiating: { hy: 'Սակարկում', ru: 'Торг', en: 'Negotiating' },
  placed: { hy: 'Նոր', ru: 'Новый', en: 'New' },
  confirmed: { hy: 'Հաստատված', ru: 'Подтверждён', en: 'Confirmed' },
  rejected: { hy: 'Մերժված', ru: 'Отклонён', en: 'Rejected' },
  cancelled: { hy: 'Չեղարկված', ru: 'Отменён', en: 'Cancelled' },
  delivering: { hy: 'Ճանապարհին', ru: 'В пути', en: 'On the way' },
  delivered: { hy: 'Առաքված', ru: 'Доставлен', en: 'Delivered' },
  disputed: { hy: 'Բողոք', ru: 'Претензия', en: 'Disputed' },
  accepted: { hy: 'Ավարտված', ru: 'Завершён', en: 'Completed' },
}

// Problem codes from the API (cart, checkout, negotiation)
export const PROBLEMS: Record<string, T3> = {
  min_order_not_reached: { hy: 'Նվազագույն պատվերը չի հասել', ru: 'Не набран минимальный заказ', en: 'Minimum order not reached' },
  out_of_stock: { hy: 'Առկա չէ', ru: 'Нет в наличии', en: 'Out of stock' },
  product_archived: { hy: 'Ապրանքը հանված է', ru: 'Товар снят с продажи', en: 'No longer sold' },
  bad_qty: { hy: 'Սխալ քանակ', ru: 'Неверное количество', en: 'Invalid quantity' },
  no_delivery_to_district: { hy: 'Ձեր թաղամաս չեն առաքում', ru: 'Не доставляют в ваш район', en: 'No delivery to your district' },
  seller_unavailable: { hy: 'Վաճառողը հասանելի չէ', ru: 'Продавец недоступен', en: 'Seller unavailable' },
  offers_not_allowed: { hy: 'Այս ապրանքի համար սակարկում չկա', ru: 'На этот товар нельзя торговаться', en: 'No offers on this product' },
  not_allowed_to_negotiate: { hy: 'Ձեզ սակարկել չի թույլատրվում', ru: 'Вам нельзя торговаться', en: 'You may not negotiate' },
  offer_not_below_price: { hy: 'Առաջարկը պետք է ցածր լինի գնից', ru: 'Предложение должно быть ниже цены', en: 'Offer must be below the price' },
  offer_too_low: { hy: 'Առաջարկը չափազանց ցածր է', ru: 'Слишком низкое предложение', en: 'Offer is too low' },
  line_too_small_for_offer: { hy: 'Տողի գումարը փոքր է սակարկման համար', ru: 'Сумма строки мала для торга', en: 'Line too small to negotiate' },
  offer_must_increase: { hy: 'Նոր առաջարկը պետք է բարձր լինի նախորդից', ru: 'Новое предложение должно быть выше прежнего', en: 'New offer must be higher' },
  offer_not_below_counter: { hy: 'Ընդունեք վաճառողի գինը', ru: 'Просто примите цену продавца', en: 'Just accept the counter' },
  counter_not_below_price: { hy: 'Պետք է ցածր լինի ցուցակային գնից', ru: 'Должна быть ниже цены каталога', en: 'Must be below the list price' },
  counter_not_above_offer: { hy: 'Ընդունեք գնորդի առաջարկը', ru: 'Просто примите предложение покупателя', en: 'Just accept the offer' },
  counter_must_decrease: { hy: 'Պետք է ցածր լինի նախորդից', ru: 'Должна быть ниже прежней', en: 'Must be lower than before' },
  no_rounds_left: { hy: 'Քայլերը սպառված են', ru: 'Ходы закончились', en: 'No rounds left' },
  over_staff_limit: { hy: 'Գերազանցում է ձեր սահմանաչափը', ru: 'Больше вашего лимита — нужен владелец', en: 'Over your limit' },
  line_and_order_offers_together: { hy: 'Ընտրեք մեկ տեսակի առաջարկ', ru: 'Либо цены по строкам, либо скидка на заказ', en: 'Either line offers or an order discount' },
  order_too_small_for_offer: { hy: 'Պատվերը փոքր է սակարկման համար', ru: 'Заказ мал для торга', en: 'Order too small to negotiate' },
  bad_discount: { hy: 'Սխալ զեղչ', ru: 'Неверная скидка', en: 'Invalid discount' },
  cart_empty: { hy: 'Զամբյուղը դատարկ է', ru: 'Корзина пуста', en: 'Cart is empty' },
  address_required: { hy: 'Նշեք հասցեն', ru: 'Укажите адрес', en: 'Address required' },
  not_your_turn: { hy: 'Հիմա ձեր հերթը չէ', ru: 'Сейчас не ваш ход', en: 'Not your turn' },
  negotiation_expired: { hy: 'Ժամկետն անցել է', ru: 'Срок ответа истёк', en: 'Time is up' },
  invalid_transition: { hy: 'Պատվերն արդեն փոխվել է', ru: 'Заказ уже изменился — обновите', en: 'The order changed, refresh' },
}

export type TextKey = keyof typeof TEXTS

export const LangContext = createContext<{ lang: Lang; setLang: (l: Lang) => void }>({
  lang: 'hy',
  setLang: () => {},
})

export function useLang(): Lang {
  return useContext(LangContext).lang
}

export function useT() {
  const { lang } = useContext(LangContext)
  return (key: TextKey) => TEXTS[key][lang]
}

/** Human text for an API problem code, falling back to the code itself. */
export function problemText(code: string, lang: Lang): string {
  return PROBLEMS[code]?.[lang] ?? code
}
