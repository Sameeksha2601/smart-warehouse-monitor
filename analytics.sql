USE smart_warehouse;

-- =====================================================
-- 1. OVERALL WAREHOUSE KPI
-- =====================================================

SELECT
    COUNT(*) AS total_readings,
    SUM(alert) AS total_alerts,
    ROUND(SUM(alert) * 100.0 / COUNT(*), 2) AS alert_rate,
    SUM(CASE WHEN item_present = FALSE THEN 1 ELSE 0 END)
        AS empty_shelf_events,
    ROUND(AVG(temperature), 2) AS average_temperature
FROM warehouse_telemetry;


-- =====================================================
-- 2. SHELF-LEVEL PERFORMANCE
-- =====================================================

SELECT
    device_id AS shelf,
    COUNT(*) AS readings,
    SUM(alert) AS alerts,
    ROUND(SUM(alert) * 100.0 / COUNT(*), 2) AS alert_rate,
    ROUND(AVG(temperature), 2) AS avg_temperature,
    ROUND(AVG(humidity), 2) AS avg_humidity,
    SUM(CASE WHEN item_present = FALSE THEN 1 ELSE 0 END)
        AS empty_events
FROM warehouse_telemetry
GROUP BY device_id
ORDER BY alert_rate DESC;


-- =====================================================
-- 3. HIGH-TEMPERATURE EVENTS
-- =====================================================

SELECT
    device_id AS shelf,
    COUNT(*) AS high_temperature_events
FROM warehouse_telemetry
WHERE temperature > 30
GROUP BY device_id
ORDER BY high_temperature_events DESC;


-- =====================================================
-- 4. SHELVES WITH ALERTS ONLY
-- =====================================================

SELECT
    device_id AS shelf,
    COUNT(*) AS alerts
FROM warehouse_telemetry
WHERE alert = TRUE
GROUP BY device_id
HAVING COUNT(*) > 0
ORDER BY alerts DESC;


-- =====================================================
-- 5. RANK SHELVES BY ALERT RATE
-- =====================================================

WITH shelf_metrics AS (
    SELECT
        device_id,
        ROUND(
            SUM(alert) * 100.0 / COUNT(*),
            2
        ) AS alert_rate
    FROM warehouse_telemetry
    GROUP BY device_id
)

SELECT
    device_id AS shelf,
    alert_rate,
    RANK() OVER (
        ORDER BY alert_rate DESC
    ) AS alert_rank
FROM shelf_metrics
ORDER BY alert_rank;


-- =====================================================
-- 6. TEMPERATURE CHANGE USING LAG()
-- =====================================================

SELECT
    device_id AS shelf,
    timestamp,
    temperature,

    LAG(temperature) OVER (
        PARTITION BY device_id
        ORDER BY timestamp
    ) AS previous_temperature,

    ROUND(
        temperature -
        LAG(temperature) OVER (
            PARTITION BY device_id
            ORDER BY timestamp
        ),
        2
    ) AS temperature_change

FROM warehouse_telemetry
ORDER BY device_id, timestamp;


-- =====================================================
-- 7. SUDDEN TEMPERATURE CHANGES
-- =====================================================

WITH temperature_changes AS (

    SELECT
        device_id,
        timestamp,
        temperature,

        temperature -
        LAG(temperature) OVER (
            PARTITION BY device_id
            ORDER BY timestamp
        ) AS temperature_change

    FROM warehouse_telemetry
)

SELECT
    device_id AS shelf,
    timestamp,
    ROUND(temperature_change, 2) AS temperature_change
FROM temperature_changes
WHERE ABS(temperature_change) > 3
ORDER BY ABS(temperature_change) DESC;


-- =====================================================
-- 8. FINAL COMBINED PRODUCT KPI
-- =====================================================

WITH shelf_metrics AS (

    SELECT
        device_id,

        COUNT(*) AS readings,

        SUM(alert) AS alerts,

        ROUND(
            SUM(alert) * 100.0 / COUNT(*),
            2
        ) AS alert_rate,

        SUM(
            CASE
                WHEN item_present = FALSE
                THEN 1
                ELSE 0
            END
        ) AS empty_events,

        ROUND(AVG(temperature), 2)
            AS avg_temperature,

        ROUND(AVG(humidity), 2)
            AS avg_humidity

    FROM warehouse_telemetry

    GROUP BY device_id
),

temperature_changes AS (

    SELECT
        device_id,

        temperature -
        LAG(temperature) OVER (
            PARTITION BY device_id
            ORDER BY timestamp
        ) AS temperature_change

    FROM warehouse_telemetry
),

sudden_events AS (

    SELECT
        device_id,
        SUM(
            CASE
                WHEN ABS(temperature_change) > 3
                THEN 1
                ELSE 0
            END
        ) AS sudden_temperature_events

    FROM temperature_changes

    GROUP BY device_id
)

SELECT
    s.device_id AS shelf,
    s.readings,
    s.alerts,
    s.alert_rate,
    s.empty_events,
    s.avg_temperature,
    s.avg_humidity,
    COALESCE(
        e.sudden_temperature_events,
        0
    ) AS sudden_temperature_events

FROM shelf_metrics s

LEFT JOIN sudden_events e
    ON s.device_id = e.device_id

ORDER BY s.alert_rate DESC;