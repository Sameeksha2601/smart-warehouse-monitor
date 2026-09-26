"""
api_lambda.py
--------------
Sits behind an API Gateway HTTP API (GET /telemetry). Returns the most
recent N telemetry records for a device so the dashboard can poll and
render a live chart.

API Gateway setup:
    1. Create an HTTP API in API Gateway.
    2. Add route: GET /telemetry
    3. Integration: this Lambda function.
    4. Enable CORS (Access-Control-Allow-Origin: *) so the dashboard HTML
       file can call it directly from the browser.
"""

import json
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("WarehouseTelemetry")

DEFAULT_DEVICE_ID = "esp32-shelf-01"
DEFAULT_LIMIT = 30


class DecimalEncoder(json.JSONEncoder):
    """DynamoDB returns Decimal objects; convert them to float/int for JSON."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj) if obj % 1 != 0 else int(obj)
        return super().default(obj)


def lambda_handler(event, context):
    params = (event or {}).get("queryStringParameters") or {}
    device_id = params.get("device_id", DEFAULT_DEVICE_ID)
    limit = int(params.get("limit", DEFAULT_LIMIT))

    response = table.query(
        KeyConditionExpression=Key("device_id").eq(device_id),
        ScanIndexForward=False,  # newest first
        Limit=limit,
    )

    items = response.get("Items", [])
    items.sort(key=lambda x: x["timestamp"])  # chronological order for charting

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(items, cls=DecimalEncoder),
    }
