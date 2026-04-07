import { useEffect, useState } from 'react'
import { useOpsStore } from './store.js'
import FleetMap from './components/FleetMap.jsx'
import RiderGrid from './components/RiderGrid.jsx'
import HazardAudit from './components/HazardAudit.jsx'
import DeliveryFeed from './components/DeliveryFeed.jsx'
import StatsBar from './components/StatsBar.jsx'

const TABS = ['Fleet Map', 'Rider State', 'Hazard Audit', 'Deliveries']

const s = {
  shell: { display: 'flex', flexDirection: 'column', height: '100vh', background: '#0A0F1E' },
  header: { display: 'flex', alignItems: 'center', gap: 16, padding: '10px 20px', background: '#0D1526', borderBottom: '1px solid #ffffff12' },
  logo: { color: '#00C8A0', fontWeight: 700, fontSize: 18, letterSpacing: -0.5, display: 'flex', alignItems: 'center', gap: 8 },
  dot: (on) => ({ width: 8, height: 8, borderRadius: '50%', background: on ? '#00C8A0' : '#ff4d4d', boxShadow: on ? '0 0 6px #00C8A0' : 'none' }),
  tabs: { display: 'flex', gap: 4, padding: '10px 20px', background: '#0D1526', borderBottom: '1px solid #ffffff0a' },
  tab: (a) => ({
    padding: '6px 16px', borderRadius: 8, fontSize: 13, cursor: 'pointer', border: 'none',
    background: a ? '#00C8A020' : 'transparent', color: a ? '#00C8A0' : '#ffffff60',
    fontWeight: a ? 600 : 400, transition: 'all .15s'
  }),
  body: { flex: 1, overflow: 'hidden' }
}

export default function App() {
  const [tab, setTab] = useState(0)
  const { connectWs, fetchInitial, wsConnected } = useOpsStore()

  useEffect(() => {
    fetchInitial()
    connectWs()
  }, [])

  const panels = [<FleetMap />, <RiderGrid />, <HazardAudit />, <DeliveryFeed />]

  return (
    <div style={s.shell}>
      <header style={s.header}>
        <div style={s.logo}>
          <span>🛡️</span> RiderShield Ops
        </div>
        <StatsBar />
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={s.dot(wsConnected)} />
          <span style={{ fontSize: 12, color: wsConnected ? '#00C8A0' : '#ff4d4d' }}>
            {wsConnected ? 'Live' : 'Offline'}
          </span>
        </div>
      </header>

      <nav style={s.tabs}>
        {TABS.map((t, i) => (
          <button key={t} style={s.tab(tab === i)} onClick={() => setTab(i)}>{t}</button>
        ))}
      </nav>

      <div style={s.body}>
        {panels[tab]}
      </div>
    </div>
  )
}
