#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
// #include <TensorFlowLite_ESP32.h>  // TFLite Micro — enable when model is embedded

// ── Config ──────────────────────────────────────────────────────────────────
const char* WIFI_SSID     = "YOUR_SSID";
const char* WIFI_PASS     = "YOUR_PASS";
const char* MQTT_HOST     = "192.168.1.100";   // FastAPI server / broker IP
const int   MQTT_PORT     = 1883;
const char* RIDER_ID      = "rider_001";

// ── Pins ─────────────────────────────────────────────────────────────────────
#define PIN_RAIN_SENSOR   34    // YL-83 analog output
#define PIN_TRIG          26    // JSN-SR04T trigger
#define PIN_ECHO          25    // JSN-SR04T echo
#define MPU_ADDR          0x68  // MPU-6050 I2C address

// ── Globals ──────────────────────────────────────────────────────────────────
WiFiClient     espClient;
PubSubClient   mqtt(espClient);
unsigned long  lastPublish = 0;
const int      PUBLISH_INTERVAL_MS = 1000;   // 1Hz publish when hazard detected
const int      SAMPLE_INTERVAL_MS  = 100;    // 10Hz sensor sampling

// Sensor readings
float depth_cm   = 0;
int   rain_raw   = 0;
float accel_rms  = 0;

// ── WiFi ─────────────────────────────────────────────────────────────────────
void connectWifi() {
  Serial.print("Connecting WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi OK: " + WiFi.localIP().toString());
}

// ── MQTT ─────────────────────────────────────────────────────────────────────
void connectMqtt() {
  while (!mqtt.connected()) {
    Serial.print("MQTT connect...");
    if (mqtt.connect(RIDER_ID)) {
      Serial.println("OK");
    } else {
      delay(2000);
    }
  }
}

// ── Sensors ──────────────────────────────────────────────────────────────────
float readDepthCm() {
  digitalWrite(PIN_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  long duration = pulseIn(PIN_ECHO, HIGH, 30000);
  return (duration == 0) ? 999.0f : (duration * 0.0343f / 2.0f);
}

int readRain() {
  return analogRead(PIN_RAIN_SENSOR);   // 0 = wet, 4095 = dry (12-bit ADC)
}

void readMPU(float& ax, float& ay, float& az) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom((uint8_t)MPU_ADDR, (uint8_t)6, (bool)true);
  ax = (Wire.read() << 8 | Wire.read()) / 16384.0f;
  ay = (Wire.read() << 8 | Wire.read()) / 16384.0f;
  az = (Wire.read() << 8 | Wire.read()) / 16384.0f;
}

float computeAccelRms(float ax, float ay, float az) {
  return sqrt(ax * ax + ay * ay + az * az);
}

// ── Hazard Classification (rule-based fallback, swap in TFLite for prod) ─────
const char* classifyHazard() {
  bool wet    = rain_raw < 800;
  bool deep   = depth_cm < 10.0f;
  bool jerk   = accel_rms > 1.5f;
  if (wet && deep) return "flood";
  if (jerk && !wet) return "pothole";
  if (jerk && wet)  return "rough";
  return "safe";
}

// ── MQTT Publish ──────────────────────────────────────────────────────────────
void publishHFV(const char* hazardClass, float confidence) {
  StaticJsonDocument<256> doc;
  doc["rider_id"]    = RIDER_ID;
  doc["lat"]         = 11.0168;    // Replace with GPS module reading
  doc["lng"]         = 76.9558;
  doc["depth_cm"]    = depth_cm;
  doc["rain_raw"]    = rain_raw;
  doc["accel_rms"]   = accel_rms;
  doc["hazard_class"] = hazardClass;
  doc["confidence"]  = confidence;

  char buf[256];
  serializeJson(doc, buf);

  char topic[64];
  snprintf(topic, sizeof(topic), "ridershield/hfv/%s", RIDER_ID);
  mqtt.publish(topic, buf);
  Serial.printf("Published HFV: %s | depth=%.1f rain=%d accel=%.2f\n",
                hazardClass, depth_cm, rain_raw, accel_rms);
}

// ── Setup ─────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  Wire.begin();

  // MPU-6050 wake up
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B);
  Wire.write(0);
  Wire.endTransmission();

  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);

  connectWifi();
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  connectMqtt();

  Serial.println("RiderShield Bike Node Ready ✅");
}

// ── Loop ──────────────────────────────────────────────────────────────────────
void loop() {
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();

  static unsigned long lastSample = 0;
  if (millis() - lastSample >= SAMPLE_INTERVAL_MS) {
    lastSample = millis();
    depth_cm  = readDepthCm();
    rain_raw  = readRain();
    float ax, ay, az;
    readMPU(ax, ay, az);
    accel_rms = computeAccelRms(ax, ay, az);
  }

  const char* hazardClass = classifyHazard();
  if (strcmp(hazardClass, "safe") != 0) {
    if (millis() - lastPublish >= PUBLISH_INTERVAL_MS) {
      lastPublish = millis();
      publishHFV(hazardClass, 0.85f);
    }
  }
}
