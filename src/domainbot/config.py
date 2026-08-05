from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "production"
    app_name: str = "domainbot"
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    log_format: str = "json"

    telegram_bot_token: str = ""
    allowed_chat_ids: str = ""

    database_url: str = "postgresql+asyncpg://domainbot:CHANGE_ME@127.0.0.1:5432/domainbot"

    rdap_base_url: str = "https://rdap.verisign.com/com/v1"
    rdap_concurrency: int = 3
    rdap_connect_timeout_seconds: float = 10.0
    rdap_read_timeout_seconds: float = 20.0
    rdap_write_timeout_seconds: float = 10.0
    rdap_pool_timeout_seconds: float = 10.0
    rdap_max_attempts: int = 3
    rdap_user_agent: str = ""

    max_domains_per_command: int = 100
    max_domains_per_watch: int = 5000
    max_active_jobs_per_group: int = 1
    max_active_jobs_per_user: int = 1
    pool_domain_refresh_batch_size: int = 250
    report_message_row_limit: int = 20

    watch_timezone: str = "Europe/Istanbul"
    watch_default_day: str = "MON"
    watch_default_hour: int = 10
    watch_daily_batch_size: int = 300

    btk_base_url: str = "https://btk.monoworks.net"
    btk_batch_size: int = 5
    btk_idle_sleep_seconds: float = 30.0
    btk_batch_sleep_seconds: float = 10.0
    btk_retry_interval_seconds: float = 21600.0
    btk_connect_timeout_seconds: float = 15.0
    btk_read_timeout_seconds: float = 90.0
    btk_write_timeout_seconds: float = 10.0
    btk_pool_timeout_seconds: float = 20.0
    btk_user_agent: str = ""

    temp_report_dir: Path = Path("/var/lib/domainbot/reports")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def allowed_chat_id_set(self) -> frozenset[int]:
        if not self.allowed_chat_ids.strip():
            return frozenset()
        return frozenset(
            int(value.strip()) for value in self.allowed_chat_ids.split(",") if value.strip()
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
