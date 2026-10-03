# Smart Warehouse Shelf Monitor

An end-to-end embedded + cloud system that monitors a warehouse shelf for
temperature, humidity, and item presence, flags anomalies, and displays live
data on a web dashboard.

Built as a simulated-hardware project (Wokwi) publishing to Adafruit IO,
chosen for a fast, reliable build under a tight deadline. The system was
originally architected for AWS IoT Core + Lambda + DynamoDB + API Gateway
(see "Production architecture" below) — that design is kept as the intended
path for a real deployment.

## Architecture (as built)

```
 ESP32 (Wokwi simulator)
   - DHT22 temp/humidity sensor
   - Ultrasonic distance sensor (item presence)
        |
        |  MQTT
        v
 Adafruit IO
   - feeds: temperature, humidity, distance, alert
   - dashboard: live gauges + alert text block
```

On-device logic (in `esp32_adafruit_sketch.ino`) reads both sensors every 5
seconds, runs a simple threshold-based anomaly check, and publishes all four
values as separate MQTT messages to Adafruit IO feeds. Adafruit IO's built-in
dashboard renders these live with zero additional backend code.

## Files

| File | Purpose |
|---|---|
| `esp32_adafruit_sketch.ino` | Firmware for the ESP32 (runs in Wokwi). Reads sensors, runs anomaly detection, publishes to Adafruit IO over MQTT. |
| `esp32_sketch.ino` | Original AWS IoT Core version (certificate-based MQTT/TLS). Kept for reference — see "Production architecture" below. |
| `ingest_lambda.py` | AWS Lambda: parses incoming telemetry, runs anomaly detection, writes to DynamoDB. Part of the production design, not used in this build. |
| `api_lambda.py` | AWS Lambda behind API Gateway: serves recent telemetry to a dashboard. Part of the production design, not used in this build. |
| `dashboard.html` | Custom live dashboard (Chart.js) built for the AWS/API Gateway version. Not used in this build — Adafruit IO's dashboard replaces it. |

## Setup (Adafruit IO version — what was actually run)

1. Create a free account at [io.adafruit.com](https://io.adafruit.com).
2. Under **Feeds**, create four feeds named exactly: `temperature`, `humidity`, `distance`, `alert`.
3. Under **Dashboards**, create a dashboard and add a Gauge block for each of `temperature`, `humidity`, `distance`, plus a Text block for `alert`.
4. Open [wokwi.com](https://wokwi.com), create an ESP32 project, and wire a DHT22 (data → GPIO 15) and an HC-SR04 ultrasonic sensor (TRIG → GPIO 5, ECHO → GPIO 18).
5. Paste in `esp32_adafruit_sketch.ino`, add the **DHT sensor library** and **Adafruit MQTT Library** via the Library Manager, and set `AIO_USERNAME` and `AIO_KEY` to your own Adafruit IO credentials.
6. Run the simulation and watch both the Serial Monitor and the Adafruit IO dashboard update live.

**Security note:** the Adafruit IO Active Key is a secret credential. It has been removed from the committed code (`PASTE_YOUR_KEY_HERE` placeholder) — do not commit real keys to a public repository.

## Anomaly detection

Kept intentionally simple and explainable rather than ML-based, given the
project timeline: a temperature outside a configured safe range, or an empty
shelf (distance sensor reading above threshold), sets an `alert` message
that's published as its own feed. This was a deliberate trade-off — the
architecture would support swapping in a real model (e.g., a rolling
z-score or a small trained classifier) without changing how sensors publish
data.

## Production architecture (intended design, not run tonight)

The original design targets a full AWS pipeline, useful to discuss as the
"real" production path:

```
 ESP32 --(MQTT/TLS)--> AWS IoT Core --(IoT Rule)--> ingest_lambda.py --> DynamoDB
                                                                              ^
                                                                              |
                                             api_lambda.py <-- API Gateway --+
                                                    ^
                                                    |
                                             dashboard.html (custom live dashboard)
```

This was substituted with Adafruit IO under time pressure because it removes
certificate management and requires no AWS account setup, letting the whole
pipeline be finished and demoed the same night. The AWS Lambda functions and
custom dashboard were written first and are included in this repo as the
intended production implementation.

## Analytics & Product Insights

The telemetry data is analyzed using MySQL and Python/Pandas to generate
operational and product-level insights.

### SQL Analytics
- Overall warehouse alert rate
- Shelf-level performance
- High-temperature event detection
- Empty-shelf event analysis
- Alert-rate ranking using `RANK()`
- Temperature-change analysis using `LAG()`
- Sudden anomaly detection
- Combined shelf KPI analysis using CTEs

### Python Analytics
Python/Pandas is used to:
- Calculate warehouse KPIs
- Analyze shelf-level performance
- Identify repeated alerts
- Detect empty-shelf events
- Generate automated product insights
- Suggest operational actions from telemetry patterns

### Streamlit Dashboard

The project includes an interactive Streamlit dashboard displaying:

- Total telemetry readings
- Total alerts
- Overall alert rate
- Empty-shelf events
- Average temperature
- Shelf-level performance
- Alert-rate comparison
- Temperature trends
- Alert-reason distribution
- Product insights
- Recommended actions
- Raw telemetry data

