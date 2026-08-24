<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { getToken } from '../api/client'
import AuthModal from '../components/AuthModal.vue'

const auth = useAuthStore()

onMounted(() => {
  if (getToken()) auth.fetchMe()
})
</script>

<template>
  <nav class="navbar">
    <div class="nav-container">
      <router-link to="/" class="nav-brand">
        <span class="ball">⚽</span> MatchPredict
      </router-link>

      <!-- 五大联赛 -->
      <div class="nav-group">
        <span class="nav-group-label">五大联赛</span>
        <router-link to="/" class="nav-btn" exact-active-class="active">经典模式</router-link>
        <router-link to="/lottery" class="nav-btn">彩票模式</router-link>
        <router-link to="/ai" class="nav-btn">AI智能</router-link>
      </div>

      <div class="nav-divider" />

      <!-- 英超专项 -->
      <div class="nav-group">
        <span class="nav-group-label">英超专项</span>
        <router-link to="/pl" class="nav-btn" exact-active-class="pl-active">总览</router-link>
        <router-link to="/pl/matches" class="nav-btn" active-class="pl-active">赛程</router-link>
        <router-link to="/pl/standings" class="nav-btn" active-class="pl-active">积分榜</router-link>
        <router-link to="/pl/ai" class="nav-btn" active-class="pl-active">AI 分析</router-link>
      </div>

      <!-- 用户区 -->
      <div class="nav-user">
        <template v-if="auth.isLoggedIn && auth.user">
          <span class="badge">{{ auth.user.username }}</span>
          <span class="badge" :class="{ premium: auth.user.user_type === 'premium' }">
            {{ auth.user.user_type === 'premium' ? '会员' : '免费' }}
          </span>
          <span class="badge quota">
            {{ auth.remaining === -1 ? '无限制' : `今日剩余 ${auth.remaining}/3` }}
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
    <router-view />
  </main>

  <AuthModal v-if="auth.authModalOpen" />
</template>
