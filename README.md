# QB

Закупки для HoReCa в Армении: оптовики, магазины и производители продают продукты и расходники,
кафе и рестораны заказывают у всех в одной корзине и могут торговаться.

- Рынок и концепция: [docs/01-research-and-concept.md](docs/01-research-and-concept.md)
- MVP — экраны, торг, модель данных, стек, план: [docs/02-mvp.md](docs/02-mvp.md)
- Как запускать и устроен код: [CLAUDE.md](CLAUDE.md)

## Быстрый старт

```bash
cp .env.example .env
docker compose up -d --build
docker compose run --rm api python -m app.seed
open http://localhost:8090
```

Вход — кнопками демо-пользователей (работает, пока в `.env` стоит `DEV_LOGIN=true`).
