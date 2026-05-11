from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .config import settings
from .database import init_db
from .services.seed import seed_defaults
from .services.monitor import MonitorService
from .services.scheduler import start_scheduler, shutdown_scheduler
from . import repository as repo

APP_DIR = Path(__file__).resolve().parent

app = FastAPI(title="ETF Agent Monitor", version="1.0.0")
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")
monitor_service = MonitorService()


class FundIn(BaseModel):
    code: str
    name: str
    category: str = "ETF"
    market: str = ""
    strategy_role: str = "观察"
    note: str = ""
    is_active: int = 1


class PositionIn(BaseModel):
    code: str
    quantity: float = 0
    cost_price: float = 0
    total_cost: float = 0
    note: str = ""


class ManualQuoteIn(BaseModel):
    code: str
    price: float | None = None
    nav_est: float | None = None
    premium_rate: float | None = Field(default=None, description="单位：%，例如 1.2 表示 1.2%")
    volume_amount: float | None = None
    change_pct: float | None = None
    note: str = ""


@app.on_event("startup")
def on_startup() -> None:
    settings.ensure_dirs()
    init_db()
    seed_defaults()
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown() -> None:
    shutdown_scheduler()


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "funds": repo.list_funds(),
            "positions": repo.list_positions(),
            "snapshots": repo.latest_snapshots(),
            "alerts": repo.list_alerts(limit=20),
            "reports": repo.list_agent_reports(limit=5),
            "settings": settings,
        },
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/funds")
def api_funds(active_only: bool = False) -> list[dict[str, Any]]:
    return repo.list_funds(active_only=active_only)


@app.post("/api/funds")
def api_add_fund(data: FundIn) -> dict[str, str]:
    repo.upsert_fund(**data.model_dump())
    return {"status": "ok"}


@app.get("/api/positions")
def api_positions() -> list[dict[str, Any]]:
    return repo.list_positions()


@app.post("/api/positions")
def api_upsert_position(data: PositionIn) -> dict[str, str]:
    repo.upsert_position(**data.model_dump())
    return {"status": "ok"}


@app.get("/api/snapshots/latest")
def api_latest_snapshots() -> list[dict[str, Any]]:
    return repo.latest_snapshots()


@app.post("/api/manual-quotes")
def api_manual_quote(data: ManualQuoteIn) -> dict[str, Any]:
    row_id = repo.insert_manual_quote(data.model_dump())
    return {"status": "ok", "id": row_id}


@app.post("/api/monitor/run")
def api_run_monitor(force_agent: bool = True) -> dict[str, Any]:
    return monitor_service.run_once(force_agent=force_agent)


@app.get("/api/alerts")
def api_alerts(limit: int = 50, unread_only: bool = False) -> list[dict[str, Any]]:
    return repo.list_alerts(limit=limit, unread_only=unread_only)


@app.post("/api/alerts/{alert_id}/read")
def api_mark_alert_read(alert_id: int) -> dict[str, str]:
    if alert_id <= 0:
        raise HTTPException(status_code=400, detail="invalid alert_id")
    repo.mark_alert_read(alert_id)
    return {"status": "ok"}


@app.get("/api/reports")
def api_reports(limit: int = 20) -> list[dict[str, Any]]:
    return repo.list_agent_reports(limit=limit)
