from __future__ import annotations

import json
from typing import Any

from .database import db_cursor, rows_to_dicts


def upsert_fund(code: str, name: str, category: str = "", market: str = "", strategy_role: str = "", note: str = "", is_active: int = 1) -> None:
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO funds(code, name, category, market, strategy_role, note, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                name=excluded.name,
                category=excluded.category,
                market=excluded.market,
                strategy_role=excluded.strategy_role,
                note=excluded.note,
                is_active=excluded.is_active,
                updated_at=CURRENT_TIMESTAMP
            """,
            (code, name, category, market, strategy_role, note, is_active),
        )


def list_funds(active_only: bool = False) -> list[dict[str, Any]]:
    sql = "SELECT * FROM funds"
    params: list[Any] = []
    if active_only:
        sql += " WHERE is_active = 1"
    sql += " ORDER BY strategy_role, code"
    with db_cursor() as cur:
        cur.execute(sql, params)
        return rows_to_dicts(cur.fetchall())


def upsert_position(code: str, quantity: float = 0, cost_price: float = 0, total_cost: float = 0, note: str = "") -> None:
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO positions(code, quantity, cost_price, total_cost, note)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                quantity=excluded.quantity,
                cost_price=excluded.cost_price,
                total_cost=excluded.total_cost,
                note=excluded.note,
                updated_at=CURRENT_TIMESTAMP
            """,
            (code, quantity, cost_price, total_cost, note),
        )


def list_positions() -> list[dict[str, Any]]:
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT p.*, f.name, f.strategy_role
            FROM positions p
            LEFT JOIN funds f ON f.code = p.code
            ORDER BY p.updated_at DESC
            """
        )
        return rows_to_dicts(cur.fetchall())


def insert_snapshot(snapshot: dict[str, Any]) -> int:
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO market_snapshots(
                code, name, price, nav_est, premium_rate, volume_amount,
                change_pct, source, raw_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot.get("code"),
                snapshot.get("name"),
                snapshot.get("price"),
                snapshot.get("nav_est"),
                snapshot.get("premium_rate"),
                snapshot.get("volume_amount"),
                snapshot.get("change_pct"),
                snapshot.get("source"),
                json.dumps(snapshot.get("raw_data", {}), ensure_ascii=False),
            ),
        )
        return int(cur.lastrowid)


def latest_snapshots() -> list[dict[str, Any]]:
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT ms.*
            FROM market_snapshots ms
            JOIN (
                SELECT code, MAX(id) AS max_id
                FROM market_snapshots
                GROUP BY code
            ) latest ON latest.max_id = ms.id
            ORDER BY ms.code
            """
        )
        return rows_to_dicts(cur.fetchall())


def latest_snapshot_for(code: str) -> dict[str, Any] | None:
    with db_cursor() as cur:
        cur.execute(
            "SELECT * FROM market_snapshots WHERE code=? ORDER BY id DESC LIMIT 1",
            (code,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def insert_manual_quote(data: dict[str, Any]) -> int:
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO manual_quotes(code, price, nav_est, premium_rate, volume_amount, change_pct, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("code"),
                data.get("price"),
                data.get("nav_est"),
                data.get("premium_rate"),
                data.get("volume_amount"),
                data.get("change_pct"),
                data.get("note", ""),
            ),
        )
        return int(cur.lastrowid)


def latest_manual_quote(code: str) -> dict[str, Any] | None:
    with db_cursor() as cur:
        cur.execute("SELECT * FROM manual_quotes WHERE code=? ORDER BY id DESC LIMIT 1", (code,))
        row = cur.fetchone()
        return dict(row) if row else None


def add_rule(code: str, rule_name: str, metric: str, operator: str, threshold: float, action: str, level: str, message_template: str, enabled: int = 1) -> None:
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO rules(code, rule_name, metric, operator, threshold, action, level, message_template, enabled)
            SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?
            WHERE NOT EXISTS (
                SELECT 1 FROM rules WHERE code=? AND rule_name=? AND metric=? AND operator=? AND threshold=? AND action=?
            )
            """,
            (
                code, rule_name, metric, operator, threshold, action, level, message_template, enabled,
                code, rule_name, metric, operator, threshold, action,
            ),
        )


def list_rules(enabled_only: bool = False) -> list[dict[str, Any]]:
    sql = "SELECT * FROM rules"
    if enabled_only:
        sql += " WHERE enabled=1"
    sql += " ORDER BY code, id"
    with db_cursor() as cur:
        cur.execute(sql)
        return rows_to_dicts(cur.fetchall())


def insert_alert(alert: dict[str, Any]) -> int:
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO alerts(code, level, action, message, raw_data)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                alert.get("code"),
                alert.get("level"),
                alert.get("action"),
                alert.get("message"),
                json.dumps(alert.get("raw_data", {}), ensure_ascii=False),
            ),
        )
        return int(cur.lastrowid)


def list_alerts(limit: int = 50, unread_only: bool = False) -> list[dict[str, Any]]:
    sql = "SELECT * FROM alerts"
    params: list[Any] = []
    if unread_only:
        sql += " WHERE is_read=0"
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with db_cursor() as cur:
        cur.execute(sql, params)
        return rows_to_dicts(cur.fetchall())


def mark_alert_read(alert_id: int) -> None:
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE alerts SET is_read=1 WHERE id=?", (alert_id,))


def insert_agent_report(report_type: str, content: str, model: str, raw_prompt: str = "") -> int:
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO agent_reports(report_type, content, model, raw_prompt)
            VALUES (?, ?, ?, ?)
            """,
            (report_type, content, model, raw_prompt),
        )
        return int(cur.lastrowid)


def list_agent_reports(limit: int = 20) -> list[dict[str, Any]]:
    with db_cursor() as cur:
        cur.execute("SELECT * FROM agent_reports ORDER BY id DESC LIMIT ?", (limit,))
        return rows_to_dicts(cur.fetchall())
