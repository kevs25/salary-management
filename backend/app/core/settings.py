from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", extra="ignore")

    database_url: str = "mysql+pymysql://salary:salary@localhost:3306/salary"
    db_pool_size: int = 10
    db_max_overflow: int = 10
    db_pool_recycle_seconds: int = 3600  # below MySQL's default wait_timeout of 8h
    sql_echo: bool = False
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
