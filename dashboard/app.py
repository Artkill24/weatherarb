"""
The Pulse — Dashboard di Validazione Strategica
Streamlit app che visualizza la heatmap di opportunità in tempo reale.
"""

import json
import time
from datetime import datetime

import requests
import streamlit as st

# ─────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────

API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="The Pulse — Nano-Arbitrage Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS custom - stile dashboard operativo
st.markdown("""
<style>
    .main { background-color: #0a0e1a; }
    .stMetric { background: #111827; border-radius: 8px; padding: 12px; border: 1px solid #1f2937; }
    .score-critical { color: #ef4444; font-weight: bold; }
    .score-high { color: #f97316; font-weight: bold; }
    .score-medium { color: #eab308; }
    .score-low { color: #6b7280; }
    .phase-badge { padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────

def fetch_heatmap():
    try:
        r = requests.get(f"{API_BASE}/pulse/heatmap/scores", timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        st.error(f"API non raggiungibile: {e}")
    return None


def fetch_pulse(provincia: str):
    try:
        r = requests.get(f"{API_BASE}/pulse/{provincia}", timeout=15)
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 404:
            st.warning(r.json().get("detail", "Provincia non trovata"))
    except Exception as e:
        st.error(f"Errore: {e}")
    return None


def trigger_refresh():
    try:
        r = requests.post(f"{API_BASE}/pulse/refresh", timeout=5)
        return r.status_code == 200
    except:
        return False


def score_color(score: float) -> str:
    if score >= 8.0: return "#ef4444"
    if score >= 7.0: return "#f97316"
    if score >= 6.0: return "#eab308"
    return "#6b7280"


def phase_label(phase: str) -> str:
    labels = {
        "PRE_EVENT_PREP": "🟡 Pre-Evento (Warm-up)",
        "PRE_EVENT_LAUNCH": "🟠 Pre-Evento (Launch)",
        "BLACKOUT": "🔴 BLACKOUT (Solo Info)",
        "POST_EVENT_RECOVERY": "🟢 Recovery",
        "NO_ACTION": "⚫ No Action",
    }
    return labels.get(phase, phase)


def anomaly_badge(level: str) -> str:
    badges = {
        "CRITICAL": "🔴 CRITICA",
        "EXTREME": "🟠 ESTREMA",
        "UNUSUAL": "🟡 INUSUALE",
        "NORMAL": "⚫ NORMALE",
    }
    return badges.get(level, level)


# ─────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────

with st.sidebar:
    st.title("⚡ The Pulse")
    st.caption("Nano-Arbitrage Engine v0.1 — Sprint 1")
    st.divider()

    # Status API
    try:
        status = requests.get(f"{API_BASE}/", timeout=3).json()
        mode = status.get("mode", "UNKNOWN")
        st.success(f"✅ API Online — Modalità: **{mode}**")
        st.caption(f"Province caricate: {status.get('province_loaded', 0)}")
        st.caption(f"Cache: {status.get('cache_entries', 0)} province")
        last_ref = status.get("last_refresh")
        if last_ref:
            st.caption(f"Ultimo refresh: {last_ref[:19]}")
    except:
        st.error("❌ API non raggiungibile")
        st.caption(f"Assicurati che FastAPI giri su {API_BASE}")
        st.stop()

    st.divider()

    # Controlli
    min_score = st.slider("Score minimo opportunità", 0.0, 10.0, 6.0, 0.5)
    show_blocked = st.checkbox("Mostra campagne bloccate (HARD_BLOCK)", False)

    st.divider()
    if st.button("🔄 Forza Refresh Globale", use_container_width=True):
        with st.spinner("Refresh in corso..."):
            if trigger_refresh():
                time.sleep(3)
                st.success("Refresh avviato!")
                st.rerun()

    # Drilldown provincia
    st.divider()
    st.subheader("🔍 Drilldown Provincia")
    provincia_input = st.text_input("Nome provincia (es. Vicenza)")
    if st.button("Analizza", use_container_width=True) and provincia_input:
        st.session_state["drilldown_provincia"] = provincia_input


# ─────────────────────────────────────────────────
# MAIN CONTENT
# ─────────────────────────────────────────────────

st.title("🌩️ Nano-Arbitrage Engine — The Pulse")
st.caption(f"Dashboard di Validazione Strategica | {datetime.now().strftime('%d/%m/%Y %H:%M')}")

# Fetch data
data = fetch_heatmap()

if not data or not data.get("data"):
    st.warning("⏳ Cache vuota. Clicca 'Forza Refresh Globale' nella sidebar e attendi ~30 secondi.")
    if st.button("🚀 Avvia primo refresh"):
        trigger_refresh()
        with st.spinner("Calcolo anomalie per tutte le province..."):
            time.sleep(8)
        st.rerun()
    st.stop()

province_data = data.get("data", [])

# ─────────────────────────────────────────────────
# KPI HEADER
# ─────────────────────────────────────────────────

actionable = [p for p in province_data if p["score"] >= min_score and
              (show_blocked or p["guardrail"] != "HARD_BLOCK")]
top = province_data[0] if province_data else {}
total_budget = sum(p.get("budget_eur", 0) for p in actionable)

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Province Monitorate", len(province_data))
with col2:
    st.metric("Opportunità Azionabili", len(actionable),
              delta=f"Score ≥ {min_score}")
with col3:
    st.metric("Budget Consigliato (€/g)",
              f"€{total_budget:.0f}",
              delta="Tutte le opportunità")
with col4:
    top_score = top.get("score", 0)
    st.metric("Top Score",
              f"{top_score:.1f}/10",
              delta=top.get("provincia", "—"))
with col5:
    extreme_count = sum(1 for p in province_data
                        if p.get("anomaly_level") in ["EXTREME", "CRITICAL"])
    st.metric("Anomalie Estreme", extreme_count, delta="Z ≥ 2.0")

st.divider()

# ─────────────────────────────────────────────────
# DRILLDOWN PROVINCE (se richiesto)
# ─────────────────────────────────────────────────

if "drilldown_provincia" in st.session_state:
    nome = st.session_state["drilldown_provincia"]
    st.subheader(f"🔍 Analisi Dettagliata: {nome}")

    with st.spinner(f"Caricamento dati per {nome}..."):
        pulse = fetch_pulse(nome)

    if pulse:
        c1, c2 = st.columns([1, 1])

        with c1:
            st.subheader("📍 Location & Trigger")
            loc = pulse.get("location", {})
            trig = pulse.get("weather_trigger", {})

            st.json({
                "Provincia": loc.get("provincia"),
                "Regione": loc.get("regione"),
                "Cluster": loc.get("cluster"),
                "Popolazione": f"{loc.get('popolazione', 0):,}",
                "Evento": trig.get("type"),
                "Anomalia": anomaly_badge(trig.get("anomaly_level", "")),
                "Z-Score": trig.get("z_score"),
                "Delta storico": trig.get("delta_historical"),
                "Temp attuale": f"{trig.get('current_temp_c', 'N/A')}°C",
                "Media storica": f"{trig.get('historical_avg_temp_c', 'N/A')}°C",
                "Peak tra": trig.get("peak_expected_in"),
            })

        with c2:
            st.subheader("💰 Arbitrage & Action Plan")
            arb = pulse.get("arbitrage_score", {})
            action = pulse.get("action_plan", {})

            score_val = arb.get("score", 0)
            st.metric("Arbitrage Score", f"{score_val:.2f}/10",
                      delta="AZIONABILE ✅" if arb.get("actionable") else "Sotto soglia")

            st.progress(score_val / 10)

            st.json({
                "Confidence": f"{arb.get('confidence', 0) * 100:.0f}%",
                "ROI stimato": f"{arb.get('historical_roi_estimate', 0)}x",
                "Scale aggressivo": arb.get("aggressive_scale", False),
                "Fase campagna": phase_label(action.get("phase", "")),
                "Guardrail": action.get("guardrail"),
                "Vertical": action.get("recommended_vertical"),
                "Budget €/g": action.get("budget_recommendation", {}).get("daily_eur", 0),
                "Strategia": action.get("budget_recommendation", {}).get("strategy"),
                "Prodotti consigliati": action.get("top_product_categories", []),
            })

        # Delta breakdown
        st.subheader("📊 Delta Breakdown (Z-Score per variabile)")
        deltas = pulse.get("delta_breakdown", [])
        if deltas:
            cols = st.columns(len(deltas))
            for i, delta in enumerate(deltas):
                with cols[i]:
                    st.metric(
                        label=delta["variable"].upper(),
                        value=f"Z = {delta['z_score']:+.2f}",
                        delta=delta["delta_historical"],
                    )
                    st.caption(f"Osservato: {delta['observed']} | Media: {delta['historical_mean']}")
                    st.caption(f"Livello: {anomaly_badge(delta['anomaly_level'])}")

    st.divider()

# ─────────────────────────────────────────────────
# TABELLA OPPORTUNITÀ
# ─────────────────────────────────────────────────

st.subheader(f"📋 Opportunità ({len(actionable)} province con score ≥ {min_score})")

if actionable:
    # Prepara dati per tabella
    table_rows = []
    for p in sorted(actionable, key=lambda x: x["score"], reverse=True):
        table_rows.append({
            "Provincia": p["provincia"],
            "Regione": p["regione"],
            "Score": p["score"],
            "Conf.": f"{p['confidence']*100:.0f}%",
            "Evento": p["event_type"] or "—",
            "Anomalia": p["anomaly_level"],
            "Z-Score": p["z_score"],
            "Fase": p["phase"],
            "Guardrail": p["guardrail"],
            "Budget €/g": p["budget_eur"],
            "Vertical": p["vertical"],
        })

    import pandas as pd
    df = pd.DataFrame(table_rows)

    # Color coding score
    def color_score(val):
        if val >= 8.0: return "background-color: #450a0a; color: #ef4444"
        if val >= 7.0: return "background-color: #431407; color: #f97316"
        if val >= 6.0: return "background-color: #422006; color: #eab308"
        return ""

    styled = df.style.applymap(color_score, subset=["Score"])
    st.dataframe(styled, use_container_width=True, height=400)

    # Export JSON
    st.download_button(
        label="📥 Esporta Opportunità JSON",
        data=json.dumps(actionable, indent=2, ensure_ascii=False),
        file_name=f"pulse_opportunities_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
        mime="application/json",
    )
else:
    st.info(f"Nessuna opportunità con score ≥ {min_score}. Abbassa la soglia o attendi il prossimo refresh.")

# ─────────────────────────────────────────────────
# MAPPA GEOGRAFICA (usando pydeck se disponibile)
# ─────────────────────────────────────────────────

st.subheader("🗺️ Heatmap Geografica")

try:
    import pydeck as pdk
    import pandas as pd

    map_data = []
    for p in province_data:
        if p.get("lat") and p.get("lon"):
            map_data.append({
                "lat": p["lat"],
                "lon": p["lon"],
                "provincia": p["provincia"],
                "score": p["score"],
                "event": p["event_type"] or "",
                "radius": max(p["score"] * 1500, 3000),
                # Colore: rosso=alto score, verde=basso
                "r": min(int(p["score"] * 25), 255),
                "g": max(255 - int(p["score"] * 25), 0),
                "b": 50,
                "a": 160,
            })

    df_map = pd.DataFrame(map_data)

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df_map,
        get_position=["lon", "lat"],
        get_radius="radius",
        get_fill_color=["r", "g", "b", "a"],
        pickable=True,
        opacity=0.8,
    )

    view = pdk.ViewState(
        latitude=45.5,
        longitude=10.8,
        zoom=6,
        pitch=0,
    )

    r = pdk.Deck(
        layers=[layer],
        initial_view_state=view,
        tooltip={"text": "{provincia}\nScore: {score}\nEvento: {event}"},
        map_style="mapbox://styles/mapbox/dark-v10",
    )

    st.pydeck_chart(r)

except ImportError:
    # Fallback: tabella con coordinate
    st.info("💡 Installa `pydeck` per la mappa interattiva: `pip install pydeck`")

    # Tabella semplice con lat/lon
    if province_data:
        import pandas as pd
        df_simple = pd.DataFrame([
            {"Provincia": p["provincia"], "Lat": p["lat"], "Lon": p["lon"],
             "Score": p["score"], "Evento": p["event_type"]}
            for p in province_data[:20] if p.get("lat")
        ])
        st.dataframe(df_simple, use_container_width=True)

# ─────────────────────────────────────────────────
# AUTO-REFRESH
# ─────────────────────────────────────────────────

st.divider()
col_r1, col_r2 = st.columns([3, 1])
with col_r1:
    auto_refresh = st.checkbox("⟳ Auto-refresh ogni 5 minuti", value=False)
with col_r2:
    if st.button("🔄 Refresh Manuale"):
        st.rerun()

if auto_refresh:
    time.sleep(300)
    st.rerun()
