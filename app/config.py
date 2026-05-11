from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_path: str = os.getenv("DATABASE_PATH", "./data/etf_monitor.db")
    openrouter_api_key: str | None = os.getenv("OPENROUTER_API_KEY") or None
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")
    openrouter_site_url: str = os.getenv("OPENROUTER_SITE_URL", "http://localhost:8000")
    openrouter_app_name: str = os.getenv("OPENROUTER_APP_NAME", "ETF Agent Monitor")
    scheduler_enabled: bool = os.getenv("SCHEDULER_ENABLED", "true").lower() in {"1", "true", "yes", "y"}
    scheduler_timezone: str = os.getenv("SCHEDULER_TIMEZONE", "Asia/Shanghai")
    scheduler_hours: str = os.getenv("SCHEDULER_HOURS", "10,14")
    scheduler_minute: int = int(os.getenv("SCHEDULER_MINUTE", "30"))
    debug: bool = os.getenv("DEBUG", "false").lower() in {"1", "true", "yes", "y"}

    def ensure_dirs(self) -> None:
        db_path = Path(self.database_path)
        if db_path.parent and str(db_path.parent) != ".":
            db_path.parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
