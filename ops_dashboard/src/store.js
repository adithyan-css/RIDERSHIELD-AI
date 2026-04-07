import { create } from 'zustand'

const TOKEN_KEY = 'ops_jwt_token'

const readInitialToken = () => {
  if (typeof window === 'undefined') return null
  return window.localStorage.getItem(TOKEN_KEY)
}

export const useOpsStore = create((set, get) => ({
  riders: [],
  hazards: [],
  alerts: [],
  stats: null,
  wsConnected: false,
  isLoading: false,
  fetchError: null,
  authError: null,
  companyId: 'demo_company',
  token: readInitialToken(),

  setRiders: (riders) => set({ riders }),
  setHazards: (hazards) => set({ hazards }),
  addAlert: (alert) => set((s) => ({ alerts: [alert, ...s.alerts].slice(0, 100) })),
  setStats: (stats) => set({ stats }),
  setWsConnected: (v) => set({ wsConnected: v }),
  setToken: (token) => {
    if (typeof window !== 'undefined') {
      if (token) window.localStorage.setItem(TOKEN_KEY, token)
      else window.localStorage.removeItem(TOKEN_KEY)
    }
    set({ token, authError: null })
  },
  clearToken: () => {
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem(TOKEN_KEY)
    }
    set({ token: null, authError: 'Session expired. Please sign in again.' })
  },

  ws: null,

  connectWs() {
    const { companyId, token } = get()
    const baseDelayMs = 1000
    const maxDelayMs = 30000
    let attempt = 0

    const connect = () => {
      const tokenQuery = token ? `?token=${encodeURIComponent(token)}` : ''
      const wsBase = import.meta.env.VITE_WS_BASE_URL
      if (!wsBase) {
        set({ wsConnected: false, fetchError: 'Missing VITE_WS_BASE_URL configuration.' })
        return
      }
      const base = wsBase.endsWith('/') ? wsBase.slice(0, -1) : wsBase
      const ws = new WebSocket(`${base}/ws/ops/${companyId}${tokenQuery}`)
      set({ ws })

      ws.onopen = () => {
        attempt = 0
        set({ wsConnected: true })
      }
      ws.onclose = () => {
        set({ wsConnected: false })
        const delay = Math.min(baseDelayMs * (2 ** attempt), maxDelayMs)
        attempt += 1
        setTimeout(connect, delay)
      }
      ws.onmessage = (e) => {
        let msg = null
        try {
          msg = JSON.parse(e.data)
        } catch {
          return
        }

        if (!msg || typeof msg !== 'object') return
        if (msg.type === 'fleet') set({ riders: msg.riders || [] })
        if (msg.type === 'new_hazard') {
          const payload = msg.payload || msg
          set((s) => ({ hazards: [payload, ...s.hazards].slice(0, 200) }))
        }
        if (msg.type === 'alert_stream') get().addAlert(msg)
        if (msg.type === 'peer_alert') get().addAlert(msg)
        if (msg.type === 'AI_EVENT') {
          const payload = msg.payload || {}
          const metadata = payload.metadata || {}
          const location = payload.location || {}
          const normalizedAlert = {
            type: 'AI_EVENT',
            event_type: payload.event_type,
            rider_id: payload.rider_id,
            timestamp: payload.timestamp,
            confidence: payload.confidence,
            hazard_type: metadata.hazard_type || payload.event_type,
            message: metadata.message || `${payload.event_type || 'ai_event'} detected`,
            lat: location.lat,
            lng: location.lng,
          }
          get().addAlert(normalizedAlert)

          const hazardTypes = new Set(['hazard', 'hazard_detected', 'road_hazard', 'collision_risk'])
          if (hazardTypes.has(payload.event_type)) {
            const normalizedHazard = {
              hazard_type: metadata.hazard_type || metadata.hazard_class || payload.event_type,
              hazard_class: metadata.hazard_class || metadata.hazard_type || payload.event_type,
              confidence: payload.confidence,
              rider_id: payload.rider_id,
              timestamp: payload.timestamp,
              lat: location.lat,
              lng: location.lng,
              verified: false,
              proof_score: metadata.proof_score || payload.confidence || 0,
              cross_rider_count: metadata.cross_rider_count || 1,
            }
            set((s) => ({ hazards: [normalizedHazard, ...s.hazards].slice(0, 200) }))
          }
        }
      }
    }

    connect()
  },

  async fetchInitial() {
    const { companyId } = get()
    const authFetch = async (url) => {
      const { token } = get()
      const response = await fetch(url, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      })
      if (response.status === 401) {
        get().clearToken()
        throw new Error('Unauthorized')
      }
      if (!response.ok) {
        throw new Error(`Request failed ${response.status}`)
      }
      return response.json()
    }

    set({ isLoading: true, fetchError: null })
    try {
      const [fleet, alerts, stats, hazards] = await Promise.all([
        authFetch(`/api/ops/fleet?company_id=${companyId}&page=1&limit=200`),
        authFetch(`/api/ops/alerts?company_id=${companyId}&page=1&limit=100`),
        authFetch(`/api/ops/stats?company_id=${companyId}`),
        authFetch(`/api/hazards/verified?lat=11.0168&lng=76.9558&radius_m=5000`),
      ])
      set({ riders: fleet, alerts, stats, hazards, isLoading: false, fetchError: null })
    } catch (e) {
      console.error('fetchInitial error', e)
      set({ isLoading: false, fetchError: 'Failed to load ops data. Retrying is recommended.' })
    }
  }
}))
