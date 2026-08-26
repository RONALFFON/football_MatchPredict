# 英超数据分析平台（PL Analytics）架构设计书

> 版本：v1.1 | 状态：实施中（v1.1 架构已落地为 `frontend/` + `backend/`）
> 定位：在 MatchPredict 主站之外，新建一个**架构完全独立**的英超深度数据分析应用，内置 AI Agent 能力。
> 核心原则：**新代码零耦合主站，主站仅保留"入口链接 + 账号互通"两条细粒度连接。**

---

## ⚠️ v1.1 架构变更说明（最新决策，以此为准）

因与英超达成新合作，英超板块与五大联赛**共用同一套前后端**，原"独立子项目"方案调整为：

| 项 | v1.0 方案 | v1.1 落地方案 |
|----|-----------|---------------|
| 前端 | 独立 `premier-league/frontend/` | **统一 `frontend/`**（Vue3 SPA，导航分两组：五大联赛 / 英超专项） |
| 后端 | 独立 `premier-league/backend/` | **统一 `backend/`**（FastAPI，路由按 `/api/v1/*` 与 `/api/v1/pl/*` 分组） |
| 数据库 | 独立库 | 复用主站 PostgreSQL，独立 schema `pl_analytics`（不变） |
| 防耦合手段 | 物理目录隔离 | **模块化隔离**：PL 后端收敛于 `app/agent/`、`app/pl_data/`、`api/v1/pl_data.py`、`api/v1/agent_pl.py`，与五大联赛路由零互相 import |

v1.0 其余原则（前端零密钥、Agent 经 services 访问数据、护栏、SSE 流式、配额打通）均已按原设计落地。

### v1.2 变更：AI 能力层独立成包（已落地）

`backend/ai_service/` 独立包收纳全部 AI 能力：`llm.py`（SenseNova 客户端）、`predictor.py`（五大联赛预测）、`agent/`（编排/工具/护栏）。通过**依赖倒置**解耦：AI 层定义 `PlDataProvider` 接口，app 层以 `app/pl_data/provider.py` 实现并注入；`ai_service` 对 app/scripts/数据库零 import，可独立测试与复用。


---

## 1. 背景与问题分析

### 1.1 现状痛点

当前主站 `football_MatchPredict` 是一个典型的**单体演化架构**：

| 问题 | 现状 | 后果 |
|------|------|------|
| 后端单文件巨石 | `app.py` 882 行，路由/认证/业务/编排混杂 | 任何新功能都要改这一个文件，回归风险高 |
| 前后端半耦合 | `templates/index.html` 由 Flask 服务端渲染 + 9 个原生 JS 文件全局变量互通 | 无法独立开发、独立部署、独立测试 |
| 数据脚本耦合 | 五大联赛特征数据、体彩爬虫、SenseNova 调用混在同一 `scripts/` 目录 | 英超专项深化（xG、阵容、伤病、实时比分）无处安放 |
| 无扩展性 | 新增"某联赛专项分析"只能继续往主站堆功能 | 耦合持续恶化，最终不可维护 |

### 1.2 需求目标

1. 新增一个**英超专项数据分析窗口/应用**：赛程、积分榜、球队画像、赔率走势、深度数据面板。
2. 内置 **AI / Agent 能力**：用户可对话式提问（"阿森纳最近 5 场防守如何？"），Agent 自主调用数据工具回答。
3. **架构分离**：前后端分离、新应用与主站解耦，防止互相拖累。
4. 可复用主站已有资产：用户体系、数据管道经验、SenseNova 接入。

---

## 2. 总体架构

### 2.1 架构决策：独立子项目（推荐）

采用 **Monorepo 独立子项目** 起步，保留后续拆分为独立 Git 仓库的能力：

