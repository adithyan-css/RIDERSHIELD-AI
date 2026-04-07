import { MapContainer, TileLayer, Marker, Popup, CircleMarker } from 'react-leaflet'
import L from 'leaflet'
import { useOpsStore } from '../store.js'

// Fix Leaflet default icon
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

const HAZARD_COLORS = { flood: '#3B8BD4', pothole: '#FF6B35', rough: '#FFB347', safe: '#00C8A0' }
const FATIGUE_COLORS = { 1: '#00C8A0', 2: '#FFB347', 3: '#FF6B35', 4: '#ff4d4d' }

export default function FleetMap() {
  const { riders, hazards } = useOpsStore()

  return (
    <div style={{ height: '100%', width: '100%' }}>
      <MapContainer
        center={[11.0168, 76.9558]}
        zoom={13}
        style={{ height: '100%', width: '100%', background: '#0D1526' }}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; CartoDB'
          subdomains="abcd"
        />

        {/* Rider dots */}
        {riders.map((r) => {
          const loc = r.location?.coordinates || r.current_location?.coordinates
          if (!loc) return null
          const [lng, lat] = loc
          const color = FATIGUE_COLORS[r.fatigue_level] || '#00C8A0'
          return (
            <CircleMarker key={r._id} center={[lat, lng]} radius={10}
              pathOptions={{ color, fillColor: color, fillOpacity: 0.9, weight: 2 }}>
              <Popup>
                <div style={{ fontSize: 13 }}>
                  <strong>{r.name}</strong><br />
                  Speed: {r.speed_kmh?.toFixed(1) ?? 0} km/h<br />
                  Fatigue: {['', 'Fresh', 'Moderate', 'Tired', 'Critical'][r.fatigue_level] ?? '?'}<br />
                  Helmet: {r.helmet_connected ? '🟢 Connected' : '🔴 Disconnected'}
                </div>
              </Popup>
            </CircleMarker>
          )
        })}

        {/* Hazard markers */}
        {hazards.map((h, i) => {
          const cls = h.hazard_type || h.hazard_class || 'unknown'
          const coords = h.location?.coordinates || [h.lng, h.lat]
          const [lng, lat] = coords
          if (typeof lat !== 'number' || typeof lng !== 'number') return null
          const color = HAZARD_COLORS[cls] || '#ffffff'
          return (
            <CircleMarker key={i} center={[lat, lng]} radius={6}
              pathOptions={{ color, fillColor: color, fillOpacity: 0.7, weight: 1 }}>
              <Popup>
                <div style={{ fontSize: 13 }}>
                  <strong>{cls}</strong><br />
                  Confidence: {((h.confidence || h.proof_score || 0) * 100).toFixed(0)}%<br />
                  {h.verified ? '✅ Verified' : '⏳ Pending'}
                </div>
              </Popup>
            </CircleMarker>
          )
        })}
      </MapContainer>
    </div>
  )
}
