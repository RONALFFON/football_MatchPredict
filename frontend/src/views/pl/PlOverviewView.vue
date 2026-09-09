<script setup lang="ts">
import { onMounted, computed } from 'vue'
import * as api from '@/api'
import { formatMatchDate, localTimeZone } from '@/shared/date'
import { useRequest } from '@/composables/useRequest'
import type { PlMatch, Standing } from '@/api/types'

const matchReq = useRequest<{ matches: PlMatch[] }>()
const standingReq = useRequest<{ standings: Standing[] }>()

const upcoming = computed(() => matchReq.data.value?.matches ?? [])
const standings = computed(() => standingReq.data.value?.standings ?? [])

onMounted(() => {
  matchReq.execute(() => api.getPlMatches('SCHEDULED', 8))
  standingReq.execute(() => api.getPlStandings())
})
</script>

<template>
  <h1 class="page-title">英超专项分析</h1>
  <p class="page-sub">聚焦英超，掌握赛程、积分与球队动态。时间：{{ localTimeZone }}</p>

  <div v-if="matchReq.error.value" class="alert error">{{ matchReq.error.value }}</div>

  <div class="grid-2">
    <div class="card">
      <div class="card-title">即将开赛</div>
      <div v-if="matchReq.loading.value" class="skeleton" aria-label="正在加载比赛" />
      <div v-if="!upcoming.length && !matchReq.loading.value" class="empty">暂无数据</div>
      <div v-for="m in upcoming" :key="m.match_uid" class="match-row">
        <div class="match-teams">{{ m.home_team }} <span class="vs">vs</span> {{ m.away_team }}</div>
        <div class="match-meta">{{ formatMatchDate(m.utc_date) }}</div>
      </div>
      <router-link to="/pl/matches" class="btn ghost sm mt-12 inline-block">查看完整赛程 →</router-link>
    </div>

    <div class="card">
      <div class="card-title">积分榜（前 8）</div>
      <div v-if="standingReq.loading.value" class="skeleton" aria-label="正在加载积分榜" />
      <div v-if="standingReq.error.value" class="alert error">{{ standingReq.error.value }}</div>
      <div v-if="!standings.length && !standingReq.loading.value" class="empty">暂无积分榜数据</div>
      <table v-if="standings.length" class="table">
        <thead><tr><th>#</th><th>球队</th><th class="num">赛</th><th class="num">分</th></tr></thead>
        <tbody>
          <tr v-for="t in standings.slice(0, 8)" :key="t.team_name">
            <td>{{ t.position }}</td>
            <td>{{ t.team_name }}</td>
            <td class="num">{{ t.played }}</td>
            <td class="num"><b>{{ t.points }}</b></td>
          </tr>
        </tbody>
      </table>
      <router-link to="/pl/standings" class="btn ghost sm mt-12 inline-block">完整积分榜 →</router-link>
    </div>
  </div>

  <div class="card">
    <div class="card-title">关于英超，你还想知道什么？</div>
    <p class="text-dim agent-desc">
      支持对话式提问：<b>「阿森纳最近 5 场状态如何？」</b>、<b>「曼城对利物浦历史交锋」</b>、
      <b>「预测 切尔西 vs 热刺」</b>…… 结合球队近况、历史交锋、积分与赔率，为你解读比赛。
    </p>
    <router-link to="/pl/ai" class="btn accent mt-12 inline-block">开始对话 →</router-link>
  </div>
</template>
