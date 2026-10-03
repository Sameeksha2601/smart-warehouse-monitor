import streamlit as st
import mysql.connector
import pandas as pd

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------

st.set_page_config(
    page_title="Smart Warehouse Analytics",
    page_icon="📦",
    layout="wide"
)

st.title("📦 Smart Warehouse Analytics")
st.caption("Product and operational analytics from warehouse telemetry")

# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

password = st.sidebar.text_input(
    "MySQL Password",
    type="password"
)

if not password:
    st.info("Enter your MySQL password in the sidebar to load the dashboard.")
    st.stop()

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password=password,
        database="smart_warehouse"
    )

    query = """
    SELECT *
    FROM warehouse_telemetry
    ORDER BY timestamp;
    """

    df = pd.read_sql(query, conn)
    conn.close()

except Exception as e:
    st.error(f"Database connection failed: {e}")
    st.stop()

# --------------------------------------------------
# DATA PREPARATION
# --------------------------------------------------

df["timestamp"] = pd.to_datetime(df["timestamp"])

df["alert"] = df["alert"].astype(bool)
df["item_present"] = df["item_present"].astype(bool)

total_readings = len(df)
total_alerts = int(df["alert"].sum())

alert_rate = (
    total_alerts / total_readings * 100
    if total_readings > 0
    else 0
)

empty_events = int(
    ((df["item_present"] == False)).sum()
)

high_temp_events = int(
    ((df["temperature"] > 30)).sum()
)

avg_temperature = df["temperature"].mean()

# --------------------------------------------------
# KPI SECTION
# --------------------------------------------------

st.subheader("Warehouse KPIs")

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric(
    "Total Readings",
    total_readings
)

col2.metric(
    "Total Alerts",
    total_alerts
)

col3.metric(
    "Alert Rate",
    f"{alert_rate:.2f}%"
)

col4.metric(
    "Empty Shelf Events",
    empty_events
)

col5.metric(
    "Avg Temperature",
    f"{avg_temperature:.2f} °C"
)

st.divider()

# --------------------------------------------------
# SHELF PERFORMANCE
# --------------------------------------------------

st.subheader("Shelf Performance")

shelf_summary = (
    df.groupby("device_id")
    .agg(
        readings=("id", "count"),
        alerts=("alert", "sum"),
        avg_temperature=("temperature", "mean"),
        avg_humidity=("humidity", "mean"),
        empty_events=("item_present", lambda x: (~x).sum())
    )
    .reset_index()
)

shelf_summary["alert_rate"] = (
    shelf_summary["alerts"]
    / shelf_summary["readings"]
    * 100
)

shelf_summary = shelf_summary.sort_values(
    "alert_rate",
    ascending=False
)

display_summary = shelf_summary.copy()

display_summary["alert_rate"] = (
    display_summary["alert_rate"].map(
        lambda x: f"{x:.2f}%"
    )
)

display_summary["avg_temperature"] = (
    display_summary["avg_temperature"].map(
        lambda x: f"{x:.2f} °C"
    )
)

display_summary["avg_humidity"] = (
    display_summary["avg_humidity"].map(
        lambda x: f"{x:.2f}%"
    )
)

display_summary.columns = [
    "Shelf",
    "Readings",
    "Alerts",
    "Avg Temperature",
    "Avg Humidity",
    "Empty Events",
    "Alert Rate"
]

st.dataframe(
    display_summary,
    use_container_width=True,
    hide_index=True
)

# --------------------------------------------------
# CHARTS
# --------------------------------------------------

col1, col2 = st.columns(2)

with col1:

    st.subheader("Alert Rate by Shelf")

    chart_alert = shelf_summary.set_index(
        "device_id"
    )[["alert_rate"]]

    st.bar_chart(chart_alert)

with col2:

    st.subheader("Average Temperature by Shelf")

    chart_temp = shelf_summary.set_index(
        "device_id"
    )[["avg_temperature"]]

    st.bar_chart(chart_temp)

# --------------------------------------------------
# TIME TREND
# --------------------------------------------------

st.subheader("Telemetry Trend")

trend = (
    df.groupby("timestamp")
    .agg(
        temperature=("temperature", "mean"),
        humidity=("humidity", "mean"),
        alerts=("alert", "sum")
    )
)

st.line_chart(
    trend[["temperature", "humidity"]]
)

# --------------------------------------------------
# ALERT ANALYSIS
# --------------------------------------------------

st.subheader("Alert Analysis")

col1, col2 = st.columns(2)

with col1:

    st.write("Alert Reasons")

    reason_summary = (
        df[df["alert"] == True]
        .groupby("alert_reason")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

    st.dataframe(
        reason_summary,
        use_container_width=True,
        hide_index=True
    )

with col2:

    st.write("Alert Distribution")

    alert_distribution = (
        df[df["alert"] == True]
        .groupby("device_id")
        .size()
        .reset_index(name="alerts")
        .set_index("device_id")
    )

    st.bar_chart(alert_distribution)

# --------------------------------------------------
# PRODUCT INSIGHTS
# --------------------------------------------------

st.subheader("💡 Product Insights")

problem_shelves = shelf_summary[
    shelf_summary["alerts"] > 0
]

empty_shelves = shelf_summary[
    shelf_summary["empty_events"] > 0
]

hot_shelves = shelf_summary[
    shelf_summary["avg_temperature"] > 28
]

if len(problem_shelves) > 0:

    st.write(
        f"• **{len(problem_shelves)} shelf(s)** generated alerts: "
        + ", ".join(problem_shelves["device_id"])
    )

else:

    st.write("• No shelves generated alerts.")

if len(empty_shelves) > 0:

    st.write(
        "• Empty-shelf events occurred on: "
        + ", ".join(empty_shelves["device_id"])
    )

if len(hot_shelves) > 0:

    st.write(
        "• Higher average temperatures were observed on: "
        + ", ".join(hot_shelves["device_id"])
    )

# --------------------------------------------------
# RECOMMENDATIONS
# --------------------------------------------------

st.subheader("🎯 Recommended Actions")

if len(empty_shelves) > 0:

    st.write(
        "🔹 Consider replenishment checks for shelves "
        "with repeated empty-shelf events."
    )

if len(hot_shelves) > 0:

    st.write(
        "🔹 Investigate environmental conditions around "
        "shelves with elevated average temperature."
    )

if len(problem_shelves) > 0:

    st.write(
        "🔹 Prioritize monitoring of shelves with repeated alerts."
    )

# --------------------------------------------------
# RAW DATA
# --------------------------------------------------

with st.expander("View Raw Telemetry"):

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )