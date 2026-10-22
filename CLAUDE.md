# QB — закупки для HoReCa в Армении

Маркетплейс: оптовики, магазины и производители продают продукты и расходники, кафе и рестораны покупают.
Одна корзина на нескольких продавцов, торг (предложить цену, автопилот продавца), позже — счета и путевые листы
в системе КГД. Продукт и рынок — [docs/01-research-and-concept.md](docs/01-research-and-concept.md),
экраны, торг, модель данных и план — [docs/02-mvp.md](docs/02-mvp.md),
принципы, флоу, модули и правила слоёв — [docs/03-architecture.md](docs/03-architecture.md).

Языки интерфейса и каталога: армянский (`hy`), русский (`ru`), английский (`en`). Валюта — AMD, целые драмы.
Пользователю всё пишем по-русски; код, комментарии и коммиты — по-английски.

## Стек (как в Gumar)

| Слой | Выбор |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0 (async, asyncpg), Alembic, Pydantic v2 |
| БД / очередь | PostgreSQL 16 + `pg_trgm`, Redis 7 + RQ |
| Планировщик | APScheduler, процесс `scheduler`, тик раз в минуту (истечение торгов, автоприёмка) |
| Telegram | aiogram 3, профиль compose `bot` |
| Frontend | React 18 + Vite + TypeScript, PWA (`vite-plugin-pwa`, injectManifest) |
| Инфра | Docker Compose |

## Порты (не пересекаются с Gumar)

| Сервис | Порт |
|---|---|
| PWA (nginx, `/api` → API) | http://localhost:8090 |
| API напрямую | http://localhost:8010 (docs: `/docs`) |
| Vite dev | http://localhost:5180 |
| PostgreSQL | 5435 (`qb` и `qb_test`) |
| Redis | 6381 |

## Команды

```bash
cp .env.example .env
docker compose up -d --build                     # всё; api сам применяет миграции
docker compose run --rm api python -m app.seed   # демо-данные (вход: DEV_LOGIN, *@qb.local)

# тесты и линтер бэкенда (база qb_test в том же контейнере db)
docker compose run --rm -v "$PWD/backend:/app" -e TEST_DATABASE_URL=postgresql+asyncpg://qb:qb@db:5432/qb_test api pytest -q
docker compose run --rm -v "$PWD/backend:/app" api sh -c "ruff check . && ruff format --check ."

# новая миграция после правки моделей
docker compose run --rm -v "$PWD/backend:/app" api alembic revision --autogenerate -m "..."
docker compose run --rm -v "$PWD/backend:/app" api alembic check

# фронтенд
cd web && npm install && npm run dev   # http://localhost:5180, проксирует /api на :8010
npm test && npm run lint && npx tsc -b
```

## Устройство бэкенда

```
backend/app/
├── models/        # SQLAlchemy: identity, catalog, orders, negotiation, platform (outbox, idempotency)
├── domain/        # чистые функции: pricing, orders (статусы, суммы, дата доставки), negotiation (правила,
│                  # автопилот), commission — без базы и HTTP; из app.models берут только enum
├── services/      # работа с базой: cart, checkout, orders, negotiation, agreements, prices — без commit
├── platform/      # authz (Actor + таблица прав), errors, clock, outbox, idempotency
├── api/           # auth, catalog, cart (+ /checkout), orders (+ торг, /agreements); commit здесь
├── auth/          # JWT, current_user, current_actor (заголовок X-Org-Id)
├── core/          # search (search_text + транслит hy/ru → latin)
├── workers/       # outbox-диспетчер (пока только лог), очередь RQ "qb"
├── bot/           # Telegram-бот (пока только /start)
├── scheduler.py   # истечение торгов, автоприёмка 48 ч, истечение контрактов, outbox каждые 2 с
└── seed.py        # демо-данные: 3 продавца, 2 заведения, 13 товаров
```

## Правила

- **Деньги** — `bigint` в целых драмах (`Amd`), количество — `numeric(12,3)` (`Qty`). Ставки — в базисных пунктах (100 bp = 1%).
- **Enum** хранятся как VARCHAR + CHECK (`str_enum`). Автогенерация Alembic дублирует эти CHECK — после
  `--autogenerate` удаляйте строки `sa.CheckConstraint("<col> IN (...)")`, колонка `sa.Enum(..., create_constraint=True)`
  создаёт ограничение сама.
- Автогенерация не видит расширения и отдельные последовательности: `pg_trgm` и `order_number_seq` созданы вручную в `0001`.
- В строках заказа цена и название — **снимки** на момент заказа; комиссия и источник клиента копируются в заказ при приёмке.
- Цена для покупателя — `domain/pricing.resolve_unit_price`: договорённая в торге окончательна, иначе самая низкая из
  каталожной, объёмного порога и контрактной. В строке заказа `list_price_amd` — цена **до** торга; отклонённое
  предложение оставляет её.
- **Транзакции:** сервисы не делают `commit`, его делает вызывающий (API, планировщик). Порядок блокировок:
  orders → negotiations → order_lines.
- **Торг:** первое предложение приходит с checkout (`cart_items.offer_price_amd` или скидка на заказ). Ответ на
  каждую открытую строку: принять / отклонить / встречная. Нет ответа в срок → заказ отменён (`offer_expired`).
- **Ошибки** сервисов — `platform/errors.py` → `{"code", "message", "details": {"problems": [...]}}`; тексты
  для кодов — `PROBLEMS` в `web/src/i18n.ts`.
- **Уведомлений пока нет** (канал не выбран): события копятся в `outbox`, экраны продавца обновляются опросом.
- Поиск: `products.search_text` собирается `core/search.build_search_text` из всех языков + транслитерации;
  обновляйте его при каждом изменении названия.

## Дизайн-система (web/src/styles.css)

Метафора — **кухонный чек на «пассе»**: заказ едет по станциям, как тикет на кухне.
- **Цвета-токены:** бумага `--paper`, чек `--ticket`, бренд гранат `--brand`, янтарь `--lamp` — срочно и таймеры,
  зелень `--herb` — выгода и «готово», синий `--seller` — сторона продавца. Тёмная тема — те же токены.
- **Поверхности:** `.ticket` (+ `.perf` — перфорация сверху), пунктир `.rule`; числа всегда `.num` (табличные цифры).
- **Ключевые компоненты:** `OrderMeter` (минимум и бесплатная доставка на одной шкале), `PriceDial` (торг ползунком
  с пресетами и суммой на строке), `ConvergenceTrack` (цены сторон сходятся на одной линии), `StageRail` (этапы заказа
  с временем), баннер `.next` с `Countdown` (что делать дальше и до какого времени), полоса корзины `.cartbar`.
- **API для экранов:** заказ отдаёт `next_step`, `deadline`, `saving_amd`, `events`; список — то же + `preview`.
- **Движение:** короткое для частого (`--t-fast`), пружина `--spring` для появления объектов; `prefers-reduced-motion`
  отключает анимации.

## Не проверено

- Service worker не регистрируется во встроенном браузере Claude (у Gumar так же) — проверять установку PWA в Chrome/Safari.
