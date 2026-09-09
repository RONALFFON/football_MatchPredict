<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { getToken } from '@/api/client'
import AuthModal from '@/components/AuthModal.vue'
import ToastContainer from '@/components/ToastContainer.vue'

const auth = useAuthStore()
const toast = useToastStore()
const route = useRoute()
const mobileMenuOpen = ref(false)
const isPremier = computed(() => route.path === '/pl' || route.path.startsWith('/pl/'))
const links = computed(() => isPremier.value ? [
  { to: '/pl', label: '赛事总览', detail: 'OVERVIEW' },
  { to: '/pl/matches', label: '赛程赛果', detail: 'MATCHES' },
  { to: '/pl/standings', label: '积分榜', detail: 'STANDINGS' },
  { to: '/pl/ai', label: 'AI 对话分析', detail: 'AI ASSISTANT' },
] : [
  { to: '/', label: '经典预测', detail: 'STATISTICS' },
  { to: '/lottery', label: '体彩赛程', detail: 'MATCH CENTER' },
  { to: '/ai', label: 'AI 批量预测', detail: 'AI PREDICTION' },
])
watch(() => route.fullPath, () => { mobileMenuOpen.value = false })
function onUnauthorized() {
  toast.error('登录已过期，请重新登录')
  auth.openModal('login')
}
function closeMenu(event: KeyboardEvent) {
  if (event.key === 'Escape') mobileMenuOpen.value = false
}
onMounted(() => {
  if (getToken()) auth.fetchMe()
  window.addEventListener('auth:unauthorized', onUnauthorized)
  window.addEventListener('keydown', closeMenu)
})
onUnmounted(() => {
  window.removeEventListener('auth:unauthorized', onUnauthorized)
  window.removeEventListener('keydown', closeMenu)
})
</script>

<template>
  <a class="skip-link" href="#main-content">跳转到内容</a>
  <header class="navbar">
    <div class="nav-container">
      <router-link to="/" class="nav-brand" aria-label="MatchPredict 首页">
        <span class="brand-mark" aria-hidden="true">M<span>.</span></span>
        <span>MatchPredict<small>读懂比赛 · 看见可能</small></span>
      </router-link>
      <nav class="workspace-tabs" aria-label="赛事范围">
        <router-link to="/" :class="{ selected: !isPremier }">五大联赛</router-link>
        <router-link to="/pl" :class="{ selected: isPremier }">英超专项</router-link>
      </nav>
      <div class="nav-user">
        <template v-if="auth.isLoggedIn && auth.user">
          <span class="user-name">{{ auth.user.username }}</span>
          <span class="badge" :class="{ premium: auth.user.user_type === 'premium' }">{{ auth.user.user_type === 'premium' ? '会员' : '免费' }}</span>
          <button class="btn ghost sm" @click="auth.logout()">退出</button>
        </template>
        <template v-else>
          <button class="btn ghost sm" @click="auth.openModal('login')">登录</button>
          <button class="btn primary sm" @click="auth.openModal('register')">注册</button>
        </template>
      </div>
      <button class="nav-hamburger" @click="mobileMenuOpen = !mobileMenuOpen" :aria-expanded="mobileMenuOpen" aria-controls="page-navigation" aria-label="切换导航菜单"><span :class="{ open: mobileMenuOpen }" /></button>
    </div>
    <nav id="page-navigation" class="subnav" :class="{ open: mobileMenuOpen }" aria-label="功能导航">
      <div class="subnav-inner">
        <router-link v-for="link in links" :key="link.to" :to="link.to" class="nav-btn" :class="{ active: route.path === link.to }">
          {{ link.label }}<span>{{ link.detail }}</span>
        </router-link>
        <span class="nav-caption">FOOTBALL INTELLIGENCE</span>
      </div>
    </nav>
  </header>
  <main id="main-content" class="container" tabindex="-1">
    <router-view v-slot="{ Component, route: currentRoute }">
      <Transition name="page" mode="out-in">
        <section :key="currentRoute.path" class="page-content"><component :is="Component" /></section>
      </Transition>
    </router-view>
    <footer class="site-footer"><span>MatchPredict <span class="text-dim">/ 足球数据与分析</span></span><span>每一场比赛，都有更多可能。</span></footer>
  </main>
  <AuthModal v-if="auth.authModalOpen" />
  <ToastContainer />
</template>
