# 环境变量配置指南

项目使用统一的 AI 配置接入 OpenAI 兼容模型服务；所有敏感信息只通过环境变量读取，不在代码中内置厂商地址、模型名或密钥。

## AI 配置

### 1. AI_MODE
- **描述**: AI 接入方式
- **可选值**: `api_key`（远程厂商）或 `local`（本地部署）
- **必需**: 是

### 2. AI_API_KEY
- **描述**: 当前 AI 厂商的 API Key
- **必需**: `AI_MODE=api_key` 时必需；`AI_MODE=local` 时通常可留空，但本地服务开启鉴权时需要填写
- **示例**: `AI_API_KEY=your_api_key_here`

### 3. AI_MODEL
- **描述**: 当前 AI 服务的模型名称
- **必需**: 是
- **示例**: `AI_MODEL=your-model-name`

### 4. AI_BASE_URL
- **描述**: 当前 AI 服务的接口地址；本地 GGUF 需要先由推理服务暴露 OpenAI 兼容接口
- **必需**: 是
- **示例**: `AI_BASE_URL=你的模型服务地址`

## 本地开发配置

### 方法1: 使用 .env 文件
在 `backend/.env` 中配置（已在 .gitignore 中）：
```bash
# 远程厂商
AI_MODE=api_key
AI_API_KEY=your_api_key_here
AI_MODEL=your-model-name
AI_BASE_URL=你的远程OpenAI兼容接口地址

# 本地 GGUF 模型：先用推理服务加载 GGUF，并暴露 OpenAI 兼容接口（与上面二选一）
# AI_MODE=local
# AI_API_KEY=
# AI_MODEL=你的本地模型名
# AI_BASE_URL=你的本地OpenAI兼容接口地址（通常包含 /v1）
```

本地 OpenAI 兼容服务未开启鉴权时 `AI_API_KEY` 留空；如果 LM Studio Server Settings 开启了 API Key 鉴权，填写本地服务对应的 Key。

如果使用 LM Studio 加载 GGUF，先请求 `GET <服务地址>/v1/models`，将返回的模型 `id` 填入 `AI_MODEL`；GGUF 文件路径本身不填入环境变量。

### 方法2: 直接设置环境变量
```bash
export AI_MODE="api_key"  # 或 local
export AI_API_KEY="your_api_key_here"
export AI_MODEL="your-model-name"
export AI_BASE_URL="你的远程OpenAI兼容接口地址"
```

## Vercel 部署配置

1. 登录 Vercel 控制台
2. 选择你的项目
3. 进入 "Settings" → "Environment Variables"
4. 添加以下环境变量：
   - Name: `AI_MODE`, Value: `api_key` 或 `local`
   - Name: `AI_API_KEY`, Value: `远程模式或开启鉴权的本地服务 Key`
   - Name: `AI_MODEL`, Value: `当前 AI 服务的模型名`
   - Name: `AI_BASE_URL`, Value: `当前 AI 服务的 OpenAI 兼容接口地址`

## 安全注意事项

1. API Key 不要提交到版本控制系统或硬编码到前端源码。
2. GGUF 文件不能直接作为 URL；本地模式的 URL 必须指向已加载 GGUF 的推理服务，并能被运行后端的机器访问。
3. 生产环境优先使用 Vercel Secret 或其他 Secret 管理服务。

## 功能说明

- `AI_MODE=api_key` 时必须设置 `AI_API_KEY`。
- `AI_MODE=local` 时通常不强制要求 API Key；若本地服务开启鉴权则必须填写，同时必须设置可访问的 `AI_BASE_URL`。
- 两种模式都必须设置 `AI_MODEL` 和 `AI_BASE_URL`。
- 经典模式使用本地算法，不依赖任何外部API
- 彩票模式爬取公开数据，不需要 AI API Key
