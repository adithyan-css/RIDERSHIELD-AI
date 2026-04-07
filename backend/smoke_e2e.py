import json
import time
import uuid

import httpx
import paho.mqtt.client as mqtt

BASE_URL = "http://127.0.0.1:8000"
API_BASE = f"{BASE_URL}/api"


def post_json(client: httpx.Client, path: str, payload: dict):
    response = client.post(f"{API_BASE}{path}", json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def main() -> int:
    run_id = uuid.uuid4().hex[:8]
    rider_a = f"smoke_rider_a_{run_id}"
    rider_b = f"smoke_rider_b_{run_id}"
    rider_c = f"smoke_rider_c_{run_id}"
    rider_mqtt = f"smoke_rider_mqtt_{run_id}"
    lat = 11.0168
    lng = 76.9558

    with httpx.Client() as client:
        health = client.get(f"{BASE_URL}/health", timeout=10)
        health.raise_for_status()
        print("health:", health.json())

        reg_a = post_json(client, "/rider/register", {
            "rider_id": rider_a,
            "name": "Smoke Rider A",
            "phone": f"+91000{run_id}1",
            "company_id": "smoke_company",
            "password": "smoke",
        })
        reg_b = post_json(client, "/rider/register", {
            "rider_id": rider_b,
            "name": "Smoke Rider B",
            "phone": f"+91000{run_id}2",
            "company_id": "smoke_company",
            "password": "smoke",
        })
        reg_c = post_json(client, "/rider/register", {
            "rider_id": rider_c,
            "name": "Smoke Rider C",
            "phone": f"+91000{run_id}3",
            "company_id": "smoke_company",
            "password": "smoke",
        })
        print("register:", reg_a["rider_id"], reg_b["rider_id"], reg_c["rider_id"])

        post_json(client, "/rider/location", {"rider_id": rider_a, "lat": lat, "lng": lng})
        post_json(client, "/rider/location", {"rider_id": rider_b, "lat": lat + 0.00015, "lng": lng + 0.00015})
        post_json(client, "/rider/location", {"rider_id": rider_c, "lat": lat + 0.00020, "lng": lng + 0.00005})
        print("location updates: ok")

        h1 = post_json(client, "/hfv", {
            "rider_id": rider_a,
            "lat": lat,
            "lng": lng,
            "hazard_type": "flood",
            "confidence": 0.93,
            "depth_cm": 12,
            "rain_raw": 480,
        })
        h2 = post_json(client, "/hfv", {
            "rider_id": rider_b,
            "lat": lat + 0.0001,
            "lng": lng + 0.0001,
            "hazard_type": "flood",
            "confidence": 0.91,
            "depth_cm": 13,
            "rain_raw": 500,
        })
        h3 = post_json(client, "/hfv", {
            "rider_id": rider_c,
            "lat": lat + 0.0002,
            "lng": lng + 0.00005,
            "hazard_type": "flood",
            "confidence": 0.95,
            "depth_cm": 14,
            "rain_raw": 520,
            "accel_rms": 2.8,
        })
        print("hfv api:", h1["id"], h2["id"], h3["id"])

        batch = client.post(
            f"{API_BASE}/hfv/batch",
            json=[
                {
                    "rider_id": rider_a,
                    "lat": lat + 0.0002,
                    "lng": lng + 0.0002,
                    "hazard_type": "flood",
                    "confidence": 0.89,
                },
                {
                    "rider_id": rider_c,
                    "lat": lat + 0.00025,
                    "lng": lng + 0.00025,
                    "hazard_type": "flood",
                    "confidence": 0.88,
                },
            ],
            timeout=20,
        )
        batch.raise_for_status()
        print("hfv batch processed:", batch.json().get("processed"))

    mqtt_payload = {
        "rider_id": rider_mqtt,
        "lat": lat + 0.0003,
        "lng": lng + 0.0003,
        "hazard_type": "flood",
        "confidence": 0.87,
        "depth_cm": 11,
    }

    published = {"ok": False}

    def on_connect(client, userdata, flags, reason_code, properties=None):
        client.publish("ridershield/hfv/test", json.dumps(mqtt_payload), qos=0)
        published["ok"] = True

    mc = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    mc.on_connect = on_connect
    mc.connect("localhost", 1883, 60)
    mc.loop_start()
    time.sleep(1)
    mc.loop_stop()
    mc.disconnect()
    print("mqtt publish:", published["ok"])

    verified = []
    for _ in range(20):
        with httpx.Client() as client:
            response = client.get(
                f"{API_BASE}/hazards/verified",
                params={"lat": lat, "lng": lng, "radius_m": 1000, "limit": 20},
                timeout=10,
            )
            response.raise_for_status()
            verified = response.json()
            flood_verified = [x for x in verified if x.get("hazard_type") == "flood" and x.get("verified")]
            if len(flood_verified) >= 1:
                print("verified hazards:", len(flood_verified))
                break
        time.sleep(1)

    if not verified:
        print("verified hazards query returned empty")

    surface = None
    for _ in range(45):
        try:
            with httpx.Client() as client:
                response = client.get(
                    f"{API_BASE}/hazards/surface",
                    params={"lat": lat, "lng": lng},
                    timeout=10,
                )
                response.raise_for_status()
                payload = response.json()
                features = payload.get("geojson", {}).get("features", [])
                if features:
                    surface = payload
                    print("gp surface features:", len(features), "source:", payload.get("source"))
                    break
        except httpx.TimeoutException:
            pass
        time.sleep(1)

    if not published["ok"]:
        print("FAIL: MQTT publish path failed")
        return 1

    if surface is None:
        print("FAIL: GP surface was not generated in time")
        return 1

    print("PASS: end-to-end smoke succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
