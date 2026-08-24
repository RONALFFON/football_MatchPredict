<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import * as api from '../api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()

const leagues = ref<Record<string, string>>({})
const teams = ref<Record<string, string[]>>({})
const league = ref('PL')
const homeTeam = ref('')
const awayTeam = ref('')
const odds = ref({ home: 2.0, draw: 3.2, away: 2.8 })
const result = ref<any>(null)
const error = ref('')
const loading = ref(false)

const teamOptions = computed(() => teams.value[league.value] || [])

onMounted(async () => {
  try {
    const data = await api.getTeams()
    leagues.value = data.leagues
    teams.value = data.teams
  } catch (e: any) {
    error.value = e.message
  }
})

async function predict() {
  error.value = ''
  result.value = null
  if (!homeTeam.value || !awayTeam.value) {
    error.value = '请选择主客队'
    return
  }
  loading.value = true
  try {
    const data = await api.simplePredict([{
      home_team: homeTeam.value, away_team: awayTeam.value,
      home_odds: odds.value.home, draw_odds: odds.value.draw, away_odds: odds.value.away,
    }])
    result.value = data.individual_predictions[0]
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function saveResult() {
  try {
    await api.savePrediction({
      mode: 'classic',
      match_data: { home_team: homeTeam.value, away_team: awayTeam.value,
                    league_name: leagues.value[league.value], ...odds.value },
      prediction_result: result.value.recommendation,
      confidence: Math.round(result.value.probabilities.home * 100) / 10,
    })
    await auth.fetchMe()
    alert('预测已保存')
  } catch (e: any) {
    alert(e.message)
    if (/登录/.test(e.message)) auth.openModal('login')
  }
}
</script>

<template>
  <h1 class="page-title">经典模式 · 统计分析</h1>
  <p class="page-sub">基于五大联赛历史数据与赔率的概率模型（泊松分布 + 期望值）</p>

  <div class="grid-2">
    <div class="card">
      <div class="card-title">选择比赛</div>
      <div v-if="error && !result" class="alert error">{{ error }}</div>

      <div class="form-row">
        <label class="form-label">联赛</label>
        <select class="select" v-model="league">
          <option v-for="(name, code) in leagues" :key="code" :value="code">{{ name }}</option>
        </select>
      </div>
      <div class="form-row">
        <label class="form-label">主队</label>
        <select class="select" v-model="homeTeam">
          <option value="" disabled>请选择</option>
          <option v-for="t in teamOptions" :key="t" :value="t">{{ t }}</option>
        </select>
      </div>
      <div class="form-row">
        <label class="form-label">客队</label>
        <select class="select" v-model="awayTeam">
          <option value="" disabled>请选择</option>
          <option v-for="t in teamOptions" :key="t" :value="t">{{ t }}</option>
        </select>
      </div>
      <div class="grid-3">
        <div class="form-row"><label class="form-label">主胜赔率</label>
          <input class="input mono" type="number" step="0.01" v-model.number="odds.home" /></div>
        <div class="form-row"><label class="form-label">平局赔率</label>
          <input class="input mono" type="number" step="0.01" v-model.number="odds.draw" /></div>
        <div class="form-row"><label class="form-label">客胜赔率</label>
          <input class="input mono" type="number" step="0.01" v-model.number="odds.away" /></div>
      </div>
      <button class="btn primary" :disabled="loading" @click="predict">
        {{ loading ? '计算中…' : '开始预测' }}
      </button>
    </div>

    <div class="card">
      <div class="card-title">预测结果</div>
      <div v-if="!result" class="empty">选择比赛并点击"开始预测"</div>
      <div v-else>
        <p class="mb-12"><b>{{ result.home_team }}</b> vs <b>{{ result.away_team }}</b></p>
        <table class="table">
          <tr><td>主胜</td><td class="num">{{ (result.probabilities.home * 100).toFixed(1) }}%</td></tr>
          <tr><td>平局</td><td class="num">{{ (result.probabilities.draw * 100).toFixed(1) }}%</td></tr>
          <tr><td>客胜</td><td class="num">{{ (result.probabilities.away * 100).toFixed(1) }}%</td></tr>
        </table>
        <div class="alert info mt-12">推荐：{{ result.recommendation }}</div>
        <button class="btn ghost mt-12" @click="saveResult">保存预测记录</button>
      </div>
    </div>
  </div>
</template>
