# ETF Agent Monitor

这是一个本地运行的 **ETF/LOF 盯盘与 Agent 辅助决策系统**，用于延续当前的稳健型海外 ETF 投资流程。

> 定位：只做行情记录、规则提醒、Agent解释和报告保存。**不自动交易，不替代人工决策。**

## 1. 第一版功能

- FastAPI 后端
- SQLite 本地数据库
- 默认基金池：
  - `513650` 南方标普500ETF：核心
  - `513030` 德国ETF：小仓位分散
  - `159209` 招商中证全指红利质量ETF：现有持仓观察
  - `513000` 日经225ETF：观察
  - `513800` 东证ETF：观察
  - `159941` 广发纳指ETF：观察
  - `513100` 国泰纳指ETF：观察
- 默认规则：
  - 513650 溢价率 ≤ 1%：可观察加仓
  - 513650 溢价率 > 2.5%：暂停买入
  - 513650 溢价率 > 3%：高溢价风险
  - 513030 溢价率 ≤ 1.5%：可小额加仓
  - 513030 溢价率 > 2.5%：暂停买入
  - 159209 价格 ≤ 1.18：重新评估
  - 159209 价格 ≥ 1.23：反弹减仓观察
  - 159209 价格 ≥ 1.241：回本观察
- OpenRouter Agent 报告
- APScheduler 定时任务：默认交易日 10:30 和 14:30 运行
- 简单网页看板：基金池、持仓、最新快照、提醒、Agent报告
- 人工行情录入：当免费数据源不可用时，可用券商软件/HaoETF数据手动校准

## 2. 安装

建议使用 Python 3.11 或 3.12。

```bash
cd etf_agent_monitor
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

## 3. 配置 OpenRouter

复制 `.env.example` 为 `.env`：

```bash
cp .env.example .env
```

Windows PowerShell：

```powershell
Copy-Item .env.example .env
```

然后编辑 `.env`：

```env
OPENROUTER_API_KEY=你的OpenRouter密钥
OPENROUTER_MODEL=deepseek/deepseek-chat
```

如果不填 `OPENROUTER_API_KEY`，系统仍可运行，但只会输出本地规则解释，不会调用大模型。

## 4. 启动

从仓库根目录启动：

```bash
uvicorn app.main:app --reload
```

如果当前目录不在仓库根目录，可指定仓库路径后启动；应用会根据 `app/main.py` 的实际位置加载 `app/static` 和 `app/templates`，首页静态资源和模板不依赖当前工作目录：

```bash
PYTHONPATH=/path/to/etf_agent_monitor uvicorn app.main:app --reload
```

打开：

```text
http://127.0.0.1:8000
```

首次启动会自动创建数据库并写入默认基金池、持仓占位和规则。

## 5. 推荐使用流程

### 第一步：补录实际持仓

进入网页首页，或者调用 API：

```bash
curl -X POST http://127.0.0.1:8000/api/positions \
  -H "Content-Type: application/json" \
  -d '{"code":"159209","quantity":10000,"cost_price":1.241,"total_cost":12410,"note":"实际份额请自行修改"}'
```

513030 如果你已经买入 1 万元，也建议补录实际成交价和份额。

### 第二步：运行一次监控

网页点击“运行一次监控”，或：

```bash
curl -X POST "http://127.0.0.1:8000/api/monitor/run?force_agent=true"
```

### 第三步：如果 AKShare 数据缺失，人工录入行情

网页里有“人工行情录入”。例如录入 513650：

```json
{
  "code": "513650",
  "price": 1.82,
  "nav_est": 1.80,
  "premium_rate": 1.11,
  "volume_amount": 140000000,
  "note": "券商软件/HaoETF人工录入"
}
```

然后再运行一次监控。

## 6. 重要说明

### 6.1 为什么保留人工行情录入？

免费行情接口经常变化，尤其是 QDII ETF 的盘中估值、IOPV、折溢价率，不同来源口径可能不一致。程序需要能用人工数据校准，避免错误提醒。

### 6.2 为什么不自动交易？

因为 QDII ETF 的真实风险来自：

- 场内折溢价
- QDII 额度和申赎状态
- A股与美股/欧洲/日本市场交易时差
- 做市商报价
- 成交额
- 基金公告和停牌提示

这些信息很难完全自动化确认。第一版只做提醒更稳妥。

### 6.3 下单前一定要人工确认

真正买卖前，请至少确认：

- 券商软件实时价格
- 场内溢价率/IOPV/估算净值
- 当日成交额
- 基金公告是否有溢价风险提示或停牌提示
- 你的总仓位是否超出计划

## 7. 项目结构

```text
etf_agent_monitor/
├── app/
│   ├── main.py                 # FastAPI入口
│   ├── config.py               # 配置读取
│   ├── database.py             # SQLite连接与初始化
│   ├── repository.py           # 数据访问层
│   ├── schema.sql              # 数据库表结构
│   ├── services/
│   │   ├── seed.py             # 默认基金池和规则
│   │   ├── market_data.py      # AKShare/人工行情适配器
│   │   ├── rules.py            # 硬规则引擎
│   │   ├── openrouter_agent.py # OpenRouter Agent
│   │   ├── monitor.py          # 盯盘主流程
│   │   └── scheduler.py        # 定时任务
│   ├── templates/
│   │   └── dashboard.html      # 简单网页
│   └── static/
│       └── style.css
├── requirements.txt
├── .env.example
└── README.md
```

## 8. 后续可扩展方向

- 接入邮件/Telegram/企业微信提醒
- 增加基金公告爬取 Agent
- 增加美元人民币汇率和底层指数数据
- 增加组合净值曲线
- 增加规则编辑页面
- 增加回测模块
- 增加数据源健康检查
- 增加 Dockerfile

## 9. 当前策略口径

当前系统默认延续以下策略：

- 总体：稳健型
- 首选核心：513650 南方标普500ETF
- 小比例分散：513030 德国ETF
- 159209：暂不卖、不加仓，等待反弹或破位信号
- 日本 ETF：观察，不急买
- 纳指 ETF：等溢价回落，不追高
- 任一 QDII ETF 溢价过高：暂停买入

