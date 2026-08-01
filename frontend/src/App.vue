<template>
  <n-config-provider :theme="darkTheme" :locale="zhCN" :date-locale="dateZhCN">
    <n-layout style="height: 100vh">
      <n-layout-header bordered style="height: 56px; display: flex; align-items: center; padding: 0 24px;">
        <n-space align="center" style="width: 100%; justify-content: space-between;">
          <n-space align="center">
            <h2 style="margin: 0; font-size: 18px;">🚀 Grok Register</h2>
            <n-tag :type="stats.running ? 'success' : 'default'" size="small" round>
              {{ stats.running ? '注册中' : '空闲' }}
            </n-tag>
          </n-space>
          <n-space>
            <n-tag v-if="stats.success > 0" type="success" size="small">成功 {{ stats.success }}</n-tag>
            <n-tag v-if="stats.fail > 0" type="error" size="small">失败 {{ stats.fail }}</n-tag>
            <n-tag v-if="stats.pending > 0" type="warning" size="small">待恢复 {{ stats.pending }}</n-tag>
          </n-space>
        </n-space>
      </n-layout-header>
      <n-layout has-sider style="height: calc(100vh - 56px)">
        <n-layout-sider bordered :width="180">
          <n-menu v-model:value="activeTab" :options="menuOptions" />
        </n-layout-sider>
        <n-layout-content content-style="padding: 20px; overflow: auto;">
          <Dashboard v-if="activeTab === 'dashboard'" :stats="stats" />
          <Accounts v-else-if="activeTab === 'accounts'" />
          <GrokApi v-else-if="activeTab === 'grokapi'" />
          <ConfigView v-else-if="activeTab === 'config'" />
        </n-layout-content>
      </n-layout>
    </n-layout>
  </n-config-provider>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { darkTheme, zhCN, dateZhCN, createDiscreteApi } from 'naive-ui'

import Dashboard from './views/Dashboard.vue'
import Accounts from './views/Accounts.vue'
import GrokApi from './views/GrokApi.vue'
import ConfigView from './views/Config.vue'

// Use discrete API instead of provider components — works everywhere
const { message, dialog } = createDiscreteApi(['message', 'dialog'])
// Make available globally for child components
window.$message = message
window.$dialog = dialog

const activeTab = ref('dashboard')
const stats = reactive({ success: 0, fail: 0, pending: 0, warnings: 0, processed: 0, total: 0, running: false })

const menuOptions = [
  { label: '总览控制台', key: 'dashboard' },
  { label: '账号管理', key: 'accounts' },
  { label: 'Grok2API', key: 'grokapi' },
  { label: '配置', key: 'config' },
]

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
