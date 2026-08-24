# 英超数据分析平台（PL Analytics）实施 ToDoList

> 配套设计书：`PREMIER_LEAGUE_DESIGN.md`
> 任务编号规则：M{里程碑}-{序号}。勾选规则：代码合入 + 验收标准通过才可勾选。

---

## M1 工程基建（预计 3 天）

### 后端脚手架
- [ ] **M1-1** 创建 `premier-league/backend/` FastAPI 骨架：`main.py` + `api/v1/` + `services/` + `models/` + `core/`
  - 验收：`uvicorn app.main:app` 启动，`GET /health` 返回 200，`/docs` 出现 Swagger 页面
- [ ] **M1-2** 统一响应契约与全局异常处理：`{code, message, data}` + 错误码表
  - 验收：404/500/参数校验错误均返回统一格式
- [ ] **M1-3** 配置管理：Pydantic Settings 读取环境变量（DB/Gemini/JWT/CORS），本地 `.env` + `.gitignore`
  - 验收：代码中无任何硬编码密钥与路径
- [ ] **M1-4** SQLAlchemy/asyncpg 接入：独立 schema `pl_analytics`，初始化迁移脚本（Alembic 或 init SQL）
  - 验收：本地可连库建表，连接串全部来自环境变量

### 前端脚手架
- [ ] **M1-5** `pnpm create vite frontend --template vue-ts`，集成 Pinia / Vue Router / Tailwind / axios / ECharts
  - 验收：`pnpm dev` 可访问，路由切换正常
- [ ] **M1-6** 封装 API 层：`api/client.ts`（baseURL、统一错误拦截、超时）
  - 验收：唯一环境变量 `VITE_API_BASE_URL`，前端无密钥
- [ ] **M1-7** 基础布局：顶栏导航（总览/赛程/球队/积分榜/AI分析）+ 响应式容器

### CI/CD
- [ ] **M1-8** GitHub Actions：PR 触发 `pytest`（后端）+ `vue-tsc && vite build`（前端）
  - 验收：提交 PR 自动跑检查并出结果

---

## M2 英超数据管道（预计 4 天）

- [ ] **M2-1** `pipeline/sync_matches.py`：Football-Data.org PL 赛程+比分入库（UPSERT by match_uid，幂等）
  - 验收：2024/2025 赛季全量比赛入库，重复执行不产生脏数据
- [ ] **M2-2** `pipeline/sync_standings.py`：积分榜入库
  - 验收：与官网积分一致（抽查 3 队）
- [ ] **M2-3** `pipeline/sync_odds.py`：赔率快照入库（`pl_odds_history` 时序）
  - 验收：同一比赛多时刻快照可按时间排序查询
- [ ] **M2-4** `pipeline/feature_builder.py`：球队特征工程（主客场进失球、近 10 场状态、胜率——重写主站算法，不 import 主站）
  - 验收：产出 `pl_features` 表，覆盖 20 队
- [ ] **M2-5** API 限流保护：请求间隔控制 + 失败重试 + 本地缓存
  - 验收：全量同步不触发 Football-Data.org 429
- [ ] **M2-6** GitHub Actions cron 定时任务（每日 02:00 UTC 同步），失败告警（邮件/Issue）
  - 验收：连续 3 天自动运行成功，日志可查

---

## M3 数据应用（前后端，预计 5 天）

### 后端 API
- [ ] **M3-1** `GET /api/v1/matches`（round/date/status 筛选、分页）
- [ ] **M3-2** `GET /api/v1/matches/{id}`（含赔率快照序列）
- [ ] **M3-3** `GET /api/v1/teams`、`GET /api/v1/teams/{id}`（画像：近 10 场、主客场拆分）
- [ ] **M3-4** `GET /api/v1/standings`、`GET /api/v1/odds/history?match_id=`
  - 验收：全部接口有 OpenAPI 文档 + 单元测试覆盖率 ≥ 70%

### 前端页面
- [ ] **M3-5** 总览仪表盘：今日赛程卡片 + 积分榜 Top8 + 状态徽标
- [ ] **M3-6** 赛程页：轮次/日期筛选、状态过滤、分页
- [ ] **M3-7** 比赛详情页：比分信息 + 赔率走势折线图（ECharts）
- [ ] **M3-8** 球队页 + 球队画像：近 10 场走势柱状图 + 主客场雷达图
- [ ] **M3-9** 积分榜页：实时排名、净胜球、积分高亮前四/降级区
  - 验收：所有数据来自 API，页面间跳转正常，移动端适配

