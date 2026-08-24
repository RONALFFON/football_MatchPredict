import { http, unwrap, getToken } from './client'

// ===== 通用 =====
export const getMeta = () => http.get('/api/v1/meta').then(unwrap)
export const getTeams = () => http.get('/api/v1/teams').then(unwrap)

// ===== 五大联赛：彩票模式 =====
export const getLotteryMatches = (days = 3) =>
  http.get('/api/v1/lottery/matches', { params: { days } }).then(unwrap)
export const refreshLottery = (days = 3) =>
  http.post('/api/v1/lottery/refresh', null, { params: { days } }).then(unwrap)

// ===== 五大联赛：预测 =====
export const simplePredict = (matches: any[]) =>
  http.post('/api/v1/predict', { matches }).then(unwrap)
export const aiPredict = (matches: any[]) =>
  http.post('/api/v1/ai/predict', { matches }).then(unwrap)
export const savePrediction = (payload: {
  mode: string; match_data: any; prediction_result: string
  confidence?: number; ai_analysis?: string
}) => http.post('/api/v1/save-prediction', payload).then(unwrap)

// ===== 认证 =====
export const register = (username: string, email: string, password: string) =>
  http.post('/api/v1/auth/register', { username, email, password }).then(() => null)
export const login = (username: string, password: string) =>
  http.post('/api/v1/auth/login', { username, password }).then(unwrap)
export const getMe = () => http.get('/api/v1/auth/me').then(unwrap)

// ===== 英超专项 =====
export const getPlMatches = (status?: string, limit = 50) =>
  http.get('/api/v1/pl/matches', { params: { status, limit } }).then(unwrap)
export const getPlStandings = () => http.get('/api/v1/pl/standings').then(unwrap)
export const getPlTeam = (name: string) => http.get(`/api/v1/pl/teams/${encodeURIComponent(name)}`).then(unwrap)

// ===== 英超 Agent：SSE 流式对话 =====
export interface AgentEvent {
  type: 'tool_call' | 'tool_result' | 'text_delta' | 'done' | 'error'
  [key: string]: any
}

export async function* chatAgent(
  message: string,
  history: { role: string; text: string }[],
): AsyncGenerator<AgentEvent> {
  const resp = await fetch('/api/v1/pl/agent/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
    },
    body: JSON.stringify({ message, history }),
  })

  // 401/403 等非流式错误：后端返回契约 JSON
  const contentType = resp.headers.get('content-type') || ''
  if (!resp.ok || !contentType.includes('text/event-stream')) {
    const body = await resp.json().catch(() => null)
    const msg = body?.detail?.message || body?.message || `请求失败(${resp.status})`
    yield { type: 'error', message: msg }
    return
  }

  const reader = resp.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const data = line.slice(6).trim()
      if (data === '[DONE]') return
      try {
        yield JSON.parse(data) as AgentEvent
      } catch {
        /* 忽略不完整块 */
      }
    }
  }
}
