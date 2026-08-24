<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const username = ref('')
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    if (auth.authModalTab === 'login') {
      await auth.login(username.value, password.value)
      auth.authModalOpen = false
    } else {
      await auth.register(username.value, email.value, password.value)
      auth.authModalTab = 'login'
      error.value = ''
      alert('注册成功，请登录')
    }
  } catch (e: any) {
    error.value = e.message || '操作失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="modal-mask" @click.self="auth.authModalOpen = false">
    <div class="modal">
      <div class="modal-tabs">
        <div class="tab" :class="{ active: auth.authModalTab === 'login' }"
             @click="auth.authModalTab = 'login'">登录</div>
        <div class="tab" :class="{ active: auth.authModalTab === 'register' }"
             @click="auth.authModalTab = 'register'">注册</div>
      </div>

      <div v-if="error" class="alert error">{{ error }}</div>

      <div class="form-row">
        <label class="form-label">用户名</label>
        <input class="input" v-model="username" placeholder="至少3个字符" />
      </div>
      <div v-if="auth.authModalTab === 'register'" class="form-row">
        <label class="form-label">邮箱</label>
        <input class="input" v-model="email" type="email" placeholder="you@example.com" />
      </div>
      <div class="form-row">
        <label class="form-label">密码</label>
        <input class="input" v-model="password" type="password"
               placeholder="至少6个字符" @keyup.enter="submit" />
      </div>

      <button class="btn primary" style="width: 100%" :disabled="loading" @click="submit">
        {{ loading ? '处理中…' : (auth.authModalTab === 'login' ? '登 录' : '注 册') }}
      </button>
    </div>
  </div>
</template>
