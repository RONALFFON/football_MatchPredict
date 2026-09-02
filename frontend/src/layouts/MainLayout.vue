<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { getToken } from '@/api/client'
import AuthModal from '@/components/AuthModal.vue'
import ToastContainer from '@/components/ToastContainer.vue'

const auth = useAuthStore()
const toast = useToastStore()
const mobileMenuOpen = ref(false)

function onUnauthorized() {
  toast.error('登录已过期，请重新登录')
  auth.openModal('login')
}

onMounted(() => {
  if (getToken()) auth.fetchMe()
  window.addEventListener('auth:unauthorized', onUnauthorized)
})

onUnmounted(() => {
  window.removeEventListener('auth:unauthorized', onUnauthorized)
})
</script>

<template>
  <nav class="navbar">
    <div class="nav-container">
      <router-link to="/" class="nav-brand" @click="mobileMenuOpen = false">
        <span class="ball">⚽</span> MatchPredict
      </router-link>

      <button class="nav-hamburger" @click="mobileMenuOpen = !mobileMenuOpen" aria-label="菜单">
        <span :class="{ open: mobileMenuOpen }" />
      </button>

      <div class="nav-links" :class="{ open: mobileMenuOpen }">
        <div class="nav-group">
          <span class="nav-group-label">五大联赛</span>
          <router-link to="/" class="nav-btn" exact-active-class="active" @click="mobileMenuOpen = false">经典模式</router-link>
          <router-link to="/lottery" class="nav-btn" @click="mobileMenuOpen = false">彩票模式</router-link>
          <router-link to="/ai" class="nav-btn" @click="mobileMenuOpen = false">AI智能</router-link>
        </div>

        <div class="nav-divider" />

        <div class="nav-group">
          <span class="nav-group-label">英超专项</span>
          <router-link to="/pl" class="nav-btn" exact-active-class="pl-active" @click="mobileMenuOpen = false">总览</router-link>
          <router-link to="/pl/matches" class="nav-btn" active-class="pl-active" @click="mobileMenuOpen = false">赛程</router-link>
          <router-link to="/pl/standings" class="nav-btn" active-class="pl-active" @click="mobileMenuOpen = false">积分榜</router-link>
          <router-link to="/pl/ai" class="nav-btn" active-class="pl-active" @click="mobileMenuOpen = false">AI 分析</router-link>
        </div>
      </div>

      <div class="nav-user">
        <template v-if="auth.isLoggedIn && auth.user">
          <span class="badge">{{ auth.user.username }}</span>
          <span class="badge" :class="{ premium: auth.user.user_type === 'premium' }">
            {{ auth.user.user_type === 'premium' ? '会员' : '免费' }}
          </span>
          <button class="btn ghost sm" @click="auth.logout()">退出</button>
        </template>
        <template v-else>
          <button class="btn primary sm" @click="auth.openModal('login')">登录</button>
          <button class="btn ghost sm" @click="auth.openModal('register')">注册</button>
        </template>
      </div>
    </div>
  </nav>

  <main class="container">
    <router-view v-slot="{ Component }">
      <Transition name="fade" mode="out-in">
        <component :is="Component" />
      </Transition>
    </router-view>
  </main>

  <AuthModal v-if="auth.authModalOpen" />
  <ToastContainer />
</template>
