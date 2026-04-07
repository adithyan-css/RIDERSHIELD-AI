import { useEffect, useState } from 'react'

const s = {
  wrap: { padding: 20, overflowY: 'auto', height: '100%' },
  title: { fontSize: 16, fontWeight: 600, color: '#fff', marginBottom: 16 },
  card: { background: '#0D1526', border: '1px solid #ffffff10', borderRadius: 14, padding: 16, marginBottom: 10 },
  row: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 },
  orderId: { fontFamily: 'monospace', fontSize: 12, color: '#ffffff80' },
  status: (s) => ({
    fontSize: 11, padding: '2px 10px', borderRadius: 99, fontWeight: 600,
    background: s === 'delivered' ? '#00C8A015' : s === 'enroute' ? '#FFB34720' : '#ff4d4d20',
    color: s === 'delivered' ? '#00C8A0' : s === 'enroute' ? '#FFB347' : '#ff4d4d',
  }),
  digipin: { fontFamily: 'monospace', fontSize: 13, color: '#00C8A0', fontWeight: 600 },
  meta: { fontSize: 11, color: '#ffffff40', marginTop: 4 }
}

const MOCK_DELIVERIES = [
  { order_id: 'ORD-001', rider: 'Karthik R.', digipin: '5F3-KJ2-9P4Q', status: 'delivered', gps_verified: true, ts: new Date().toISOString() },
  { order_id: 'ORD-002', rider: 'Priya M.', digipin: '4A1-BN8-3LWQ', status: 'enroute', gps_verified: false, ts: new Date().toISOString() },
  { order_id: 'ORD-003', rider: 'Arjun S.', digipin: '7G9-XP5-2MNQ', status: 'assigned', gps_verified: false, ts: new Date().toISOString() },
]

export default function DeliveryFeed() {
  const [deliveries, setDeliveries] = useState(MOCK_DELIVERIES)

  useEffect(() => {
    fetch('/api/ops/fleet?company_id=demo_company')
      .catch(() => null)
  }, [])

  return (
    <div style={s.wrap}>
      <div style={s.title}>Delivery Verification Feed</div>
      {deliveries.map((d, i) => (
        <div key={i} style={s.card}>
          <div style={s.row}>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600, color: '#fff', marginBottom: 2 }}>{d.rider}</div>
              <div style={s.orderId}>{d.order_id}</div>
            </div>
            <span style={s.status(d.status)}>{d.status.toUpperCase()}</span>
          </div>
          <div style={s.row}>
            <div>
              <div style={{ fontSize: 11, color: '#ffffff40', marginBottom: 2 }}>Drop DIGIPIN</div>
              <div style={s.digipin}>{d.digipin}</div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 11, color: '#ffffff40', marginBottom: 2 }}>GPS Match</div>
              <span style={{ fontSize: 13, color: d.gps_verified ? '#00C8A0' : '#FFB347', fontWeight: 600 }}>
                {d.gps_verified ? '✓ Verified' : '⏳ Pending'}
              </span>
            </div>
          </div>
          <div style={s.meta}>{new Date(d.ts).toLocaleString()}</div>
        </div>
      ))}
    </div>
  )
}