---

## M4 AI Agent（预计 6 天）

### 后端
- [ ] **M4-1** Agent 工具层：6 个工具实现（recent_form / h2h / team_stats / standings / odds_movement / predict_match），统一注册到 Tool Registry
  - 验收：每个工具有单元测试，返回结构化 JSON
- [ ] **M4-2** Orchestrator：Gemini Function Calling + ReAct 循环（上限 5 轮），工具结果回填上下文
  - 验收：给定"阿森纳最近状态如何"能正确触发 query_recent_form 并给出基于真实数据的回答
- [ ] **M4-3** 系统提示词与护栏：技术研究声明、禁止投注建议、数字必须来自工具、防幻觉指令
- [ ] **M4-4** SSE 流式输出：`POST /api/v1/agent/chat` 返回 StreamingResponse（文本增量 + 工具调用事件）
  - 验收：curl 可观察到逐块输出与工具事件
- [ ] **M4-5** 会话持久化：`pl_ai_sessions` / `pl_ai_messages`，上下文窗口 10 轮 + 超限摘要
- [ ] **M4-6** 降级与观测：LLM 超时返回统计摘要兜底；每次运行记录 tokens/耗时/工具链到 `pl_agent_runs`
- [ ] **M4-7** 泊松预测工具：复用主站算法思路实现 `predict_match`（比分矩阵 → 胜平负概率 → EV）
  - 验收：与主站 `parlay_predictor` 对同一输入结果一致（误差 <1%）

### 前端
- [ ] **M4-8** Chat 面板：消息流渲染（Markdown）、流式打字机效果
- [ ] **M4-9** 工具调用可视化：气泡展示"正在查询阿森纳近 5 场…"状态
- [ ] **M4-10** 会话管理：历史会话列表、新建/切换会话
- [ ] **M4-11** 快捷入口：比赛详情页「AI 分析本场」按钮，自动带入比赛上下文发起对话

---

## M5 主站集成与账号（预计 3 天）

- [ ] **M5-1** 主站导航栏新增「英超分析」外链入口（仅此一处改动主站）
- [ ] **M5-2** P1 账号：新应用独立注册/登录（bcrypt + JWT）
  - 验收：注册→登录→携带 JWT 调用受保护接口全链路通过
- [ ] **M5-3** P2 账号互通：新应用只读主站 `users` 表，兼容校验旧 hash，统一发放 JWT（配置开关控制）
  - 验收：主站老账号可直接登录新应用
- [ ] **M5-4** 配额打通：Agent 对话消耗 `daily_predictions_used`（free 每日 3 次，VIP 不限）
  - 验收：第 4 次对话被拒绝并提示升级
- [ ] **M5-5** CORS 白名单配置：仅允许新前端域名

---

## M6 部署与加固（预计 3 天）

- [ ] **M6-1** 前端部署 Vercel（独立 Project），配置 `VITE_API_BASE_URL`
- [ ] **M6-2** 后端部署 Vercel（`@vercel/python`），Secrets 配置（DB 凭证改为 Secret 管理，不复用主站硬编码默认值）
- [ ] **M6-3** 冒烟测试脚本：部署后自动验证 /health + 核心 API + Agent 一轮对话
- [ ] **M6-4** SSE 长连接验证：确认所用 Vercel 套餐下 Agent 流式不超时（超时则启用分段响应预案）
- [ ] **M6-5** 日志与监控：结构化日志输出 stdout，Agent 运行指标看板（可用 `pl_agent_runs` 做简单统计页）
- [ ] **M6-6** 安全检查清单：前端产物无密钥泄露、调试接口仅 dev 可用、SQL 全部参数化
- [ ] **M6-7** 编写 `premier-league/README.md`：本地启动、环境变量、部署说明

---

## 依赖关系总览

```
M1 ──► M2 ──► M3 ──► M5(入口)
              └────► M4 ──► M5(账号/配额) ──► M6
```

**关键路径**：M1 → M2 → M4 → M6（Agent 是核心价值，数据管道是 Agent 的地基）。

**建议排期**（单人）：M1+M2 第 1 周，M3 第 2 周，M4 第 3 周，M5+M6 第 4 周。
