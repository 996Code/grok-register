<template>
  <n-space vertical size="large">
    <n-card>
      <n-space align="center" justify="space-between">
        <n-space align="center">
          <n-h3 style="margin: 0">已注册账号 ({{ accounts.length }})</n-h3>
        </n-space>
        <n-space>
          <n-button @click="loadAccounts" :loading="loading" quaternary>刷新</n-button>
          <n-button @click="downloadAccounts" quaternary>下载 TXT</n-button>
        </n-space>
      </n-space>
    </n-card>

    <n-data-table
      :columns="columns"
      :data="accounts"
      :pagination="{ pageSize: 20 }"
      :bordered="false"
      size="small"
    />

    <!-- Pending Recovery -->
    <n-card v-if="pending.length > 0" title="待恢复文件">
      <n-space vertical>
        <div v-for="p in pending" :key="p.file">
          <n-space align="center">
            <n-tag type="warning">{{ p.file }}</n-tag>
            <n-text depth="3">{{ p.count }} 条</n-text>
            <n-button size="small" @click="handleRetry(p.file)">恢复</n-button>
          </n-space>
        </div>
      </n-space>
    </n-card>
  </n-space>
</template>

<script setup>
import { ref, onMounted, h } from 'vue'
import { useMessage, NButton as NBtn, NTag } from 'naive-ui'
import api from '../api'

const message = useMessage()
const accounts = ref([])
const pending = ref([])
const loading = ref(false)

const columns = [
  { title: '邮箱', key: 'email', ellipsis: { tooltip: true } },
  { title: '密码', key: 'password', ellipsis: { tooltip: true } },
  { title: 'SSO Token', key: 'sso', ellipsis: { tooltip: true } },
  { title: '文件', key: 'file', width: 200, render: (row) => h(NTag, { size: 'small' }, { default: () => row.file }) },
]

async function loadAccounts() {
  loading.value = true
  try {
    const [accRes, pendRes] = await Promise.all([api.getAccounts(), api.getPending()])
    accounts.value = accRes.data.accounts
    pending.value = pendRes.data.pending
  } catch (e) {
    message.error('加载失败')
  } finally {
    loading.value = false
  }
}

function downloadAccounts() {
  window.open('/api/accounts/download', '_blank')
}

async function handleRetry(file) {
  try {
    await api.retryPending(file)
    message.success('恢复完成')
    loadAccounts()
  } catch (e) {
    message.error(e.response?.data?.error || '恢复失败')
  }
}

onMounted(loadAccounts)
</script>
