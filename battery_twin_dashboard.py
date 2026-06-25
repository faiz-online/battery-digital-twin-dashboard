
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Battery Digital Twin",
    page_icon="🔋",
    layout="wide"
)

# ── CONSTANTS ────────────────────────────────────────────────────────────────
CELLS_IN_SERIES = 96
CAPACITY_AH     = 94.5
CAPACITY_KWH    = 30.2
MAX_CELL_V      = 4.2
MIN_CELL_V      = 3.0
BASE_RANGE_KM   = 250
A_SEI    = 0.0082
B_LINEAR = 0.0055

# ── SIMULATED "LIVE" SNAPSHOT (stand-in for real sensor feed) ────────────────
# In v1, this represents a single point-in-time reading from the Day 1 simulator.
# A fixed seed keeps the cockpit numbers consistent across reruns within a session.
np.random.seed(42)

def get_current_snapshot(cycle_count=320, ambient_temp=31.0):
    """Returns a realistic 'current moment' reading for the cockpit view."""
    soc = 68.0 + np.random.normal(0, 1.5)
    soc = float(np.clip(soc, 0, 100))

    temp_factor = 1.0 + max(0, (ambient_temp - 25) / 10) * 0.45
    dod_factor  = 0.80 + (0.85 * 0.28)
    fc_factor   = 1.0 + (0.12 * 0.30)
    sei_loss    = A_SEI    * np.sqrt(cycle_count) * temp_factor * dod_factor
    linear_loss = B_LINEAR * cycle_count          * fc_factor   * temp_factor
    soh = float(np.clip(100.0 - sei_loss - linear_loss, 50.0, 100.0))

    temperature = ambient_temp + np.random.normal(2, 1.0)
    voltage     = (MIN_CELL_V + (soc/100) * (MAX_CELL_V - MIN_CELL_V)) * CELLS_IN_SERIES
    current     = 18.0 + np.random.normal(0, 4.0)
    range_km    = BASE_RANGE_KM * (soh/100) * (soc/100)

    # Remaining Useful Life — cycles/years until 70% SoH
    n = cycle_count
    while n < 5000:
        sl = A_SEI * np.sqrt(n) * temp_factor * dod_factor
        ll = B_LINEAR * n * fc_factor * temp_factor
        if 100.0 - sl - ll <= 70.0:
            break
        n += 1
    rul_cycles = n - cycle_count
    rul_years  = rul_cycles / 300

    return {
        'soc': soc, 'soh': soh, 'temperature': temperature,
        'voltage': voltage, 'current': current, 'range_km': range_km,
        'cycle_count': cycle_count, 'capacity_ah': CAPACITY_AH * (soh/100),
        'rul_years': rul_years, 'rul_cycles': rul_cycles,
        'ambient_temp': ambient_temp,
    }

snap = get_current_snapshot()

# ── HEALTH STATUS LOGIC ───────────────────────────────────────────────────────
def get_health_status(soh, temperature, anomaly_count=0):
    if soh < 75 or temperature > 50 or anomaly_count >= 3:
        return "🔴 Action Needed", "#F44336", \
            "Battery health or temperature requires attention."
    elif soh < 85 or temperature > 42 or anomaly_count >= 1:
        return "⚠️ Monitor", "#FF9800", \
            "Battery is operating within range but showing early signs of stress."
    else:
        return "✅ Healthy", "#4CAF50", \
            "Battery is operating normally with no concerns."

status_label, status_color, status_desc = get_health_status(
    snap['soh'], snap['temperature'], anomaly_count=0
)

# ════════════════════════════════════════════════════════════════
#  TABS
# ════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs([
    "🔋 Battery Overview", "🧬 Digital Twin", "🚨 Diagnostics", "🔮 Scenario Lab"
])

with tab1:
    st.title("🔋 Battery Overview")
    st.markdown("**Tata Nexon EV (30.2 kWh) | BESCOM Digital Twin Project**")

    # ── Health status banner ─────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="background-color:{status_color}22; border-left: 6px solid {status_color};
                    padding: 16px; border-radius: 8px; margin-bottom: 20px;">
            <span style="font-size: 22px; font-weight: bold; color:{status_color};">
                {status_label}
            </span>
            <br><span style="font-size: 15px; color: #444;">{status_desc}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ── Top metric row ────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("State of Health (SoH)", f"{snap['soh']:.1f}%")
    col2.metric("State of Charge (SoC)", f"{snap['soc']:.1f}%")
    col3.metric("Remaining Useful Life", f"{snap['rul_years']:.1f} yrs",
                f"{snap['rul_cycles']} cycles")
    col4.metric("Range Remaining", f"{snap['range_km']:.0f} km")

    st.divider()

    col_left, col_right = st.columns([1, 1.3])

    # ── Battery visualization ────────────────────────────────────────────────
    with col_left:
        st.subheader("Battery Status")
        fig, ax = plt.subplots(figsize=(5, 3.2))

        soh_color = '#4CAF50' if snap['soh'] > 85 else '#FF9800' if snap['soh'] > 75 else '#F44336'

        # Battery body outline
        ax.add_patch(plt.Rectangle((0, 0), 8, 3, fill=False, edgecolor='black', linewidth=2.5))
        ax.add_patch(plt.Rectangle((8, 1), 0.5, 1, color='black'))  # terminal nub

        # SoC fill
        fill_width = 7.6 * (snap['soc'] / 100)
        ax.add_patch(plt.Rectangle((0.2, 0.2), fill_width, 2.6, color=soh_color, alpha=0.85))

        ax.text(4, 1.5, f"{snap['soc']:.0f}%", ha='center', va='center',
                fontsize=22, fontweight='bold', color='white' if fill_width > 3 else 'black')

        ax.set_xlim(-0.5, 9)
        ax.set_ylim(-0.5, 3.5)
        ax.axis('off')
        ax.set_title(f"SoH: {snap['soh']:.1f}%  (fill colour reflects health)", fontsize=10)
        st.pyplot(fig)

    # ── Compact parameter table ───────────────────────────────────────────────
    with col_right:
        st.subheader("Live Parameters")
        param_rows = [
            ("Pack Voltage",      f"{snap['voltage']:.1f} V"),
            ("Current",           f"{snap['current']:.1f} A"),
            ("Temperature",       f"{snap['temperature']:.1f} °C"),
            ("Ambient Temp",      f"{snap['ambient_temp']:.1f} °C"),
            ("Cycle Count",       f"{snap['cycle_count']}"),
            ("Usable Capacity",   f"{snap['capacity_ah']:.1f} Ah"),
            ("Usable Energy",     f"{snap['capacity_ah']/CAPACITY_AH*CAPACITY_KWH:.2f} kWh"),
        ]
        st.dataframe(
            {"Parameter": [r[0] for r in param_rows], "Value": [r[1] for r in param_rows]},
            use_container_width=True, hide_index=True
        )

with tab2:
    st.title("🧬 Digital Twin")
    st.info("Coming next — Day 1 simulator + Day 2 SoC/SoH model")

with tab3:
    st.title("🚨 Diagnostics")
    st.info("Coming next — anomaly detection")

with tab4:
    st.title("🔮 Scenario Lab")
    st.info("Coming next — what-if simulator")
