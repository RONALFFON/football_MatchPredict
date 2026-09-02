import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface ToastItem {
  id: number
  message: string
  type: 'success' | 'error' | 'info'
}

export const useToastStore = defineStore('toast', () => {
  const items = ref<ToastItem[]>([])
  let nextId = 0

  function push(message: string, type: ToastItem['type'] = 'info', duration = 3000) {
    const id = nextId++
    items.value.push({ id, message, type })
    if (duration > 0) setTimeout(() => remove(id), duration)
  }

  function remove(id: number) {
    items.value = items.value.filter((t) => t.id !== id)
  }

  return {
    items,
    push,
    remove,
    success: (msg: string) => push(msg, 'success'),
    error: (msg: string) => push(msg, 'error'),
    info: (msg: string) => push(msg, 'info'),
  }
})
