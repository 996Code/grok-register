<template>
  <div class="dashboard">
    <!-- Stat Cards -->
    <div class="stat-row">
      <div class="stat-card" v-for="card in statCards" :key="card.key" :class="card.cls">
        <div class="stat-icon-wrap" :class="card.cls">
          <span>{{ card.icon }}</span>
        </div>
        <div class="stat-info">
          <div class="stat-num">{{ card.value }}</div>
          <div class="stat-name">{{ card.label }}</div>
        </div>
      </div>
    </div>

    <!-- Control Bar -->
    <div class="control-bar">
      <div class="control-left">
        <label class="ctrl-label">注册数量</label>
        <n-input-number v-model:value="count" :min="1" :max="2500" size="large" style="width: 160px" />
        <n-tag v-if="stats.running" type="info" size="small" :bordered="false" round>
          正在处理 {{ stats.processed }}/{{ stats.total }}
        </n-tag>
      </div>
      <div class="control-right">
        <button
          v-if="!stats.running"
          class="btn-action btn-start"
          :disabled="starting"
          @click="handleStart"
        >
          {{ starting ? '启动中...' : '▶ 开始注册' }}
        </button>
        <button
          v-else
          class="btn-action btn-stop"
          :disabled="stopping"
          @click="handleStop"
        >
          {{ stopping ? '停止中...' : '⏹ 停止' }}
        </button>
      </div>
    </div>

    <!-- Log Panel -->
    <div class="log-panel">
      <div class="log-toolbar">
        <span class="log-title">📡 实时日志</span>
        <div class="log-tools">
          <span class="log-count">{{ logs.length }} 条</span>
          <button class="btn-tiny" @click="autoScroll = !autoScroll" :class="{ on: autoScroll }">
            {{ autoScroll ? '自动滚动 ✓' : '手动滚动' }}
          </button>
          <button class="btn-tiny" @click="logs = []">清空</button>
        </div>
      </div>
      <div ref="logBox" class="log-box">
        <div v-if="logs.length === 0" class="log-empty">
          <span style="font-size: 32px; opacity: 0.3;">📭</span>
          <p>暂无日志，点击「开始注册」启动</p>
        </div>
        <div
          v-for="line in displayLogs"
          :key="line.id"
          class="log-entry"
          :class="logClass(line)"
        >
          <span class="log-ts">{{ line.time }}</span>
          <span class="log-msg">{{ line.line }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import api from '../api'

const props = defineProps({ stats: Object })
const message = window.$message

const count = ref(1)
const starting = ref(false)
const stopping = ref(false)
const logs = ref([])
const autoScroll = ref(true)
const logBox = ref(null)
let logId = 0
let eventSource = null

// Newest first (reverse display)
const displayLogs = computed(() => [...logs.value].reverse())

onMounted(() => {
  eventSource = new EventSource('/api/register/stream')
  eventSource.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data)
      if (msg.type === 'log') {
        logs.value.push({ ...msg.data, id: logId++ })
        if (logs.value.length > 500) logs.value.shift()
        if (autoScroll.value) {
          nextTick(() => { if (logBox.value) logBox.value.scrollTop = 0 })
        }
      }
    } catch {}
  }
})
onUnmounted(() => eventSource?.close())

const statCards = computed(() => [
  { key: 'ok', label: '成功', value: props.stats?.success || 0, icon: '✅', cls: 'ok' },
  { key: 'fail', label: '失败', value: props.stats?.fail || 0, icon: '❌', cls: 'err' },
  { key: 'pend', label: '待恢复', value: props.stats?.pending || 0, icon: '⏳', cls: 'warn' },
  { key: 'warn', label: '警告', value: props.stats?.warnings || 0, icon: '⚠️', cls: 'info' },
])

function logClass(line) {
  const t = line.line || ''
  if (t.includes('[+]')) return 'le-ok'
  if (t.includes('[-]')) return 'le-err'
  if (t.includes('[!]')) return 'le-warn'
  if (t.includes('[Debug]')) return 'le-dbg'
  return 'le-info'
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
  } catch { message.error('停止失败') }
  finally { stopping.value = false }
}
</script>

