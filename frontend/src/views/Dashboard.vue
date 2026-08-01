<template>
  <n-space vertical size="large">
    <!-- Stats Cards -->
    <n-grid :cols="4" :x-gap="16">
      <n-gi><StatCard title="成功" :value="stats.success" type="success" icon="✅" /></n-gi>
      <n-gi><StatCard title="失败" :value="stats.fail" type="error" icon="❌" /></n-gi>
      <n-gi><StatCard title="待恢复" :value="stats.pending" type="warning" icon="⏳" /></n-gi>
      <n-gi><StatCard title="警告" :value="stats.warnings" type="info" icon="⚠️" /></n-gi>
    </n-grid>

    <!-- Progress -->
    <n-card v-if="stats.running || stats.processed > 0">
      <n-space vertical>
        <n-progress
          type="line"
          :percentage="stats.total > 0 ? Math.round((stats.processed / stats.total) * 100) : 0"
          :status="stats.fail > 0 ? 'warning' : 'success'"
        />
        <n-text depth="3">已处理 {{ stats.processed }} / {{ stats.total }}</n-text>
      </n-space>
    </n-card>

    <!-- Controls -->
    <n-card title="注册控制">
      <n-space align="center">
        <n-input-number v-model:value="count" :min="1" :max="2500" style="width: 140px">
          <template #prefix>数量</template>
        </n-input-number>
        <n-button v-if="!stats.running" type="success" @click="handleStart" :loading="starting">
          开始注册
        </n-button>
        <n-button v-else type="error" :loading="stopping" @click="handleStop">
          停止注册
        </n-button>
      </n-space>
    </n-card>

    <!-- Live Log -->
    <n-card title="实时日志" style="flex: 1; min-height: 300px">
      <template #header-extra>
        <n-button size="small" @click="logs = []" quaternary>清空</n-button>
      </template>
      <div ref="logContainer" class="log-container">
        <div v-for="(line, i) in logs" :key="i" :class="logClass(line)">
          <span class="log-time">{{ line.time }}</span>
          <span>{{ line.line }}</span>
        </div>
      </div>
    </n-card>
  </n-space>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import StatCard from '../components/StatCard.vue'
import api from '../api'

const props = defineProps({ stats: Object })
const message = window.$message

const count = ref(1)
const starting = ref(false)
const stopping = ref(false)
const logs = ref([])
const logContainer = ref(null)

let eventSource = null

function connectSSE() {
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
}
connectSSE()

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
.log-container {
  max-height: 50vh;
  overflow-y: auto;
  font-family: 'Menlo', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.6;
  background: #1a1a1a;
  padding: 12px;
  border-radius: 6px;
}
.log-time {
  color: #666;
  margin-right: 8px;
}
.log-success { color: #52c41a; }
.log-error { color: #ff4d4f; }
.log-warning { color: #faad14; }
.log-debug { color: #888; }
.log-info { color: #d9d9d9; }
</style>
