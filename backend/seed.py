"""
RiderShield seed script — injects realistic test HFVs for demo.
Run: python seed.py
"""
import asyncio
import random
from datetime import datetime, timezone, timedelta
import httpx

BASE_URL = "http://localhost:8000/api"
RIDERS = ["rider_001", "rider_002", "rider_003"]
CENTER_LAT, CENTER_LNG = 11.0168, 76.9558
HAZARD_CLASSES = ["flood", "pothole", "rough", "safe"]

async def seed():
    async with httpx.AsyncClient() as client:
        # Register demo riders
        for i, rid in enumerate(RIDERS):
            try:
                res = await client.post(f"{BASE_URL}/rider/register", json={
                    "name": f"Demo Rider {i+1}",
                    "phone": f"+9198765432{i:02d}",
                    "company_id": "demo_company"
                })
                print(f"Registered {rid}: {res.status_code}")
            except Exception as e:
                print(f"Register failed: {e}")

        # Inject 30 HFVs spread around center
        hfvs_sent = 0
        for _ in range(30):
            rider_id = random.choice(RIDERS)
            hazard_class = random.choices(
                HAZARD_CLASSES, weights=[0.4, 0.3, 0.2, 0.1]
            )[0]
            lat = CENTER_LAT + random.uniform(-0.01, 0.01)
            lng = CENTER_LNG + random.uniform(-0.01, 0.01)
            hfv = {
                "rider_id": rider_id,
                "lat": lat,
                "lng": lng,
                "depth_cm": random.uniform(0, 25) if hazard_class == "flood" else random.uniform(0, 2),
                "rain_raw": random.randint(0, 500) if hazard_class in ["flood", "rough"] else random.randint(700, 1023),
                "accel_rms": random.uniform(1.5, 3.5) if hazard_class != "safe" else random.uniform(0.8, 1.2),
                "hazard_class": hazard_class,
                "confidence": random.uniform(0.7, 0.98),
                "ts": (datetime.now(timezone.utc) - timedelta(minutes=random.randint(0, 60))).isoformat()
            }
            try:
                res = await client.post(f"{BASE_URL}/hfv", json=hfv)
                hfvs_sent += 1
            except Exception as e:
                print(f"HFV error: {e}")

        print(f"\n✅ Seeded {hfvs_sent} HFVs across {len(RIDERS)} riders")
        print("→ Start the Flutter app and ops dashboard to see live data!")

if __name__ == "__main__":
    asyncio.run(seed())
