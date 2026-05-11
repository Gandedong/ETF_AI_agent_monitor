from __future__ import annotations

from .. import repository as repo


def seed_defaults() -> None:
    """初始化默认基金池、持仓占位和规则。重复执行是安全的。"""
    funds = [
        ("513650", "南方标普500ETF", "ETF", "QDII-美国", "核心", "海外股票核心仓，优先观察溢价率"),
        ("513030", "德国ETF", "ETF", "QDII-欧洲", "分散", "小仓位分散美国市场风险"),
        ("159209", "招商中证全指红利质量ETF", "ETF", "A股", "现有持仓", "暂不加仓，反弹或破位时提醒"),
        ("513000", "日经225ETF易方达", "ETF", "QDII-日本", "观察", "日本方向观察池"),
        ("513800", "东证ETF", "ETF", "QDII-日本", "观察", "日本方向观察池"),
        ("159941", "广发纳斯达克100ETF", "ETF", "QDII-美国", "观察", "纳指类等溢价回落"),
        ("513100", "国泰纳斯达克100ETF", "ETF", "QDII-美国", "观察", "纳指类等溢价回落"),
    ]
    for item in funds:
        repo.upsert_fund(*item, is_active=1)

    # 仅做占位，实际份额建议你在网页或 API 中补录。
    repo.upsert_position("159209", quantity=0, cost_price=1.241, total_cost=0, note="成本价已知；请补充实际份额或总成本。暂不卖、不加仓。")
    repo.upsert_position("513030", quantity=0, cost_price=0, total_cost=10000, note="计划或已买入约1万元；请补充实际成交价和份额。")

    rules = [
        ("513650", "低溢价可加仓", "premium_rate", "<=", 1.0, "CONSIDER_ADD", "info", "513650 溢价率 {value:.2f}% ≤ 1%，满足稳健加仓观察条件。"),
        ("513650", "暂停买入", "premium_rate", ">", 2.5, "PAUSE_BUY", "warning", "513650 溢价率 {value:.2f}% > 2.5%，暂停买入。"),
        ("513650", "高溢价风险", "premium_rate", ">", 3.0, "PREMIUM_RISK", "danger", "513650 溢价率 {value:.2f}% > 3%，注意溢价回落风险。"),
        ("513030", "德国ETF小额加仓", "premium_rate", "<=", 1.5, "CONSIDER_SMALL_ADD", "info", "513030 溢价率 {value:.2f}% ≤ 1.5%，可以考虑小额加仓。"),
        ("513030", "德国ETF暂停买入", "premium_rate", ">", 2.5, "PAUSE_BUY", "warning", "513030 溢价率 {value:.2f}% > 2.5%，暂停买入。"),
        ("513030", "德国ETF高溢价风险", "premium_rate", ">", 3.0, "PREMIUM_RISK", "danger", "513030 溢价率 {value:.2f}% > 3%，注意溢价回落风险。"),
        ("159209", "红利ETF破位观察", "price", "<=", 1.18, "REVIEW_POSITION", "warning", "159209 价格 {value:.3f} ≤ 1.18，需要重新评估是否继续持有。"),
        ("159209", "红利ETF反弹减仓观察", "price", ">=", 1.23, "CONSIDER_REDUCE", "info", "159209 价格 {value:.3f} ≥ 1.23，可以考虑是否减仓转向海外ETF。"),
        ("159209", "红利ETF回本观察", "price", ">=", 1.241, "COST_RECOVERY", "info", "159209 价格 {value:.3f} 已接近或超过成本价 1.241，可重新评估仓位。"),
    ]
    for r in rules:
        repo.add_rule(*r)
