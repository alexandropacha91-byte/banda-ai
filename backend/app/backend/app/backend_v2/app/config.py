"""BANDA AI - Configuration Sécurisée"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    BANDA_SECURITY_SALT: str
    CINETPAY_API_KEY: str
    CINETPAY_SITE_ID: str
    CINETPAY_WEBHOOK_SECRET: str
    R2_ACCESS_KEY: str
    R2_SECRET_KEY: str
    R2_BUCKET_NAME: str = "banda-models"
    R2_PUBLIC_URL: str
    APP_ENV: str = "production"
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="forbid",
    )

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def database_url_async(self) -> str:
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)


@lru_cache()
def get_settings() -> Settings:
    return Settings()
