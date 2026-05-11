from __future__ import annotations

import operator
from typing import Any, Callable

from .. import repository as repo

OPS: dict[str, Callable[[float, float], bool]] = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
}


def evaluate_snapshot(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    rules = [r for r in repo.list_rules(enabled_only=True) if r["code"] == snapshot.get("code")]
    alerts: list[dict[str, Any]] = []
    for rule in rules:
        metric = rule["metric"]
        value = snapshot.get(metric)
        if value is None:
            continue
        try:
            value_num = float(value)
            threshold = float(rule["threshold"])
        except (TypeError, ValueError):
            continue
        op = OPS.get(rule["operator"])
        if not op:
            continue
        if op(value_num, threshold):
            template = rule.get("message_template") or "{code} 触发规则 {rule_name}: {metric}={value}"
            try:
                message = template.format(
                    code=snapshot.get("code"),
                    name=snapshot.get("name"),
                    metric=metric,
                    value=value_num,
                    threshold=threshold,
                    rule_name=rule.get("rule_name"),
                )
            except Exception:  # noqa: BLE001
                message = f"{snapshot.get('code')} 触发规则 {rule.get('rule_name')}: {metric}={value_num}"
            alerts.append(
                {
                    "code": snapshot.get("code"),
                    "level": rule.get("level"),
                    "action": rule.get("action"),
                    "message": message,
                    "raw_data": {"snapshot": snapshot, "rule": rule},
                }
            )
    return alerts


def build_deterministic_recommendation(snapshots: list[dict[str, Any]], alerts: list[dict[str, Any]]) -> str:
    """没有配置 OpenRouter 时的本地规则解释。"""
    if not snapshots:
        return "暂无行情数据。请先运行一次监控，或在 manual_quotes 表/页面中录入人工行情。"

    lines = ["# ETF盯盘报告", "", "## 今日结论"]
    danger = [a for a in alerts if a.get("level") == "danger"]
    warning = [a for a in alerts if a.get("level") == "warning"]
    info = [a for a in alerts if a.get("level") == "info"]

    if danger:
        lines.append("出现高风险信号：优先停止买入，必要时考虑减仓或等待溢价回落。")
    elif warning:
        lines.append("出现谨慎信号：暂停对应标的买入，继续观察。")
    elif info:
        lines.append("出现可观察加仓信号：只适合小额分批，不建议一次性重仓。")
    else:
        lines.append("未触发加仓或减仓信号，建议继续观察，不操作。")

    lines.append("")
    lines.append("## 最新快照")
    for s in snapshots:
        lines.append(
            f"- {s.get('code')} {s.get('name') or ''}: 价格={_fmt(s.get('price'))}, "
            f"净值/估值={_fmt(s.get('nav_est'))}, 溢价率={_fmt(s.get('premium_rate'))}%, "
            f"成交额={_fmt(s.get('volume_amount'))}, 来源={s.get('source')}"
        )

    lines.append("")
    lines.append("## 触发规则")
    if alerts:
        for a in alerts:
            lines.append(f"- [{a.get('level')}] {a.get('message')}")
    else:
        lines.append("- 无")

    lines.append("")
    lines.append("## 操作提醒")
    lines.append("- 本系统只做提醒，不自动交易。真正下单前请核对券商行情、IOPV/估值、基金公告和成交额。")
    return "\n".join(lines)


def _fmt(value: Any) -> str:
    if value is None:
        return "N/A"
    try:
        return f"{float(value):.4f}"
    except Exception:  # noqa: BLE001
        return str(value)
