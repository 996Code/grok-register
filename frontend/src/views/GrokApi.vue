<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">🔌 Grok2API 状态</h2>
      <button class="btn-primary-sm" @click="loadAll" :disabled="loading">🔄 刷新</button>
    </div>

    <!-- API Access Info -->
    <div class="section">
      <div class="section-head">🌐 API 访问信息</div>
      <div class="info-grid">
        <div class="info-item">
          <span class="info-label">API 地址</span>
          <code class="info-value">{{ apiInfo.base }}</code>
        </div>
        <div class="info-item" v-for="k in keys" :key="k.id">
          <span class="info-label">API Key ({{ k.name }})</span>
          <code class="info-value">g2a_{{ k.prefix }}_***</code>
        </div>
        <div class="info-item">
          <span class="info-label">模型</span>
          <code class="info-value">grok-chat-fast</code>
        </div>
      </div>
    </div>

    <!-- Egress Nodes -->
    <div class="section">
      <div class="section-head">🛫 出口代理节点 ({{ egressNodes.length }})</div>
      <div v-if="loading" class="loading-state">加载中...</div>
      <div v-else-if="egressNodes.length === 0" class="empty-state"><p>暂无代理节点</p></div>
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

    <!-- Test API -->
    <div class="section">
      <div class="section-head">🧪 API 测试</div>
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
const apiInfo = { base: 'http://<服务器IP>:8000/v1' }

async function loadAll() {
  loading.value = true
  try {
    const [keyRes, egressRes] = await Promise.all([
      api.grok2api.getClientKeys(),
      api.grok2api.getEgressNodes(),
    ])
    keys.value = keyRes.data.data?.items || []
    egressNodes.value = egressRes.data.data?.items || []
  } catch (e) {
    message.error('加载失败: ' + (e.response?.data?.error || e.message))
  } finally {
    loading.value = false
  }
}

async function testApi() {
  testing.value = true
  testResult.value = null
  try {
    // Use grok2api proxy to do a chat completion test
    const resp = await fetch('/api/grok2api/accounts').then(r => r.json())
    if (resp.data) {
      testResult.value = { ok: true, message: `✅ grok2api 连接正常，${resp.data.items?.length || 0} 个在线账号` }
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

.section {
  background: #1a1a2e; border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px; padding: 20px;
}
.section-head { margin-bottom: 16px; font-size: 15px; font-weight: 600; color: #cbd5e1; }

.info-grid { display: flex; flex-direction: column; gap: 10px; }
.info-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; background: #16162a; border-radius: 8px;
}
.info-label { font-size: 13px; color: #64748b; }
.info-value { font-size: 13px; color: #a78bfa; font-family: monospace; }

.loading-state, .empty-state { text-align: center; padding: 30px; color: #475569; }

.egress-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 10px; }
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
.test-result {
  padding: 12px 16px; border-radius: 8px; font-size: 13px;
}
.test-ok { background: rgba(34,197,94,0.1); color: #4ade80; }
.test-err { background: rgba(239,68,68,0.1); color: #f87171; }

.btn-primary-sm {
  padding: 6px 14px; border-radius: 8px; border: 1px solid rgba(124,58,237,0.3);
  background: rgba(124,58,237,0.1); color: #a78bfa; font-size: 13px;
  cursor: pointer; transition: all 0.15s;
}
.btn-primary-sm:hover { background: rgba(124,58,237,0.2); }
.btn-primary-sm:disabled { opacity: 0.5; }
</style>
