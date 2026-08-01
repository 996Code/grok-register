<template>
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
        <n-menu v-model:value="localTab" :options="menuOptions" />
      </n-layout-sider>
      <n-layout-content content-style="padding: 20px; overflow: auto;">
        <Dashboard v-if="localTab === 'dashboard'" :stats="stats" />
        <Accounts v-else-if="localTab === 'accounts'" />
        <GrokApi v-else-if="localTab === 'grokapi'" />
        <ConfigView v-else-if="localTab === 'config'" />
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<script setup>
import { ref, watch } from 'vue'
import Dashboard from '../views/Dashboard.vue'
import Accounts from '../views/Accounts.vue'
import GrokApi from '../views/GrokApi.vue'
import ConfigView from '../views/Config.vue'

const props = defineProps({ activeTab: String, stats: Object })
const emit = defineEmits(['update:activeTab'])

const localTab = ref(props.activeTab || 'dashboard')
watch(localTab, (v) => emit('update:activeTab', v))
watch(() => props.activeTab, (v) => { if (v) localTab.value = v })

const menuOptions = [
  { label: '总览控制台', key: 'dashboard' },
  { label: '账号管理', key: 'accounts' },
  { label: 'Grok2API', key: 'grokapi' },
  { label: '配置', key: 'config' },
]
</script>
