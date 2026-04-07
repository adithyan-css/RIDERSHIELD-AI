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

  connectWs() {
    const { companyId } = get()
    const ws = new WebSocket(`ws://localhost:8000/ws/ops/${companyId}`)
    ws.onopen = () => set({ wsConnected: true })
    ws.onclose = () => {
      set({ wsConnected: false })
      setTimeout(() => get().connectWs(), 5000)
    }
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      if (msg.type === 'fleet') set({ riders: msg.riders })
      if (msg.type === 'new_hazard') set((s) => ({ hazards: [msg, ...s.hazards].slice(0, 200) }))
      if (msg.type === 'alert_stream') get().addAlert(msg)
    }
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
