# 环境变量配置指南

项目使用统一的 AI 配置接入模型服务，当前默认是商汤日日新（SenseNova）；所有敏感信息只通过环境变量读取。

## 必需的环境变量

### 1. AI_API_KEY
- **描述**: 当前 AI 厂商的 API Key
- **必需**: 是（如果使用AI预测功能）
- **示例**: `AI_API_KEY=your_api_key_here`

### 2. AI_MODEL
- **描述**: 当前 AI 厂商的模型名称
- **必需**: 否（有默认值）
- **默认值**: `sensenova-6.7-flash-lite`
- **示例**: `AI_MODEL=sensenova-6.7-flash-lite`

### 3. AI_BASE_URL
- **描述**: 当前 AI 厂商的 OpenAI 兼容接口地址
- **必需**: 否（有默认值）
- **默认值**: `https://token.sensenova.cn/v1`

## 本地开发配置

### 方法1: 使用 .env 文件
在 `backend/.env` 中配置（已在 .gitignore 中）：
```bash
AI_API_KEY=your_api_key_here
AI_MODEL=sensenova-6.7-flash-lite
AI_BASE_URL=https://token.sensenova.cn/v1
```

### 方法2: 直接设置环境变量
```bash
export AI_API_KEY="your_api_key_here"
export AI_MODEL="sensenova-6.7-flash-lite"
export AI_BASE_URL="https://token.sensenova.cn/v1"
```

## Vercel 部署配置

1. 登录 Vercel 控制台
2. 选择你的项目
3. 进入 "Settings" → "Environment Variables"
4. 添加以下环境变量：
   - Name: `AI_API_KEY`, Value: `当前 AI 厂商的 API Key`
   - Name: `AI_MODEL`, Value: `sensenova-6.7-flash-lite`
   - Name: `AI_BASE_URL`, Value: `https://token.sensenova.cn/v1`

## 安全注意事项

1. API Key 不要提交到版本控制系统或硬编码到前端源码。
2. API Key 泄露后，应在日日新控制台禁用并重新创建。
3. 生产环境优先使用 Vercel Secret 或其他 Secret 管理服务。

## 功能说明

- 如果未设置 `AI_API_KEY`，AI预测功能将不可用，但经典模式和彩票模式仍然可以正常使用
- 经典模式使用本地算法，不依赖任何外部API
- 彩票模式爬取公开数据，不需要 AI API Key
