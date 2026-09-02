<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import * as api from '@/api'
import { useRequest } from '@/composables/useRequest'
import type { PlMatch } from '@/api/types'

const STATUS_LABEL: Record<string, string> = {
  SCHEDULED: '未开赛',
  LIVE: '进行中',
  FINISHED: '已结束',
}

const status = ref('')
const req = useRequest<{ matches: PlMatch[] }>()
const matches = computed(() => req.data.value?.matches ?? [])

function load() {
  req.execute(() => api.getPlMatches(status.value || undefined, 100))
}

onMounted(load)
watch(status, load)
</script>

<template>
  <h1 class="page-title">英超赛程</h1>
  <p class="page-sub">英超全部赛程与赛果</p>

  <div class="card">
    <div class="toolbar">
      <button
        v-for="(label, key) in { '': '全部', SCHEDULED: '未开赛', LIVE: '进行中', FINISHED: '已结束' }"
        :key="key"
        class="btn sm"
        :class="{ accent: status === key }"
        @click="status = key"
      >
        {{ label }}
      </button>
    </div>
  </div>

  <div v-if="req.error.value" class="alert info">{{ req.error.value }}</div>
  <div v-if="req.loading.value" class="empty">加载中…</div>

  <div v-for="m in matches" :key="m.match_uid" class="match-row">
    <span class="status-tag" :class="m.status">{{ STATUS_LABEL[m.status] || m.status }}</span>
    <div class="match-teams">{{ m.home_team }} <span class="vs">vs</span> {{ m.away_team }}</div>
    <span v-if="m.status === 'FINISHED'" class="score">{{ m.home_score }} - {{ m.away_score }}</span>
    <div class="match-meta">第{{ (m.round || '').replace(/\D/g, '') }}轮 · {{ (m.utc_date || '').slice(0, 16) }}</div>
  </div>

  <div v-if="!req.loading.value && !matches.length && !req.error.value" class="empty">暂无比赛数据</div>
</template>
