<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
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
const saveRequestId = ref('')

const leagues = computed(() => meta.data.value?.leagues ?? {})
const teams = computed(() => meta.data.value?.teams ?? {})
const teamOptions = computed(() => teams.value[league.value] || [])
const result = computed(() => predict.data.value?.individual_predictions[0] ?? null)

const formError = ref('')
const resultLeague = ref('')
const resultOdds = ref({ home: 2, draw: 3.2, away: 2.8 })
const outcomes = computed(() => result.value ? [
  { key: 'home', label: '主胜', value: result.value.probabilities.home },
  { key: 'draw', label: '平局', value: result.value.probabilities.draw },
  { key: 'away', label: '客胜', value: result.value.probabilities.away },
] : [])
watch(league, () => { homeTeam.value = ''; awayTeam.value = '' })
watch([league, homeTeam, awayTeam, () => odds.value.home, () => odds.value.draw, () => odds.value.away], () => {
  predict.data.value = undefined
  predict.error.value = ''
  formError.value = ''
})
function loadTeams() { return meta.execute(() => api.getTeams()) }
onMounted(loadTeams)

async function runPredict() {
  if (predict.loading.value) return
  formError.value = ''
  if (!homeTeam.value || !awayTeam.value || homeTeam.value === awayTeam.value) {
    formError.value = '请选择两支不同的球队'
    return
  }
  if (Object.values(odds.value).some(value => !Number.isFinite(value) || value <= 1)) {
    formError.value = '请填写大于 1 的有效赔率'
    return
  }
  resultLeague.value = leagues.value[league.value] || league.value
  resultOdds.value = { ...odds.value }
  saveRequestId.value = crypto.randomUUID()
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
      request_id: saveRequestId.value,
      match_data: {
        home_team: result.value.home_team,
        away_team: result.value.away_team,
        league_name: resultLeague.value,
        ...resultOdds.value,
      },
      prediction_result: result.value.recommendation,
      confidence: Math.round(Math.max(...Object.values(result.value.probabilities)) * 100) / 10,
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
  <div class="page-heading">
    <div><div class="eyebrow"><span class="live-dot" /> MATCH INSIGHTS</div><h1 class="page-title">让每一次预测，更有依据<span class="title-dot">.</span></h1><p class="page-sub">从球队到赔率，用数据发现比赛的更多可能。</p></div>
    <router-link to="/pl/matches" class="text-link">浏览英超赛程 <span aria-hidden="true">↗</span></router-link>
  </div>
  <div class="prediction-layout">
    <div class="card setup-card">
      <div class="section-heading"><div><span class="section-number">01</span><h2 class="card-title">选择比赛</h2></div><span class="badge">经典模式</span></div>
      <p class="section-description">选择联赛与对阵，输入赔率即可开始分析。</p>
      <div v-if="meta.error.value" class="alert error" role="alert">球队加载失败 <button class="btn ghost sm" @click="loadTeams">重试</button></div>
      <form @submit.prevent="runPredict">
        <fieldset :disabled="predict.loading.value || meta.loading.value || !!meta.error.value">
          <div class="form-row"><label class="form-label" for="league">所属联赛</label><select id="league" class="select" v-model="league"><option v-if="meta.loading.value" value="PL">正在加载联赛…</option><option v-for="(name, code) in leagues" :key="code" :value="code">{{ name }}</option></select></div>
          <div class="team-select-grid">
            <div class="form-row"><label class="form-label" for="home-team">主队 <span>HOME</span></label><select id="home-team" class="select" v-model="homeTeam"><option value="" disabled>选择主队</option><option v-for="t in teamOptions" :key="t" :value="t" :disabled="t === awayTeam">{{ t }}</option></select></div>
            <span class="versus-mark" aria-hidden="true">VS</span>
            <div class="form-row"><label class="form-label" for="away-team">客队 <span>AWAY</span></label><select id="away-team" class="select" v-model="awayTeam"><option value="" disabled>选择客队</option><option v-for="t in teamOptions" :key="t" :value="t" :disabled="t === homeTeam">{{ t }}</option></select></div>
          </div>
          <div class="field-divider"><span>胜平负赔率</span><span class="text-dim">十进制</span></div>
          <div class="odds-grid">
            <div v-for="(label, key) in { home: '主胜', draw: '平局', away: '客胜' }" :key="key" class="form-row"><label class="form-label" :for="'odds-' + key">{{ label }}</label><input :id="'odds-' + key" class="input mono" type="number" inputmode="decimal" step="0.01" min="1.01" required v-model.number="odds[key]" /></div>
          </div>
          <p v-if="formError" class="field-error mb-12" role="alert">{{ formError }}</p>
          <button class="btn primary predict-button" :disabled="!homeTeam || !awayTeam || predict.loading.value" type="submit"><span v-if="predict.loading.value" class="spinner" />{{ predict.loading.value ? '正在计算概率…' : '开始分析比赛' }}<span v-if="!predict.loading.value" aria-hidden="true">→</span></button>
        </fieldset>
      </form>
      <div class="model-note"><span class="live-dot" /> 赔率隐含概率 <span>·</span> 经典计算与保存免费</div>
    </div>
    <div class="card result-card" :aria-busy="predict.loading.value" aria-live="polite">
      <div class="section-heading"><div><span class="section-number">02</span><h2 class="card-title">比赛洞察</h2></div><span class="badge">{{ result ? '分析完成' : '概率分析' }}</span></div>
      <div v-if="predict.loading.value" class="result-placeholder"><div class="skeleton skeleton-title" /><div class="skeleton" /><div class="skeleton" /><p>正在结合比赛数据计算概率…</p></div>
      <div v-else-if="predict.error.value" class="result-placeholder"><span class="empty-symbol">!</span><h3>暂时未能完成分析</h3><p>{{ predict.error.value }}</p><button class="btn ghost" @click="runPredict">重新分析</button></div>
      <div v-else-if="!result" class="result-placeholder"><div class="pitch-art" aria-hidden="true"><div class="pitch-circle" /><span class="pitch-ball" /></div><h3>下一场比赛，从这里读懂</h3><p>在左侧选择对阵，查看胜平负概率<br />与模型推荐结果。</p><div class="placeholder-tags"><span>主胜概率</span><span>平局概率</span><span>客胜概率</span></div></div>
      <div v-else class="prediction-result">
        <div class="result-fixture"><div><span class="team-avatar">{{ result.home_team.slice(0, 1) }}</span><strong>{{ result.home_team }}</strong><small>主队</small></div><span class="versus-mark">VS</span><div><span class="team-avatar away">{{ result.away_team.slice(0, 1) }}</span><strong>{{ result.away_team }}</strong><small>客队</small></div></div>
        <div class="probability-bar" aria-hidden="true"><span v-for="item in outcomes" :key="item.key" :class="item.key" :style="{ flexGrow: item.value }" /></div>
        <div class="probability-values"><div v-for="item in outcomes" :key="item.key" :class="item.key"><span>{{ item.label }}</span><strong>{{ (item.value * 100).toFixed(1) }}<small>%</small></strong></div></div>
        <div class="recommendation"><span>模型推荐</span><strong>{{ result.recommendation }}</strong></div>
        <button class="btn ghost save-button" :disabled="saving" @click="saveResult">{{ saving ? '保存中…' : '保存本次预测' }} <span aria-hidden="true">↗</span></button>
      </div>
    </div>
  </div>
  <div class="explore-grid"><router-link to="/lottery" class="explore-card"><span class="explore-icon" aria-hidden="true">▤</span><div><h3>更多比赛，一起分析</h3><p>浏览体彩赛程，批量查看预测结果</p></div><span aria-hidden="true">↗</span></router-link><router-link to="/pl/ai" class="explore-card"><span class="explore-icon blue" aria-hidden="true">✧</span><div><h3>关于比赛，问问 AI</h3><p>球队近况、历史交锋与赛前分析</p></div><span aria-hidden="true">↗</span></router-link></div>
</template>
