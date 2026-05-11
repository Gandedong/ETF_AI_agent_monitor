from __future__ import annotations

from typing import Any


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text or text in {"-", "--", "None", "nan", "NaN"}:
        return None
    text = text.replace("%", "").replace(",", "").replace("元", "")
    try:
        return float(text)
    except ValueError:
        return None


def pick_column(row: dict[str, Any], candidates: list[str]) -> Any:
    for name in candidates:
        if name in row:
            return row[name]
    # 兼容字段名带日期或前缀的情况
    for key, val in row.items():
        for name in candidates:
            if name in str(key):
                return val
    return None


def pct_from_price_nav(price: float | None, nav: float | None) -> float | None:
    if price is None or nav is None or nav == 0:
        return None
    return (price / nav - 1.0) * 100
