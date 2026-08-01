<template>
  <n-space vertical size="large">
    <n-card title="配置编辑">
      <template #header-extra>
        <n-space>
          <n-button @click="handleValidate" :loading="validating" quaternary>校验</n-button>
          <n-button @click="loadConfig" :loading="loading" quaternary>重载</n-button>
          <n-button type="primary" @click="handleSave" :loading="saving">保存</n-button>
        </n-space>
      </template>

      <n-tabs type="line">
        <!-- Email -->
        <n-tab-pane name="email" tab="邮箱服务">
          <n-form label-placement="left" :label-width="180">
            <n-form-item label="邮箱服务商">
              <n-select v-model:value="cfg.email_provider" :options="providerOpts" />
            </n-form-item>
            <n-form-item label="默认域名">
              <n-input v-model:value="cfg.defaultDomains" placeholder="example.com" />
            </n-form-item>

            <n-divider>Cloudflare 临时邮箱</n-divider>
            <n-form-item label="API 地址">
              <n-input v-model:value="cfg.cloudflare_api_base" placeholder="https://mail.example.com" />
            </n-form-item>
            <n-form-item label="Auth Mode">
              <n-select v-model:value="cfg.cloudflare_auth_mode" :options="authModeOpts" />
            </n-form-item>
            <n-form-item label="API Key">
              <n-input v-model:value="cfg.cloudflare_api_key" placeholder="留空=匿名" />
            </n-form-item>
            <n-collapse>
              <n-collapse-item title="高级路径配置" name="paths">
                <n-form-item label="Domains 路径">
                  <n-input v-model:value="cfg.cloudflare_path_domains" placeholder="/api/domains" />
                </n-form-item>
                <n-form-item label="Accounts 路径">
                  <n-input v-model:value="cfg.cloudflare_path_accounts" placeholder="/api/new_address" />
                </n-form-item>
                <n-form-item label="Token 路径">
                  <n-input v-model:value="cfg.cloudflare_path_token" placeholder="/api/token" />
                </n-form-item>
                <n-form-item label="Messages 路径">
                  <n-input v-model:value="cfg.cloudflare_path_messages" placeholder="/api/mails" />
                </n-form-item>
              </n-collapse-item>
            </n-collapse>

            <n-divider>DuckMail / mail.tm</n-divider>
            <n-form-item label="API Key">
              <n-input v-model:value="cfg.duckmail_api_key" placeholder="留空=免费" />
            </n-form-item>
            <n-form-item label="API Base">
              <n-input v-model:value="cfg.duckmail_api_base" placeholder="https://api.mail.tm" />
            </n-form-item>

            <n-divider>Cloud Mail</n-divider>
            <n-form-item label="API 地址">
              <n-input v-model:value="cfg.cloudmail_api_base" placeholder="https://mail.example.com" />
            </n-form-item>
            <n-form-item label="Public Token">
              <n-input v-model:value="cfg.cloudmail_public_token" />
            </n-form-item>
            <n-form-item label="域名">
              <n-input v-model:value="cfg.cloudmail_domains" placeholder="逗号分隔" />
            </n-form-item>

            <n-divider>YYDS</n-divider>
            <n-form-item label="API Key">
              <n-input v-model:value="cfg.yyds_api_key" />
            </n-form-item>
            <n-form-item label="JWT">
              <n-input v-model:value="cfg.yyds_jwt" />
            </n-form-item>
          </n-form>
        </n-tab-pane>

        <!-- Registration -->
        <n-tab-pane name="register" tab="注册参数">
          <n-form label-placement="left" :label-width="180">
            <n-form-item label="注册数量">
              <n-input-number v-model:value="cfg.register_count" :min="1" :max="2500" />
            </n-form-item>
            <n-form-item label="代理地址">
              <n-input v-model:value="cfg.proxy" placeholder="http://grok-mihomo:7897" />
            </n-form-item>
            <n-form-item label="开启 NSFW">
              <n-switch v-model:value="cfg.enable_nsfw" />
            </n-form-item>
            <n-form-item label="User Agent">
              <n-input v-model:value="cfg.user_agent" type="textarea" :autosize="{ minRows: 2 }" />
            </n-form-item>
          </n-form>
        </n-tab-pane>

        <!-- Grok2API -->
        <n-tab-pane name="grok2api" tab="Grok2API 入池">
          <n-form label-placement="left" :label-width="180">
            <n-form-item label="自动入池 (远端)">
              <n-switch v-model:value="cfg.grok2api_auto_add_remote" />
            </n-form-item>
            <n-form-item label="自动入池 (本地)">
              <n-switch v-model:value="cfg.grok2api_auto_add_local" />
            </n-form-item>
            <n-form-item label="远端地址">
              <n-input v-model:value="cfg.grok2api_remote_base" placeholder="http://grok2api:8000" />
            </n-form-item>
            <n-form-item label="管理员用户名">
              <n-input v-model:value="cfg.grok2api_remote_admin_username" placeholder="admin" />
            </n-form-item>
            <n-form-item label="管理员密码">
              <n-input v-model:value="cfg.grok2api_remote_admin_password" type="password" show-password-on="click" />
            </n-form-item>
            <n-form-item label="池名称">
              <n-select v-model:value="cfg.grok2api_pool_name" :options="poolOpts" />
            </n-form-item>
            <n-form-item label="本地 Token 文件">
              <n-input v-model:value="cfg.grok2api_local_token_file" placeholder="留空=默认路径" />
            </n-form-item>
            <n-form-item label="旧版 App Key">
              <n-input v-model:value="cfg.grok2api_remote_app_key" placeholder="仅旧版 grok2api 使用" />
            </n-form-item>
            <n-form-item label="允许旧版全量保存">
              <n-switch v-model:value="cfg.grok2api_allow_legacy_full_save" />
              <n-text depth="3" style="margin-left: 12px; font-size: 12px;">⚠️ 危险：多进程并发可能覆盖</n-text>
            </n-form-item>
          </n-form>
        </n-tab-pane>

        <!-- CPA -->
        <n-tab-pane name="cpa" tab="CPA 导出">
          <n-form label-placement="left" :label-width="180">
            <n-form-item label="启用 CPA 导出">
              <n-switch v-model:value="cfg.cpa_export_enabled" />
            </n-form-item>
            <n-form-item label="Base URL">
              <n-input v-model:value="cfg.cpa_base_url" placeholder="https://cli-chat-proxy.grok.com/v1" />
            </n-form-item>
            <n-form-item label="CPA 代理">
              <n-input v-model:value="cfg.cpa_proxy" placeholder="留空=使用全局代理" />
            </n-form-item>
            <n-form-item label="Headless">
              <n-switch v-model:value="cfg.cpa_headless" />
            </n-form-item>
            <n-form-item label="Standalone">
              <n-switch v-model:value="cfg.cpa_force_standalone" />
            </n-form-item>
            <n-form-item label="Cookie 注入">
              <n-switch v-model:value="cfg.cpa_mint_cookie_inject" />
            </n-form-item>
            <n-form-item label="Mint 超时 (秒)">
              <n-input-number v-model:value="cfg.cpa_mint_timeout_sec" :min="30" :max="1800" />
            </n-form-item>
            <n-form-item label="OIDC 请求超时 (秒)">
              <n-input-number v-model:value="cfg.cpa_oidc_request_timeout_sec" :min="3" :max="120" />
            </n-form-item>
            <n-form-item label="OIDC 轮询超时 (秒)">
              <n-input-number v-model:value="cfg.cpa_oidc_poll_timeout_sec" :min="3" :max="120" />
            </n-form-item>
            <n-form-item label="凭证目录">
              <n-input v-model:value="cfg.cpa_auth_dir" placeholder="./cpa_auths" />
            </n-form-item>
            <n-form-item label="热加载到">
              <n-input v-model:value="cfg.cpa_hotload_dir" placeholder="CLIProxyAPI auth-dir" />
            </n-form-item>
            <n-form-item label="自动复制到热加载">
              <n-switch v-model:value="cfg.cpa_copy_to_hotload" />
            </n-form-item>
          </n-form>
        </n-tab-pane>
      </n-tabs>
    </n-card>
  </n-space>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import api from '../api'

