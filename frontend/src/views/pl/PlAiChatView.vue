<script setup lang="ts">
import { ref, nextTick } from 'vue'
import * as api from '../../api'
import { useAuthStore } from '../../stores/auth'
import { errorMessage } from '../../shared/error'

const auth = useAuthStore()

interface ChatItem {
  kind: 'user' | 'assistant' | 'tool'
  text: string
  toolName?: string
  isError?: boolean
  typing?: boolean
}

const messages = ref<ChatItem[]>([])
const input = ref('')
const sending = ref(false)
const listRef = ref<HTMLElement | null>(null)

const TOOL_LABEL: Record<string, string> = {
  query_recent_form: '查询近期状态',
  query_head_to_head: '查询历史交锋',
  query_team_stats: '查询球队统计',
  query_standings: '查询积分榜',
  query_odds_movement: '查询赔率走势',
  predict_match: '泊松模型预测',
}

const QUICK_QUESTIONS = [
  '阿森纳最近5场状态如何？',
  '曼城 vs 利物浦历史交锋',
  '当前英超积分榜形势',
  '预测 切尔西 vs 热刺',
]

function scrollToBottom() {
  nextTick(() => {
    if (listRef.value) listRef.value.scrollTop = listRef.value.scrollHeight
  })
}

async function send(text?: string) {
  const question = (text ?? input.value).trim()
  if (!question || sending.value) return

  if (!auth.isLoggedIn) {
    auth.openModal('login')
    return
  }

  input.value = ''
  messages.value.push({ kind: 'user', text: question })
  const history = messages.value
    .filter((m) => (m.kind === 'user' || m.kind === 'assistant') && !m.typing)
    .slice(0, -1)
    .map((m) => ({ role: m.kind, text: m.text }))

  sending.value = true
  const assistant: ChatItem = { kind: 'assistant', text: '', typing: true }
  messages.value.push(assistant)
  scrollToBottom()

  try {
    for await (const event of api.chatAgent(question, history)) {
      if (event.type === 'tool_call') {
        messages.value.push({
          kind: 'tool',
          text: `正在调用：${TOOL_LABEL[event.tool] || event.tool}`,
          toolName: event.tool,
        })
      } else if (event.type === 'text_delta') {
        assistant.text += event.text
      } else if (event.type === 'error') {
        assistant.text += event.message
        assistant.typing = false
      } else if (event.type === 'done') {
        assistant.typing = false
      }
      scrollToBottom()
    }
  } catch (e: unknown) {
    assistant.text += errorMessage(e)
  } finally {
    assistant.typing = false
    sending.value = false
    await auth.fetchMe() // 刷新配额显示
    scrollToBottom()
  }
}
</script>

<template>
  <h1 class="page-title">英超 AI 分析助手</h1>
  <p class="page-sub">
    Agent 实时调用数据库工具作答 · 免费用户每日 3 次 ·
    当前剩余：<b>{{ auth.isLoggedIn ? (auth.remaining === -1 ? '无限制' : `${auth.remaining} 次`) : '未登录' }}</b>
  </p>

  <div class="card chat-box">
    <div class="chat-messages" ref="listRef">
      <div v-if="!messages.length" class="empty">
        试试这些问题：<br /><br />
        <button v-for="q in QUICK_QUESTIONS" :key="q" class="btn ghost sm"
                style="margin: 4px" @click="send(q)">{{ q }}</button>
      </div>

      <template v-for="(m, i) in messages" :key="i">
        <div v-if="m.kind === 'tool'" style="text-align: center">
          <span class="tool-chip">🔧 {{ m.text }}</span>
        </div>
        <div v-else class="msg" :class="m.kind">
          <div class="bubble" :class="{ typing: m.typing && !m.text }">
            {{ m.text || '…' }}
          </div>
        </div>
      </template>
    </div>

    <div class="chat-input-bar">
      <input class="input" v-model="input" placeholder="输入问题，如：阿森纳最近状态如何？"
             :disabled="sending" @keyup.enter="send()" />
      <button class="btn accent" :disabled="sending || !input.trim()" @click="send()">
        {{ sending ? '分析中…' : '发送' }}
      </button>
    </div>
  </div>
</template>
