import { useOpsStore } from '../store.js'

const HAZARD_COLORS = { flood: '#3B8BD4', pothole: '#FF6B35', rough: '#FFB347', safe: '#00C8A0' }

const s = {
  wrap: { padding: 20, overflowY: 'auto', height: '100%' },
  title: { fontSize: 16, fontWeight: 600, color: '#fff', marginBottom: 16 },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  th: { textAlign: 'left', padding: '8px 12px', color: '#ffffff50', fontSize: 11, fontWeight: 600, borderBottom: '1px solid #ffffff10', textTransform: 'uppercase', letterSpacing: 0.5 },
  td: { padding: '10px 12px', borderBottom: '1px solid #ffffff08', color: '#ffffffCC', verticalAlign: 'middle' },
  badge: (cls) => ({
    display: 'inline-block', fontSize: 11, padding: '2px 10px', borderRadius: 99,
    background: `${HAZARD_COLORS[cls] || '#fff'}20`,
    color: HAZARD_COLORS[cls] || '#fff',
    border: `1px solid ${HAZARD_COLORS[cls] || '#fff'}50`,
    fontWeight: 600
  }),
  verified: (v) => ({
    display: 'inline-block', fontSize: 11, padding: '2px 10px', borderRadius: 99,
    background: v ? '#00C8A015' : '#FFB34720',
    color: v ? '#00C8A0' : '#FFB347',
    border: `1px solid ${v ? '#00C8A040' : '#FFB34750'}`,
    fontWeight: 600
  }),
  proof: (score) => {
    const pct = Math.round(score * 100)
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ flex: 1, height: 6, background: '#ffffff10', borderRadius: 3, overflow: 'hidden' }}>
          <div style={{ width: `${pct}%`, height: '100%', background: '#00C8A0', borderRadius: 3 }} />
        </div>
        <span style={{ fontSize: 11, color: '#ffffff60', minWidth: 28 }}>{pct}%</span>
      </div>
    )
  }
}

export default function HazardAudit() {
  const { hazards, alerts } = useOpsStore()
  const all = [...hazards].sort((a, b) => new Date(b.ts) - new Date(a.ts))

  return (
    <div style={s.wrap}>
      <div style={s.title}>Hazard Audit Trail — {all.length} events</div>
      {all.length === 0 && (
        <p style={{ color: '#ffffff40', fontSize: 14 }}>No hazards recorded yet.</p>
      )}
      <table style={s.table}>
        <thead>
          <tr>
            {['Type', 'Location', 'Confidence', 'Proof Score', 'Riders', 'Status', 'Time'].map(h => (
              <th key={h} style={s.th}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {all.map((h, i) => (
            <tr key={i} style={{ background: i % 2 === 0 ? '#0D152640' : 'transparent' }}>
              <td style={s.td}>
                <span style={s.badge(h.hazard_class)}>{h.hazard_class}</span>
              </td>
              <td style={s.td}>
                <span style={{ fontFamily: 'monospace', fontSize: 11 }}>
                  {h.lat?.toFixed(4)}, {h.lng?.toFixed(4)}
                </span>
              </td>
              <td style={s.td}>{((h.confidence || 0) * 100).toFixed(0)}%</td>
              <td style={{ ...s.td, minWidth: 120 }}>
                {s.proof(h.proof_score || 0)}
              </td>
              <td style={s.td}>{h.cross_rider_count || 1}</td>
              <td style={s.td}>
                <span style={s.verified(h.verified)}>{h.verified ? '✓ Verified' : '⏳ Pending'}</span>
              </td>
              <td style={{ ...s.td, color: '#ffffff50', fontSize: 11 }}>
                {h.ts ? new Date(h.ts).toLocaleTimeString() : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
