from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"
    database_url: str = "postgresql+asyncpg://qb:qb@localhost:5435/qb"
    redis_url: str = "redis://localhost:6381/0"
    cors_origins: list[str] = ["http://localhost:5180"]

    # Auth
    jwt_secret: str = "change-me"
    jwt_ttl_days: int = 30
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""
    # Passwordless sign-in as any seeded user, for local testing only. Never in prod.
    dev_login: bool = False

    web_app_url: str = "http://localhost:8090"

    # Marketplace defaults (sellers can override most of them, see docs/02-mvp.md §6)
    offer_response_hours: int = 24
    offer_max_rounds: int = 3
    offer_min_line_amd: int = 20_000
    auto_accept_after_delivery_hours: int = 48

    @model_validator(mode="after")
    def _prod_guards(self) -> "Settings":
        if self.env == "prod" and (self.jwt_secret == "change-me" or len(self.jwt_secret) < 32):
            raise ValueError("JWT_SECRET must be a random string of 32+ chars in prod")
        if self.env == "prod" and self.dev_login:
            raise ValueError("DEV_LOGIN must be off in prod")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