```
football_MatchPredict/                  # 主站（保持不动，只加一个导航入口）
│
└── premier-league/                     # ★ 新应用：完全独立的子项目
    ├── frontend/                       # Vue 3 SPA（纯静态产物）
    │   ├── src/
    │   │   ├── views/                  # 页面：赛程/积分榜/球队详情/赔率走势/AI对话
    │   │   ├── components/             # 组件：比赛卡片、数据图表、ChatPanel
    │   │   ├── stores/                 # Pinia 状态管理
    │   │   ├── api/                    # 后端 API 封装（axios）
    │   │   └── router/
    │   ├── vite.config.ts
    │   └── package.json
    │
    ├── backend/                        # FastAPI 服务（BFF + 领域服务）
    │   ├── app/
    │   │   ├── api/v1/                 # 路由层：matches/teams/standings/odds/agent
    │   │   ├── services/               # 领域服务层：比赛/球队/赔率/分析
    │   │   ├── agent/                  # ★ AI Agent 层
    │   │   │   ├── orchestrator.py     #   ReAct 编排循环
    │   │   │   ├── tools/              #   工具集：stats/form/h2h/odds/standings
    │   │   │   ├── prompts.py          #   系统提示词与护栏
    │   │   │   └── memory.py           #   会话记忆（DB 持久化）
    │   │   ├── models/                 # SQLAlchemy ORM / Pydantic schema
    │   │   ├── core/                   # 配置、认证、日志、异常
    │   │   └── main.py
    │   └── requirements.txt
    │
    ├── pipeline/                       # 英超数据管道（独立定时任务）
    │   ├── sync_matches.py             # Football-Data.org PL 赛程/结果
    │   ├── sync_standings.py           # 积分榜
    │   ├── sync_odds.py                # 赔率快照
    │   └── feature_builder.py          # 英超球队特征工程（复用主站算法思路）
    │
    └── docs/                           # 本设计书等
```

**为什么不直接在主站加页面？**
主站是"服务端渲染 + 原生 JS"架构，加入现代化 SPA 会形成两套技术栈硬拼在一个进程里；而独立子项目可以：独立技术栈、独立部署、独立发版、独立回滚，主站故障不影响英超应用，反之亦然。

### 2.2 系统架构图

```
                        ┌────────────────────────────┐
                        │   主站 MatchPredict         │
                        │   (导航栏新增"英超分析"入口) │
                        └──────────────┬─────────────┘
                                       │ ①链接跳转 + ②JWT 账号互通
                                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                     PL Analytics（新应用）                        │
│                                                                    │
│  ┌──────────────┐        REST/SSE         ┌──────────────────┐   │
│  │ Vue3 SPA     │ ◄─────────────────────► │ FastAPI 后端      │   │
│  │ (Vercel静态) │                          │ (BFF+领域服务)    │   │
│  └──────────────┘                          └───┬──────────┬───┘   │
│                                                │          │       │
│                                    ┌───────────▼───┐ ┌────▼─────┐ │
│                                    │ AI Agent 层   │ │ 领域服务  │ │
│                                    │ 编排+工具调用 │ │ 比赛/球队 │ │
│                                    └───────┬───────┘ │ /赔率    │ │
│                                            │         └────┬─────┘ │
└────────────────────────────────────────────┼──────────────┼───────┘
                                             │              │
                        ┌────────────────────┼──────────────┼──────┐
                        │                    ▼              ▼      │
                        │ SenseNova API   PostgreSQL(schema: pl_*) │
                        │   (LLM推理)    + Redis(缓存/会话)         │
                        └──────────────────────────────────────────┘
                                             ▲
                        ┌────────────────────┴──────────────────┐
                        │ pipeline/ 定时任务 (GitHub Actions)    │
                        │ Football-Data.org PL + 赔率快照        │
                        └────────────────────────────────────────┘
```

---

## 3. 技术选型（含对比与否决理由）

### 3.1 后端框架

| 候选 | 优势 | 劣势 | 结论 |
|------|------|------|------|
| **FastAPI** | 原生 async（Agent 流式输出刚需）、自动 OpenAPI 文档、Pydantic 强校验 | 与主站 Flask 不同栈 | ✅ **选定** |
| Flask | 与主站一致、团队熟悉 | 无原生 async，SSE/Agent 流式实现别扭；无自动文档 | ❌ 否决：Agent 场景 async 是硬需求 |
| Django REST | 功能全 | 过重，本应用体量不需要 | ❌ 否决 |

### 3.2 前端框架

