<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">⚙️ 系统配置</h2>
      <div class="header-actions">
        <button class="btn-primary-sm" @click="handleValidate" :disabled="validating">校验</button>
        <button class="btn-primary-sm" @click="loadConfig" :disabled="loading">重载</button>
        <button class="btn-save" @click="handleSave" :disabled="saving">保存</button>
      </div>
    </div>

    <div v-if="errorMsg" class="error-banner">{{ errorMsg }}</div>

    <div class="tabs-row">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="['tab-btn', { active: activeTab === tab.key }]"
        @click="activeTab = tab.key"
      >{{ tab.label }}</button>
    </div>

    <div class="config-section">
      <!-- Email -->
      <div v-show="activeTab === 'email'" class="form-grid">
        <div class="form-group">
          <label>邮箱服务商</label>
          <select v-model="cfg.email_provider" class="form-input">
            <option value="cloudflare">Cloudflare 临时邮箱</option>
            <option value="duckmail">DuckMail / mail.tm</option>
            <option value="yyds">YYDS</option>
            <option value="cloudmail">Cloud Mail</option>
          </select>
        </div>
        <div class="form-group">
          <label>默认域名</label>
          <input v-model="cfg.defaultDomains" class="form-input" placeholder="example.com" />
        </div>

        <template v-if="cfg.email_provider === 'cloudflare'">
          <div class="form-group full">
            <label>Cloudflare API 地址</label>
            <input v-model="cfg.cloudflare_api_base" class="form-input" placeholder="https://mail.example.com" />
          </div>
          <div class="form-group">
            <label>Auth Mode</label>
            <select v-model="cfg.cloudflare_auth_mode" class="form-input">
              <option value="none">匿名 (none)</option>
              <option value="bearer">Bearer</option>
              <option value="x-api-key">X-API-Key</option>
              <option value="x-admin-auth">X-Admin-Auth</option>
            </select>
          </div>
          <div class="form-group">
            <label>API Key</label>
            <input v-model="cfg.cloudflare_api_key" class="form-input" placeholder="留空=匿名" />
          </div>
        </template>

        <template v-if="cfg.email_provider === 'duckmail'">
          <div class="form-group">
            <label>DuckMail API Key</label>
            <input v-model="cfg.duckmail_api_key" class="form-input" placeholder="留空=免费" />
          </div>
          <div class="form-group">
            <label>DuckMail API Base</label>
            <input v-model="cfg.duckmail_api_base" class="form-input" placeholder="https://api.mail.tm" />
          </div>
        </template>
      </div>

      <!-- Register -->
      <div v-show="activeTab === 'register'" class="form-grid">
        <div class="form-group">
          <label>注册数量</label>
          <input type="number" v-model.number="cfg.register_count" min="1" max="2500" class="form-input" />
        </div>
        <div class="form-group">
          <label>代理地址</label>
          <input v-model="cfg.proxy" class="form-input" placeholder="http://grok-mihomo:7897" />
        </div>
        <div class="form-group">
          <label>开启 NSFW</label>
          <label class="switch">
            <input type="checkbox" v-model="cfg.enable_nsfw" />
            <span class="slider"></span>
          </label>
        </div>
        <div class="form-group full">
          <label>User Agent</label>
          <input v-model="cfg.user_agent" class="form-input" />
        </div>
      </div>

      <!-- Grok2API -->
      <div v-show="activeTab === 'grok2api'" class="form-grid">
        <div class="form-group">
          <label>自动入池 (远端)</label>
          <label class="switch"><input type="checkbox" v-model="cfg.grok2api_auto_add_remote" /><span class="slider"></span></label>
        </div>
        <div class="form-group">
          <label>远端地址</label>
          <input v-model="cfg.grok2api_remote_base" class="form-input" placeholder="http://grok2api:8000" />
        </div>
        <div class="form-group">
          <label>管理员用户名</label>
          <input v-model="cfg.grok2api_remote_admin_username" class="form-input" placeholder="admin" />
        </div>
        <div class="form-group">
          <label>管理员密码</label>
          <input type="password" v-model="cfg.grok2api_remote_admin_password" class="form-input" />
        </div>
        <div class="form-group">
          <label>池名称</label>
          <select v-model="cfg.grok2api_pool_name" class="form-input">
            <option value="ssoBasic">ssoBasic</option>
            <option value="ssoSuper">ssoSuper</option>
          </select>
        </div>
      </div>

      <!-- CPA -->
      <div v-show="activeTab === 'cpa'" class="form-grid">
        <div class="form-group">
          <label>启用 CPA 导出</label>
          <label class="switch"><input type="checkbox" v-model="cfg.cpa_export_enabled" /><span class="slider"></span></label>
        </div>
        <div class="form-group full">
          <label>CPA Base URL</label>
          <input v-model="cfg.cpa_base_url" class="form-input" placeholder="https://cli-chat-proxy.grok.com/v1" />
        </div>
        <div class="form-group">
          <label>CPA 代理</label>
          <input v-model="cfg.cpa_proxy" class="form-input" placeholder="留空=全局" />
        </div>
        <div class="form-group">
          <label>Mint 超时 (秒)</label>
          <input type="number" v-model.number="cfg.cpa_mint_timeout_sec" min="30" max="1800" class="form-input" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import api from '../api'

