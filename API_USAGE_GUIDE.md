# 🤖 AI预测功能使用指南

## 🚀 功能说明

项目使用统一的 AI 配置提供足球比赛分析，服务端只调用部署者配置的模型服务接口。新版前端优先通过后端代理调用，旧版页面保留直连兼容方式。

## 🔑 API密钥配置

### 后端配置（推荐）

在 `backend/.env` 中填写：

```bash
# 远程厂商
AI_MODE=api_key
AI_API_KEY=your_api_key_here
AI_MODEL=your-model-name
AI_BASE_URL=你的远程OpenAI兼容接口地址
```

API Key 请在你选择的模型厂商控制台创建。

如果使用本地部署的 GGUF 开源模型，请先用推理服务加载模型并暴露 OpenAI 兼容接口，然后将配置改为：

```bash
AI_MODE=local
AI_API_KEY=
AI_MODEL=你的本地模型名
AI_BASE_URL=你的本地GGUF推理服务地址
```

本地服务未开启鉴权时 `AI_API_KEY` 留空；如果 LM Studio 的 Server Settings 开启了 API Key 鉴权，则填写本地服务对应的 Key，项目会在本地模式下自动发送它。

本地 URL 必须从后端运行环境可访问；例如后端在 Docker 中运行时，容器内的 `localhost` 不是宿主机。项目会自动补上 `/chat/completions`，也接受已经包含该路径的完整 URL。

以 LM Studio 加载 GGUF 为例，`AI_BASE_URL` 使用服务器地址加 `/v1`，`AI_MODEL` 使用模型接口返回的标识，不填写 GGUF 文件路径：

```bash
curl http://127.0.0.1:<LM Studio端口>/v1/models
# 将返回的 data[0].id 填入 AI_MODEL
AI_BASE_URL=http://127.0.0.1:<LM Studio端口>/v1
```

### 旧版页面临时配置

如果使用旧版 Flask 页面，可在浏览器控制台临时设置：

```javascript
localStorage.setItem('AI_API_KEY', 'your_api_key_here')
```

生产环境不要把 API Key 注入公开页面；应配置后端环境变量并通过后端接口调用。

## 📍 使用方法

1. 启动后端和前端。
2. 切换到“AI智能模式”或“彩票模式”。
3. 填写或选择比赛信息。
4. 点击“AI智能预测”。

经典模式使用本地算法，不需要 AI API Key。

## 🔧 技术实现

远程和本地服务都需要提供 OpenAI 兼容的 Chat Completions 接口：

```text
POST <AI_BASE_URL>/chat/completions
Authorization: Bearer <AI_API_KEY>  # 配置了 AI_API_KEY 时发送；未配置时省略
```

提示词包含比赛分析、胜平负、比分、半全场、进球数和风险提示。

## 🔍 故障排除

- `AI服务未配置`：远程模式检查 `AI_API_KEY`；本地模式检查 `AI_BASE_URL` 和 `AI_MODE=local`，并重启后端。
- `401`：远程模式检查厂商 API Key；本地模式检查 LM Studio 是否开启鉴权，并确认 `AI_API_KEY` 与本地 Key 一致。
- `404`：检查模型名和 `AI_BASE_URL` 是否匹配。
- `429`：稍后重试，服务端已对限流进行重试处理。
