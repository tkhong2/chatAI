<template>
  <div class="app">
    <!-- Sidebar -->
    <aside class="sidebar" :class="{ open: sidebarOpen }">
      <div class="sidebar-header">
        <span class="logo">🤖 Groq Chat</span>
        <button class="new-chat-btn" @click="newChat" title="Cuộc trò chuyện mới">+</button>
      </div>

      <div class="conv-list">
        <div
          v-for="conv in conversations"
          :key="conv.id"
          class="conv-item"
          :class="{ active: conv.id === currentId }"
          @click="loadConv(conv.id)"
        >
          <span class="conv-title">{{ conv.title }}</span>
          <button class="del-btn" @click.stop="deleteConv(conv.id)">✕</button>
        </div>
        <div v-if="!conversations.length" class="no-conv">Chưa có cuộc trò chuyện</div>
      </div>
    </aside>

    <!-- Overlay mobile -->
    <div class="overlay" :class="{ show: sidebarOpen }" @click="sidebarOpen = false"></div>

    <!-- Main -->
    <div class="main">
      <!-- Header -->
      <div class="header">
        <button class="menu-btn" @click="sidebarOpen = !sidebarOpen">☰</button>
        <div class="header-controls">
          <select v-model="selectedSystem" class="ctrl-select" title="Vai trò AI">
            <option v-for="s in systemPrompts" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
          <select v-model="selectedModel" class="ctrl-select">
            <option v-for="m in models" :key="m.id" :value="m.id">{{ m.name }}</option>
          </select>
        </div>
      </div>

      <!-- Messages -->
      <div class="messages" ref="messagesEl">
        <div v-if="!messages.length" class="empty">
          <div class="empty-icon">🤖</div>
          <p>Bắt đầu cuộc trò chuyện</p>
          <div class="quick-prompts">
            <button v-for="q in quickPrompts" :key="q" class="quick-btn" @click="sendQuick(q)">{{ q }}</button>
          </div>
        </div>

        <div v-for="(msg, i) in messages" :key="i" class="message" :class="msg.role">
          <div class="avatar">{{ msg.role === 'user' ? '👤' : '🟠' }}</div>
          <div class="msg-wrap">
            <div class="bubble" v-html="renderContent(msg.content)"></div>
            <div class="msg-actions">
              <button class="action-btn" @click="copyMsg(msg.content, i)" :title="copied === i ? 'Đã copy!' : 'Copy'">
                {{ copied === i ? '✓' : '⎘' }}
              </button>
              <button v-if="msg.role === 'user'" class="action-btn" @click="resend(i)" title="Gửi lại">↺</button>
            </div>
          </div>
        </div>

        <!-- Streaming indicator -->
        <div v-if="streaming" class="message assistant">
          <div class="avatar">🟠</div>
          <div class="msg-wrap">
            <div class="bubble" v-html="renderContent(streamBuffer) || '<span class=\'dots\'><span>.</span><span>.</span><span>.</span></span>'"></div>
          </div>
        </div>
      </div>

      <!-- Input -->
      <div class="input-area">
        <div class="input-row">
          <textarea
            v-model="input"
            placeholder="Nhắn tin... (Enter gửi, Shift+Enter xuống dòng)"
            rows="1"
            @keydown.enter.exact.prevent="send"
            @input="autoResize"
            ref="textareaEl"
            :disabled="streaming"
          ></textarea>
          <button v-if="!streaming" class="send-btn" @click="send" :disabled="!input.trim()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
          <button v-else class="stop-btn" @click="stopStream" title="Dừng">■</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted } from 'vue'
import { marked } from 'marked'

// --- API base ---
const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
const models = [
  { id: 'llama-3.3-70b-versatile', name: 'Llama 3.3 70B' },
  { id: 'llama-3.1-8b-instant',    name: 'Llama 3.1 8B (Nhanh)' },
  { id: 'mixtral-8x7b-32768',       name: 'Mixtral 8x7B' },
  { id: 'gemma2-9b-it',             name: 'Gemma 2 9B' },
]
const systemPrompts = [
  { id: 'default',    name: '🤖 Trợ lý' },
  { id: 'coder',      name: '💻 Lập trình' },
  { id: 'translator', name: '🌐 Dịch thuật' },
  { id: 'teacher',    name: '📚 Giảng dạy' },
  { id: 'writer',     name: '✍️ Viết lách' },
]
const quickPrompts = [
  'Giải thích về AI',
  'Viết code Python đọc file CSV',
  'Dịch sang tiếng Anh: Xin chào',
  'Kể một câu chuyện ngắn',
]

