import { http, unwrap, getToken } from './client'
import type {
  AgentEvent,
  AiPrediction,
  ClassicPrediction,
  LotteryMatch,
  MatchInput,
  PlMatch,
  Standing,
  TeamsData,
  UserInfo,
} from './types'

interface MatchList<T> {
  matches: T[]
  count?: number
  source?: string
}

export const getMeta = () => http.get('/api/v1/meta').then(unwrap)
export const getTeams = () => http.get('/api/v1/teams').then(unwrap<TeamsData>)

export const getLotteryMatches = (days = 3) =>
  http.get('/api/v1/lottery/matches', { params: { days } }).then(unwrap<MatchList<LotteryMatch>>)

export const refreshLottery = (days = 3) =>
  http.post('/api/v1/lottery/refresh', null, { params: { days } }).then(unwrap<MatchList<LotteryMatch>>)

export const simplePredict = (matches: MatchInput[]) =>
  http.post('/api/v1/predict', { matches }).then(
    unwrap<{ individual_predictions: ClassicPrediction[] }>,
  )

export const aiPredict = (matches: MatchInput[]) =>
  http.post('/api/v1/ai/predict', { matches }).then(
    unwrap<{ predictions: AiPrediction[]; count: number }>,
  )

export const savePrediction = (payload: {
  mode: string
  match_data: Record<string, unknown>
  prediction_result: string
  confidence?: number
  ai_analysis?: string
}) => http.post('/api/v1/save-prediction', payload).then(unwrap<{ user: UserInfo }>)

export const register = (username: string, email: string, password: string) =>
  http.post('/api/v1/auth/register', { username, email, password }).then(() => null)

export const login = (username: string, password: string) =>
  http.post('/api/v1/auth/login', { username, password }).then(
    unwrap<{ token: string; user: UserInfo }>,
  )

export const getMe = () => http.get('/api/v1/auth/me').then(unwrap<{ user: UserInfo }>)

export const getPlMatches = (status?: string, limit = 50) =>
  http.get('/api/v1/pl/matches', { params: { status, limit } }).then(unwrap<{ matches: PlMatch[] }>)

export const getPlStandings = () =>
  http.get('/api/v1/pl/standings').then(unwrap<{ standings: Standing[] }>)

export const getPlTeam = (name: string) =>
  http.get(`/api/v1/pl/teams/${encodeURIComponent(name)}`).then(unwrap)

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

  const contentType = resp.headers.get('content-type') || ''
  if (!resp.ok || !contentType.includes('text/event-stream')) {
    const body = await resp.json().catch(() => null)
    const msg = body?.detail?.message || body?.message || `请求失败(${resp.status})`
    yield { type: 'error', message: msg }
    return
  }

  const reader = resp.body?.getReader()
  if (!reader) {
    yield { type: 'error', message: '服务器未返回流式内容' }
    return
  }

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
        // 等待下一段完整事件
      }
    }
  }
}
