<template>
  <n-space vertical size="large">
    <n-card>
      <n-space align="center" justify="space-between">
        <n-h3 style="margin: 0">已注册账号 ({{ accounts.length }})</n-h3>
        <n-space>
          <n-button @click="loadAccounts" :loading="loading" quaternary>刷新</n-button>
          <n-button @click="checkAllAlive" :loading="checkingAll" quaternary>全部探活</n-button>
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
      :row-key="(row) => row._idx"
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
import { useMessage, NTag, NButton as NBtn, NTooltip } from 'naive-ui'
import api from '../api'

const message = useMessage()
const accounts = ref([])
const pending = ref([])
const loading = ref(false)
const checkingAll = ref(false)
const aliveStatus = ref({}) // idx -> {alive, checking, message}

const columns = [
  { title: '#', key: '_idx', width: 50 },
  { title: '邮箱', key: 'email', ellipsis: { tooltip: true } },
  { title: '密码', key: 'password', width: 150, ellipsis: { tooltip: true } },
  { title: 'SSO Token', key: 'sso', ellipsis: { tooltip: true } },
  {
    title: '状态',
    key: 'alive',
    width: 100,
    render: (row) => {
      const status = aliveStatus.value[row._idx]
      if (!status) return h(NTag, { size: 'small', type: 'default', bordered: false }, { default: () => '未检测' })
      if (status.checking) return h(NTag, { size: 'small', type: 'info', bordered: false }, { default: () => '检测中...' })
      return h(NTag, {
        size: 'small',
        type: status.alive ? 'success' : 'error',
        bordered: false,
      }, { default: () => status.alive ? '✅ 有效' : '❌ 失效' })
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 100,
    render: (row) => h(NBtn, {
      size: 'tiny',
      quaternary: true,
      loading: aliveStatus.value[row._idx]?.checking,
      onClick: () => checkAlive(row._idx),
    }, { default: () => '探活' })
  },
]

async function loadAccounts() {
  loading.value = true
  try {
    const [accRes, pendRes] = await Promise.all([api.getAccounts(), api.getPending()])
    accounts.value = accRes.data.accounts.map((a, i) => ({ ...a, _idx: i }))
    pending.value = pendRes.data.pending
    aliveStatus.value = {}
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

async function checkAlive(idx) {
  aliveStatus.value[idx] = { ...aliveStatus.value[idx], checking: true }
  try {
    const res = await api.checkAccount(idx)
    aliveStatus.value[idx] = {
      alive: res.data.alive,
      checking: false,
      message: res.data.message,
    }
    if (res.data.alive) message.success(`${accounts.value[idx]?.email}: 有效`)
    else message.warning(`${accounts.value[idx]?.email}: 失效`)
  } catch (e) {
    aliveStatus.value[idx] = { alive: false, checking: false, message: e.response?.data?.error || '检测失败' }
    message.error('探活失败')
  }
}

async function checkAllAlive() {
  checkingAll.value = true
  for (const acc of accounts.value) {
    await checkAlive(acc._idx)
  }
  checkingAll.value = false
  message.info('全部探活完成')
}

onMounted(loadAccounts)
</script>
