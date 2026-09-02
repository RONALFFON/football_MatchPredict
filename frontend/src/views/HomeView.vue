<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import * as api from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { useRequest } from '@/composables/useRequest'
import type { ClassicPrediction, TeamsData } from '@/api/types'
import { errorMessage } from '@/shared/error'

const auth = useAuthStore()
const toast = useToastStore()

const meta = useRequest<TeamsData>()
const predict = useRequest<{ individual_predictions: ClassicPrediction[] }>()

const league = ref('PL')
const homeTeam = ref('')
const awayTeam = ref('')
const odds = ref({ home: 2.0, draw: 3.2, away: 2.8 })
const saving = ref(false)

const leagues = computed(() => meta.data.value?.leagues ?? {})
const teams = computed(() => meta.data.value?.teams ?? {})
const teamOptions = computed(() => teams.value[league.value] || [])
const result = computed(() => predict.data.value?.individual_predictions[0] ?? null)

onMounted(() => meta.execute(() => api.getTeams()))

async function runPredict() {
  if (!homeTeam.value || !awayTeam.value) {
    toast.error('请选择主客队')
    return
  }
  await predict.execute(() =>
    api.simplePredict([{
      home_team: homeTeam.value,
      away_team: awayTeam.value,
      home_odds: odds.value.home,
      draw_odds: odds.value.draw,
      away_odds: odds.value.away,
    }]),
  )
}

async function saveResult() {
  if (!result.value || saving.value) return
  saving.value = true
  try {
    await api.savePrediction({
      mode: 'classic',
      match_data: {
        home_team: homeTeam.value,
        away_team: awayTeam.value,
        league_name: leagues.value[league.value],
        ...odds.value,
      },
      prediction_result: result.value.recommendation,
      confidence: Math.round(result.value.probabilities.home * 100) / 10,
    })
    toast.success('预测已保存')
    await auth.fetchMe()
  } catch (e: unknown) {
    const msg = errorMessage(e)
    toast.error(msg)
    if (/登录/.test(msg)) auth.openModal('login')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <h1 class="page-title">经典模式 · 统计分析</h1>
  <p class="page-sub">基于五大联赛历史数据与赔率的概率模型（泊松分布 + 期望值）</p>

  <div class="grid-2">
    <div class="card">
      <div class="card-title">选择比赛</div>

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
        <div class="form-row">
          <label class="form-label">主胜赔率</label>
          <input class="input mono" type="number" step="0.01" min="1" v-model.number="odds.home" />
        </div>
        <div class="form-row">
          <label class="form-label">平局赔率</label>
          <input class="input mono" type="number" step="0.01" min="1" v-model.number="odds.draw" />
        </div>
        <div class="form-row">
          <label class="form-label">客胜赔率</label>
          <input class="input mono" type="number" step="0.01" min="1" v-model.number="odds.away" />
        </div>
      </div>
      <button class="btn primary" :disabled="predict.loading.value" @click="runPredict">
        {{ predict.loading.value ? '计算中…' : '开始预测' }}
      </button>
    </div>

    <div class="card">
      <div class="card-title">预测结果</div>
      <div v-if="predict.error.value" class="alert error">{{ predict.error.value }}</div>
      <div v-else-if="!result" class="empty">选择比赛并点击"开始预测"</div>
      <div v-else>
        <p class="mb-12"><b>{{ result.home_team }}</b> vs <b>{{ result.away_team }}</b></p>
        <table class="table">
          <tr><td>主胜</td><td class="num">{{ (result.probabilities.home * 100).toFixed(1) }}%</td></tr>
          <tr><td>平局</td><td class="num">{{ (result.probabilities.draw * 100).toFixed(1) }}%</td></tr>
          <tr><td>客胜</td><td class="num">{{ (result.probabilities.away * 100).toFixed(1) }}%</td></tr>
        </table>
        <div class="alert info mt-12">推荐：{{ result.recommendation }}</div>
        <button class="btn ghost mt-12" :disabled="saving" @click="saveResult">
          {{ saving ? '保存中…' : '保存预测记录' }}
        </button>
      </div>
    </div>
  </div>
</template>
