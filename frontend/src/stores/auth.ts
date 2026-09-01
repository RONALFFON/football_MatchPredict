import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as api from '../api'
import { setToken } from '../api/client'
import type { UserInfo } from '../api/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserInfo | null>(null)
  const authModalOpen = ref(false)
  const authModalTab = ref<'login' | 'register'>('login')

  const isLoggedIn = computed(() => !!user.value)
  const remaining = computed(() => {
    if (!user.value) return 0
    return -1
  })

  async function login(username: string, password: string) {
    const data = await api.login(username, password)
    setToken(data.token)
    user.value = data.user
  }

  async function register(username: string, email: string, password: string) {
    await api.register(username, email, password)
  }

  async function fetchMe() {
    try {
      const data = await api.getMe()
      user.value = data.user
    } catch {
      logout()
    }
  }

  function logout() {
    setToken('')
    user.value = null
  }

  function openModal(tab: 'login' | 'register') {
    authModalTab.value = tab
    authModalOpen.value = true
  }

  return { user, authModalOpen, authModalTab, isLoggedIn, remaining,
           login, register, fetchMe, logout, openModal }
})
