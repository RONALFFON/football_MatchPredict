<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as api from '../../api'
import type { PlMatch, Standing } from '../../api/types'
import { errorMessage } from '../../shared/error'

const upcoming = ref<PlMatch[]>([])
const standings = ref<Standing[]>([])
const error = ref('')

onMounted(async () => {
  try {
    const [m, s] = await Promise.allSettled([
      api.getPlMatches('SCHEDULED', 8),
      api.getPlStandings(),
    ])
    if (m.status === 'fulfilled') upcoming.value = m.value.matches
    if (s.status === 'fulfilled') standings.value = s.value.standings
    if (m.status === 'rejected') error.value = (m.reason as Error).message
  } catch (e: unknown) {
    error.value = errorMessage(e)
  }
})
</script>

<template>
  <h1 class="page-title">英超专项分析</h1>
  <p class="page-sub">基于英超官方数据源的深度分析板块 · 支持 AI Agent 对话式查询</p>

  <div v-if="error" class="alert info">{{ error }}</div>

  <div class="grid-2">
    <div class="card">
      <div class="card-title">即将开赛</div>
      <div v-if="!upcoming.length" class="empty">
        暂无数据 —— 请执行初始化：<br />
        <code>backend/sql/pl_analytics_init.sql</code> 并运行同步管道
      </div>
      <div v-for="m in upcoming" :key="m.match_uid" class="match-row">
        <div class="match-teams">{{ m.home_team }} <span class="vs">vs</span> {{ m.away_team }}</div>
        <div class="match-meta">{{ (m.utc_date || '').slice(0, 16) }}</div>
      </div>
      <router-link to="/pl/matches" class="btn ghost sm mt-12" style="display: inline-block">
        查看完整赛程 →
      </router-link>
    </div>

    <div class="card">
      <div class="card-title">积分榜（前 8）</div>
      <div v-if="!standings.length" class="empty">暂无积分榜数据</div>
      <table v-else class="table">
        <thead><tr><th>#</th><th>球队</th><th class="num">赛</th><th class="num">分</th></tr></thead>
        <tbody>
          <tr v-for="t in standings.slice(0, 8)" :key="t.team_name">
            <td>{{ t.position }}</td><td>{{ t.team_name }}</td>
            <td class="num">{{ t.played }}</td><td class="num"><b>{{ t.points }}</b></td>
          </tr>
        </tbody>
      </table>
      <router-link to="/pl/standings" class="btn ghost sm mt-12" style="display: inline-block">
        完整积分榜 →
      </router-link>
    </div>
  </div>

  <div class="card">
    <div class="card-title">🤖 AI Agent 能力一览</div>
    <p class="text-dim" style="font-size: 13px; line-height: 1.8">
      支持对话式提问：<b>「阿森纳最近 5 场状态如何？」</b>、<b>「曼城对利物浦历史交锋」</b>、
      <b>「预测 切尔西 vs 热刺」</b>…… Agent 会自动调用近况、交锋、统计、积分榜、赔率、泊松预测 6 个数据工具作答。
    </p>
    <router-link to="/pl/ai" class="btn accent mt-12" style="display: inline-block">开始对话 →</router-link>
  </div>
</template>