<style scoped>
.dashboard { max-width: 1200px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; }

/* Stats */
.stat-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.stat-card {
  display: flex; align-items: center; gap: 14px;
  padding: 18px 20px; border-radius: 14px;
  background: #1a1a2e; border: 1px solid rgba(255,255,255,0.06);
  transition: all 0.2s;
}
.stat-card:hover { transform: translateY(-2px); border-color: rgba(255,255,255,0.12); }
.stat-icon-wrap {
  width: 44px; height: 44px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; flex-shrink: 0;
}
.stat-icon-wrap.ok { background: rgba(34,197,94,0.12); }
.stat-icon-wrap.err { background: rgba(239,68,68,0.12); }
.stat-icon-wrap.warn { background: rgba(251,191,36,0.12); }
.stat-icon-wrap.info { background: rgba(124,58,237,0.12); }
.stat-num { font-size: 26px; font-weight: 700; line-height: 1.1; color: #e2e8f0; }
.stat-name { font-size: 12px; color: #64748b; margin-top: 2px; }

/* Control */
.control-bar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px; border-radius: 14px;
  background: #1a1a2e; border: 1px solid rgba(255,255,255,0.06);
}
.control-left { display: flex; align-items: center; gap: 12px; }
.ctrl-label { font-size: 13px; color: #94a3b8; font-weight: 500; }

.btn-action {
  padding: 10px 24px; border-radius: 10px; border: none;
  font-size: 14px; font-weight: 600; cursor: pointer;
  transition: all 0.15s;
}
.btn-action:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-start {
  background: linear-gradient(135deg, #16a34a, #22c55e);
  color: white; box-shadow: 0 4px 12px rgba(34,197,94,0.25);
}
.btn-start:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 6px 16px rgba(34,197,94,0.35); }
.btn-stop {
  background: linear-gradient(135deg, #dc2626, #ef4444);
  color: white; box-shadow: 0 4px 12px rgba(239,68,68,0.25);
}
.btn-stop:hover:not(:disabled) { transform: translateY(-1px); }

/* Log */
.log-panel {
  border-radius: 14px; overflow: hidden;
  background: #1a1a2e; border: 1px solid rgba(255,255,255,0.06);
}
.log-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 16px;
  background: rgba(255,255,255,0.02);
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.log-title { font-size: 13px; font-weight: 600; color: #94a3b8; }
.log-tools { display: flex; align-items: center; gap: 8px; }
.log-count { font-size: 11px; color: #475569; }
.btn-tiny {
  padding: 3px 10px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.08);
  background: transparent; color: #64748b; font-size: 11px; cursor: pointer;
  transition: all 0.15s;
}
.btn-tiny:hover { background: rgba(255,255,255,0.05); color: #cbd5e1; }
.btn-tiny.on { background: rgba(124,58,237,0.15); color: #a78bfa; border-color: rgba(124,58,237,0.3); }

.log-box {
  height: 48vh; overflow-y: auto; padding: 12px 16px;
  font-family: 'SF Mono', 'Fira Code', 'Menlo', monospace;
  font-size: 12.5px; line-height: 1.8;
  background: #0d0d17;
}
.log-box::-webkit-scrollbar { width: 6px; }
.log-box::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }
.log-empty { text-align: center; padding: 40px; color: #475569; }
.log-empty p { font-size: 13px; margin-top: 8px; }
.log-entry { display: flex; gap: 10px; padding: 1px 0; }
.log-ts { color: #334155; flex-shrink: 0; font-size: 11px; padding-top: 2px; }
.log-msg { word-break: break-all; }
.le-ok .log-msg { color: #4ade80; }
.le-err .log-msg { color: #f87171; }
.le-warn .log-msg { color: #fbbf24; }
.le-dbg .log-msg { color: #475569; }
.le-info .log-msg { color: #cbd5e1; }
</style>
