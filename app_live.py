import streamlit as st
import paho.mqtt.client as mqtt
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import json
import time
import queue

st.set_page_config(
    page_title="DRDO HAES - Live Defense Telemetry",
    page_icon="🛡️",
    layout="wide"
)

# Custom White Theme Styling
st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #FFFFFF !important;
        color: #1E293B !important;
    }
    [data-testid="stMetricValue"] { color: #0F172A !important; font-weight: 700 !important; }
    [data-testid="stMetricLabel"] p { color: #475569 !important; font-weight: 600 !important; }
    .status-ok { color: #059669; font-weight: bold; font-size: 1.1rem; }
    .status-warn { color: #D97706; font-weight: bold; font-size: 1.1rem; }
    .status-crit { color: #DC2626; font-weight: bold; font-size: 1.1rem; }
</style>
""", unsafe_allow_html=True)

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "drdo/haes/anshi_project_telemetry"

@st.cache_resource
def get_msg_queue():
    return queue.Queue()

msg_queue = get_msg_queue()

@st.cache_resource
def start_mqtt_client():
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    except AttributeError:
        client = mqtt.Client()

    def on_connect(c, userdata, flags, rc, *args):
        c.subscribe(MQTT_TOPIC)

    def on_message(c, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            msg_queue.put(data)
        except Exception:
            pass

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    return client

mqtt_client = start_mqtt_client()

# Session state initialization
if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=[
        "Time", "Battery_Temp", "Heatsink_Temp", "Pressure", "Altitude", "Air_Density"
    ])

if "latest" not in st.session_state:
    st.session_state.latest = {
        "battery_temp_c": 25.0, "heatsink_temp_c": 25.0,
        "pressure_hpa": 1013.25, "altitude_m": 0.0,
        "air_density_kgm3": 1.225, "heater_on": False,
        "low_pressure_alarm": False
    }

# Read incoming frames from the background MQTT queue
while not msg_queue.empty():
    item = msg_queue.get()
    st.session_state.latest = item
    new_row = {
        "Time": datetime.now().strftime("%H:%M:%S"),
        "Battery_Temp": item.get("battery_temp_c", 0.0),
        "Heatsink_Temp": item.get("heatsink_temp_c", 0.0),
        "Pressure": item.get("pressure_hpa", 0.0),
        "Altitude": item.get("altitude_m", 0.0),
        "Air_Density": item.get("air_density_kgm3", 0.0)
    }
    st.session_state.history = pd.concat(
        [st.session_state.history, pd.DataFrame([new_row])], ignore_index=True
    ).tail(30)

data = st.session_state.latest

# Header
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.title("🛡️ High-Altitude Environmental Shield (HAES)")
    st.caption("DRDO Indigenous Drone Payload Telemetry | Live Microclimate Monitoring")
with col_h2:
    st.markdown("### `SYSTEM STATUS`")
    if data.get("low_pressure_alarm"):
        st.markdown("<p class='status-crit'>🔴 LOW PRESSURE ALARM (&lt;550 hPa)</p>", unsafe_allow_html=True)
    elif data.get("heater_on"):
        st.markdown("<p class='status-warn'>🟡 ACTIVE HEATING (&lt;5°C)</p>", unsafe_allow_html=True)
    else:
        st.markdown("<p class='status-ok'>🟢 NOMINAL OPERATION</p>", unsafe_allow_html=True)

st.divider()

# Metric Cards
m1, m2, m3, m4, m5 = st.columns(5)
b_temp = data["battery_temp_c"]
m1.metric("🌡️ Battery Temp", f"{b_temp:.1f} °C", "Heater Active" if data.get("heater_on") else "Nominal")
m2.metric("❄️ Heatsink Temp", f"{data['heatsink_temp_c']:.1f} °C")
m3.metric("📉 Chamber Pressure", f"{data['pressure_hpa']:.1f} hPa", "ALARM" if data.get("low_pressure_alarm") else "Nominal")
m4.metric("🏔️ Altitude", f"{data['altitude_m']:.0f} m")
m5.metric("💨 Air Density (ρ)", f"{data['air_density_kgm3']:.3f} kg/m³")

# Live Plotly Charts
st.divider()
df = st.session_state.history
c1, c2 = st.columns(2)

with c1:
    st.subheader("📊 Thermal Microclimate (Battery vs Heatsink)")
    fig_temp = go.Figure()
    if not df.empty:
        fig_temp.add_trace(go.Scatter(x=df["Time"], y=df["Battery_Temp"], name="Battery (°C)", line=dict(color="#DC2626", width=2.5)))
        fig_temp.add_trace(go.Scatter(x=df["Time"], y=df["Heatsink_Temp"], name="Heatsink (°C)", line=dict(color="#2563EB", width=2)))
        fig_temp.add_hline(y=5.0, line_dash="dash", line_color="#D97706", annotation_text="Heater Trigger (5°C)")
        fig_temp.add_hline(y=12.0, line_dash="dot", line_color="#059669", annotation_text="Heater Cutoff (12°C)")
    fig_temp.update_layout(template="plotly_white", height=320, margin=dict(l=20, r=20, t=30, b=20), yaxis_title="Temp (°C)")
    st.plotly_chart(fig_temp, use_container_width=True)

with c2:
    st.subheader("🏔️ Barometric Pressure vs Air Density")
    fig_baro = go.Figure()
    if not df.empty:
        fig_baro.add_trace(go.Scatter(x=df["Time"], y=df["Pressure"], name="Pressure (hPa)", line=dict(color="#0891B2", width=2.5)))
        fig_baro.add_trace(go.Scatter(x=df["Time"], y=df["Air_Density"], name="Density (kg/m³)", line=dict(color="#DB2777", width=2), yaxis="y2"))
        fig_baro.add_hline(y=550.0, line_dash="dash", line_color="#DC2626", annotation_text="Limit (550 hPa)")
    fig_baro.update_layout(template="plotly_white", height=320, margin=dict(l=20, r=20, t=30, b=20), yaxis=dict(title="Pressure (hPa)"), yaxis2=dict(title="Density (kg/m³)", overlaying="y", side="right"))
    st.plotly_chart(fig_baro, use_container_width=True)

time.sleep(1.0)
st.rerun()