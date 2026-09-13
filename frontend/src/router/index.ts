import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getToken } from '@/api/client'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior(_to, _from, savedPosition) {
    return savedPosition ?? { top: 0 }
  },
  routes: [
    { path: '/admin', name: 'admin', component: () => import('@/views/AdminView.vue'), meta: { requiresAdmin: true } },
    { path: '/account', name: 'account', component: () => import('@/views/AccountView.vue') },
    { path: '/', name: 'classic', component: () => import('@/views/HomeView.vue') },
    { path: '/lottery', name: 'lottery', component: () => import('@/views/LotteryView.vue') },
    { path: '/ai', name: 'ai-mode', component: () => import('@/views/AiModeView.vue') },
    { path: '/pl', name: 'pl-overview', component: () => import('@/views/pl/PlOverviewView.vue') },
    { path: '/pl/matches', name: 'pl-matches', component: () => import('@/views/pl/PlMatchesView.vue') },
    { path: '/pl/standings', name: 'pl-standings', component: () => import('@/views/pl/PlStandingsView.vue') },
    { path: '/pl/ai', name: 'pl-ai', component: () => import('@/views/pl/PlAiChatView.vue') },
  ],
})

router.beforeEach(async (to) => {
  if (!to.meta.requiresAdmin) return true
  const auth = useAuthStore()
  if (!auth.user && getToken()) await auth.fetchMe()
  return auth.user?.role === 'system_admin' ? true : { name: 'account' }
})

export default router
