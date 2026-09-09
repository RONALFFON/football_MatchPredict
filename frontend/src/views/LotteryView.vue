<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import * as api from '@/api'
import { useToastStore } from '@/stores/toast'
import { useRequest } from '@/composables/useRequest'
import type { ClassicPrediction, LotteryMatch } from '@/api/types'

const toast = useToastStore()

const days = ref(3)
const selected = ref<Set<number>>(new Set())
const source = ref('')
const resultsSection = ref<HTMLElement | null>(null)
function showResults() {
  resultsSection.value?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' })
}

const matchReq = useRequest<{ matches: LotteryMatch[]; source?: string }>()
const predictReq = useRequest<{ individual_predictions: ClassicPrediction[] }>()

const matches = computed(() => matchReq.data.value?.matches ?? [])
const results = computed(() => predictReq.data.value?.individual_predictions ?? [])

async function load(fromLive = false) {
  if (matchReq.loading.value || predictReq.loading.value) return
  selected.value.clear()
  predictReq.data.value = undefined
  predictReq.error.value = ''
  const data = await matchReq.execute(() =>
    fromLive ? api.refreshLottery(days.value) : api.getLotteryMatches(days.value),
  )
  source.value = fromLive ? '体彩官方 API 实时数据' : (data?.source || '数据库')
}

function toggle(i: number) {
  const next = new Set(selected.value)
  next.has(i) ? next.delete(i) : next.add(i)
  selected.value = next
}

async function batchPredict() {
  const picked = [...selected.value].map((i) => matches.value[i]).filter(Boolean)
  if (!picked.length) {
    toast.error('请先勾选要预测的比赛')
    return
  }
  await predictReq.execute(() =>
    api.simplePredict(
      picked.map((m) => ({
        home_team: m.home_team,
        away_team: m.away_team,
        match_id: m.match_id,
        league_name: m.league_name,
        odds: m.odds,
        home_odds: m.home_odds,
        draw_odds: m.draw_odds,
        away_odds: m.away_odds,
      })),
    ),
  )
}

onMounted(() => load())
</script>

<template>
  <h1 class="page-title">彩票模式 · 体彩数据</h1>
  <p class="page-sub">发现值得关注的对阵，选择多场比赛，一次完成概率分析。</p>

  <div class="card">
    <div class="toolbar">
      <label class="text-dim toolbar-label">赛程范围</label>
      <select class="select toolbar-select" aria-label="赛程天数" :disabled="matchReq.loading.value || predictReq.loading.value" v-model.number="days">
        <option v-for="d in 7" :key="d" :value="d">{{ d }} 天</option>
      </select>
      <button class="btn primary" :disabled="matchReq.loading.value || predictReq.loading.value" @click="load(false)">加载赛程</button>
      <button class="btn ghost" :disabled="matchReq.loading.value || predictReq.loading.value" @click="load(true)">实时刷新</button>
      <span v-if="source" class="text-dim toolbar-source">{{ matches.length }} 场比赛可供查看</span>
    </div>
  </div>

  <div v-if="matchReq.error.value" class="alert error" role="alert">{{ matchReq.error.value }} <button class="btn ghost sm" @click="load(false)">重试</button></div>
  <div v-if="predictReq.error.value" class="alert error" role="alert">{{ predictReq.error.value }}</div>
  <div v-if="matchReq.loading.value && !matches.length" aria-label="正在加载比赛" aria-busy="true"><div v-for="n in 4" :key="n" class="skeleton" /></div>
  <div v-else-if="!matches.length && !matchReq.loading.value && !matchReq.error.value" class="empty">暂无比赛数据</div>

  <label
    v-for="(m, i) in matches"
    :key="m.match_id || i"
    class="match-row selectable"
    :class="{ 'match-selected': selected.has(i) }"
  >
    <input type="checkbox" :checked="selected.has(i)" :disabled="predictReq.loading.value || matchReq.loading.value" :aria-label="`选择 ${m.home_team} 对 ${m.away_team}`" @change="toggle(i)" />
    <span class="match-teams">{{ m.home_team }} <span class="vs">vs</span> {{ m.away_team }}</span>
    <span class="match-meta">{{ m.league_name || '' }} · {{ m.match_time || m.match_date || '' }}</span>
  </label>

  <div v-if="results.length" ref="resultsSection" class="card mt-12 results-section">
    <div class="card-title">预测结果</div>
    <div class="table-scroll" tabindex="0" role="region" aria-label="批量预测结果，可横向滚动"><table class="table">
      <thead>
        <tr><th>比赛</th><th class="num">主胜</th><th class="num">平局</th><th class="num">客胜</th><th>推荐</th></tr>
      </thead>
      <tbody>
        <tr v-for="r in results" :key="r.home_team + r.away_team">
          <td>{{ r.home_team }} vs {{ r.away_team }}</td>
          <td class="num">{{ (r.probabilities.home * 100).toFixed(1) }}%</td>
          <td class="num">{{ (r.probabilities.draw * 100).toFixed(1) }}%</td>
          <td class="num">{{ (r.probabilities.away * 100).toFixed(1) }}%</td>
          <td>{{ r.recommendation }}</td>
        </tr>
      </tbody>
    </table></div>
  </div>
  <div v-if="matches.length" class="selection-bar">
    <span>已选 <strong>{{ selected.size }}</strong> 场比赛</span>
    <button class="btn ghost sm" :disabled="!selected.size || predictReq.loading.value" @click="selected.clear()">清空</button>
    <button v-if="results.length" class="btn ghost sm" @click="showResults">查看结果 ↓</button>
    <button class="btn primary" :disabled="predictReq.loading.value || matchReq.loading.value || !selected.size" @click="batchPredict"><span v-if="predictReq.loading.value" class="spinner" />{{ predictReq.loading.value ? '正在分析…' : '预测已选比赛 →' }}</button>
  </div>
</template>
