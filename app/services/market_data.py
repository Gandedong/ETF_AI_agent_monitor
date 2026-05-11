from __future__ import annotations

import traceback
from typing import Any

from .. import repository as repo
from .utils import to_float, pick_column, pct_from_price_nav


class MarketDataClient:
    """
    免费行情数据适配器。

    设计原则：
    1. 如果存在最新 manual_quotes 记录，人工录入字段优先；
    2. 人工字段为空时，再回退到 AKShare ETF 实时行情；
    3. AKShare 实时行情缺失时，再尝试 AKShare 场内基金净值/折价率数据。

    注意：免费数据源字段名、频率、可用性可能变化。人工录入数据代表用户主动校准，
    因此优先级高于免费接口；真正下单前仍应以券商行情和基金公告为准。
    """

    def get_snapshot(self, code: str, name_hint: str = "") -> dict[str, Any]:
        errors: list[str] = []
        ak_spot = self._get_akshare_etf_spot(code, errors)
        ak_daily = self._get_akshare_etf_daily(code, errors)
        manual = repo.latest_manual_quote(code)

        name = name_hint or (ak_spot or {}).get("name") or (ak_daily or {}).get("name") or (manual or {}).get("name") or code
        price, price_source = self._first_non_none_with_source(
            ("manual_quote", (manual or {}).get("price")),
            ("akshare.fund_etf_spot_em", (ak_spot or {}).get("price")),
            ("akshare.fund_etf_fund_daily_em", (ak_daily or {}).get("price")),
        )
        nav_est, nav_est_source = self._first_non_none_with_source(
            ("manual_quote", (manual or {}).get("nav_est")),
            ("akshare.fund_etf_fund_daily_em", (ak_daily or {}).get("nav_est")),
        )
        premium_from_price_nav = pct_from_price_nav(price, nav_est)
        premium_rate, premium_rate_source = self._first_non_none_with_source(
            ("manual_quote", (manual or {}).get("premium_rate")),
            ("akshare.fund_etf_fund_daily_em", (ak_daily or {}).get("premium_rate")),
            ("derived.price_nav", premium_from_price_nav),
        )
        volume_amount, volume_amount_source = self._first_non_none_with_source(
            ("manual_quote", (manual or {}).get("volume_amount")),
            ("akshare.fund_etf_spot_em", (ak_spot or {}).get("volume_amount")),
        )
        change_pct, change_pct_source = self._first_non_none_with_source(
            ("manual_quote", (manual or {}).get("change_pct")),
            ("akshare.fund_etf_spot_em", (ak_spot or {}).get("change_pct")),
        )

        field_sources = {
            "price": price_source,
            "nav_est": nav_est_source,
            "premium_rate": premium_rate_source,
            "volume_amount": volume_amount_source,
            "change_pct": change_pct_source,
        }
        source_parts = [
            f"{field}={source}"
            for field, source in field_sources.items()
            if source is not None
        ]
        if not source_parts:
            source_parts.append("unavailable")

        return {
            "code": code,
            "name": name,
            "price": price,
            "nav_est": nav_est,
            "premium_rate": premium_rate,
            "volume_amount": volume_amount,
            "change_pct": change_pct,
            "source": "; ".join(source_parts),
            "raw_data": {
                "ak_spot": ak_spot,
                "ak_daily": ak_daily,
                "manual": manual,
                "errors": errors,
                "field_sources": field_sources,
            },
        }

    @staticmethod
    def _first_non_none(*values: Any) -> Any:
        for value in values:
            if value is not None:
                return value
        return None

    @staticmethod
    def _first_non_none_with_source(*source_values: tuple[str, Any]) -> tuple[Any, str | None]:
        for source, value in source_values:
            if value is not None:
                return value, source
        return None, None

    def _get_akshare_etf_spot(self, code: str, errors: list[str]) -> dict[str, Any] | None:
        try:
            import akshare as ak  # type: ignore

            if not hasattr(ak, "fund_etf_spot_em"):
                errors.append("AKShare missing fund_etf_spot_em")
                return None
            df = ak.fund_etf_spot_em()
            if df is None or df.empty:
                return None
            code_col = self._find_col(df.columns, ["代码", "基金代码", "symbol", "代码"])
            if not code_col:
                return None
            rows = df[df[code_col].astype(str).str.zfill(6) == code.zfill(6)]
            if rows.empty:
                return None
            row = rows.iloc[0].to_dict()
            return {
                "code": code,
                "name": pick_column(row, ["名称", "基金简称", "简称"]),
                "price": to_float(pick_column(row, ["最新价", "现价", "收盘", "市价"])),
                "change_pct": to_float(pick_column(row, ["涨跌幅", "涨幅", "日涨幅"])),
                "volume_amount": to_float(pick_column(row, ["成交额", "成交金额"])),
                "raw": {str(k): self._safe_val(v) for k, v in row.items()},
            }
        except Exception as exc:  # noqa: BLE001
            errors.append(f"fund_etf_spot_em error: {exc}\n{traceback.format_exc(limit=2)}")
            return None

    def _get_akshare_etf_daily(self, code: str, errors: list[str]) -> dict[str, Any] | None:
        try:
            import akshare as ak  # type: ignore

            if not hasattr(ak, "fund_etf_fund_daily_em"):
                errors.append("AKShare missing fund_etf_fund_daily_em")
                return None
            df = ak.fund_etf_fund_daily_em()
            if df is None or df.empty:
                return None
            code_col = self._find_col(df.columns, ["基金代码", "代码"])
            if not code_col:
                return None
            rows = df[df[code_col].astype(str).str.zfill(6) == code.zfill(6)]
            if rows.empty:
                return None
            row = rows.iloc[0].to_dict()
            price = to_float(pick_column(row, ["市价", "最新价", "现价"])
            )
            nav = to_float(pick_column(row, ["单位净值", "当前交易日-单位净值"])
            )
            premium = to_float(pick_column(row, ["折价率", "溢价率", "折溢价率"])
            )
            # 天天基金字段常称“折价率”，正数/负数口径可能因数据源变化而不同。
            # 本系统只把它作为触发提醒的参考。下单前必须再核对券商软件或基金公告。
            return {
                "code": code,
                "name": pick_column(row, ["基金简称", "名称", "简称"]),
                "price": price,
                "nav_est": nav,
                "premium_rate": premium if premium is not None else pct_from_price_nav(price, nav),
                "raw": {str(k): self._safe_val(v) for k, v in row.items()},
            }
        except Exception as exc:  # noqa: BLE001
            errors.append(f"fund_etf_fund_daily_em error: {exc}\n{traceback.format_exc(limit=2)}")
            return None

    @staticmethod
    def _find_col(columns: Any, candidates: list[str]) -> str | None:
        col_list = [str(c) for c in columns]
        for c in candidates:
            if c in col_list:
                return c
        for col in col_list:
            for c in candidates:
                if c in col:
                    return col
        return None

    @staticmethod
    def _safe_val(value: Any) -> Any:
        if hasattr(value, "item"):
            try:
                return value.item()
            except Exception:  # noqa: BLE001
                pass
        try:
            if value != value:  # NaN
                return None
        except Exception:  # noqa: BLE001
            pass
        return value
