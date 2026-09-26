/*
  Smart Warehouse Monitoring - ESP32 Firmware (Adafruit IO version)
  -------------------------------------------------------------------
  Reads a DHT22 (temperature/humidity) and an ultrasonic sensor (item
  presence / shelf distance), then publishes readings to Adafruit IO
  feeds over MQTT. No certificates needed - just username + key.

  Designed to run in the Wokwi simulator (wokwi.com).

  Libraries required (Arduino Library Manager):
    - DHT sensor library (Adafruit)
    - Adafruit MQTT Library

  Wokwi wiring:
    - DHT22 data pin      -> GPIO 15
    - Ultrasonic TRIG pin -> GPIO 5
    - Ultrasonic ECHO pin -> GPIO 18

  Before running: create 4 feeds in Adafruit IO named exactly:
    temperature, humidity, distance, alert
*/

#include <WiFi.h>
#include <DHT.h>
#include "Adafruit_MQTT.h"
#include "Adafruit_MQTT_Client.h"

// ---------- USER CONFIG ----------
const char* WIFI_SSID     = "Wokwi-GUEST";
const char* WIFI_PASSWORD = "";

#define AIO_SERVER      "io.adafruit.com"
#define AIO_SERVERPORT  1883                 // unencrypted MQTT port (fine for a demo)
#define AIO_USERNAME    "Sam2601"            // <-- your Adafruit IO username
#define AIO_KEY         "PASTE_YOUR_KEY_HERE" // <-- your Adafruit IO Active Key
// ----------------------------------

#define DHTPIN 15
#define DHTTYPE DHT22
#define TRIG_PIN 5
#define ECHO_PIN 18

DHT dht(DHTPIN, DHTTYPE);

WiFiClient client;
Adafruit_MQTT_Client mqtt(&client, AIO_SERVER, AIO_SERVERPORT, AIO_USERNAME, AIO_KEY);

// One "feed" object per Adafruit IO feed we publish to
Adafruit_MQTT_Publish tempFeed  = Adafruit_MQTT_Publish(&mqtt, AIO_USERNAME "/feeds/temperature");
Adafruit_MQTT_Publish humFeed   = Adafruit_MQTT_Publish(&mqtt, AIO_USERNAME "/feeds/humidity");
Adafruit_MQTT_Publish distFeed  = Adafruit_MQTT_Publish(&mqtt, AIO_USERNAME "/feeds/distance");
Adafruit_MQTT_Publish alertFeed = Adafruit_MQTT_Publish(&mqtt, AIO_USERNAME "/feeds/alert");

unsigned long lastPublish = 0;
const unsigned long PUBLISH_INTERVAL_MS = 5000;

// Anomaly thresholds - same logic as the AWS Lambda version, just done on-device
const float TEMP_HIGH_THRESHOLD = 30.0;
const float TEMP_LOW_THRESHOLD  = 10.0;
const int   SHELF_THRESHOLD_CM  = 15;

void connectWiFi() {
  Serial.print("Connecting to WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected. IP: " + WiFi.localIP().toString());
}

void connectMQTT() {
  if (mqtt.connected()) return;

  Serial.print("Connecting to Adafruit IO");
  int8_t ret;
  while ((ret = mqtt.connect()) != 0) {
    Serial.println(mqtt.connectErrorString(ret));
    Serial.println("Retrying in 3 seconds...");
    mqtt.disconnect();
    delay(3000);
  }
  Serial.println("Connected to Adafruit IO!");
}

long readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  if (duration == 0) return -1;
  return duration * 0.0343 / 2;
}

void publishTelemetry() {
  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();
  long distance = readDistanceCm();

  if (isnan(temperature) || isnan(humidity)) {
    Serial.println("Failed to read from DHT sensor!");
    return;
  }

  bool itemPresent = (distance > 0 && distance < SHELF_THRESHOLD_CM);

  // Simple threshold-based anomaly detection, done right on the ESP32
  String alertMsg = "OK";
  if (temperature > TEMP_HIGH_THRESHOLD) alertMsg = "Temperature high: " + String(temperature) + "C";
  else if (temperature < TEMP_LOW_THRESHOLD) alertMsg = "Temperature low: " + String(temperature) + "C";
  else if (!itemPresent) alertMsg = "Shelf appears empty";

  Serial.println("---- Publishing ----");
  Serial.println("Temp: " + String(temperature) + "C  Hum: " + String(humidity) +
                  "%  Dist: " + String(distance) + "cm  Alert: " + alertMsg);

  tempFeed.publish(temperature);
  humFeed.publish(humidity);
  distFeed.publish((int32_t)distance);
  alertFeed.publish(alertMsg.c_str());
}

void setup() {
  Serial.begin(115200);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  dht.begin();

  connectWiFi();
  connectMQTT();
}

void loop() {
  connectMQTT();

  if (millis() - lastPublish > PUBLISH_INTERVAL_MS) {
    lastPublish = millis();
    publishTelemetry();
  }

  // Keeps the MQTT connection alive
  mqtt.processPackets(10);
  if (!mqtt.ping()) {
    mqtt.disconnect();
  }
}
