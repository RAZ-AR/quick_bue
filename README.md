# QB

Закупки для HoReCa в Армении: оптовики, магазины и производители продают продукты и расходники,
кафе и рестораны заказывают у всех в одной корзине и могут торговаться.

- Рынок и концепция: [docs/01-research-and-concept.md](docs/01-research-and-concept.md)
- MVP — экраны, торг, модель данных, стек, план: [docs/02-mvp.md](docs/02-mvp.md)
- Принципы, флоу и архитектура: [docs/03-architecture.md](docs/03-architecture.md)
- Документы РА, регистрация по ИНН, верификация: [docs/04-documents-and-verification.md](docs/04-documents-and-verification.md)
- Вход, гостевой режим, кабинеты, две роли: [docs/05-cabinets-and-auth.md](docs/05-cabinets-and-auth.md)
- Бесплатный хостинг на Oracle Cloud: [docs/06-deploy-oracle.md](docs/06-deploy-oracle.md)
- Как запускать и устроен код: [CLAUDE.md](CLAUDE.md)

## Быстрый старт

```bash
cp .env.example .env
docker compose up -d --build
docker compose run --rm api python -m app.seed
open http://localhost:8090
```

Каталог открыт без входа. Войти — кодом на почту (в разработке код показывается на экране) или кнопками
демо-пользователей (работает, пока в `.env` стоит `DEV_LOGIN=true`). Google и Telegram включаются ключами в `.env`.
