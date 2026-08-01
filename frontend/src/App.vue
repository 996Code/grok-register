<template>
  <n-config-provider :theme="darkTheme" :theme-overrides="themeOverrides" :locale="zhCN" :date-locale="dateZhCN">
    <n-global-style />
    <div class="app-root">
      <!-- Sidebar -->
      <aside class="sidebar">
        <div class="sidebar-brand">
          <div class="brand-icon">🚀</div>
          <div>
            <div class="brand-title">Grok Stack</div>
            <div class="brand-sub">控制台</div>
          </div>
        </div>
        <nav class="sidebar-nav">
          <button
            v-for="item in menuItems"
            :key="item.key"
            :class="['nav-item', { active: activeTab === item.key }]"
            @click="activeTab = item.key"
          >
            <span class="nav-icon">{{ item.icon }}</span>
            <span class="nav-label">{{ item.label }}</span>
          </button>
        </nav>
        <div class="sidebar-status">
          <div class="status-pill" :class="{ running: stats.running }">
            <span class="status-indicator"></span>
            {{ stats.running ? '运行中' : '空闲' }}
          </div>
        </div>
      </aside>

      <!-- Main -->
      <main class="main-area">
        <header class="top-bar">
          <div class="top-stats">
            <div v-if="stats.success > 0" class="mini-stat ok">✅ {{ stats.success }}</div>
            <div v-if="stats.fail > 0" class="mini-stat err">❌ {{ stats.fail }}</div>
            <div v-if="stats.pending > 0" class="mini-stat warn">⏳ {{ stats.pending }}</div>
          </div>
          <div v-if="stats.running" class="top-progress">
            <div class="progress-bar-track">
              <div class="progress-bar-fill" :style="{ width: progressPct + '%' }"></div>
            </div>
            <span class="progress-num">{{ stats.processed }}/{{ stats.total }}</span>
          </div>
        </header>
        <div class="content-scroll">
          <Dashboard v-if="activeTab === 'dashboard'" :stats="stats" />
          <Accounts v-else-if="activeTab === 'accounts'" />
          <GrokApi v-else-if="activeTab === 'grokapi'" />
          <ConfigView v-else-if="activeTab === 'config'" />
        </div>
      </main>
    </div>
  </n-config-provider>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { darkTheme, zhCN, dateZhCN, createDiscreteApi } from 'naive-ui'
import Dashboard from './views/Dashboard.vue'
import Accounts from './views/Accounts.vue'
import GrokApi from './views/GrokApi.vue'
import ConfigView from './views/Config.vue'

const { message, dialog } = createDiscreteApi(['message', 'dialog'])
window.$message = message
window.$dialog = dialog

const themeOverrides = {
  common: {
    primaryColor: '#7c3aed',
    primaryColorHover: '#8b5cf6',
    primaryColorPressed: '#6d28d9',
    borderRadius: '10px',
    bodyColor: '#0f0f1a',
    cardColor: '#1a1a2e',
    modalColor: '#1a1a2e',
    popoverColor: '#1a1a2e',
    tableHeaderColor: '#16213e',
  },
}

const activeTab = ref('dashboard')
const stats = reactive({ success: 0, fail: 0, pending: 0, warnings: 0, processed: 0, total: 0, running: false })
const progressPct = computed(() => stats.total > 0 ? Math.round((stats.processed / stats.total) * 100) : 0)

const menuItems = [
  { key: 'dashboard', label: '总览控制台', icon: '📊' },
  { key: 'accounts', label: '账号管理', icon: '👥' },
  { key: 'grokapi', label: 'Grok2API', icon: '🔌' },
  { key: 'config', label: '系统配置', icon: '⚙️' },
]

let eventSource = null, poll = null

onMounted(() => {
  eventSource = new EventSource('/api/register/stream')
  eventSource.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data)
      if (msg.type === 'stats') Object.assign(stats, msg.data)
      else if (msg.type === 'done' || msg.type === 'error') stats.running = false
    } catch {}
  }
  poll = setInterval(async () => {
    try {
      const res = await fetch('/api/register/status')
      Object.assign(stats, await res.json())
    } catch {}
  }, 5000)
})
onUnmounted(() => { eventSource?.close(); if (poll) clearInterval(poll) })
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f0f1a; }

.app-root { display: flex; height: 100vh; overflow: hidden; }

/* Sidebar */
.sidebar {
  width: 220px; flex-shrink: 0;
  background: linear-gradient(180deg, #0d0d1a 0%, #111125 100%);
  border-right: 1px solid rgba(255,255,255,0.06);
  display: flex; flex-direction: column;
  padding: 20px 0;
}
.sidebar-brand {
  display: flex; align-items: center; gap: 12px;
  padding: 0 20px 20px; margin-bottom: 8px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.brand-icon { font-size: 28px; }
.brand-title { font-size: 16px; font-weight: 700; color: #e2e8f0; }
.brand-sub { font-size: 11px; color: #64748b; margin-top: 2px; }

.sidebar-nav { flex: 1; padding: 12px; display: flex; flex-direction: column; gap: 4px; }
.nav-item {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 14px; border-radius: 10px;
  border: none; background: transparent; cursor: pointer;
  color: #64748b; font-size: 14px; font-weight: 500;
  transition: all 0.15s; text-align: left; width: 100%;
}
.nav-item:hover { background: rgba(255,255,255,0.04); color: #cbd5e1; }
.nav-item.active {
  background: linear-gradient(135deg, rgba(124,58,237,0.2), rgba(139,92,246,0.1));
  color: #a78bfa; border: 1px solid rgba(124,58,237,0.3);
}
.nav-icon { font-size: 18px; width: 24px; text-align: center; }

.sidebar-status { padding: 16px 20px; border-top: 1px solid rgba(255,255,255,0.06); }
.status-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 12px; border-radius: 20px;
  background: rgba(100,116,139,0.15); color: #64748b;
  font-size: 12px; font-weight: 600;
}
.status-pill.running { background: rgba(34,197,94,0.15); color: #4ade80; }
.status-indicator {
  width: 6px; height: 6px; border-radius: 50%;
  background: #64748b;
}
.status-pill.running .status-indicator { background: #4ade80; animation: pulse 1.5s infinite; }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }

/* Main */
.main-area { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.top-bar {
  height: 52px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: flex-end;
  gap: 16px; padding: 0 24px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  background: rgba(26,26,46,0.5);
}
.top-stats { display: flex; gap: 8px; }
.mini-stat { font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 6px; }
.mini-stat.ok { background: rgba(34,197,94,0.15); color: #4ade80; }
.mini-stat.err { background: rgba(239,68,68,0.15); color: #f87171; }
.mini-stat.warn { background: rgba(251,191,36,0.15); color: #fbbf24; }

.top-progress { display: flex; align-items: center; gap: 8px; }
.progress-bar-track { width: 100px; height: 4px; background: rgba(255,255,255,0.08); border-radius: 2px; }
.progress-bar-fill { height: 100%; background: linear-gradient(90deg, #7c3aed, #a78bfa); border-radius: 2px; transition: width 0.3s; }
.progress-num { font-size: 11px; color: #64748b; }

.content-scroll { flex: 1; overflow-y: auto; padding: 24px; }
</style>
