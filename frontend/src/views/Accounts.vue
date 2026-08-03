<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">👥 账号管理</h2>
      <button class="btn-primary-sm" @click="loadAll" :disabled="loading">🔄 刷新</button>
    </div>

    <!-- Online accounts from grok2api -->
    <div class="section">
      <div class="section-head">
        <span>🌐 在线账号池 ({{ accounts.length }})</span>
        <div class="section-actions">
          <button class="btn-primary-sm" @click="refreshAllQuota" :disabled="refreshingAll">
            {{ refreshingAll ? `刷新中(${refreshProgress}/${accounts.length})...` : '🔄 全部刷新配额' }}
          </button>
        </div>
      </div>
      <div v-if="loading" class="loading-state">加载中...</div>
      <div v-else-if="accounts.length === 0" class="empty-state">
        <span style="font-size: 32px; opacity: 0.3;">📭</span>
        <p>暂无在线账号</p>
      </div>
      <div v-else class="account-grid">
        <div v-for="acc in accounts" :key="acc.id" class="account-card">
          <div class="acc-row">
            <span class="acc-email">{{ acc.email || '(未知)' }}</span>
            <span class="acc-badge" :class="acc.authStatus === 'active' ? 'badge-ok' : 'badge-err'">
              {{ acc.authStatus }}
            </span>
          </div>
          <div class="acc-meta">
            <span class="meta-tag">Tier: {{ acc.webTier || '?' }}</span>
            <span class="meta-tag">ID: {{ acc.id }}</span>
          </div>
          <div v-if="acc.quotaWindows && acc.quotaWindows.length" class="quota-bar">
            <div v-for="w in acc.quotaWindows" :key="w.mode" class="quota-item">
              <div class="quota-label">{{ w.mode }}</div>
              <div class="quota-track">
                <div class="quota-fill" :style="{ width: (w.total > 0 ? (w.remaining / w.total * 100) : 0) + '%' }"></div>
              </div>
              <div class="quota-text">{{ w.remaining }}/{{ w.total }}</div>
            </div>
          </div>
          <div class="acc-actions">
            <button class="btn-tiny" @click="refreshQuota(acc.id)">刷新配额</button>
            <button class="btn-tiny danger" @click="deleteAccount(acc)">删除</button>
          </div>
        </div>
      </div>
    </div>

    <!-- API Keys -->
    <div class="section">
      <div class="section-head">
        <span>🔑 API Keys ({{ keys.length }})</span>
        <button class="btn-primary-sm" @click="createKey">+ 创建</button>
      </div>
      <div v-if="keys.length === 0" class="empty-state"><p>暂无 API Key</p></div>
      <div v-else class="key-list">
        <div v-for="k in keys" :key="k.id" class="key-row">
          <div class="key-info">
            <span class="key-name">{{ k.name }}</span>
            <code class="key-prefix">g2a_{{ k.prefix }}_...</code>
          </div>
          <div class="key-actions">
            <span class="meta-tag">{{ k.rpmLimit }} RPM</span>
            <button class="btn-tiny danger" @click="deleteKey(k)">删除</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Pending files -->
    <div v-if="pending.length > 0" class="section">
      <div class="section-head">
        <span>⏳ 待恢复 ({{ pending.length }})</span>
      </div>
      <div v-for="p in pending" :key="p.file" class="pending-row">
        <span class="meta-tag">{{ p.file }}</span>
        <span class="meta-tag">{{ p.count }} 条</span>
        <button class="btn-tiny" @click="retryPending(p.file)">恢复</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, h } from 'vue'
import api from '../api'

const message = window.$message
const dialog = window.$dialog

const accounts = ref([])
const keys = ref([])
const pending = ref([])
const loading = ref(false)
const refreshingAll = ref(false)
const refreshProgress = ref(0)

async function loadAll() {
  loading.value = true
  try {
    const [accRes, keyRes, pendRes] = await Promise.all([
      api.grok2api.getAccounts(),
      api.grok2api.getClientKeys(),
      api.getPending(),
    ])
    accounts.value = accRes.data.data?.items || []
    keys.value = keyRes.data.data?.items || []
    pending.value = pendRes.data.pending || []
  } catch (e) {
    message.error('加载数据失败: ' + (e.response?.data?.error || e.message))
  } finally {
    loading.value = false
  }
}

async function refreshQuota(id) {
  try {
    await api.grok2api.refreshQuota(id)
    message.success('配额已刷新')
    loadAll()
  } catch { message.error('刷新失败') }
}

