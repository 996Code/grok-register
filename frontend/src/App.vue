<template>
  <n-config-provider :theme="darkTheme" :locale="zhCN" :date-locale="dateZhCN">
    <n-message-provider>
      <n-dialog-provider>
        <AppContent :active-tab="activeTab" :stats="stats" />
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { darkTheme, zhCN, dateZhCN } from 'naive-ui'
import AppContent from './components/AppContent.vue'

const activeTab = ref('dashboard')
const stats = reactive({ success: 0, fail: 0, pending: 0, warnings: 0, processed: 0, total: 0, running: false })

let eventSource = null
let poll = null

onMounted(() => {
  eventSource = new EventSource('/api/register/stream')
  eventSource.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data)
      if (msg.type === 'stats') Object.assign(stats, msg.data)
      else if (msg.type === 'done') stats.running = false
      else if (msg.type === 'error') stats.running = false
    } catch {}
  }
  poll = setInterval(async () => {
    try {
      const res = await fetch('/api/register/status')
      const data = await res.json()
      Object.assign(stats, data)
    } catch {}
  }, 5000)
})

onUnmounted(() => {
  eventSource?.close()
  if (poll) clearInterval(poll)
})
</script>
