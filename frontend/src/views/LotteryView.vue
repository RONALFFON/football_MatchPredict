<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as api from '../api'
import type { ClassicPrediction, LotteryMatch } from '../api/types'
import { errorMessage } from '../shared/error'

const matches = ref<LotteryMatch[]>([])
const selected = ref<Set<number>>(new Set())
const results = ref<ClassicPrediction[]>([])
const days = ref(3)
const loading = ref(false)
const error = ref('')
const source = ref('')

async function load(fromLive = false) {
  loading.value = true
  error.value = ''
  results.value = []
  selected.value.clear()
  try {
    const data = fromLive
      ? await api.refreshLottery(days.value)
      : await api.getLotteryMatches(days.value)
    matches.value = data.matches || []
    source.value = fromLive ? '体彩官方 API 实时数据' : (data.source || '数据库')
  } catch (e: unknown) {
    matches.value = []
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

function toggle(i: number) {
  selected.value.has(i) ? selected.value.delete(i) : selected.value.add(i)
}

async function batchPredict() {
  const picked = [...selected.value].map((i) => matches.value[i]).filter(Boolean)
  if (!picked.length) {
    error.value = '请先勾选要预测的比赛'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const toApi = picked.map((m) => ({
      home_team: m.home_team, away_team: m.away_team,
      home_odds: m.odds?.home_odds || m.home_odds || 2.0,
      draw_odds: m.odds?.draw_odds || m.draw_odds || 3.2,
      away_odds: m.odds?.away_odds || m.away_odds || 2.8,
    }))
    const data = await api.simplePredict(toApi)
    results.value = data.individual_predictions || []
  } catch (e: unknown) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

onMounted(() => load())
</script>

<template>
  <h1 class="page-title">彩票模式 · 体彩数据</h1>
  <p class="page-sub">中国体育彩票胜平负赛程（数据库优先，数据由定时任务同步）</p>

  <div class="card">
    <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap">
      <label class="text-dim" style="font-size: 13px">获取天数</label>
      <select class="select" style="width: 90px" v-model.number="days">
        <option v-for="d in 7" :key="d" :value="d">{{ d }} 天</option>
      </select>
      <button class="btn primary" :disabled="loading" @click="load(false)">加载赛程</button>
      <button class="btn ghost" :disabled="loading" @click="load(true)">实时刷新</button>
      <button class="btn accent" :disabled="loading || !selected.size" @click="batchPredict">
        预测已选 ({{ selected.size }})
      </button>
      <span v-if="source" class="text-dim" style="font-size: 12px; margin-left: auto">来源：{{ source }}</span>
    </div>
  </div>

  <div v-if="error" class="alert error">{{ error }}</div>
  <div v-if="loading && !matches.length" class="empty">加载中…</div>
  <div v-else-if="!matches.length" class="empty">
    暂无比赛数据。请先运行同步任务：<code>cd backend &amp;&amp; python -m app.workers.sync_lottery --days 7</code>
  </div>

  <div v-for="(m, i) in matches" :key="i" class="match-row" @click="toggle(i)"
       :style="{ borderColor: selected.has(i) ? 'var(--primary)' : undefined, cursor: 'pointer' }">
    <input type="checkbox" :checked="selected.has(i)" @click.stop="toggle(i)" />
    <div class="match-teams">
      {{ m.home_team }} <span class="vs">vs</span> {{ m.away_team }}
    </div>
    <div class="match-meta">{{ m.league_name || '' }} · {{ m.match_time || m.match_date || '' }}</div>
  </div>

  <div v-if="results.length" class="card mt-12">
    <div class="card-title">预测结果</div>
    <table class="table">
      <thead><tr><th>比赛</th><th class="num">主胜</th><th class="num">平局</th><th class="num">客胜</th><th>推荐</th></tr></thead>
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
