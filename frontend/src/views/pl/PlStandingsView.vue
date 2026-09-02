<script setup lang="ts">
import { onMounted, computed } from 'vue'
import * as api from '@/api'
import { useRequest } from '@/composables/useRequest'
import type { Standing } from '@/api/types'

const req = useRequest<{ standings: Standing[] }>()
const standings = computed(() => req.data.value?.standings ?? [])

onMounted(() => req.execute(() => api.getPlStandings()))

function rowClass(pos: number) {
  if (pos <= 4) return 'row-ucl'
  if (pos >= 18) return 'row-rel'
  return ''
}
</script>

<template>
  <h1 class="page-title">英超积分榜</h1>
  <p class="page-sub">
    <span class="legend-ucl">■</span> 欧冠区（1-4）
    <span class="legend-rel">■</span> 降级区（18-20）
  </p>

  <div v-if="req.error.value" class="alert info">{{ req.error.value }}</div>

  <div class="card" v-if="standings.length">
    <table class="table">
      <thead>
        <tr>
          <th>#</th><th>球队</th>
          <th class="num">赛</th><th class="num">胜</th><th class="num">平</th><th class="num">负</th>
          <th class="num">进球</th><th class="num">失球</th><th class="num">净胜</th><th class="num">积分</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="t in standings" :key="t.team_name" :class="rowClass(t.position)">
          <td>{{ t.position }}</td>
          <td><b>{{ t.team_name }}</b></td>
          <td class="num">{{ t.played }}</td>
          <td class="num">{{ t.won }}</td>
          <td class="num">{{ t.drawn }}</td>
          <td class="num">{{ t.lost }}</td>
          <td class="num">{{ t.goals_for }}</td>
          <td class="num">{{ t.goals_against }}</td>
          <td class="num">{{ t.goals_for - t.goals_against }}</td>
          <td class="num"><b>{{ t.points }}</b></td>
        </tr>
      </tbody>
    </table>
  </div>
  <div v-else-if="!req.loading.value && !req.error.value" class="empty">暂无积分榜数据</div>
</template>
