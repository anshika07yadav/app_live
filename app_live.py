import streamlit as st
import paho.mqtt.client as mqtt
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import json
import queue



# Hide the GitHub icon
hide_github_icon = """
<style>
.viewerBadge_container__1QSob,
.styles_viewerBadge__1yVx5,
[data-testid="stToolbar"] a[href*="github.com"] {
    display: none !important;
}
</style>
"""
st.markdown(hide_github_icon, unsafe_allow_html=True)

# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="DRDO HAES - Live Defense Telemetry",
    page_icon="🛡️",
    layout="wide"
)

# ============================================================
# CUSTOM WHITE THEME
# ============================================================

st.markdown("""
<style>

html, body, [data-testid="stAppViewContainer"],
[data-testid="stHeader"] {
    background-color: #FFFFFF !important;
    color: #1E293B !important;
}

[data-testid="stMetricValue"] {
    color: #0F172A !important;
    font-weight: 700 !important;
}

[data-testid="stMetricLabel"] p {
    color: #475569 !important;
    font-weight: 600 !important;
}

.status-ok {
    color: #059669;
    font-weight: bold;
    font-size: 1.1rem;
}

.status-warn {
    color: #D97706;
    font-weight: bold;
    font-size: 1.1rem;
}

.status-crit {
    color: #DC2626;
    font-weight: bold;
    font-size: 1.1rem;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# MQTT CONFIGURATION
# ============================================================

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883

# IMPORTANT:
# ESP32 must publish to THIS SAME topic
MQTT_TOPIC = "drdo/haes/anshi_project_telemetry"


# ============================================================
# MESSAGE QUEUE
# ============================================================

@st.cache_resource
def get_msg_queue():
    return queue.Queue()


msg_queue = get_msg_queue()


# ============================================================
# MQTT CLIENT
# ============================================================

@st.cache_resource
def start_mqtt_client():

    # Create MQTT client
    try:
        # Paho MQTT 2.x
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )
    except (AttributeError, TypeError):

        # Compatibility with older Paho MQTT versions
        client = mqtt.Client()

    # --------------------------------------------------------
    # MQTT CONNECT CALLBACK
    # --------------------------------------------------------

    def on_connect(client, userdata, flags, reason_code, properties=None):

        print("====================================")
        print("MQTT Connected")
        print("Broker:", MQTT_BROKER)
        print("Topic:", MQTT_TOPIC)
        print("====================================")

        try:
            client.subscribe(MQTT_TOPIC)

            print("Successfully subscribed to:")
            print(MQTT_TOPIC)

        except Exception as e:
            print("Subscription error:", e)

    # --------------------------------------------------------
    # MQTT MESSAGE CALLBACK
    # --------------------------------------------------------

    def on_message(client, userdata, msg):

        try:

            # Convert MQTT payload to string
            payload = msg.payload.decode("utf-8")

            print("MQTT Message Received:")
            print(payload)

            # Convert JSON string to Python dictionary
            data = json.loads(payload)

            # Put data into queue
            msg_queue.put(data)

        except json.JSONDecodeError as e:

            print("JSON decoding error:")
            print(e)

        except Exception as e:

            print("MQTT message error:")
            print(e)

    # --------------------------------------------------------
    # MQTT DISCONNECT CALLBACK
    # --------------------------------------------------------

    def on_disconnect(
        client,
        userdata,
        disconnect_flags=None,
        reason_code=None,
        properties=None
    ):

        print("MQTT disconnected.")
        print("Reason:", reason_code)

    # Assign callbacks
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    # --------------------------------------------------------
    # CONNECT TO BROKER
    # --------------------------------------------------------

    try:

        client.connect(
            MQTT_BROKER,
            MQTT_PORT,
            60
        )

        # Start MQTT background loop
        client.loop_start()

        print("MQTT client started successfully.")

    except Exception as e:

        print("MQTT connection failed:")
        print(e)

    return client


mqtt_client = start_mqtt_client()


# ============================================================
# SESSION STATE
# ============================================================

if "history" not in st.session_state:

    st.session_state.history = pd.DataFrame(
        columns=[
            "Time",
            "Battery_Temp",
            "Heatsink_Temp",
            "Pressure",
            "Altitude",
            "Air_Density"
        ]
    )


if "latest" not in st.session_state:

    st.session_state.latest = {

        "battery_temp_c": 25.0,

        "heatsink_temp_c": 25.0,

        "pressure_hpa": 1013.25,

        "altitude_m": 0.0,

        "air_density_kgm3": 1.225,

        "heater_on": False,

        "low_pressure_alarm": False
    }


# ============================================================
# READ MQTT MESSAGES
# ============================================================

while not msg_queue.empty():

    try:

        item = msg_queue.get_nowait()

        # ----------------------------------------------------
        # Update latest telemetry
        # ----------------------------------------------------

        st.session_state.latest = {

            "battery_temp_c":
                item.get(
                    "battery_temp_c",
                    st.session_state.latest["battery_temp_c"]
                ),

            "heatsink_temp_c":
                item.get(
                    "heatsink_temp_c",
                    st.session_state.latest["heatsink_temp_c"]
                ),

            "pressure_hpa":
                item.get(
                    "pressure_hpa",
                    st.session_state.latest["pressure_hpa"]
                ),

            "altitude_m":
                item.get(
                    "altitude_m",
                    st.session_state.latest["altitude_m"]
                ),

            "air_density_kgm3":
                item.get(
                    "air_density_kgm3",
                    st.session_state.latest["air_density_kgm3"]
                ),

            "heater_on":
                item.get(
                    "heater_on",
                    st.session_state.latest["heater_on"]
                ),

            "low_pressure_alarm":
                item.get(
                    "low_pressure_alarm",
                    st.session_state.latest["low_pressure_alarm"]
                )
        }

        # ----------------------------------------------------
        # Add data to history
        # ----------------------------------------------------

        new_row = {

            "Time":
                datetime.now().strftime("%H:%M:%S"),

            "Battery_Temp":
                st.session_state.latest["battery_temp_c"],

            "Heatsink_Temp":
                st.session_state.latest["heatsink_temp_c"],

            "Pressure":
                st.session_state.latest["pressure_hpa"],

            "Altitude":
                st.session_state.latest["altitude_m"],

            "Air_Density":
                st.session_state.latest["air_density_kgm3"]
        }

        st.session_state.history = pd.concat(
            [
                st.session_state.history,
                pd.DataFrame([new_row])
            ],
            ignore_index=True
        )

        # Keep only latest 30 readings
        st.session_state.history = (
            st.session_state.history.tail(30)
        )

    except queue.Empty:
        break

    except Exception as e:
        print("Error processing telemetry:", e)


# ============================================================
# CURRENT DATA
# ============================================================

data = st.session_state.latest


# ============================================================
# HEADER
# ============================================================

col_h1, col_h2 = st.columns([3, 1])


with col_h1:

    st.title(
        "🛡️ High-Altitude Environmental Shield (HAES)"
    )

    st.caption(
        "DRDO Indigenous Drone Payload Telemetry | "
        "Live Microclimate Monitoring"
    )


with col_h2:

    st.markdown("### `SYSTEM STATUS`")

    # Low pressure alarm
    if data.get("low_pressure_alarm", False):

        st.markdown(
            """
            <p class="status-crit">
            🔴 LOW PRESSURE ALARM (&lt;550 hPa)
            </p>
            """,
            unsafe_allow_html=True
        )

    # Heater active
    elif data.get("heater_on", False):

        st.markdown(
            """
            <p class="status-warn">
            🟡 ACTIVE HEATING (&lt;5°C)
            </p>
            """,
            unsafe_allow_html=True
        )

    # Normal
    else:

        st.markdown(
            """
            <p class="status-ok">
            🟢 NOMINAL OPERATION
            </p>
            """,
            unsafe_allow_html=True
        )


st.divider()


# ============================================================
# METRIC CARDS
# ============================================================

m1, m2, m3, m4, m5 = st.columns(5)


# Battery temperature
battery_temp = float(
    data.get("battery_temp_c", 25.0)
)


m1.metric(
    "🌡️ Battery Temp",
    f"{battery_temp:.1f} °C",
    "Heater Active"
    if data.get("heater_on", False)
    else "Nominal"
)


# Heatsink temperature
heatsink_temp = float(
    data.get("heatsink_temp_c", 25.0)
)


m2.metric(
    "❄️ Heatsink Temp",
    f"{heatsink_temp:.1f} °C"
)


# Pressure
pressure = float(
    data.get("pressure_hpa", 1013.25)
)


m3.metric(
    "📉 Chamber Pressure",
    f"{pressure:.1f} hPa",
    "ALARM"
    if data.get("low_pressure_alarm", False)
    else "Nominal"
)


# Altitude
altitude = float(
    data.get("altitude_m", 0.0)
)


m4.metric(
    "🏔️ Altitude",
    f"{altitude:.0f} m"
)


# Air density
air_density = float(
    data.get("air_density_kgm3", 1.225)
)


m5.metric(
    "💨 Air Density (ρ)",
    f"{air_density:.3f} kg/m³"
)


# ============================================================
# CHARTS
# ============================================================

st.divider()

df = st.session_state.history


c1, c2 = st.columns(2)


# ============================================================
# TEMPERATURE CHART
# ============================================================

with c1:

    st.subheader(
        "📊 Thermal Microclimate "
        "(Battery vs Heatsink)"
    )

    fig_temp = go.Figure()

    if not df.empty:

        # Battery temperature
        fig_temp.add_trace(
            go.Scatter(
                x=df["Time"],
                y=df["Battery_Temp"],
                name="Battery (°C)",
                mode="lines+markers",
                line=dict(
                    color="#DC2626",
                    width=2.5
                )
            )
        )

        # Heatsink temperature
        fig_temp.add_trace(
            go.Scatter(
                x=df["Time"],
                y=df["Heatsink_Temp"],
                name="Heatsink (°C)",
                mode="lines+markers",
                line=dict(
                    color="#2563EB",
                    width=2
                )
            )
        )

        # Heater ON threshold
        fig_temp.add_hline(
            y=5.0,
            line_dash="dash",
            line_color="#D97706",
            annotation_text="Heater Trigger (5°C)"
        )

        # Heater OFF threshold
        fig_temp.add_hline(
            y=12.0,
            line_dash="dot",
            line_color="#059669",
            annotation_text="Heater Cutoff (12°C)"
        )

    fig_temp.update_layout(

        template="plotly_white",

        height=320,

        margin=dict(
            l=20,
            r=20,
            t=30,
            b=20
        ),

        yaxis_title="Temperature (°C)",

        xaxis_title="Time",

        hovermode="x unified"
    )

    st.plotly_chart(
        fig_temp,
        use_container_width=True
    )


# ============================================================
# PRESSURE + AIR DENSITY CHART
# ============================================================

with c2:

    st.subheader(
        "🏔️ Barometric Pressure vs Air Density"
    )

    fig_baro = go.Figure()

    if not df.empty:

        # Pressure
        fig_baro.add_trace(
            go.Scatter(
                x=df["Time"],
                y=df["Pressure"],
                name="Pressure (hPa)",
                mode="lines+markers",
                line=dict(
                    color="#0891B2",
                    width=2.5
                )
            )
        )

        # Air density
        fig_baro.add_trace(
            go.Scatter(
                x=df["Time"],
                y=df["Air_Density"],
                name="Density (kg/m³)",
                mode="lines+markers",
                line=dict(
                    color="#DB2777",
                    width=2
                ),
                yaxis="y2"
            )
        )

        # Pressure alarm limit
        fig_baro.add_hline(
            y=550.0,
            line_dash="dash",
            line_color="#DC2626",
            annotation_text="Limit (550 hPa)"
        )

    fig_baro.update_layout(

        template="plotly_white",

        height=320,

        margin=dict(
            l=20,
            r=20,
            t=30,
            b=20
        ),

        yaxis=dict(
            title="Pressure (hPa)"
        ),

        yaxis2=dict(
            title="Air Density (kg/m³)",
            overlaying="y",
            side="right"
        ),

        xaxis_title="Time",

        hovermode="x unified"
    )

    st.plotly_chart(
        fig_baro,
        use_container_width=True
    )


# ============================================================
# TELEMETRY TABLE
# ============================================================

st.divider()

st.subheader("📡 Latest Telemetry Data")

if not df.empty:

    display_df = df.tail(10).copy()

    display_df = display_df.rename(
        columns={
            "Time": "Time",
            "Battery_Temp": "Battery Temp (°C)",
            "Heatsink_Temp": "Heatsink Temp (°C)",
            "Pressure": "Pressure (hPa)",
            "Altitude": "Altitude (m)",
            "Air_Density": "Air Density (kg/m³)"
        }
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

else:

    st.info(
        "Waiting for telemetry data from ESP32..."
    )


# ============================================================
# AUTO REFRESH
# ============================================================

# Streamlit automatically reruns this script every 1 second.
# This replaces time.sleep(1) + st.rerun().

try:

    from streamlit_autorefresh import st_autorefresh

    st_autorefresh(
        interval=1000,
        key="haes_refresh"
    )

except ImportError:

    st.warning(
        "Install streamlit-autorefresh for live updates: "
        "pip install streamlit-autorefresh"
    )
