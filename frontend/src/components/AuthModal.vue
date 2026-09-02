<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { errorMessage } from '@/shared/error'

const auth = useAuthStore()
const toast = useToastStore()

const username = ref('')
const email = ref('')
const password = ref('')
const loading = ref(false)
const touched = ref({ username: false, email: false, password: false })

const isRegister = computed(() => auth.authModalTab === 'register')

const errors = computed(() => {
  const e: Record<string, string> = {}
  if (touched.value.username && username.value.length < 3) e.username = '用户名至少 3 个字符'
  if (touched.value.email && isRegister.value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value))
    e.email = '请输入有效邮箱'
  if (touched.value.password && password.value.length < 6) e.password = '密码至少 6 个字符'
  return e
})

const hasError = computed(() => Object.keys(errors.value).length > 0)

async function submit() {
  touched.value = { username: true, email: true, password: true }
  if (hasError.value) return

  loading.value = true
  try {
    if (isRegister.value) {
      await auth.register(username.value, email.value, password.value)
      auth.authModalTab = 'login'
      toast.success('注册成功，请登录')
    } else {
      await auth.login(username.value, password.value)
      auth.authModalOpen = false
      toast.success(`欢迎回来，${username.value}`)
    }
  } catch (e: unknown) {
    toast.error(errorMessage(e, '操作失败'))
  } finally {
    loading.value = false
  }
}

function switchTab(tab: 'login' | 'register') {
  auth.authModalTab = tab
  touched.value = { username: false, email: false, password: false }
}
</script>

<template>
  <div class="modal-mask" @click.self="auth.authModalOpen = false">
    <div class="modal">
      <div class="modal-tabs">
        <div class="tab" :class="{ active: !isRegister }" @click="switchTab('login')">登录</div>
        <div class="tab" :class="{ active: isRegister }" @click="switchTab('register')">注册</div>
      </div>

      <div class="form-row">
        <label class="form-label">用户名</label>
        <input class="input" v-model="username" placeholder="至少 3 个字符"
               :class="{ invalid: errors.username }" @blur="touched.username = true" />
        <span v-if="errors.username" class="field-error">{{ errors.username }}</span>
      </div>

      <div v-if="isRegister" class="form-row">
        <label class="form-label">邮箱</label>
        <input class="input" v-model="email" type="email" placeholder="you@example.com"
               :class="{ invalid: errors.email }" @blur="touched.email = true" />
        <span v-if="errors.email" class="field-error">{{ errors.email }}</span>
      </div>

      <div class="form-row">
        <label class="form-label">密码</label>
        <input class="input" v-model="password" type="password" placeholder="至少 6 个字符"
               :class="{ invalid: errors.password }" @blur="touched.password = true"
               @keyup.enter="submit" />
        <span v-if="errors.password" class="field-error">{{ errors.password }}</span>
      </div>

      <button class="btn primary" style="width: 100%" :disabled="loading || hasError" @click="submit">
        {{ loading ? '处理中…' : (isRegister ? '注 册' : '登 录') }}
      </button>
    </div>
  </div>
</template>
