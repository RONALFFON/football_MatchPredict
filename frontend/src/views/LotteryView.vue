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

const matchReq = useRequest<{ matches: LotteryMatch[]; source?: string }>()
const predictReq = useRequest<{ individual_predictions: ClassicPrediction[] }>()

const matches = computed(() => matchReq.data.value?.matches ?? [])
const results = computed(() => predictReq.data.value?.individual_predictions ?? [])

async function load(fromLive = false) {
  selected.value.clear()
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
        home_odds: m.odds?.home_odds || m.home_odds || 2.0,
        draw_odds: m.odds?.draw_odds || m.draw_odds || 3.2,
        away_odds: m.odds?.away_odds || m.away_odds || 2.8,
      })),
    ),
  )
}

onMounted(() => load())
</script>

<template>
  <h1 class="page-title">彩票模式 · 体彩数据</h1>
  <p class="page-sub">中国体育彩票胜平负赛程（数据库优先，数据由定时任务同步）</p>

  <div class="card">
    <div class="toolbar">
      <label class="text-dim toolbar-label">获取天数</label>
      <select class="select toolbar-select" v-model.number="days">
        <option v-for="d in 7" :key="d" :value="d">{{ d }} 天</option>
      </select>
      <button class="btn primary" :disabled="matchReq.loading.value" @click="load(false)">加载赛程</button>
      <button class="btn ghost" :disabled="matchReq.loading.value" @click="load(true)">实时刷新</button>
      <button class="btn accent" :disabled="predictReq.loading.value || !selected.size" @click="batchPredict">
        预测已选 ({{ selected.size }})
      </button>
      <span v-if="source" class="text-dim toolbar-source">来源：{{ source }}</span>
    </div>
  </div>

  <div v-if="matchReq.error.value" class="alert error">{{ matchReq.error.value }}</div>
  <div v-if="matchReq.loading.value && !matches.length" class="empty">加载中…</div>
  <div v-else-if="!matches.length && !matchReq.loading.value" class="empty">暂无比赛数据</div>

  <div
    v-for="(m, i) in matches"
    :key="m.match_id || i"
    class="match-row"
    :class="{ 'match-selected': selected.has(i) }"
    @click="toggle(i)"
  >
    <input type="checkbox" :checked="selected.has(i)" @click.stop="toggle(i)" />
    <div class="match-teams">{{ m.home_team }} <span class="vs">vs</span> {{ m.away_team }}</div>
    <div class="match-meta">{{ m.league_name || '' }} · {{ m.match_time || m.match_date || '' }}</div>
  </div>

  <div v-if="results.length" class="card mt-12">
    <div class="card-title">预测结果</div>
    <table class="table">
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
    </table>
  </div>
</template>
