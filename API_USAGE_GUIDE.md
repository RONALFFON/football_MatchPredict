# 🤖 AI预测功能使用指南

## 🚀 功能说明

项目使用统一的 AI 配置提供足球比赛分析，当前默认接入商汤日日新（SenseNova）。新版前端优先通过后端代理调用，旧版页面保留直连兼容方式。

## 🔑 API密钥配置

### 后端配置（推荐）

在 `backend/.env` 中填写：

```bash
AI_API_KEY=your_api_key_here
AI_MODEL=sensenova-6.7-flash-lite
AI_BASE_URL=https://token.sensenova.cn/v1
```

API Key 可在 [日日新控制台](https://platform.sensenova.cn/console) 创建。

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

经典模式使用本地算法，不需要日日新 API Key。

## 🔧 技术实现

日日新接口采用 OpenAI 兼容的 Chat Completions 格式：

```text
POST https://token.sensenova.cn/v1/chat/completions
Authorization: Bearer <AI_API_KEY>
```

提示词包含比赛分析、胜平负、比分、半全场、进球数和风险提示。

## 🔍 故障排除

- `AI服务未配置`：检查 `backend/.env` 中是否填写 `AI_API_KEY`，并重启后端。
- `401`：检查 API Key 是否正确、是否已在控制台开通服务。
- `404`：检查模型名和 `AI_BASE_URL` 是否匹配。
- `429`：稍后重试，服务端已对限流进行重试处理。
