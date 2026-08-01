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

  // Accounts
  getAccounts: () => api.get('/accounts'),
  getPending: () => api.get('/pending'),
  retryPending: (file) => api.post('/pending/retry', { file }),

  // grok2api proxy
  grok2api: {
    login: (username, password) =>
      api.post('/grok2api/auth/login', { username, password }),
    getAccounts: (token) =>
      api.get('/grok2api/accounts', { headers: { Authorization: `Bearer ${token}` } }),
    getEgressNodes: (token) =>
      api.get('/grok2api/egress-nodes', { headers: { Authorization: `Bearer ${token}` } }),
    getClientKeys: (token) =>
      api.get('/grok2api/client-keys', { headers: { Authorization: `Bearer ${token}` } }),
    createClientKey: (token, name) =>
      api.post('/grok2api/client-keys', { name, enabled: true }, { headers: { Authorization: `Bearer ${token}` } }),
    refreshQuota: (token, id) =>
      api.post(`/grok2api/accounts/${id}/refresh-quota`, {}, { headers: { Authorization: `Bearer ${token}` } }),
  },
}
