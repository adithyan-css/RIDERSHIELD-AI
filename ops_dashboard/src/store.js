import { create } from 'zustand'

export const useOpsStore = create((set, get) => ({
  riders: [],
  hazards: [],
  alerts: [],
  stats: null,
  wsConnected: false,
  companyId: 'demo_company',

  setRiders: (riders) => set({ riders }),
  setHazards: (hazards) => set({ hazards }),
  addAlert: (alert) => set((s) => ({ alerts: [alert, ...s.alerts].slice(0, 100) })),
  setStats: (stats) => set({ stats }),
  setWsConnected: (v) => set({ wsConnected: v }),

  ws: null,

  connectWs() {
    const { companyId } = get()
    const baseDelayMs = 1000
    const maxDelayMs = 30000
    let attempt = 0

    const connect = () => {
      const ws = new WebSocket(`ws://localhost:8000/ws/ops/${companyId}`)
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
        const msg = JSON.parse(e.data)
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
    try {
      const [fleet, alerts, stats, hazards] = await Promise.all([
        fetch(`/api/ops/fleet?company_id=${companyId}`).then(r => r.json()),
        fetch(`/api/ops/alerts?company_id=${companyId}`).then(r => r.json()),
        fetch(`/api/ops/stats?company_id=${companyId}`).then(r => r.json()),
        fetch(`/api/hazards/verified?lat=11.0168&lng=76.9558&radius_m=5000`).then(r => r.json()),
      ])
      set({ riders: fleet, alerts, stats, hazards })
    } catch (e) {
      console.error('fetchInitial error', e)
    }
  }
}))
