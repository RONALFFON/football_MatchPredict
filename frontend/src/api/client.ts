import axios from 'axios'

const TOKEN_KEY = 'mp_token'

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function setToken(token: string) {
  token ? localStorage.setItem(TOKEN_KEY, token) : localStorage.removeItem(TOKEN_KEY)
}

// 开发环境走 vite proxy（baseURL 留空）；生产由 VITE_API_BASE_URL 注入
export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 60000,
})

http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 统一响应契约：{ code, message, data }；code !== 0 视为业务错误
http.interceptors.response.use(
  (resp) => {
    const body = resp.data
    if (body && typeof body === 'object' && 'code' in body && body.code !== 0) {
      return Promise.reject(new Error(body.message || '请求失败'))
    }
    return resp
  },
  (error) => {
    const detail = error.response?.data?.detail
    const message = typeof detail === 'object' ? detail?.message : detail
    if (error.response?.status === 401) setToken('')
    return Promise.reject(new Error(message || error.message || '网络错误'))
  },
)

/** 提取契约体的 data 字段 */
export function unwrap<T = any>(resp: { data: { data: T; message?: string } }): T {
  return resp.data.data
}