async function refreshAllQuota() {
  if (accounts.value.length === 0) return
  refreshingAll.value = true
  refreshProgress.value = 0
  let ok = 0, fail = 0
  for (const acc of accounts.value) {
    try {
      await api.grok2api.refreshQuota(acc.id)
      ok++
    } catch {
      fail++
    }
    refreshProgress.value++
  }
  refreshingAll.value = false
  await loadAll()
  message.success(`批量刷新完成: ${ok} 成功, ${fail} 失败`)
}

async function deleteAccount(acc) {
  dialog.warning({
    title: '删除账号',
    content: `确认删除 ${acc.email || acc.id}？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await api.grok2api.deleteAccount(acc.id)
        message.success('已删除')
        loadAll()
      } catch { message.error('删除失败') }
    },
  })
}

async function createKey() {
  try {
    const res = await api.grok2api.createClientKey(`key-${Date.now()}`)
    message.success(`Key 已创建: ${res.data.data.secret}`, { duration: 10000 })
    loadAll()
  } catch { message.error('创建失败') }
}

async function deleteKey(k) {
  dialog.warning({
    title: '删除 Key',
    content: `确认删除 "${k.name}"？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await api.grok2api.deleteClientKey(k.id)
        message.success('已删除')
        loadAll()
      } catch { message.error('删除失败') }
    },
  })
}

async function retryPending(file) {
  try {
    const res = await api.retryPending(file)
    message.success(`恢复 ${res.data.restored} 条，剩余 ${res.data.remaining} 条`)
    loadAll()
  } catch { message.error('恢复失败') }
}

onMounted(loadAll)
window.addEventListener('refresh-all', loadAll)
</script>

<style scoped>
.page { max-width: 1100px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; }
.page-header { display: flex; align-items: center; justify-content: space-between; }
.page-title { font-size: 20px; font-weight: 700; color: #e2e8f0; }

.section {
  background: #1a1a2e; border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px; padding: 20px;
}
.section-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 16px; font-size: 15px; font-weight: 600; color: #cbd5e1;
}
.section-sub { font-size: 12px; color: #64748b; font-weight: 400; }

.loading-state, .empty-state {
  text-align: center; padding: 40px; color: #475569; font-size: 14px;
}

.account-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 12px; }
.account-card {
  background: #16162a; border: 1px solid rgba(255,255,255,0.05);
  border-radius: 10px; padding: 14px;
}
.acc-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.acc-email { font-size: 14px; font-weight: 600; color: #e2e8f0; }
.acc-badge {
  padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 600;
}
.badge-ok { background: rgba(34,197,94,0.15); color: #4ade80; }
.badge-err { background: rgba(239,68,68,0.15); color: #f87171; }
.acc-meta { display: flex; gap: 8px; margin-bottom: 10px; }
.meta-tag { font-size: 11px; color: #64748b; background: rgba(255,255,255,0.04); padding: 2px 8px; border-radius: 4px; }

.quota-bar { display: flex; flex-direction: column; gap: 6px; margin-bottom: 10px; }
.quota-item { display: flex; align-items: center; gap: 8px; }
.quota-label { font-size: 11px; color: #64748b; width: 40px; }
.quota-track { flex: 1; height: 5px; background: rgba(255,255,255,0.06); border-radius: 3px; }
.quota-fill { height: 100%; background: linear-gradient(90deg, #7c3aed, #a78bfa); border-radius: 3px; }
.quota-text { font-size: 11px; color: #94a3b8; width: 50px; text-align: right; }

.acc-actions { display: flex; gap: 6px; }

.key-list { display: flex; flex-direction: column; gap: 8px; }
.key-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; background: #16162a; border-radius: 8px;
}
.key-info { display: flex; align-items: center; gap: 12px; }
.key-name { font-size: 14px; color: #e2e8f0; }
.key-prefix { font-size: 12px; color: #a78bfa; font-family: monospace; }
.key-actions { display: flex; align-items: center; gap: 8px; }

.pending-row { display: flex; align-items: center; gap: 8px; padding: 8px 0; }

.btn-primary-sm {
  padding: 6px 14px; border-radius: 8px; border: 1px solid rgba(124,58,237,0.3);
  background: rgba(124,58,237,0.1); color: #a78bfa; font-size: 13px;
  cursor: pointer; transition: all 0.15s;
}
.btn-primary-sm:hover { background: rgba(124,58,237,0.2); }
.btn-primary-sm:disabled { opacity: 0.5; }

.btn-tiny {
  padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.08);
  background: transparent; color: #94a3b8; font-size: 11px; cursor: pointer;
}
.btn-tiny:hover { background: rgba(255,255,255,0.05); color: #e2e8f0; }
.btn-tiny.danger { color: #f87171; }
.btn-tiny.danger:hover { background: rgba(239,68,68,0.1); }
</style>
