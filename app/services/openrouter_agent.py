from __future__ import annotations

import json
from typing import Any

import requests

from ..config import settings


SYSTEM_PROMPT = """
你是一个稳健型 ETF/LOF 投资分析 Agent。你的任务是基于程序给出的行情快照、折溢价率、成交额、持仓和硬规则触发结果，生成简明的盯盘报告。

必须遵守：
1. 你不能承诺收益，也不能说“必涨”“稳赚”。
2. 你不能建议自动交易，只能给“提醒、观察、加仓候选、暂停买入、减仓观察”等辅助意见。
3. 对 QDII ETF，优先关注折溢价率、成交额、申赎/额度/风险公告，再看技术面。
4. 风格要稳健，宁可错过，不要追高溢价。
5. 输出要直接，包含“今日动作”“理由”“建议金额区间”“风险提示”。
""".strip()


def build_agent_prompt(snapshots: list[dict[str, Any]], alerts: list[dict[str, Any]], positions: list[dict[str, Any]]) -> str:
    payload = {
        "strategy_profile": {
            "risk_level": "稳健型",
            "principle": "不追高溢价；先买低溢价标普500核心，德国ETF小比例；日本和纳指观察；159209暂不急卖。",
            "capital_context": "用户计划海外ETF资金约15万元，已决定513030只买约1万元，513650分批。",
        },
        "snapshots": snapshots,
        "alerts": alerts,
        "positions": positions,
    }
    return "请基于以下 JSON 生成中文盯盘报告：\n" + json.dumps(payload, ensure_ascii=False, indent=2, default=str)


def call_openrouter(prompt: str) -> str:
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY 未配置")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.openrouter_site_url,
        "X-Title": settings.openrouter_app_name,
    }
    body = {
        "model": settings.openrouter_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    resp = requests.post(url, headers=headers, json=body, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]
