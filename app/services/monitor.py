from __future__ import annotations

from typing import Any

from .. import repository as repo
from ..config import settings
from .market_data import MarketDataClient
from .rules import evaluate_snapshot, build_deterministic_recommendation
from .openrouter_agent import build_agent_prompt, call_openrouter
from .email_notifier import send_monitor_email


class MonitorService:
    def __init__(self) -> None:
        self.market = MarketDataClient()

    def run_once(self, force_agent: bool = True) -> dict[str, Any]:
        funds = repo.list_funds(active_only=True)
        snapshots: list[dict[str, Any]] = []
        alerts: list[dict[str, Any]] = []

        for fund in funds:
            snapshot = self.market.get_snapshot(fund["code"], fund.get("name") or "")
            repo.insert_snapshot(snapshot)
            snapshots.append(snapshot)

            triggered = evaluate_snapshot(snapshot)
            for alert in triggered:
                repo.insert_alert(alert)
            alerts.extend(triggered)

        positions = repo.list_positions()
        prompt = build_agent_prompt(snapshots, alerts, positions)
        report = ""
        model = "local-rules"

        if force_agent or alerts:
            try:
                report = call_openrouter(prompt)
                model = settings.openrouter_model
            except Exception as exc:  # noqa: BLE001
                report = build_deterministic_recommendation(snapshots, alerts)
                report += f"\n\n> OpenRouter 未调用成功：{exc}"
                model = "local-rules-fallback"
            repo.insert_agent_report("monitor", report, model, prompt)

        email_status = send_monitor_email(snapshots, alerts, report, model)

        return {
            "snapshots": snapshots,
            "alerts": alerts,
            "report": report,
            "model": model,
            "email": email_status,
        }
