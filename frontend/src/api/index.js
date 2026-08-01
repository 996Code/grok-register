import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export default {
  // Register
  startRegister: (count) => api.post('/register/start', { count }),
  stopRegister: () => api.post('/register/stop'),
  getStatus: () => api.get('/register/status'),

  // Config
  getConfig: () => api.get('/config'),
  saveConfig: (config) => api.put('/config', config),
  validateConfig: (config) => api.post('/config/validate', config),

  // Accounts
  getAccounts: () => api.get('/accounts'),
  getPending: () => api.get('/pending'),
  retryPending: (file) => api.post('/pending/retry', { file }),
  checkAccount: (idx) => api.post(`/accounts/${idx}/check`),

  // Token Pool
  addTokenToPools: (sso, email) => api.post('/tokens/add', { sso, email }),
  getLocalTokenFile: () => api.get('/tokens/local-file'),

  // Mail
  getMailDomains: () => api.get('/mail/domains'),
  testMail: () => api.post('/mail/test'),

  // CPA
  getCpaCredentials: () => api.get('/cpa/credentials'),
  getCpaFailures: () => api.get('/cpa/failures'),

  // grok2api proxy
  grok2api: {
    login: (username, password) =>
      api.post('/grok2api/auth/login', { username, password }),
    getAccounts: (token) =>
      api.get('/grok2api/accounts', { headers: { Authorization: `Bearer ${token}` } }),
    deleteAccount: (token, id) =>
      api.delete(`/grok2api/accounts/${id}`, { headers: { Authorization: `Bearer ${token}` } }),
    getEgressNodes: (token) =>
      api.get('/grok2api/egress-nodes', { headers: { Authorization: `Bearer ${token}` } }),
    getClientKeys: (token) =>
      api.get('/grok2api/client-keys', { headers: { Authorization: `Bearer ${token}` } }),
    createClientKey: (token, name) =>
      api.post('/grok2api/client-keys', { name, enabled: true }, { headers: { Authorization: `Bearer ${token}` } }),
    deleteClientKey: (token, id) =>
      api.delete(`/grok2api/client-keys/${id}`, { headers: { Authorization: `Bearer ${token}` } }),
    refreshQuota: (token, id) =>
      api.post(`/grok2api/accounts/${id}/refresh-quota`, {}, { headers: { Authorization: `Bearer ${token}` } }),
    acceptTerms: (token, id) =>
      api.post(`/grok2api/accounts/web/${id}/accept-terms`, {}, { headers: { Authorization: `Bearer ${token}` } }),
  },
}
