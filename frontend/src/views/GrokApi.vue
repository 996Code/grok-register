<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">🔌 Grok2API 状态</h2>
      <div class="header-actions">
        <a href="/api/grok2api/auto-login" target="_blank" class="btn-link">🎨 打开创意控制台</a>
        <a :href="grok2apiUrl" target="_blank" class="btn-link">🔗 Grok2API 后台</a>
        <button class="btn-primary-sm" @click="loadAll" :disabled="loading">🔄 刷新</button>
      </div>
    </div>

    <!-- API Access Info -->
    <div class="section">
      <div class="section-head">🌐 API 访问信息</div>
      <div class="info-grid">
        <div class="info-item">
          <span class="info-label">API 地址 (OpenAI 兼容)</span>
          <code class="info-value">{{ apiBaseUrl }}</code>
        </div>
        <div class="info-item">
          <span class="info-label">模型</span>
          <code class="info-value">grok-chat-fast</code>
        </div>
      </div>
    </div>

    <!-- API Keys -->
    <div class="section">
      <div class="section-head">
        <span>🔑 API Keys ({{ keys.length }})</span>
        <button class="btn-primary-sm" @click="createKey">+ 创建新 Key</button>
      </div>
      <div v-if="loading" class="loading-state">加载中...</div>
      <div v-else-if="keys.length === 0" class="empty-state"><p>暂无 API Key，点击创建</p></div>
      <div v-else class="key-list">
        <div v-for="k in keys" :key="k.id" class="key-row">
          <div class="key-info">
            <span class="key-name">{{ k.name }}</span>
            <code class="key-full" v-if="k.fullSecret">{{ k.fullSecret }}</code>
            <code class="key-prefix" v-else>g2a_{{ k.prefix }}_***<span class="key-hint">（仅创建时可见）</span></code>
          </div>
          <div class="key-actions">
            <button v-if="k.fullSecret" class="btn-tiny" @click="copyKey(k.fullSecret)">复制</button>
            <span class="meta-tag">{{ k.rpmLimit }} RPM</span>
          </div>
        </div>
      </div>
      <div v-if="newKeyMsg" class="new-key-tip">
        💡 {{ newKeyMsg }}
      </div>
    </div>

    <!-- Egress Nodes -->
    <div class="section">
      <div class="section-head">🛫 出口代理节点 ({{ egressNodes.length }})</div>
      <div v-if="egressNodes.length === 0" class="empty-state"><p>暂无代理节点</p></div>
      <div v-else class="egress-grid">
        <div v-for="node in egressNodes" :key="node.id" class="egress-card">
          <div class="egress-row">
            <span class="egress-name">{{ node.name }}</span>
            <span class="egress-badge" :class="node.probeStatus === 'healthy' ? 'badge-ok' : 'badge-err'">
              {{ node.probeStatus }}
            </span>
          </div>
          <div class="egress-meta">
            <span class="meta-tag">{{ node.scope }}</span>
            <span class="meta-tag">账号: {{ node.assignedAccountCount }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Connection Test -->
    <div class="section">
      <div class="section-head">🧪 连接测试</div>
      <div class="test-area">
        <button class="btn-primary-sm" @click="testApi" :disabled="testing">
          {{ testing ? '测试中...' : '测试 API 调用' }}
        </button>
        <div v-if="testResult" class="test-result" :class="testResult.ok ? 'test-ok' : 'test-err'">
          {{ testResult.message }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const message = window.$message
const loading = ref(false)
const testing = ref(false)
const keys = ref([])
const egressNodes = ref([])
const testResult = ref(null)
const newKeyMsg = ref('')

const grok2apiUrl = 'http://' + window.location.hostname + ':8000'
const apiBaseUrl = 'http://' + window.location.hostname + ':8000/v1'

async function loadAll() {
  loading.value = true
  try {
    const [keyRes, egressRes] = await Promise.all([
      api.grok2api.getClientKeys(),
      api.grok2api.getEgressNodes(),
    ])
    keys.value = (keyRes.data.data?.items || []).map(k => ({
      ...k,
      fullSecret: k.fullSecret || null,
    }))
    egressNodes.value = egressRes.data.data?.items || []
  } catch (e) {
    message.error('加载失败: ' + (e.response?.data?.error || e.message))
  } finally {
    loading.value = false
  }
}

async function createKey() {
  newKeyMsg.value = ''
  try {
    const res = await api.grok2api.createClientKey(`key-${Date.now()}`)
    const secret = res.data.data.secret
    // Mark the new key with its full secret
    await loadAll()
    const newKey = keys.value.find(k => k.prefix === secret.split('_')[1])
    if (newKey) newKey.fullSecret = secret
    newKeyMsg.value = `新 Key 已创建，请立即复制保存（仅显示一次）: ${secret}`
    message.success('Key 创建成功，请复制保存')
  } catch { message.error('创建失败') }
}

function copyKey(secret) {
  navigator.clipboard.writeText(secret).then(() => {
    message.success('已复制到剪贴板')
  }).catch(() => {
    message.error('复制失败')
  })
}

async function testApi() {
  testing.value = true
  testResult.value = null
  try {
    const resp = await fetch('/api/grok2api/accounts').then(r => r.json())
    if (resp.data) {
      const count = resp.data.items?.length || 0
      testResult.value = { ok: true, message: `✅ grok2api 连接正常，${count} 个在线账号` }
    }
  } catch (e) {
    testResult.value = { ok: false, message: '❌ 连接失败: ' + e.message }
  } finally {
    testing.value = false
  }
}

onMounted(loadAll)
window.addEventListener('refresh-all', loadAll)
</script>

<style scoped>
.page { max-width: 900px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; }
.page-header { display: flex; align-items: center; justify-content: space-between; }
.page-title { font-size: 20px; font-weight: 700; color: #e2e8f0; }
.header-actions { display: flex; gap: 8px; align-items: center; }
.btn-link {
  padding: 6px 14px; border-radius: 8px; border: 1px solid rgba(59,130,246,0.3);
  background: rgba(59,130,246,0.1); color: #60a5fa; font-size: 13px;
  cursor: pointer; text-decoration: none; transition: all 0.15s;
}
.btn-link:hover { background: rgba(59,130,246,0.2); }

.section {
  background: #1a1a2e; border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px; padding: 20px;
}
.section-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 16px; font-size: 15px; font-weight: 600; color: #cbd5e1;
}

.info-grid { display: flex; flex-direction: column; gap: 10px; }
.info-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; background: #16162a; border-radius: 8px;
}
.info-label { font-size: 13px; color: #64748b; }
.info-value { font-size: 13px; color: #a78bfa; font-family: monospace; }

.loading-state, .empty-state { text-align: center; padding: 30px; color: #475569; }

.key-list { display: flex; flex-direction: column; gap: 8px; }
.key-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; background: #16162a; border-radius: 8px;
}
.key-info { display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0; }
.key-name { font-size: 14px; color: #e2e8f0; flex-shrink: 0; }
.key-full {
  font-size: 12px; color: #4ade80; font-family: monospace;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.key-prefix { font-size: 12px; color: #64748b; font-family: monospace; }
.key-hint { font-size: 10px; color: #475569; margin-left: 4px; }
.key-actions { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }

.new-key-tip {
  margin-top: 12px; padding: 10px 14px; border-radius: 8px;
  background: rgba(34,197,94,0.08); color: #4ade80; font-size: 12px;
  word-break: break-all;
}

.egress-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 10px; }
.egress-card {
  background: #16162a; border: 1px solid rgba(255,255,255,0.05);
  border-radius: 8px; padding: 12px;
}
.egress-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.egress-name { font-size: 13px; font-weight: 600; color: #e2e8f0; }
.egress-badge { padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; }
.badge-ok { background: rgba(34,197,94,0.15); color: #4ade80; }
.badge-err { background: rgba(239,68,68,0.15); color: #f87171; }
.egress-meta { display: flex; gap: 6px; }
.meta-tag { font-size: 11px; color: #64748b; background: rgba(255,255,255,0.04); padding: 2px 8px; border-radius: 4px; }

.test-area { display: flex; flex-direction: column; gap: 12px; }
.test-result { padding: 12px 16px; border-radius: 8px; font-size: 13px; }
.test-ok { background: rgba(34,197,94,0.1); color: #4ade80; }
.test-err { background: rgba(239,68,68,0.1); color: #f87171; }

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
</style>
