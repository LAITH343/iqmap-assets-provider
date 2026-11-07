from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    storage_root: Path
    routing_engine_url: str = "http://127.0.0.1:8090"
    routing_engine_timeout: float = 10.0

    @field_validator("storage_root")
    @classmethod
    def resolve_storage_root(cls, value: Path) -> Path:
        return value.resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings.model_validate({})
