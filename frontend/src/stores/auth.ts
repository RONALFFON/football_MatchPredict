import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as api from '@/api'
import { setToken, getToken, ApiError } from '@/api/client'
import type { UserInfo } from '@/api/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserInfo | null>(null)
  const authModalOpen = ref(false)
  const authModalTab = ref<'login' | 'register'>('login')

  const isLoggedIn = computed(() => !!user.value)

  async function login(username: string, password: string) {
    const data = await api.login(username, password)
    setToken(data.token)
    user.value = data.user
  }

  async function register(username: string, email: string, password: string) {
    await api.register(username, email, password)
  }

  async function fetchMe() {
    const token = getToken()
    try {
      const data = await api.getMe()
      if (getToken() === token) user.value = data.user
    } catch (error) {
      if (getToken() === token && error instanceof ApiError && error.code === 401) logout()
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

  return { user, authModalOpen, authModalTab, isLoggedIn, login, register, fetchMe, logout, openModal }
})