const message = useMessage()
const loading = ref(false)
const saving = ref(false)
const validating = ref(false)
const cfg = reactive({})

const providerOpts = [
  { label: 'Cloudflare 临时邮箱', value: 'cloudflare' },
  { label: 'DuckMail / mail.tm', value: 'duckmail' },
  { label: 'YYDS', value: 'yyds' },
  { label: 'Cloud Mail', value: 'cloudmail' },
]
const authModeOpts = [
  { label: '匿名 (none)', value: 'none' },
  { label: 'Bearer', value: 'bearer' },
  { label: 'X-API-Key', value: 'x-api-key' },
  { label: 'X-Admin-Auth', value: 'x-admin-auth' },
  { label: 'Query-Key', value: 'query-key' },
]
const poolOpts = [
  { label: 'ssoBasic', value: 'ssoBasic' },
  { label: 'ssoSuper', value: 'ssoSuper' },
]

async function loadConfig() {
  loading.value = true
  try {
    const res = await api.getConfig()
    Object.keys(cfg).forEach(k => delete cfg[k])
    Object.assign(cfg, res.data)
  } catch {
    message.error('加载配置失败')
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    await api.saveConfig({ ...cfg })
    message.success('配置已保存')
  } catch (e) {
    message.error(e.response?.data?.error || '保存失败')
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
    message.error(e.response?.data?.message || e.response?.data?.error || '校验失败')
  } finally {
    validating.value = false
  }
}

onMounted(loadConfig)
</script>
