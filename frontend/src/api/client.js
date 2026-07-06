import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

function getToken(key) {
  return localStorage.getItem(key) || sessionStorage.getItem(key)
}

const client = axios.create({ baseURL: BASE })

client.interceptors.request.use((config) => {
  const token = getToken('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refresh = getToken('refresh_token')
      if (refresh) {
        try {
          const { data } = await axios.post(`${BASE}/auth/refresh/`, { refresh })
          // Write refreshed access token back to whichever storage holds the session
          const store = localStorage.getItem('refresh_token') ? localStorage : sessionStorage
          store.setItem('access_token', data.access)
          original.headers.Authorization = `Bearer ${data.access}`
          return client(original)
        } catch {
          ['access_token', 'refresh_token', 'user'].forEach(k => {
            localStorage.removeItem(k)
            sessionStorage.removeItem(k)
          })
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(error)
  }
)

export default client
