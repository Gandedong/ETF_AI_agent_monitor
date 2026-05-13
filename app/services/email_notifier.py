from __future__ import annotations

import smtplib
from datetime import datetime
from email.message import EmailMessage
from typing import Any

from ..config import settings

LEVEL_PRIORITY = {
    "info": 1,
    "warning": 2,
    "danger": 3,
}


def send_monitor_email(
    snapshots: list[dict[str, Any]],
    alerts: list[dict[str, Any]],
    report: str = "",
    model: str = "",
) -> dict[str, Any]:
    """Send an SMTP email for triggered monitor alerts.

    The function returns a structured status instead of raising so the monitor
    run will not fail just because the notification channel is unavailable.
    """
    recipients = _parse_recipients(settings.email_to)
    if not settings.email_enabled:
        return {"status": "skipped", "reason": "email_disabled"}
    if not settings.email_smtp_host:
        return {"status": "skipped", "reason": "missing_smtp_host"}
    if not settings.email_from:
        return {"status": "skipped", "reason": "missing_email_from"}
    if not recipients:
        return {"status": "skipped", "reason": "missing_email_to"}

    matched_alerts = _filter_alerts(alerts)
    if not matched_alerts:
        return {"status": "skipped", "reason": "no_matching_alerts"}

    try:
        message = _build_message(recipients, matched_alerts, snapshots, report, model)
        _send_message(message, recipients)
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "reason": str(exc)}

    return {"status": "sent", "recipients": recipients, "alert_count": len(matched_alerts)}


def _parse_recipients(raw: str) -> list[str]:
    normalized = raw.replace(";", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def _enabled_levels() -> set[str]:
    return {
        item.strip().lower()
        for item in settings.email_alert_levels.split(",")
        if item.strip()
    }


def _filter_alerts(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enabled_levels = _enabled_levels()
    if not enabled_levels:
        return alerts
    return [alert for alert in alerts if str(alert.get("level", "")).lower() in enabled_levels]


def _build_message(
    recipients: list[str],
    alerts: list[dict[str, Any]],
    snapshots: list[dict[str, Any]],
    report: str,
    model: str,
) -> EmailMessage:
    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = ", ".join(recipients)
    message["Subject"] = _build_subject(alerts)
    message.set_content(_build_body(alerts, snapshots, report, model))
    return message


def _build_subject(alerts: list[dict[str, Any]]) -> str:
    highest = max(
        alerts,
        key=lambda alert: LEVEL_PRIORITY.get(str(alert.get("level", "")).lower(), 0),
    )
    level = str(highest.get("level") or "alert")
    codes = sorted({str(alert.get("code")) for alert in alerts if alert.get("code")})
    code_text = ",".join(codes[:4])
    if len(codes) > 4:
        code_text += f"等{len(codes)}只"
    return f"[{settings.email_subject_prefix}][{level}] {len(alerts)}条提醒 {code_text}".strip()


def _build_body(
    alerts: list[dict[str, Any]],
    snapshots: list[dict[str, Any]],
    report: str,
    model: str,
) -> str:
    lines = [
        "ETF/LOF 盯盘提醒",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 触发提醒",
    ]
    for alert in alerts:
        lines.append(
            f"- [{alert.get('level')}] {alert.get('code')} "
            f"{alert.get('action')}: {alert.get('message')}"
        )

    lines.extend(["", "## 最新快照"])
    for snapshot in snapshots:
        lines.append(
            "- "
            f"{snapshot.get('code')} {snapshot.get('name') or ''}: "
            f"价格={_fmt(snapshot.get('price'))}, "
            f"净值/估值={_fmt(snapshot.get('nav_est'))}, "
            f"溢价率={_fmt(snapshot.get('premium_rate'))}%, "
            f"成交额={_fmt(snapshot.get('volume_amount'))}, "
            f"来源={snapshot.get('source') or 'N/A'}"
        )

    if report:
        lines.extend(["", f"## Agent 报告（{model or 'unknown'}）", report])

    lines.extend(
        [
            "",
            "## 风险提示",
            "本邮件只做提醒，不自动交易；下单前请核对券商行情、IOPV/估值、基金公告和成交额。",
        ]
    )
    return "\n".join(lines)


def _fmt(value: Any) -> str:
    if value is None:
        return "N/A"
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)


def _send_message(message: EmailMessage, recipients: list[str]) -> None:
    if settings.email_smtp_use_ssl:
        with smtplib.SMTP_SSL(settings.email_smtp_host, settings.email_smtp_port, timeout=30) as smtp:
            _login_if_needed(smtp)
            smtp.send_message(message, from_addr=settings.email_from, to_addrs=recipients)
        return

    with smtplib.SMTP(settings.email_smtp_host, settings.email_smtp_port, timeout=30) as smtp:
        if settings.email_smtp_use_tls:
            smtp.starttls()
        _login_if_needed(smtp)
        smtp.send_message(message, from_addr=settings.email_from, to_addrs=recipients)


def _login_if_needed(smtp: smtplib.SMTP) -> None:
    if settings.email_smtp_username:
        smtp.login(settings.email_smtp_username, settings.email_smtp_password)
