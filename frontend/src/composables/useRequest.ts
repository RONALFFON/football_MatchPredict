import { ref, shallowRef, onScopeDispose } from 'vue'
import { errorMessage } from '@/shared/error'

/**
 * 通用异步请求封装：统一管理 loading / error / abort
 * 消除各 View 中重复的 try-catch + loading 样板代码
 */
export function useRequest<T = unknown>() {
  const data = shallowRef<T | undefined>(undefined)
  const loading = ref(false)
  const error = ref('')
  let controller: AbortController | null = null

  async function execute(fn: (signal: AbortSignal) => Promise<T>): Promise<T | undefined> {
    if (loading.value) return undefined
    controller?.abort()
    controller = new AbortController()
    loading.value = true
    error.value = ''
    try {
      const result = await fn(controller.signal)
      data.value = result
      return result
    } catch (e: unknown) {
      if ((e as Error).name === 'AbortError') return undefined
      error.value = errorMessage(e)
      return undefined
    } finally {
      loading.value = false
      controller = null
    }
  }

  function abort() {
    controller?.abort()
  }

  onScopeDispose(() => controller?.abort())

  return { data, loading, error, execute, abort }
}