| 候选 | 优势 | 劣势 | 结论 |
|------|------|------|------|
| **Vue 3 + Vite + TS** | 上手快、组合式 API、生态成熟（Pinia/Vue Router/ECharts） | — | ✅ **选定** |
| React + Vite | 生态最大 | 团队无 React 资产，收益不明显 | ❌ 否决 |
| 沿用原生 JS | 零学习成本 | 违背"前后端分离+防耦合"初衷，组件化能力差 | ❌ 否决 |

配套：Pinia（状态）、Vue Router、ECharts（赔率走势/雷达图）、Tailwind CSS（快速构建数据密集界面）、axios。

### 3.3 AI Agent 方案

| 候选 | 优势 | 劣势 | 结论 |
|------|------|------|------|
| **自研轻量 ReAct 循环 + SenseNova 工具调用** | 依赖少、可控、贴合 Vercel 部署、便于定制护栏 | 需自己写编排 | ✅ **选定** |
| LangChain/LangGraph | 开箱即用 | 依赖重、抽象层多、Serverless 冷启动慢 | ❌ 否决 |
| 纯 Prompt 一问一答（主站现状） | 最简单 | 无法查实时数据、易幻觉 | ❌ 否决：不满足"数据分析"需求 |

### 3.4 存储

- **PostgreSQL**：复用主站实例，新建独立 schema `pl_analytics`（逻辑隔离、连接串独立、可随时迁库）。
- **Redis**（可选，P2 阶段引入）：赛程/积分榜缓存、Agent 会话上下文。
- **向量检索**（可选，P3 引入）：`pgvector` 存球队战术知识/历史分析，做 RAG。

---

## 4. 核心模块设计

### 4.1 前端（frontend/）

页面规划：

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | 总览仪表盘 | 今日赛程、积分榜 Top8、热门赔率变动 |
| `/matches` | 赛程列表 | 按轮次/日期筛选，状态（未开赛/进行中/已结束） |
| `/matches/:id` | 比赛详情 | 比分、赔率走势图（ECharts）、AI 一键分析按钮 |
| `/teams` `/teams/:id` | 球队画像 | 近 10 场走势、主客场数据雷达图、进失球分布 |
| `/standings` | 积分榜 | 实时排名、胜平负、净胜球 |
| `/ai` | **AI 分析对话窗** | Chat UI，流式输出（SSE），展示 Agent 工具调用过程 |

关键工程约束：
- 前端**不内置任何 API Key**（所有 AI 调用走后端代理）。
- 环境变量只允许 `VITE_API_BASE_URL` 一项。

### 4.2 后端（backend/）

分层职责：

```
api/v1（路由）→ services（领域逻辑）→ models（数据访问）
                      ↘ agent/（AI 编排，与领域服务平级，可调用 services）
```

REST API 设计（v1）：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/matches?round=&date=&status=` | 赛程列表 |
| GET | `/api/v1/matches/{id}` | 比赛详情（含赔率快照序列） |
| GET | `/api/v1/teams` / `/api/v1/teams/{id}` | 球队列表/画像 |
| GET | `/api/v1/standings` | 积分榜 |
| GET | `/api/v1/odds/history?match_id=` | 赔率走势 |
| POST | `/api/v1/agent/chat` | Agent 对话，**SSE 流式响应** |
| GET | `/api/v1/agent/sessions` | 会话历史 |
| POST | `/api/v1/auth/login` | JWT 登录（见 §5） |

统一响应契约：`{ "code": 0, "message": "ok", "data": {...} }`，错误码表集中维护。

### 4.3 数据管道（pipeline/）

- 数据源：**Football-Data.org** 英超（`PL`）赛程/比分/积分榜 + 赔率快照（沿用主站 Pinnacle/Odds API 经验）。
- 调度：**GitHub Actions cron**（如 `0 2 * * *`），脚本幂等（UPSERT by `match_uid`）。
- 产出：写入 `pl_analytics` schema；同时计算球队特征（复用主站 `feature_engineering.py` 的算法思路，独立实现为 `feature_builder.py`，不 import 主站代码）。

### 4.4 AI Agent 设计（重点）

**架构：Orchestrator（ReAct 循环） + Tool Registry + Memory + Guardrails**

```
用户提问
   │
   ▼
