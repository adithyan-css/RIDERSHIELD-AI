# 🛡️ RiderShield AI — Full Stack Project

> **5-layer smart rider safety system**: ESP32 bike node → Helmet Pi AI → FastAPI backend → Flutter app → React Ops Dashboard

---

## Architecture

```
Edge (ESP32)  ──MQTT──▶  FastAPI Backend  ──WS──▶  Flutter App (Android/iOS)
Helmet (Pi)   ──BLE──▶   │  MongoDB              │  Live flood heatmap
                          │  Redis                │  Peer hazard alerts
                          │  GP Model             │  DIGIPIN delivery
                          └──────────────────▶  Ops Dashboard (React)
```

## Folder Structure

```
ridershield/
├── backend/              # FastAPI server (Python)
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── models/schemas.py
│   │   ├── routers/      # hazards, riders, delivery, ops, websocket
│   │   ├── services/ws_manager.py
│   │   ├── workers/gp_worker.py
│   │   └── mqtt/subscriber.py
│   ├── seed.py           # Demo data injector
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env
├── flutter_app/          # Flutter mobile app
│   ├── lib/
│   │   ├── main.dart
│   │   ├── screens/      # home, ride, delivery, helmet, profile, login
│   │   ├── widgets/      # fatigue_gauge, alert_sheet
│   │   ├── providers/    # rider, hazard, ble
│   │   └── services/     # api, ws, location, tts
│   └── pubspec.yaml
├── ops_dashboard/        # React + Vite ops dashboard
│   └── src/
│       ├── App.jsx
│       ├── store.js      # Zustand
│       └── components/   # FleetMap, RiderGrid, HazardAudit, DeliveryFeed
├── edge/
│   ├── bike_node/        # ESP32 Arduino firmware (.ino)
│   └── helmet_pi/        # Raspberry Pi Python AI
└── docker-compose.yml
```

---

## 🚀 Quick Start

### 1. Backend (Docker)

```bash
cd ridershield
docker compose up --build
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### 2. Seed demo data

```bash
cd backend
pip install httpx
python seed.py
```

### 3. Flutter App

```bash
cd flutter_app
flutter pub get
flutter run          # Android/iOS device or emulator
```

> **Note:** Edit `lib/services/api_service.dart` to set `baseUrl`:
> - Android emulator: `http://10.0.2.2:8000/api`
> - iOS simulator: `http://localhost:8000/api`
> - Real device: `http://YOUR_MACHINE_IP:8000/api`

### 4. Ops Dashboard

```bash
cd ops_dashboard
npm install
npm run dev
# Open http://localhost:5173
```

### 5. ESP32 Firmware

Open `edge/bike_node/bike_node.ino` in Arduino IDE.
Set your WiFi credentials and MQTT broker IP, then flash to ESP32.

### 6. Helmet Pi

```bash
cd edge/helmet_pi
pip install -r requirements.txt
python helmet_main.py
```

---

## Flutter App Screens

| Screen | Description |
|--------|-------------|
| **Map** | Live flood heatmap (flutter_map + CartoDB dark tiles), hazard pins, rider position |
| **Ride** | Speed / depth / rain telemetry, fatigue gauge, real-time peer alert log, TTS voice |
| **Delivery** | DIGIPIN resolver with mini-map, start/verify delivery workflow |
| **Helmet** | BLE scan & connect, camera/voice toggle, battery status |
| **Profile** | Ride history, hazard reports, delivery stats, logout |

---

## API Endpoints (28+)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/hfv` | Ingest hazard feature vector |
| POST | `/api/hfv/batch` | Bulk HFV ingest (BLE offline buffer) |
| GET | `/api/hazards/surface` | GP flood probability GeoJSON |
| GET | `/api/hazards/verified` | Verified hazards near location |
| POST | `/api/rider/register` | Register rider |
| POST | `/api/rider/login` | Login |
| POST | `/api/rider/location` | Update GPS position |
| GET | `/api/rider/{id}/state` | Rider state (fatigue, helmet, speed) |
| GET | `/api/digipin/resolve` | DIGIPIN → GPS |
| GET | `/api/digipin/encode` | GPS → DIGIPIN |
| POST | `/api/delivery/start` | Start delivery |
| PATCH | `/api/delivery/{id}/verify` | Verify delivery |
| GET | `/api/ops/fleet` | All active riders |
| GET | `/api/ops/stats` | Aggregate dashboard stats |
| WS | `/ws/rider/{id}` | Rider real-time channel |
| WS | `/ws/ops/{company_id}` | Ops real-time fleet feed |

---

## Key Dependencies

**Flutter:** `flutter_map`, `web_socket_channel`, `provider`, `geolocator`, `flutter_blue_plus`, `flutter_tts`, `fl_chart`, `shared_preferences`

**Backend:** `fastapi`, `motor`, `redis`, `paho-mqtt`, `scikit-learn`, `pymongo`

**Ops:** `react-leaflet`, `zustand`, `recharts`

---

## Cloudflare Tunnel (for real-device demo)

```bash
cloudflared tunnel --url http://localhost:8000
# Update flutter_app/lib/services/api_service.dart with the tunnel URL
```

---

## Notes

- DIGIPIN resolver uses a stub (returns Coimbatore coords). Replace with the real IIT-India Post API.
- BLE in `BleProvider` is simulated — wire up `flutter_blue_plus` for production.
- TFLite model files (`mobilenet_v2_collision.tflite`) must be trained and placed in `edge/helmet_pi/`.
- JWT auth uses mock tokens — replace with `python-jose` signing in `riders.py` for production.
