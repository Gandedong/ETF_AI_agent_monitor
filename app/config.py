from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in {"1", "true", "yes", "y"}


def _env_int(name: str, default: str) -> int:
    return int(os.getenv(name, default))


@dataclass(frozen=True)
class Settings:
    database_path: str = os.getenv("DATABASE_PATH", "./data/etf_monitor.db")
    openrouter_api_key: str | None = os.getenv("OPENROUTER_API_KEY") or None
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")
    openrouter_site_url: str = os.getenv("OPENROUTER_SITE_URL", "http://localhost:8000")
    openrouter_app_name: str = os.getenv("OPENROUTER_APP_NAME", "ETF Agent Monitor")
    scheduler_enabled: bool = _env_bool("SCHEDULER_ENABLED", "true")
    scheduler_timezone: str = os.getenv("SCHEDULER_TIMEZONE", "Asia/Shanghai")
    scheduler_hours: str = os.getenv("SCHEDULER_HOURS", "10,14")
    scheduler_minute: int = _env_int("SCHEDULER_MINUTE", "30")
    debug: bool = _env_bool("DEBUG", "false")

    email_enabled: bool = _env_bool("EMAIL_ENABLED", "false")
    email_smtp_host: str = os.getenv("EMAIL_SMTP_HOST", "")
    email_smtp_port: int = _env_int("EMAIL_SMTP_PORT", "587")
    email_smtp_username: str = os.getenv("EMAIL_SMTP_USERNAME", "")
    email_smtp_password: str = os.getenv("EMAIL_SMTP_PASSWORD", "")
    email_smtp_use_tls: bool = _env_bool("EMAIL_SMTP_USE_TLS", "true")
    email_smtp_use_ssl: bool = _env_bool("EMAIL_SMTP_USE_SSL", "false")
    email_from: str = os.getenv("EMAIL_FROM", "")
    email_to: str = os.getenv("EMAIL_TO", "")
    email_alert_levels: str = os.getenv("EMAIL_ALERT_LEVELS", "info,warning,danger")
    email_subject_prefix: str = os.getenv("EMAIL_SUBJECT_PREFIX", "ETF盯盘提醒")

    def ensure_dirs(self) -> None:
        db_path = Path(self.database_path)
        if db_path.parent and str(db_path.parent) != ".":
            db_path.parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