Orchestrator ──► SenseNova Tool Calling
   │                  │ 返回 tool_call
   │            ┌─────┴──────────────────────────────┐
   │            ▼          ▼          ▼               ▼
   │     query_recent_  query_h2h  query_team_   query_odds_
   │     form(team,n)   (teamA,B)  stats(team)   movement(match)
   │            │          │          │               │
   │            └─────┬────┴──────────┴───────────────┘
   │                  ▼
   │         工具结果回填上下文（最多 5 轮循环）
   ▼
最终回答（SSE 流式推送给前端） + 会话落库
```

**工具集定义（Tool Registry）**：

| 工具 | 入参 | 返回 | 数据源 |
|------|------|------|--------|
| `query_recent_form` | team, n=5 | 近 n 场比分与结果 | pl_matches |
| `query_head_to_head` | team_a, team_b, n=5 | 历史交锋记录 | pl_matches |
| `query_team_stats` | team, season | 进球/失球/主客场胜率/特征向量 | pl_features |
| `query_standings` | — | 当前积分榜 | pl_standings |
| `query_odds_movement` | match_id | 赔率时间序列 | pl_odds_history |
| `predict_match` | match_id | 泊松模型概率 + EV（复用主站算法思路重写） | features + odds |

**工程要点**：
1. **流式输出**：`StreamingResponse` + SSE，前端逐字渲染，并实时展示"正在调用工具：查询阿森纳近5场…"。
2. **会话记忆**：最近 10 轮对话存 `pl_ai_messages` 表，超出窗口做摘要压缩。
3. **护栏（Guardrails）**：系统提示词明确"技术研究用途、不给出投注建议"；输出过滤敏感内容；单会话最多 5 次工具调用防死循环。
4. **降级策略**：LLM 超时/限流 → 返回基于规则的统计摘要（保证可用性）。
5. **可观测**：每次 Agent 运行记录 token 消耗、工具调用链、耗时，写入 `pl_agent_runs` 表。

---

## 5. 与主站的集成（仅两条细粒度连接）

### 5.1 入口集成
主站导航栏加一个外链按钮「英超分析」→ 指向新应用域名（如 `pl.match-predict.vercel.app`）。**不共享任何代码。**

### 5.2 账号互通（分阶段）

| 阶段 | 方案 | 说明 |
|------|------|------|
| P1 | 新应用独立账号体系（自带注册/登录，JWT） | 快速上线，零耦合 |
| P2 | **共享用户库**：新应用读主站 `users` 表（只读），登录校验复用同一 password_hash；发放 JWT | 用户一套账号走两边 |
| P3（可选） | SSO：主站颁发 token，新应用验签 | 后续若要第三个子应用再做 |

> 原则：主站**不感知**新应用的任何业务数据；新应用对主站仅有"用户表只读"一个依赖，且通过配置开关可关闭。

### 5.3 配额与商业化
沿用主站"免费每日 3 次 / VIP 无限"模型：新应用 Agent 对话同样消耗 `daily_predictions_used` 配额（P2 随共享用户库一起实现）。

---

## 6. 数据模型（schema: pl_analytics）

| 表 | 关键字段 | 说明 |
|----|---------|------|
| `pl_teams` | id, api_team_id, name, short_name, crest_url | 20 支球队 |
| `pl_matches` | id, match_uid(唯一), season, round, home/away_id, utc_date, status, home/away_score | 赛程+结果 |
| `pl_standings` | season, team_id, position, played, won, drawn, lost, gf, ga, points, updated_at | 积分榜 |
| `pl_odds_history` | match_uid, bookmaker, home/draw/away, snapshot_at | 赔率时序 |
| `pl_features` | season, team_id, 各类特征字段 | 球队特征 |
| `pl_users`（P1）/复用 `users`（P2） | — | 见 §5.2 |
| `pl_ai_sessions` | id, user_id, title, created_at | Agent 会话 |
| `pl_ai_messages` | id, session_id, role, content, tool_calls(jsonb), tokens, latency_ms | 消息流 |

索引策略：`pl_matches(season, utc_date)`、`pl_odds_history(match_uid, snapshot_at)`、`pl_ai_messages(session_id, created_at)`。

---

## 7. 部署架构

| 组件 | 部署位置 | 说明 |
|------|---------|------|
| 前端 SPA | Vercel（独立 Project） | `frontend/dist` 静态托管，构建时注入 `VITE_API_BASE_URL` |
| 后端 FastAPI | Vercel（`@vercel/python`，独立 Project） | 与主站部署模式一致，团队已有经验；`/api/*` 全量路由到 `main.py` |
| 定时同步 | GitHub Actions cron | 免服务器；失败发 Issue/邮件告警 |
| 数据库 | 复用现有托管 PostgreSQL，独立 schema | 零新增成本 |

环境变量清单（新应用）：`DB_HOST/PORT/NAME/USER/PASS`（建议换用 Secret 管理，禁止硬编码）、`AI_API_KEY`、`AI_MODEL`、`AI_BASE_URL`、`JWT_SECRET`、`FOOTBALL_DATA_API_KEY`、`CORS_ORIGINS`。

CI/CD：GitHub Actions —— PR 触发 lint+pytest；main 分支推送触发前端构建 + 后端部署。

---

## 8. 安全设计（针对主站已知问题做规避）

| 主站教训 | 新应用对策 |
|----------|-----------|
| API Key 透传前端模板 | Key 仅存在后端环境变量，前端零接触 |
| 数据库密码硬编码 | 全部走环境变量 + `.env`（gitignore）+ Vercel Secrets |
| 裸 SHA256 无盐 | 新应用自带账号用 `bcrypt`；共享主站用户时仅做兼容校验，迁移期后统一升级 |
| `/api/session/debug` 等调试接口 | 环境感知：非 dev 环境自动禁用 |
| 硬编码日志路径 | 日志统一输出 stdout（Serverless 友好）+ 可选文件 handler 走环境变量配置 |

---

## 9. 里程碑规划（详见 PREMIER_LEAGUE_TODO.md）

| 阶段 | 目标 | 产出 |
|------|------|------|
| **M1 基建** | 脚手架 + CI/CD | 前后端骨架可跑通 /health |
| **M2 数据** | 英超数据全量入库 | pipeline 定时跑通，赛程/积分榜/赔率可查 |
| **M3 应用** | 前端 5 个数据页面 | 用户可浏览全部英超数据 |
| **M4 AI** | Agent 对话上线 | 6 个工具 + 流式对话 + 会话持久化 |
| **M5 集成** | 主站入口 + 账号互通 | 一键跳转、统一登录、配额打通 |
| **M6 加固** | 监控/降级/压测 | 生产可用 |

---

## 10. 风险与对策

| 风险 | 等级 | 对策 |
|------|------|------|
| Football-Data.org 免费层限流（10 次/分钟） | 中 | 管道层加节流 + 本地缓存；增量同步而非全量 |
| Vercel Serverless 对长耗时 Agent 请求有超时（Hobby 10s/Pro 60s） | 高 | Agent 用 SSE 持续产出保活；或迁移到支持长连接的容器平台（预留方案） |
| LLM 幻觉（编造数据） | 中 | 强制"数字必须来自工具返回"写入系统提示词；工具结果以结构化 JSON 注入 |
| 赔率数据版权/合规 | 中 | 沿用主站免责声明；只展示公开数据 |
| 两套技术栈维护成本 | 低 | 新栈收敛为 Vue3+FastAPI 一套，文档先行 |

---

## 11. 评审结论（架构师建议）

1. **坚决独立子项目**，不往主站 `app.py` 里加任何一行英超专项代码。
2. **Agent 层与领域服务平级**：Agent 是"使用者"而非"拥有者"，所有数据访问必须经过 services 层，防止 Agent 代码里散落 SQL。
3. **先数据后 AI**：M2（数据管道）是 M4（Agent）的地基，工具的质量决定 Agent 的上限。
4. 第一阶段容忍"两套登录"，不要为了 SSO 阻塞上线节奏。