const message = window.$message
const loading = ref(false)
const saving = ref(false)
const validating = ref(false)
const errorMsg = ref('')
const cfg = reactive({})
const activeTab = ref('email')

const tabs = [
  { key: 'email', label: '📧 邮箱服务' },
  { key: 'register', label: '🎯 注册参数' },
  { key: 'grok2api', label: '🔌 入池配置' },
  { key: 'cpa', label: '📦 CPA 导出' },
]

async function loadConfig() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await api.getConfig()
    Object.keys(cfg).forEach(k => delete cfg[k])
    Object.assign(cfg, res.data)
  } catch (e) {
    errorMsg.value = '加载失败: ' + (e.response?.data?.error || e.message)
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  errorMsg.value = ''
  try {
    await api.saveConfig({ ...cfg })
    message.success('配置已保存')
  } catch (e) {
    errorMsg.value = e.response?.data?.error || '保存失败'
  } finally {
    saving.value = false
  }
}

async function handleValidate() {
  validating.value = true
  try {
    await api.validateConfig({ ...cfg })
    message.success('配置校验通过')
  } catch (e) {
    message.error(e.response?.data?.message || '校验失败')
  } finally {
    validating.value = false
  }
}

onMounted(loadConfig)
</script>

<style scoped>
.page { max-width: 900px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px; }
.page-header { display: flex; align-items: center; justify-content: space-between; }
.page-title { font-size: 20px; font-weight: 700; color: #e2e8f0; }
.header-actions { display: flex; gap: 8px; }

.error-banner {
  padding: 12px 16px; border-radius: 8px;
  background: rgba(239,68,68,0.1); color: #f87171;
  font-size: 13px;
}

.tabs-row { display: flex; gap: 4px; }
.tab-btn {
  padding: 8px 16px; border-radius: 8px 8px 0 0;
  border: 1px solid transparent; background: transparent;
  color: #64748b; font-size: 13px; cursor: pointer;
  transition: all 0.15s;
}
.tab-btn:hover { color: #94a3b8; }
.tab-btn.active {
  background: #1a1a2e; border-color: rgba(255,255,255,0.06);
  color: #a78bfa;
}

.config-section {
  background: #1a1a2e; border: 1px solid rgba(255,255,255,0.06);
  border-radius: 0 14px 14px 14px; padding: 24px;
}
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.form-group { display: flex; flex-direction: column; gap: 6px; }
.form-group.full { grid-column: 1 / -1; }
.form-group label { font-size: 13px; color: #94a3b8; font-weight: 500; }

.form-input {
  padding: 8px 12px; border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.08);
  background: #0f0f1a; color: #e2e8f0; font-size: 13px;
  outline: none; transition: border-color 0.15s;
}
.form-input:focus { border-color: rgba(124,58,237,0.5); }
select.form-input option { background: #1a1a2e; }

.switch { position: relative; display: inline-block; width: 40px; height: 22px; }
.switch input { opacity: 0; width: 0; height: 0; }
.slider {
  position: absolute; cursor: pointer; inset: 0;
  background: #334155; border-radius: 22px; transition: 0.2s;
}
.slider:before {
  content: ""; position: absolute; height: 16px; width: 16px;
  left: 3px; bottom: 3px; background: #e2e8f0; border-radius: 50%; transition: 0.2s;
}
.switch input:checked + .slider { background: #7c3aed; }
.switch input:checked + .slider:before { transform: translateX(18px); }

.btn-primary-sm {
  padding: 6px 14px; border-radius: 8px; border: 1px solid rgba(124,58,237,0.3);
  background: rgba(124,58,237,0.1); color: #a78bfa; font-size: 13px;
  cursor: pointer; transition: all 0.15s;
}
.btn-primary-sm:hover { background: rgba(124,58,237,0.2); }
.btn-primary-sm:disabled { opacity: 0.5; }
.btn-save {
  padding: 6px 16px; border-radius: 8px; border: none;
  background: linear-gradient(135deg, #16a34a, #22c55e); color: white;
  font-size: 13px; font-weight: 600; cursor: pointer;
}
.btn-save:hover { opacity: 0.9; }
.btn-save:disabled { opacity: 0.5; }
</style>
