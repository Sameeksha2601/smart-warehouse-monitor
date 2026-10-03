USE smart_warehouse;

-- 1. Overall warehouse KPI
SELECT
    COUNT(*) AS total_readings,
    SUM(alert) AS total_alerts,
    ROUND(100.0 * SUM(alert) / COUNT(*), 2) AS alert_rate_percent,
    SUM(CASE WHEN item_present = FALSE THEN 1 ELSE 0 END) AS empty_shelf_events,
    SUM(CASE WHEN temperature > 30 THEN 1 ELSE 0 END) AS high_temperature_events
FROM warehouse_telemetry;


-- 2. Shelf-level performance
SELECT
    device_id,
    COUNT(*) AS readings,
    SUM(alert) AS alerts,
    ROUND(100.0 * SUM(alert) / COUNT(*), 2) AS alert_rate_percent,
    ROUND(AVG(temperature), 2) AS avg_temperature,
    ROUND(AVG(humidity), 2) AS avg_humidity
FROM warehouse_telemetry
GROUP BY device_id
ORDER BY alert_rate_percent DESC;


-- 3. High-temperature events
SELECT
    device_id,
    timestamp,
    temperature
FROM warehouse_telemetry
WHERE temperature > 30
ORDER BY temperature DESC;


-- 4. Shelves with alerts
SELECT
    device_id,
    COUNT(*) AS total_alerts
FROM warehouse_telemetry
WHERE alert = TRUE
GROUP BY device_id
HAVING COUNT(*) > 0
ORDER BY total_alerts DESC;


-- 5. Rank shelves by alert rate
SELECT
    device_id,
    ROUND(100.0 * SUM(alert) / COUNT(*), 2) AS alert_rate_percent,
    RANK() OVER (
        ORDER BY 100.0 * SUM(alert) / COUNT(*) DESC
    ) AS alert_rank
FROM warehouse_telemetry
GROUP BY device_id;


-- 6. Temperature change using LAG
SELECT
    device_id,
    timestamp,
    temperature,
    LAG(temperature) OVER (
        PARTITION BY device_id
        ORDER BY timestamp
    ) AS previous_temperature,
    ROUND(
        temperature - LAG(temperature) OVER (
            PARTITION BY device_id
            ORDER BY timestamp
        ), 2
    ) AS temperature_change
FROM warehouse_telemetry
ORDER BY device_id, timestamp;


-- 7. Sudden temperature changes
WITH temperature_changes AS (
    SELECT
        device_id,
        timestamp,
        temperature,
        temperature - LAG(temperature) OVER (
            PARTITION BY device_id
            ORDER BY timestamp
        ) AS temperature_change
    FROM warehouse_telemetry
)
SELECT
    device_id,
    timestamp,
    temperature,
    ROUND(temperature_change, 2) AS temperature_change
FROM temperature_changes
WHERE ABS(temperature_change) > 3
ORDER BY ABS(temperature_change) DESC;


-- 8. Final combined product KPI
WITH shelf_metrics AS (
    SELECT
        device_id,
        COUNT(*) AS readings,
        SUM(alert) AS alerts,
        ROUND(100.0 * SUM(alert) / COUNT(*), 2) AS alert_rate_percent,
        ROUND(AVG(temperature), 2) AS avg_temperature,
        ROUND(AVG(humidity), 2) AS avg_humidity
    FROM warehouse_telemetry
    GROUP BY device_id
),
empty_events AS (
    SELECT
        device_id,
        SUM(CASE WHEN item_present = FALSE THEN 1 ELSE 0 END) AS empty_shelf_events
    FROM warehouse_telemetry
    GROUP BY device_id
)
SELECT
    s.device_id,
    s.readings,
    s.alerts,
    s.alert_rate_percent,
    e.empty_shelf_events,
    s.avg_temperature,
    s.avg_humidity
FROM shelf_metrics s
LEFT JOIN empty_events e
    ON s.device_id = e.device_id
ORDER BY s.alert_rate_percent DESC;
