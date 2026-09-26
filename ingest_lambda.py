"""
ingest_lambda.py
-----------------
Triggered by an AWS IoT Core rule whenever the ESP32 publishes to the
'warehouse/sensor1' MQTT topic. Parses the payload, runs a lightweight
threshold-based anomaly check, and writes the record to DynamoDB.

DynamoDB table schema (create via console or CLI):
    Table name : WarehouseTelemetry
    Partition key : device_id (String)
    Sort key      : timestamp (Number, epoch seconds)

IoT Core rule SQL to attach this Lambda:
    SELECT * FROM 'warehouse/sensor1'
"""

import json
import time
import boto3
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("WarehouseTelemetry")

# --- Anomaly thresholds (tune as needed) ---
TEMP_HIGH_THRESHOLD = 30.0   # degrees C - flag if warehouse gets too warm
TEMP_LOW_THRESHOLD = 10.0    # degrees C - flag if too cold (e.g. cold storage failure)


def detect_anomaly(temperature: float, item_present: bool) -> dict:
    """Simple, explainable threshold-based anomaly detection.

    Returns a dict describing whether an anomaly was found and why, so the
    dashboard can display a human-readable reason rather than just a boolean.
    """
    if temperature > TEMP_HIGH_THRESHOLD:
        return {"alert": True, "reason": f"Temperature high: {temperature}C"}
    if temperature < TEMP_LOW_THRESHOLD:
        return {"alert": True, "reason": f"Temperature low: {temperature}C"}
    if not item_present:
        return {"alert": True, "reason": "Shelf appears empty"}
    return {"alert": False, "reason": None}


def lambda_handler(event, context):
    try:
        device_id = event["device_id"]
        temperature = float(event["temperature"])
        humidity = float(event["humidity"])
        distance_cm = int(event["distance_cm"])
        item_present = bool(event["item_present"])
    except (KeyError, ValueError, TypeError) as e:
        print(f"Malformed payload: {event} ({e})")
        return {"statusCode": 400, "body": "Malformed payload"}

    anomaly = detect_anomaly(temperature, item_present)

    item = {
        "device_id": device_id,
        "timestamp": int(time.time()),
        # DynamoDB requires Decimal instead of float
        "temperature": Decimal(str(temperature)),
        "humidity": Decimal(str(humidity)),
        "distance_cm": distance_cm,
        "item_present": item_present,
        "alert": anomaly["alert"],
        "alert_reason": anomaly["reason"] or "",
    }

    table.put_item(Item=item)
    print(f"Stored telemetry: {json.dumps(item, default=str)}")

    return {"statusCode": 200, "body": "OK"}
