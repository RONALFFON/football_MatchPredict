<script setup lang="ts">
import { ref, computed } from 'vue'
import * as api from '@/api'
import { useToastStore } from '@/stores/toast'
import { useRequest } from '@/composables/useRequest'
import type { AiPrediction, MatchInput } from '@/api/types'

const toast = useToastStore()

const form = ref({ home: '', away: '', league: '英超', h: '2.00', d: '3.20', a: '2.80' })
const queue = ref<MatchInput[]>([])

const aiReq = useRequest<{ predictions: AiPrediction[]; count: number }>()
const analyses = computed(() => aiReq.data.value?.predictions ?? [])

function addMatch() {
  if (!form.value.home || !form.value.away) {
    toast.error('请填写主客队名称')
    return
  }
  queue.value.push({
    home_team: form.value.home,
    away_team: form.value.away,
    league_name: form.value.league,
    odds: { hhad: { h: form.value.h, d: form.value.d, a: form.value.a } },
  })
  form.value.home = ''
  form.value.away = ''
}

function removeMatch(i: number) {
  queue.value.splice(i, 1)
}

async function runAi() {
  if (!queue.value.length) {
    toast.error('请先添加比赛')
    return
  }
  await aiReq.execute(() => api.aiPredict(queue.value))
}
</script>

<template>
  <h1 class="page-title">AI 智能模式</h1>
  <p class="page-sub">大模型深度分析：胜平负 / 比分 / 半全场 / 进球数 / 风险提示（密钥由服务端保管）</p>

  <div class="grid-2">
    <div class="card">
      <div class="card-title">添加比赛</div>
      <div class="grid-2">
        <div class="form-row">
          <label class="form-label">主队</label>
          <input class="input" v-model="form.home" placeholder="如：曼城" />
        </div>
        <div class="form-row">
          <label class="form-label">客队</label>
          <input class="input" v-model="form.away" placeholder="如：利物浦" />
        </div>
      </div>
      <div class="form-row">
        <label class="form-label">联赛</label>
        <input class="input" v-model="form.league" />
      </div>
      <div class="grid-3">
        <div class="form-row">
          <label class="form-label">主胜赔率</label>
          <input class="input mono" v-model="form.h" />
        </div>
        <div class="form-row">
          <label class="form-label">平局赔率</label>
          <input class="input mono" v-model="form.d" />
        </div>
        <div class="form-row">
          <label class="form-label">客胜赔率</label>
          <input class="input mono" v-model="form.a" />
        </div>
      </div>
      <div class="toolbar">
        <button class="btn ghost" @click="addMatch">+ 添加到队列</button>
        <button class="btn primary" :disabled="aiReq.loading.value || !queue.length" @click="runAi">
          {{ aiReq.loading.value ? 'AI 分析中…' : 'AI 智能预测' }}
        </button>
      </div>

      <div v-if="queue.length" class="mt-12">
        <div v-for="(m, i) in queue" :key="i" class="match-row">
          <div class="match-teams">{{ m.home_team }} <span class="vs">vs</span> {{ m.away_team }}</div>
          <div class="match-meta">{{ m.league_name }}</div>
          <button class="btn ghost sm" @click="removeMatch(i)">移除</button>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">AI 分析结果</div>
      <div v-if="aiReq.error.value" class="alert error">{{ aiReq.error.value }}</div>
      <div v-else-if="aiReq.loading.value" class="empty">正在调用大模型，请稍候…</div>
      <div v-else-if="!analyses.length" class="empty">添加比赛后点击"AI 智能预测"</div>
      <div v-for="a in analyses" :key="a.match_id" class="card analysis-card">
        <div class="card-title">{{ a.home_team }} vs {{ a.away_team }}（{{ a.league_name }}）</div>
        <div class="analysis-text">{{ a.ai_analysis }}</div>
      </div>
    </div>
  </div>
</template>
