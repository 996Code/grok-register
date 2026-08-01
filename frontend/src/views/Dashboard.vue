<template>
  <n-space vertical :size="16">
    <!-- Stats Cards -->
    <div class="stat-grid">
      <div class="stat-card success">
        <div class="stat-icon">✅</div>
        <div class="stat-body">
          <div class="stat-value">{{ stats.success }}</div>
          <div class="stat-label">成功</div>
        </div>
      </div>
      <div class="stat-card error">
        <div class="stat-icon">❌</div>
        <div class="stat-body">
          <div class="stat-value">{{ stats.fail }}</div>
          <div class="stat-label">失败</div>
        </div>
      </div>
      <div class="stat-card warning">
        <div class="stat-icon">⏳</div>
        <div class="stat-body">
          <div class="stat-value">{{ stats.pending }}</div>
          <div class="stat-label">待恢复</div>
        </div>
      </div>
      <div class="stat-card info">
        <div class="stat-icon">⚠️</div>
        <div class="stat-body">
          <div class="stat-value">{{ stats.warnings }}</div>
          <div class="stat-label">警告</div>
        </div>
      </div>
    </div>

    <!-- Control Panel -->
    <n-card :bordered="false" class="glass-card">
      <div class="control-row">
        <div class="control-left">
          <span class="control-label">注册数量</span>
          <n-input-number v-model:value="count" :min="1" :max="2500" size="large" style="width: 160px" />
        </div>
        <div class="control-right">
          <n-button v-if="!stats.running" type="success" size="large" @click="handleStart" :loading="starting">
            <template #icon>▶</template>
            开始注册
          </n-button>
          <n-button v-else type="error" size="large" @click="handleStop" :loading="stopping">
            <template #icon>⏹</template>
            停止注册
          </n-button>
        </div>
      </div>
    </n-card>

    <!-- Progress -->
    <n-card v-if="stats.running || stats.processed > 0" :bordered="false" class="glass-card">
      <n-space vertical :size="8">
        <div class="progress-header">
          <span>注册进度</span>
          <span class="progress-numbers">{{ stats.processed }} / {{ stats.total }}</span>
        </div>
        <n-progress
          type="line"
          :percentage="stats.total > 0 ? Math.round((stats.processed / stats.total) * 100) : 0"
          :status="stats.fail > 0 ? 'warning' : 'success'"
          :height="8"
          :border-radius="4"
        />
      </n-space>
    </n-card>

    <!-- Live Log -->
    <n-card :bordered="false" class="glass-card log-card">
      <template #header>
        <div class="log-header">
          <span>📡 实时日志</span>
          <n-button size="tiny" quaternary @click="logs = []">清空</n-button>
        </div>
      </template>
      <div ref="logContainer" class="log-container">
        <div v-if="logs.length === 0" class="log-empty">暂无日志，点击「开始注册」启动</div>
        <div v-for="(line, i) in logs" :key="i" :class="['log-line', logClass(line)]">
          <span class="log-time">{{ line.time }}</span>
          <span class="log-text">{{ line.line }}</span>
        </div>
      </div>
    </n-card>
  </n-space>
</template>

<script setup>
import { ref, nextTick, onMounted, onUnmounted } from 'vue'
import api from '../api'

const props = defineProps({ stats: Object })
const message = window.$message

const count = ref(1)
const starting = ref(false)
const stopping = ref(false)
const logs = ref([])
const logContainer = ref(null)

let eventSource = null

onMounted(() => {
  eventSource = new EventSource('/api/register/stream')
  eventSource.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data)
      if (msg.type === 'log') {
        logs.value.push(msg.data)
        if (logs.value.length > 500) logs.value.shift()
        nextTick(() => {
          if (logContainer.value) logContainer.value.scrollTop = logContainer.value.scrollHeight
        })
      }
    } catch {}
  }
})

onUnmounted(() => eventSource?.close())

function logClass(line) {
  const text = line.line || ''
  if (text.includes('[+]')) return 'log-success'
  if (text.includes('[-]')) return 'log-error'
  if (text.includes('[!]')) return 'log-warning'
  if (text.includes('[Debug]')) return 'log-debug'
  return 'log-info'
}

async function handleStart() {
  starting.value = true
  logs.value = []
  try {
    await api.startRegister(count.value)
    message.success(`已启动 ${count.value} 个账号注册`)
  } catch (e) {
    message.error(e.response?.data?.error || '启动失败')
  } finally {
    starting.value = false
  }
}

async function handleStop() {
  stopping.value = true
  try {
    await api.stopRegister()
    message.info('正在停止...')
  } catch {
    message.error('停止失败')
  } finally {
    stopping.value = false
  }
}
</script>

<style scoped>
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}
.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  border-radius: 12px;
  background: #1e1e2e;
  border: 1px solid #313244;
  transition: transform 0.2s, box-shadow 0.2s;
}
.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.3);
}
.stat-icon { font-size: 28px; }
.stat-value { font-size: 28px; font-weight: 700; line-height: 1.2; }
.stat-label { font-size: 13px; color: #888; }
.stat-card.success { border-left: 3px solid #52c41a; }
.stat-card.error { border-left: 3px solid #ff4d4f; }
.stat-card.warning { border-left: 3px solid #faad14; }
.stat-card.info { border-left: 3px solid #6366f1; }
.stat-card.success .stat-value { color: #52c41a; }
.stat-card.error .stat-value { color: #ff4d4f; }
.stat-card.warning .stat-value { color: #faad14; }
.stat-card.info .stat-value { color: #6366f1; }
.glass-card {
  background: #1e1e2e !important;
  border: 1px solid #313244 !important;
  border-radius: 12px !important;
}
.control-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.control-left { display: flex; align-items: center; gap: 12px; }
.control-label { font-size: 14px; color: #ccc; font-weight: 500; }
.progress-header {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: #ccc;
}
.progress-numbers { font-weight: 600; }
.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}
.log-card { flex: 1; }
.log-container {
  max-height: 45vh;
  overflow-y: auto;
  font-family: 'SF Mono', 'Menlo', monospace;
  font-size: 13px;
  line-height: 1.7;
  background: #11111b;
  padding: 16px;
  border-radius: 8px;
}
.log-empty { color: #555; text-align: center; padding: 20px; }
.log-line { display: flex; gap: 12px; }
.log-time { color: #555; flex-shrink: 0; }
.log-text { word-break: break-all; }
.log-success .log-text { color: #52c41a; }
.log-error .log-text { color: #ff4d4f; }
.log-warning .log-text { color: #faad14; }
.log-debug .log-text { color: #666; }
.log-info .log-text { color: #cdd6f4; }
</style>
