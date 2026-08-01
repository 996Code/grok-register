<template>
  <n-space vertical size="large">
    <!-- Login -->
    <n-card v-if="!token" title="Grok2API 登录">
      <n-form inline>
        <n-form-item label="用户名">
          <n-input v-model:value="username" placeholder="admin" style="width: 150px" />
        </n-form-item>
        <n-form-item label="密码">
          <n-input v-model:value="password" type="password" show-password-on="click" style="width: 200px" @keyup.enter="handleLogin" />
        </n-form-item>
        <n-form-item>
          <n-button type="primary" @click="handleLogin" :loading="loggingIn">登录</n-button>
        </n-form-item>
      </n-form>
    </n-card>

    <template v-if="token">
      <!-- Account Pool -->
      <n-card title="账号池">
        <template #header-extra>
          <n-button size="small" @click="loadAll" quaternary>刷新</n-button>
        </template>
        <n-data-table :columns="accountCols" :data="accounts" :bordered="false" size="small" />
      </n-card>

      <!-- API Keys -->
      <n-card title="API Keys">
        <template #header-extra>
          <n-button size="small" type="primary" @click="handleCreateKey">创建新 Key</n-button>
        </template>
        <n-data-table :columns="keyCols" :data="clientKeys" :bordered="false" size="small" />
      </n-card>

      <!-- Egress Nodes -->
      <n-card title="出口代理节点">
        <n-data-table :columns="egressCols" :data="egressNodes" :bordered="false" size="small" />
      </n-card>
    </template>
  </n-space>
</template>

<script setup>
import { ref, onMounted, h } from 'vue'
import { NTag, NButton as NBtn, NCode } from 'naive-ui'
import api from '../api'

const message = window.$message
const dialog = window.$dialog
const token = ref(localStorage.getItem('g2a_token') || '')
const username = ref('admin')
const password = ref('')
const loggingIn = ref(false)

const accounts = ref([])
const clientKeys = ref([])
const egressNodes = ref([])

const accountCols = [
  { title: '邮箱', key: 'email', render: (r) => r.email || '(未知)' },
  { title: '状态', key: 'authStatus', render: (r) => h(NTag, { type: r.authStatus === 'active' ? 'success' : 'default', size: 'small' }, { default: () => r.authStatus }) },
  { title: 'Tier', key: 'webTier', width: 80 },
  {
    title: '配额',
    key: 'quota',
    render: (r) => {
      const windows = r.quotaWindows || []
      if (!windows.length) return '未知'
      return windows.map(w => `${w.mode}: ${w.remaining}/${w.total}`).join(' | ')
    }
  },
  { title: 'Egress', key: 'egressNodeId', width: 80 },
  {
    title: '操作',
    key: 'actions',
    width: 180,
    render: (r) => h('div', { style: 'display: flex; gap: 4px;' }, [
      h(NBtn, { size: 'tiny', quaternary: true, onClick: () => refreshQuota(r.id) }, { default: () => '刷新配额' }),
      h(NBtn, {
        size: 'tiny', quaternary: true, type: 'error',
        onClick: () => dialog.warning({
          title: '确认删除',
          content: `删除账号 ${r.email || r.id}?`,
          positiveText: '删除',
          negativeText: '取消',
          onPositiveClick: () => deleteAccount(r.id),
        })
      }, { default: () => '删除' }),
    ])
  },
]

const keyCols = [
  { title: '名称', key: 'name' },
  { title: '前缀', key: 'prefix', render: (r) => h(NCode, null, { default: () => r.prefix }) },
  { title: 'RPM', key: 'rpmLimit', width: 80 },
  { title: '状态', key: 'enabled', render: (r) => h(NTag, { type: r.enabled ? 'success' : 'default', size: 'small' }, { default: () => r.enabled ? '启用' : '禁用' }) },
  {
    title: '操作',
    key: 'actions',
    width: 80,
    render: (r) => h(NBtn, {
      size: 'tiny', quaternary: true, type: 'error',
      onClick: () => dialog.warning({
        title: '确认删除',
        content: `删除 Key "${r.name}"?`,
        positiveText: '删除',
        negativeText: '取消',
        onPositiveClick: () => deleteKey(r.id),
      })
    }, { default: () => '删除' })
  },
]

const egressCols = [
  { title: '名称', key: 'name' },
  { title: 'Scope', key: 'scope', width: 120 },
  { title: '探测状态', key: 'probeStatus', render: (r) => h(NTag, { type: r.probeStatus === 'healthy' ? 'success' : 'error', size: 'small' }, { default: () => r.probeStatus }) },
  { title: '分配账号', key: 'assignedAccountCount', width: 90 },
]

async function handleLogin() {
  loggingIn.value = true
  try {
    const res = await api.grok2api.login(username.value, password.value)
    token.value = res.data.data.tokens.accessToken
    localStorage.setItem('g2a_token', token.value)
    message.success('登录成功')
    loadAll()
  } catch (e) {
    message.error('登录失败')
  } finally {
    loggingIn.value = false
  }
}

async function loadAll() {
  if (!token.value) return
  try {
    const [acc, keys, egress] = await Promise.all([
      api.grok2api.getAccounts(token.value),
      api.grok2api.getClientKeys(token.value),
      api.grok2api.getEgressNodes(token.value),
    ])
    accounts.value = acc.data.data?.items || []
    clientKeys.value = keys.data.data?.items || []
    egressNodes.value = egress.data.data?.items || []
  } catch (e) {
    if (e.response?.status === 401) {
      token.value = ''
      localStorage.removeItem('g2a_token')
      message.warning('Token 过期，请重新登录')
    }
  }
}

async function refreshQuota(id) {
  try {
    await api.grok2api.refreshQuota(token.value, id)
    message.success('配额刷新成功')
    loadAll()
  } catch {
    message.error('刷新失败')
  }
}

async function handleCreateKey() {
  try {
    const res = await api.grok2api.createClientKey(token.value, `key-${Date.now()}`)
    const secret = res.data.data.secret
    message.info(`新 Key: ${secret}`, { duration: 10000 })
    loadAll()
  } catch {
    message.error('创建失败')
  }
}

async function deleteAccount(id) {
  try {
    await api.grok2api.deleteAccount(token.value, id)
    message.success('账号已删除')
    loadAll()
  } catch {
    message.error('删除失败')
  }
}

async function deleteKey(id) {
  try {
    await api.grok2api.deleteClientKey(token.value, id)
    message.success('Key 已删除')
    loadAll()
  } catch {
    message.error('删除失败')
  }
}

onMounted(() => { if (token.value) loadAll() })
</script>
