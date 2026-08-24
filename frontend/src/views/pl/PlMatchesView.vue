<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import * as api from '../../api'

const matches = ref<any[]>([])
const status = ref('')
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await api.getPlMatches(status.value || undefined, 100)
    matches.value = data.matches
  } catch (e: any) {
    matches.value = []
    error.value = e.message
  } finally {
    loading.value = false
  }
}

const STATUS_LABEL: Record<string, string> = {
  SCHEDULED: '未开赛', LIVE: '进行中', FINISHED: '已结束',
}

onMounted(load)
watch(status, load)
</script>

<template>
  <h1 class="page-title">英超赛程</h1>
  <p class="page-sub">英超全部赛程与赛果</p>

  <div class="card">
    <div style="display: flex; gap: 8px">
      <button v-for="(label, key) in { '': '全部', SCHEDULED: '未开赛', LIVE: '进行中', FINISHED: '已结束' }"
              :key="key" class="btn sm" :class="{ accent: status === key }" @click="status = key">
        {{ label }}
      </button>
    </div>
  </div>

  <div v-if="error" class="alert info">{{ error }}</div>
  <div v-if="loading" class="empty">加载中…</div>

  <div v-for="m in matches" :key="m.match_uid" class="match-row">
    <span class="status-tag" :class="m.status">{{ STATUS_LABEL[m.status] || m.status }}</span>
    <div class="match-teams">
      {{ m.home_team }} <span class="vs">vs</span> {{ m.away_team }}
    </div>
    <span v-if="m.status === 'FINISHED'" class="score">{{ m.home_score }} - {{ m.away_score }}</span>
    <div class="match-meta">第{{ (m.round || '').replace(/\D/g, '') }}轮 · {{ (m.utc_date || '').slice(0, 16) }}</div>
  </div>
  <div v-if="!loading && !matches.length && !error" class="empty">暂无比赛数据</div>
</template>
