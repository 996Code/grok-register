import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export default {
  startRegister: (count) => api.post('/register/start', { count }),
  stopRegister: () => api.post('/register/stop'),
  getStatus: () => api.get('/register/status'),

  getConfig: () => api.get('/config'),
  saveConfig: (config) => api.put('/config', config),
  validateConfig: (config) => api.post('/config/validate', config),

  getAccounts: () => api.get('/accounts'),
  getPending: () => api.get('/pending'),
  retryPending: (file) => api.post('/pending/retry', { file }),
  checkAccount: (idx) => api.post(`/accounts/${idx}/check`),

  addTokenToPools: (sso, email) => api.post('/tokens/add', { sso, email }),
  getLocalTokenFile: () => api.get('/tokens/local-file'),

  getMailDomains: () => api.get('/mail/domains'),
  testMail: () => api.post('/mail/test'),

  getCpaCredentials: () => api.get('/cpa/credentials'),
  getCpaFailures: () => api.get('/cpa/failures'),

  // grok2api proxy (auto-login, no token needed from frontend)
  grok2api: {
    getAccounts: () => api.get('/grok2api/accounts'),
    deleteAccount: (id) => api.delete(`/grok2api/accounts/${id}`),
    getEgressNodes: () => api.get('/grok2api/egress-nodes'),
    getClientKeys: () => api.get('/grok2api/client-keys'),
    createClientKey: (name) => api.post('/grok2api/client-keys', { name, enabled: true }),
    deleteClientKey: (id) => api.delete(`/grok2api/client-keys/${id}`),
    refreshQuota: (id) => api.post(`/grok2api/accounts/${id}/refresh-quota`),
  },
}
