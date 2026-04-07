import { useOpsStore } from '../store.js'

const FATIGUE_LABELS = ['', 'Fresh', 'Moderate', 'Tired', 'Critical']
const FATIGUE_COLORS = ['', '#00C8A0', '#FFB347', '#FF6B35', '#ff4d4d']

const s = {
  wrap: { padding: 20, overflowY: 'auto', height: '100%' },
  title: { fontSize: 16, fontWeight: 600, color: '#fff', marginBottom: 16 },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 12 },
  card: { background: '#0D1526', border: '1px solid #ffffff10', borderRadius: 14, padding: 16 },
  name: { fontSize: 14, fontWeight: 600, color: '#fff', marginBottom: 4 },
  sub: { fontSize: 12, color: '#ffffff50', marginBottom: 12 },
  gauge: (n) => ({ display: 'flex', gap: 4, marginBottom: 8, alignItems: 'center' }),
  bar: (filled, color) => ({
    flex: 1, height: 8, borderRadius: 4,
    background: filled ? color : '#ffffff15',
    boxShadow: filled ? `0 0 6px ${color}80` : 'none',
    transition: 'all .3s'
  }),
  label: (color) => ({ fontSize: 11, fontWeight: 700, color, minWidth: 52 }),
  row: { display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#ffffff60', marginTop: 4 },
  val: { color: '#fff' },
  badge: (on) => ({
    display: 'inline-block', fontSize: 10, padding: '2px 8px', borderRadius: 99,
    background: on ? '#00C8A015' : '#ff4d4d15',
    color: on ? '#00C8A0' : '#ff4d4d',
    border: `1px solid ${on ? '#00C8A040' : '#ff4d4d40'}`
  })
}

function FatigueGauge({ level }) {
  const color = FATIGUE_COLORS[level] || '#fff'
  return (
    <div style={s.gauge()}>
      {[1, 2, 3, 4].map(i => (
        <div key={i} style={s.bar(i <= level, color)} />
      ))}
      <span style={s.label(color)}>{FATIGUE_LABELS[level] || '?'}</span>
    </div>
  )
}

export default function RiderGrid() {
  const { riders } = useOpsStore()

  return (
    <div style={s.wrap}>
      <div style={s.title}>Active Riders — {riders.length}</div>
      {riders.length === 0 && (
        <p style={{ color: '#ffffff40', fontSize: 14 }}>No active riders. Start the backend and register riders.</p>
      )}
      <div style={s.grid}>
        {riders.map(r => (
          <div key={r._id} style={s.card}>
            <div style={s.name}>{r.name || 'Unknown Rider'}</div>
            <div style={s.sub}>ID: {r._id?.slice(0, 8)}…</div>
            <FatigueGauge level={r.fatigue_level || 1} />
            <div style={s.row}>
              <span>Speed</span>
              <span style={s.val}>{(r.speed_kmh || 0).toFixed(1)} km/h</span>
            </div>
            <div style={s.row}>
              <span>Duration</span>
              <span style={s.val}>{(r.ride_duration_h || 0).toFixed(1)} h</span>
            </div>
            <div style={s.row}>
              <span>Helmet</span>
              <span style={s.badge(r.helmet_connected)}>
                {r.helmet_connected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            <div style={s.row}>
              <span>Battery</span>
              <span style={s.val}>{r.helmet_battery_pct ?? 100}%</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
