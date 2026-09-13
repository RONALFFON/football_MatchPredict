<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import * as api from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import type { AccountData, MembershipChange, MembershipEvent } from '@/api/types'

const auth = useAuthStore()
const toast = useToastStore()
const account = ref<AccountData | null>(null)
const loading = ref(false)
const error = ref('')
const offset = ref(0)
const user = computed(() => account.value?.user)
const statuses = { free: '普通用户', active: '有效会员', expired: '会员已到期', lifetime: '长期会员', frozen: '会员已冻结', revoked: '会员已撤销' }
const labels: Record<string, string> = { classic: '经典预测', lottery: '彩票预测', ai: 'AI 分析', agent: '英超 AI 对话', save: '保存结果' }
const username = ref('')
const action = ref<MembershipChange['action']>('extend')
const plan = ref<'monthly' | 'annual'>('monthly')
const reason = ref('')
const managing = ref(false)
const adminError = ref('')
const events = ref<MembershipEvent[]>([])
let pending: { fingerprint: string; id: string } | null = null
let generation = 0
onUnmounted(() => { generation++ })

function formatDate(value?: string | null) {
  if (!value) return '无到期时间'
  return new Intl.DateTimeFormat('zh-CN', { timeZone: user.value?.timezone || 'Asia/Shanghai',
    dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

async function load(nextOffset = offset.value) {
  const request = ++generation
  loading.value = true
  error.value = ''
  try {
    const data = await api.getAccount(nextOffset)
    if (request !== generation || !auth.isLoggedIn) return
    account.value = data
    auth.user = data.user
    offset.value = nextOffset
  } catch (e) {
    if (request === generation) error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    if (request === generation) loading.value = false
  }
}
watch(() => auth.user?.username, (value) => {
  generation++
  account.value = null
  events.value = []
  error.value = ''
  loading.value = false
  if (value) load(0)
}, { immediate: true })

async function history() {
  events.value = (await api.getMembershipHistory(username.value.trim())).events
}
async function loadHistory() {
  if (managing.value || !username.value.trim()) return
  managing.value = true
  adminError.value = ''
  try { await history() } catch (e) { adminError.value = e instanceof Error ? e.message : '加载失败' }
  finally { managing.value = false }
}
async function changeMembership() {
  if (managing.value || !username.value.trim() || reason.value.trim().length < 2) return
  const payload = { action: action.value, plan: action.value === 'extend' ? plan.value : undefined, reason: reason.value.trim() }
  const fingerprint = JSON.stringify([username.value.trim(), payload])
  if (!pending || pending.fingerprint !== fingerprint) pending = { fingerprint, id: crypto.randomUUID() }
  if (!window.confirm(`确认对 ${username.value.trim()} 执行会员操作？原因：${payload.reason}`)) return
  managing.value = true
  adminError.value = ''
  try {
    await api.updateMembership(username.value.trim(), { ...payload, request_id: pending.id })
    pending = null
    toast.success('会员权益已更新')
    reason.value = ''
    await history()
    if (username.value.trim() === auth.user?.username) await load()
  } catch (e) { adminError.value = e instanceof Error ? e.message : '操作失败，可使用原请求重试' }
  finally { managing.value = false }
}
</script>

<template>
  <h1 class="page-title">个人中心</h1>
  <p class="page-sub">查看会员权益、AI 剩余次数和已保存的分析。</p>
  <div v-if="!auth.isLoggedIn" class="card empty"><p>登录后查看个人权益</p><button class="btn primary" @click="auth.openModal('login')">登录</button></div>
  <template v-else>
    <p v-if="error" class="alert error" role="alert">{{ error }} <button class="btn ghost" @click="load()">重试</button></p>
    <p v-if="loading && !user" class="empty">正在加载个人信息…</p>
    <template v-if="user">
      <div class="grid-2">
        <section class="card">
          <h2 class="card-title">{{ user.username }} · {{ statuses[user.membership_status] }}</h2>
          <p>到期时间：{{ formatDate(user.membership_expires) }}</p>
          <p>今日 AI 用量：{{ user.daily_used }} 次</p>
          <p>剩余次数：{{ user.remaining === null ? '不限次数' : `${user.remaining} / ${user.daily_limit}` }}</p>
          <p class="text-dim">额度重置：{{ formatDate(user.quota_resets_at) }}（{{ user.timezone }}）</p>
          <button class="btn ghost" :disabled="loading" @click="load()">刷新权益</button>
        </section>
        <section class="card">
          <h2 class="card-title">权益说明</h2>
          <p v-for="(text, mode) in user.rules" :key="mode">{{ labels[mode] }}：{{ text }}</p>
          <p>会员支持月度、年度有效期；续期从尚未到期的有效期末顺延。</p>
          <p class="text-dim">暂未开放在线购买。冻结期间到期时间继续计算。</p>
        </section>
      </div>
      <section class="card mt-12">
        <h2 class="card-title">已保存的预测与分析</h2>
        <p class="text-dim">这里只展示保存记录，不作为完整的 AI 用量账单。</p>
        <p v-if="!account?.saved_predictions.length" class="empty">暂无保存记录</p>
        <div v-for="item in account?.saved_predictions" :key="item.prediction_id" class="match-row">
          <div>{{ item.home_team }} vs {{ item.away_team }}<p class="text-dim">{{ item.prediction_mode }} · {{ item.predicted_result }}</p></div>
          <time>{{ formatDate(item.created_at) }}</time>
        </div>
        <div class="toolbar"><button class="btn ghost" :disabled="offset === 0 || loading" @click="load(Math.max(0, offset - 20))">上一页</button><button class="btn ghost" :disabled="!account?.has_more || loading" @click="load(offset + 20)">下一页</button></div>
      </section>
      <section v-if="user.is_admin" class="card mt-12">
        <h2 class="card-title">会员管理</h2>
        <p class="text-dim">人工开通不代表收到付款；每次变更都会记录原因与操作人。</p>
        <form @submit.prevent="changeMembership">
          <fieldset :disabled="managing">
            <div class="form-row"><label for="member-user" class="form-label">目标用户名</label><input id="member-user" class="input" v-model="username" required maxlength="50" /></div>
            <div class="grid-2">
              <div class="form-row"><label for="member-action" class="form-label">操作</label><select id="member-action" class="select" v-model="action"><option value="extend">开通或续期</option><option value="freeze">冻结会员</option><option value="unfreeze">解除冻结</option><option value="revoke">撤销会员</option></select></div>
              <div v-if="action === 'extend'" class="form-row"><label for="member-plan" class="form-label">有效期</label><select id="member-plan" class="select" v-model="plan"><option value="monthly">月度会员 · 1 个自然月</option><option value="annual">年度会员 · 12 个自然月</option></select></div>
            </div>
            <div class="form-row"><label for="member-reason" class="form-label">操作原因</label><textarea id="member-reason" class="input" v-model="reason" required minlength="2" maxlength="500" /></div>
            <div class="toolbar"><button class="btn primary" type="submit">{{ managing ? '处理中…' : '确认变更' }}</button><button class="btn ghost" type="button" @click="loadHistory">查询最近变更</button></div>
          </fieldset>
        </form>
        <p v-if="adminError" class="alert error" role="alert">{{ adminError }}</p>
        <details v-for="(event, index) in events" :key="index" class="mt-12"><summary>{{ formatDate(event.created_at) }} · {{ event.action }} · 操作人 #{{ event.actor_user_id }}</summary><p>{{ event.reason }}</p><p>变更前：{{ event.before_state }}</p><p>变更后：{{ event.after_state }}</p></details>
      </section>
    </template>
  </template>
</template>