const selectedModel  = ref('llama-3.3-70b-versatile')
const selectedSystem = ref('default')
const input          = ref('')
const messages       = ref([])
const streaming      = ref(false)
const streamBuffer   = ref('')
const messagesEl     = ref(null)
const textareaEl     = ref(null)
const sidebarOpen    = ref(false)
const copied         = ref(null)
const conversations  = ref([])
const currentId      = ref(null)
let   abortController = null

// --- Persistence ---
function saveConvs() {
  localStorage.setItem('groq_convs', JSON.stringify(conversations.value))
}

function loadConvs() {
  const raw = localStorage.getItem('groq_convs')
  if (raw) conversations.value = JSON.parse(raw)
}

function newChat() {
  const id = Date.now().toString()
  conversations.value.unshift({ id, title: 'Cuộc trò chuyện mới', messages: [], model: selectedModel.value, system: selectedSystem.value })
  currentId.value = id
  messages.value = []
  saveConvs()
  sidebarOpen.value = false
}

function loadConv(id) {
  const conv = conversations.value.find(c => c.id === id)
  if (!conv) return
  currentId.value = id
  messages.value = [...conv.messages]
  selectedModel.value  = conv.model  || 'llama-3.3-70b-versatile'
  selectedSystem.value = conv.system || 'default'
  sidebarOpen.value = false
  scrollToBottom()
}

function deleteConv(id) {
  conversations.value = conversations.value.filter(c => c.id !== id)
  if (currentId.value === id) {
    messages.value = []
    currentId.value = null
  }
  saveConvs()
}

function persistCurrent() {
  if (!currentId.value) return
  const conv = conversations.value.find(c => c.id === currentId.value)
  if (!conv) return
  conv.messages = [...messages.value]
  conv.model  = selectedModel.value
  conv.system = selectedSystem.value
  // Auto title from first user message
  const first = messages.value.find(m => m.role === 'user')
  if (first) conv.title = first.content.slice(0, 40) + (first.content.length > 40 ? '…' : '')
  saveConvs()
}

// --- Render ---
function renderContent(text) {
  if (!text) return ''
  return marked.parse(text)
}

// --- Scroll ---
async function scrollToBottom() {
  await nextTick()
  if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
}

// --- Resize textarea ---
function autoResize(e) {
  e.target.style.height = 'auto'
  e.target.style.height = Math.min(e.target.scrollHeight, 140) + 'px'
}

// --- Copy ---
async function copyMsg(content, idx) {
  await navigator.clipboard.writeText(content)
  copied.value = idx
  setTimeout(() => { copied.value = null }, 1500)
}

// --- Resend ---
function resend(idx) {
  const msg = messages.value[idx]
  if (!msg) return
  messages.value = messages.value.slice(0, idx)
  input.value = msg.content
  nextTick(() => send())
}

// --- Quick prompt ---
function sendQuick(text) {
  input.value = text
  send()
}

// --- Stop stream ---
function stopStream() {
  if (abortController) abortController.abort()
}

// --- Send ---
async function send() {
  const text = input.value.trim()
  if (!text || streaming.value) return

  // Create conv if none
  if (!currentId.value) newChat()

  messages.value.push({ role: 'user', content: text })
  input.value = ''
  if (textareaEl.value) textareaEl.value.style.height = 'auto'
  streaming.value = true
  streamBuffer.value = ''
  await scrollToBottom()

  abortController = new AbortController()

  try {
    const res = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: abortController.signal,
      body: JSON.stringify({
        messages: messages.value,
        model: selectedModel.value,
        system: selectedSystem.value,
      }),
    })

    const reader = res.body.getReader()
    const decoder = new TextDecoder()

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const lines = decoder.decode(value).split('\n')
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const data = line.slice(6)
        if (data === '[DONE]') break
        try {
          const parsed = JSON.parse(data)
          if (parsed.error) throw new Error(parsed.error)
          streamBuffer.value += parsed.content
          await scrollToBottom()
        } catch {}
      }
    }

    messages.value.push({ role: 'assistant', content: streamBuffer.value })
  } catch (e) {
    if (e.name !== 'AbortError') {
      messages.value.push({ role: 'assistant', content: `❌ Lỗi: ${e.message}` })
    } else if (streamBuffer.value) {
      messages.value.push({ role: 'assistant', content: streamBuffer.value + ' _(đã dừng)_' })
    }
  } finally {
    streaming.value = false
    streamBuffer.value = ''
    persistCurrent()
    await scrollToBottom()
  }
}

onMounted(() => {
  loadConvs()
})
</script>
