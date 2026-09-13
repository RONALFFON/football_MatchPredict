<script setup lang="ts">
import { onMounted, ref } from 'vue'
import * as api from '@/api'
import type { AdminOverview } from '@/api/types'
import { useToastStore } from '@/stores/toast'

const toast = useToastStore()
const overview = ref<AdminOverview | null>(null)
const loading = ref(false)
const refreshing = ref(false)
const error = ref('')

const capabilityLabels: Record<string, string> = {
  membership_management: '会员开通、续期、冻结与撤销',
  membership_audit: '会员操作审计',
  lottery_live_refresh: '体彩数据实时刷新',
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    overview.value = await api.getAdminOverview()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '管理信息加载失败'
  } finally {
    loading.value = false
  }
}

async function refreshLottery() {
  if (refreshing.value) return
  refreshing.value = true
  try {
    const result = await api.refreshLottery(7)
    toast.success(`已从体彩接口获取 ${result.count ?? result.matches.length} 场比赛`)
  } catch (cause) {
    toast.error(cause instanceof Error ? cause.message : '刷新失败')
  } finally {
    refreshing.value = false
  }
}

onMounted(load)
</script>

<template>
  <h1 class="page-title">系统管理</h1>
  <p class="page-sub">系统管理员专属区域。页面入口和服务端接口均进行权限校验。</p>

  <p v-if="error" class="alert error" role="alert">{{ error }} <button class="btn ghost" @click="load">重试</button></p>
  <p v-if="loading && !overview" class="empty">正在加载系统状态…</p>

  <template v-if="overview">
    <div class="grid-2">
      <section class="card">
        <h2 class="card-title">服务状态</h2>
        <p>数据库配置：{{ overview.database_configured ? '已配置' : '未配置' }}</p>
        <p>AI 服务：{{ overview.ai_ready ? '可用' : '未就绪' }}</p>
        <p>AI 模型：{{ overview.ai_model || '未配置' }}</p>
        <p>业务时区：{{ overview.business_timezone }}</p>
        <p>在线支付：{{ overview.payment_enabled ? '已启用' : '暂未启用' }}</p>
      </section>

      <section class="card">
        <h2 class="card-title">管理员能力</h2>
        <p v-for="item in overview.capabilities" :key="item">{{ capabilityLabels[item] || item }}</p>
      </section>
    </div>

    <section class="card mt-12">
      <h2 class="card-title">管理操作</h2>
      <p class="text-dim">会员操作会写入审计记录；体彩实时刷新只获取数据，不执行数据库 DDL。</p>
      <div class="toolbar">
        <router-link class="btn primary" to="/account">管理会员与查看审计</router-link>
        <button class="btn ghost" :disabled="refreshing" @click="refreshLottery">
          {{ refreshing ? '刷新中…' : '获取未来 7 天体彩数据' }}
        </button>
      </div>
    </section>
  </template>
</template>
