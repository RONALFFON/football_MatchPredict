import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'classic', component: () => import('@/views/HomeView.vue') },
    { path: '/lottery', name: 'lottery', component: () => import('@/views/LotteryView.vue') },
    { path: '/ai', name: 'ai-mode', component: () => import('@/views/AiModeView.vue') },
    { path: '/pl', name: 'pl-overview', component: () => import('@/views/pl/PlOverviewView.vue') },
    { path: '/pl/matches', name: 'pl-matches', component: () => import('@/views/pl/PlMatchesView.vue') },
    { path: '/pl/standings', name: 'pl-standings', component: () => import('@/views/pl/PlStandingsView.vue') },
    { path: '/pl/ai', name: 'pl-ai', component: () => import('@/views/pl/PlAiChatView.vue') },
  ],
})

export default router
