/*
  Smart Warehouse Monitoring - ESP32 Firmware
  ---------------------------------------------
  Reads a DHT22 (temperature/humidity) and an ultrasonic sensor (item presence /
  shelf distance), then publishes JSON telemetry to AWS IoT Core over MQTT/TLS.

  Designed to run in the Wokwi simulator (wokwi.com) - no physical hardware needed.

  Libraries required (install via Arduino Library Manager):
    - DHT sensor library (Adafruit)
    - PubSubClient (Nick O'Leary)
    - WiFiClientSecure (bundled with ESP32 board package)

  Wokwi wiring (if using the Wokwi diagram.json):
    - DHT22 data pin      -> GPIO 15
    - Ultrasonic TRIG pin -> GPIO 5
    - Ultrasonic ECHO pin -> GPIO 18
*/

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <DHT.h>

// ---------- USER CONFIG ----------
const char* WIFI_SSID     = "Wokwi-GUEST";   // Wokwi's built-in simulated WiFi
const char* WIFI_PASSWORD = "";

const char* AWS_IOT_ENDPOINT = "YOUR_ENDPOINT.iot.us-east-1.amazonaws.com"; // from AWS IoT Core console
const int   MQTT_PORT        = 8883;
const char* MQTT_TOPIC       = "warehouse/sensor1";
const char* DEVICE_ID        = "esp32-shelf-01";

// Paste your AWS IoT certificates here (device cert, private key, Amazon Root CA 1)
static const char AWS_CERT_CA[]   PROGMEM = R"EOF(
-----BEGIN CERTIFICATE-----
PASTE_AMAZON_ROOT_CA_1_HERE
-----END CERTIFICATE-----
)EOF";

static const char AWS_CERT_CRT[]  PROGMEM = R"EOF(
-----BEGIN CERTIFICATE-----
PASTE_DEVICE_CERTIFICATE_HERE
-----END CERTIFICATE-----
)EOF";

static const char AWS_CERT_PRIVATE[] PROGMEM = R"EOF(
-----BEGIN RSA PRIVATE KEY-----
PASTE_PRIVATE_KEY_HERE
-----END RSA PRIVATE KEY-----
)EOF";
// ----------------------------------

#define DHTPIN 15
#define DHTTYPE DHT22
#define TRIG_PIN 5
#define ECHO_PIN 18

DHT dht(DHTPIN, DHTTYPE);
WiFiClientSecure net;
PubSubClient client(net);

unsigned long lastPublish = 0;
const unsigned long PUBLISH_INTERVAL_MS = 5000;

void connectWiFi() {
  Serial.print("Connecting to WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected. IP: " + WiFi.localIP().toString());
}

void connectAWS() {
  net.setCACert(AWS_CERT_CA);
  net.setCertificate(AWS_CERT_CRT);
  net.setPrivateKey(AWS_CERT_PRIVATE);

  client.setServer(AWS_IOT_ENDPOINT, MQTT_PORT);

  Serial.print("Connecting to AWS IoT Core");
  while (!client.connected()) {
    if (client.connect(DEVICE_ID)) {
      Serial.println("\nConnected to AWS IoT Core!");
    } else {
      Serial.print(".");
      delay(1000);
    }
  }
}

// Returns distance in cm from the ultrasonic sensor
long readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000); // 30ms timeout
  if (duration == 0) return -1; // no echo received
  return duration * 0.0343 / 2; // speed of sound conversion
}

void publishTelemetry() {
  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();
  long distance = readDistanceCm();

  if (isnan(temperature) || isnan(humidity)) {
    Serial.println("Failed to read from DHT sensor!");
    return;
  }

  // Treat "item present" as distance below a shelf-specific threshold (cm)
  const int SHELF_THRESHOLD_CM = 15;
  bool itemPresent = (distance > 0 && distance < SHELF_THRESHOLD_CM);

  String payload = "{";
  payload += "\"device_id\":\"" + String(DEVICE_ID) + "\",";
  payload += "\"temperature\":" + String(temperature, 1) + ",";
  payload += "\"humidity\":" + String(humidity, 1) + ",";
  payload += "\"distance_cm\":" + String(distance) + ",";
  payload += "\"item_present\":" + String(itemPresent ? "true" : "false");
  payload += "}";

  Serial.println("Publishing: " + payload);
  client.publish(MQTT_TOPIC, payload.c_str());
}

void setup() {
  Serial.begin(115200);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  dht.begin();

  connectWiFi();
  connectAWS();
}

void loop() {
  if (!client.connected()) {
    connectAWS();
  }
  client.loop();

  if (millis() - lastPublish > PUBLISH_INTERVAL_MS) {
    lastPublish = millis();
    publishTelemetry();
  }
}
