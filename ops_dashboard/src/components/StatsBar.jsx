import { useOpsStore } from '../store.js'

const s = {
  wrap: { display: 'flex', gap: 20, alignItems: 'center' },
  stat: { textAlign: 'center' },
  val: { fontSize: 18, fontWeight: 700, color: '#00C8A0', lineHeight: 1 },
  lbl: { fontSize: 10, color: '#ffffff40', marginTop: 2, textTransform: 'uppercase', letterSpacing: 0.4 }
}

export default function StatsBar() {
  const { stats, riders, hazards } = useOpsStore()
  const items = [
    { val: riders.length, lbl: 'Active Riders' },
    { val: stats?.hazards_today ?? hazards.length, lbl: 'Hazards Today' },
    { val: stats?.verified_hazards ?? 0, lbl: 'Verified' },
    { val: stats?.deliveries_completed ?? 0, lbl: 'Deliveries' },
  ]
  return (
    <div style={s.wrap}>
      {items.map(({ val, lbl }) => (
        <div key={lbl} style={s.stat}>
          <div style={s.val}>{val}</div>
          <div style={s.lbl}>{lbl}</div>
        </div>
      ))}
    </div>
  )
}
