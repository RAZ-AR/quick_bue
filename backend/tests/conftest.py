import os

os.environ["ENV"] = "test"
os.environ["JWT_SECRET"] = "test-secret-0123456789abcdef0123456789"
os.environ["DEV_LOGIN"] = "true"
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://qb:qb@localhost:5435/qb_test"
)

from collections.abc import AsyncIterator  # noqa: E402

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402

from app.config import Settings, get_settings  # noqa: E402
from app.db import get_session  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Base  # noqa: E402

# Tests must not depend on a developer's local .env
Settings.model_config["env_file"] = None
get_settings.cache_clear()


_schema_ready = False


@pytest.fixture
async def sessionmaker() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    global _schema_ready
    engine = create_async_engine(get_settings().database_url)
    async with engine.begin() as conn:
        if not _schema_ready:
            # Rebuild once per run: create_all does not add columns to existing tables
            await conn.execute(text("DROP SCHEMA public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            await conn.run_sync(Base.metadata.create_all)
            _schema_ready = True
    yield async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
        await conn.execute(text(f"TRUNCATE {tables} CASCADE"))
    await engine.dispose()


@pytest.fixture
async def client(sessionmaker) -> AsyncIterator[AsyncClient]:
    app = create_app()

    async def _session() -> AsyncIterator[AsyncSession]:
        async with sessionmaker() as s:
            yield s

    app.dependency_overrides[get_session] = _session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def seeded(sessionmaker, monkeypatch) -> None:
    """Demo data from app.seed, written into the test database."""
    import app.seed as seed_module

    monkeypatch.setattr(seed_module, "get_sessionmaker", lambda: sessionmaker)
    await seed_module.seed()


async def login(client: AsyncClient, email: str) -> dict[str, str]:
    r = await client.post("/auth/dev-login", json={"email": email})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
