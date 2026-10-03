import mysql.connector
import pandas as pd
from getpass import getpass

# -----------------------------
# 1. Connect to MySQL
# -----------------------------
password = getpass("Enter MySQL password: ")

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password=password,
    database="smart_warehouse"
)

print("\nConnected to MySQL successfully!")

# -----------------------------
# 2. Get telemetry data
# -----------------------------
query = """
SELECT *
FROM warehouse_telemetry
ORDER BY device_id, timestamp;
"""

cursor = conn.cursor(dictionary=True)
cursor.execute(query)

rows = cursor.fetchall()

# -----------------------------
# 3. Convert to Pandas DataFrame
# -----------------------------
df = pd.DataFrame(rows)

cursor.close()
conn.close()

# -----------------------------
# 4. Display the data
# -----------------------------
print("\nWarehouse Telemetry:")
print(df)

print("\nDataset shape:")
print(df.shape)

print("\nColumns:")
# -----------------------------
# 5. Basic KPI analysis
# -----------------------------

print("\n" + "=" * 50)
print("WAREHOUSE KPI ANALYSIS")
print("=" * 50)

# Total number of readings
total_readings = len(df)

# Total alerts
total_alerts = df["alert"].sum()

# Overall alert rate
alert_rate = (total_alerts / total_readings) * 100

# Empty shelf events
empty_shelf_events = (df["item_present"] == 0).sum()

# High temperature events
high_temperature_events = (df["temperature"] > 30).sum()

# Average temperature
average_temperature = df["temperature"].mean()

# Average humidity
average_humidity = df["humidity"].mean()


print(f"\nTotal readings          : {total_readings}")
print(f"Total alerts            : {total_alerts}")
print(f"Overall alert rate      : {alert_rate:.2f}%")
print(f"Empty shelf events      : {empty_shelf_events}")
print(f"High temperature events : {high_temperature_events}")
print(f"Average temperature    : {average_temperature:.2f} °C")
print(f"Average humidity       : {average_humidity:.2f}%")

# -----------------------------
# 6. Shelf-level KPI analysis
# -----------------------------

print("\n" + "=" * 50)
print("SHELF-LEVEL KPI ANALYSIS")
print("=" * 50)

shelf_analysis = (
    df.groupby("device_id")
      .agg(
          total_readings=("id", "count"),
          total_alerts=("alert", "sum"),
          avg_temperature=("temperature", "mean"),
          avg_humidity=("humidity", "mean"),
          empty_shelf_events=("item_present", lambda x: (x == 0).sum())
      )
      .reset_index()
)

# Calculate alert rate
shelf_analysis["alert_rate_percent"] = (
    shelf_analysis["total_alerts"]
    / shelf_analysis["total_readings"]
    * 100
)

# Round numerical values
shelf_analysis["avg_temperature"] = shelf_analysis["avg_temperature"].round(2)
shelf_analysis["avg_humidity"] = shelf_analysis["avg_humidity"].round(2)
shelf_analysis["alert_rate_percent"] = (
    shelf_analysis["alert_rate_percent"].round(2)
)

# Sort by alert rate
shelf_analysis = shelf_analysis.sort_values(
    by="alert_rate_percent",
    ascending=False
)

print("\nShelf Performance:")
print(shelf_analysis.to_string(index=False))

# -----------------------------
# 7. Automated product insights
# -----------------------------

print("\n" + "=" * 50)
print("PRODUCT INSIGHTS")
print("=" * 50)

# Shelves with alerts
problematic_shelves = shelf_analysis[
    shelf_analysis["alert_rate_percent"] > 0
]

# Shelves with empty-shelf events
empty_shelves = shelf_analysis[
    shelf_analysis["empty_shelf_events"] > 0
]

# Shelves with high average temperature
high_temp_shelves = shelf_analysis[
    shelf_analysis["avg_temperature"] > 28
]

print("\nKey Findings:")

if not problematic_shelves.empty:
    print(
        f"- {len(problematic_shelves)} shelf(s) generated alerts: "
        f"{', '.join(problematic_shelves['device_id'])}"
    )

if not empty_shelves.empty:
    print(
        f"- Empty-shelf events occurred on: "
        f"{', '.join(empty_shelves['device_id'])}"
    )

if not high_temp_shelves.empty:
    print(
        f"- Higher average temperatures were observed on: "
        f"{', '.join(high_temp_shelves['device_id'])}"
    )

print("\nRecommended Actions:")

if not empty_shelves.empty:
    print(
        "- Consider replenishment checks for shelves with repeated "
        "empty-shelf events."
    )

if not high_temp_shelves.empty:
    print(
        "- Investigate environmental conditions around shelves "
        "with elevated average temperature."
    )

if not problematic_shelves.empty:
    print(
        "- Prioritize monitoring of shelves with repeated alerts."
    )