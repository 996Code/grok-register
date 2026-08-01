<template>
  <n-config-provider :theme="darkTheme" :theme-overrides="themeOverrides" :locale="zhCN" :date-locale="dateZhCN">
    <n-global-style />
    <n-loading-bar-provider>
      <n-layout style="height: 100vh" class="app-layout">
        <n-layout-header bordered class="app-header">
          <div class="header-content">
            <div class="header-left">
              <span class="logo">🚀</span>
              <span class="title">Grok Register</span>
              <n-tag :type="stats.running ? 'success' : 'default'" size="small" round :bordered="false">
                <template #icon>
                  <span class="status-dot" :class="{ running: stats.running }"></span>
                </template>
                {{ stats.running ? '注册中' : '空闲' }}
              </n-tag>
            </div>
            <div class="header-right">
              <div v-if="stats.running" class="progress-info">
                <n-progress
                  type="line"
                  :percentage="stats.total > 0 ? Math.round((stats.processed / stats.total) * 100) : 0"
                  :show-indicator="false"
                  :height="4"
                  style="width: 120px"
                />
                <span class="progress-text">{{ stats.processed }}/{{ stats.total }}</span>
              </div>
              <n-tag v-if="stats.success > 0" type="success" size="small" :bordered="false">✅ {{ stats.success }}</n-tag>
              <n-tag v-if="stats.fail > 0" type="error" size="small" :bordered="false">❌ {{ stats.fail }}</n-tag>
            </div>
          </div>
        </n-layout-header>
        <n-layout has-sider style="height: calc(100vh - 56px)">
          <n-layout-sider bordered :width="200" class="app-sider">
            <div class="sider-logo">
              <n-gradient-text type="brand" style="font-size: 16px; font-weight: 700;">
                Grok Stack
              </n-gradient-text>
            </div>
            <n-menu v-model:value="activeTab" :options="menuOptions" :indent="18" />
            <div class="sider-footer">
              <n-button size="small" quaternary block @click="loadAll">
                <template #icon>🔄</template>
                刷新全部
              </n-button>
            </div>
          </n-layout-sider>
          <n-layout-content class="app-content">
            <div class="content-wrapper">
              <Dashboard v-if="activeTab === 'dashboard'" :stats="stats" />
              <Accounts v-else-if="activeTab === 'accounts'" />
              <GrokApi v-else-if="activeTab === 'grokapi'" />
              <ConfigView v-else-if="activeTab === 'config'" />
            </div>
          </n-layout-content>
        </n-layout>
      </n-layout>
    </n-loading-bar-provider>
  </n-config-provider>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, provide } from 'vue'
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
    primaryColor: '#6366f1',
    primaryColorHover: '#818cf8',
    primaryColorPressed: '#4f46e5',
    borderRadius: '8px',
    cardColor: '#1e1e2e',
    modalColor: '#1e1e2e',
    bodyColor: '#181825',
    siderColor: '#11111b',
    headerColor: '#181825',
  },
}

const activeTab = ref('dashboard')
const stats = reactive({ success: 0, fail: 0, pending: 0, warnings: 0, processed: 0, total: 0, running: false })

const menuOptions = [
  { label: '📊 总览控制台', key: 'dashboard' },
  { label: '📁 账号管理', key: 'accounts' },
  { label: '🔌 Grok2API', key: 'grokapi' },
  { label: '⚙️ 配置', key: 'config' },
]

const loadAll = () => {
  // Trigger refresh in child components via event
  window.dispatchEvent(new CustomEvent('refresh-all'))
}

provide('stats', stats)

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

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
.app-header {
  height: 56px;
  display: flex;
  align-items: center;
  padding: 0 24px;
}
.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}
.header-left { display: flex; align-items: center; gap: 12px; }
.header-right { display: flex; align-items: center; gap: 8px; }
.logo { font-size: 22px; }
.title { font-size: 18px; font-weight: 700; }
.status-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #999; display: inline-block;
}
.status-dot.running {
  background: #52c41a;
  animation: pulse 1.5s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
.progress-info { display: flex; align-items: center; gap: 8px; }
.progress-text { font-size: 12px; color: #999; }
.app-sider { display: flex; flex-direction: column; }
.sider-logo { padding: 16px 20px; border-bottom: 1px solid #333; }
.sider-footer { margin-top: auto; padding: 12px; border-top: 1px solid #333; }
.app-content { background: #181825; }
.content-wrapper { padding: 20px; max-width: 1400px; margin: 0 auto; }
</style>
