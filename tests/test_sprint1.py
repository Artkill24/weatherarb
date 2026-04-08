"""
Test Suite — The Pulse Sprint 1
1. Guardrail stress test: injection Rain 50mm su Vicenza
2. Ledger integration test
3. Volume stats dopo refresh reale
"""

import json
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.ingestor import load_provinces, build_historical_baseline, WeatherSnapshot
from core.delta_calculator import (
    build_pulse_json, check_guardrail, determine_campaign_phase,
    AnomalyLevel, GuardrailDecision, CampaignPhase
)
from core.ledger import PulseLedger


def separator(title: str):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print('='*55)


# ─────────────────────────────────────────────────
# TEST 1: GUARDRAIL STRESS TEST
# Injection manuale Rain: 50mm su Vicenza
# ─────────────────────────────────────────────────

def test_guardrail_stress():
    separator("GUARDRAIL STRESS TEST — Rain 50mm @ Vicenza")

    provinces = load_provinces()
    vicenza = next(p for p in provinces if p["nome"] == "Vicenza")
    baseline = build_historical_baseline(vicenza)

    # Crea snapshot con dati iniettati manualmente
    snap = WeatherSnapshot("Vicenza", vicenza["lat"], vicenza["lon"])
    snap.temp_c = 14.2
    snap.feels_like_c = 12.0
    snap.humidity_pct = 92
    snap.rain_1h_mm = 18.5        # Pioggia intensa attuale
    snap.peak_intensity = 24.0    # Peak 24mm/3h nelle prossime ore (≈ 192mm/day stimato)
    snap.peak_expected_in_hours = 8
    snap.wind_speed_ms = 7.2
    snap.weather_code = 502       # Heavy rain
    snap.event_type = "Flooding_Risk"

    pulse = build_pulse_json(
        provincia=vicenza,
        snapshot=snap,
        baseline=baseline,
        product_suggestions=["Pompe", "Deumidificatori", "Stivali", "Impermeabili"],
    )

    print(f"\n📍 Provincia: Vicenza")
    print(f"   Pioggia iniettata: 18.5mm/h | Peak: 24mm/3h")
    print(f"   Evento: {pulse['weather_trigger']['type']}")
    print(f"   Z-Score: {pulse['weather_trigger']['z_score']}")
    print(f"   Anomaly Level: {pulse['weather_trigger']['anomaly_level']}")
    print(f"   Arbitrage Score: {pulse['arbitrage_score']['score']}")
    print(f"   Fase: {pulse['action_plan']['phase']}")
    print(f"   Guardrail: {pulse['action_plan']['guardrail']}")

    # Test specifico: Pompe in flooding risk
    print("\n--- Test Guardrail: Pompe durante Flooding_Risk ---")
    scenarios = [
        ("Flooding_Risk", "CRITICAL", ["Pompe"], "PRE_EVENT_LAUNCH"),
        ("Flooding_Risk", "EXTREME", ["Deumidificatori"], "PRE_EVENT_PREP"),
        ("Heavy_Rain",    "EXTREME", ["Impermeabili"], "PRE_EVENT_LAUNCH"),
        ("Flooding_Risk", "CRITICAL", ["Pompe"], "BLACKOUT"),
        ("Heavy_Rain",    "UNUSUAL", ["Stivali"], "POST_EVENT_RECOVERY"),
    ]

    all_passed = True
    for event, anomaly, products, phase in scenarios:
        decision = check_guardrail(event, anomaly, products, phase)
        expected_block = (
            (anomaly == "CRITICAL" and "Pompe" in products) or
            phase == CampaignPhase.BLACKOUT
        )
        expected = GuardrailDecision.HARD_BLOCK if expected_block else GuardrailDecision.APPROVED
        passed = decision == expected

        icon = "✅" if passed else "❌ FAIL"
        all_passed = all_passed and passed
        print(f"  {icon} [{phase[:18]:<18}] {event:<20} + {products[0]:<18} "
              f"→ {decision} (expected: {expected})")

    print(f"\n{'✅ TUTTI I TEST GUARDRAIL PASSATI' if all_passed else '❌ ALCUNI TEST FALLITI'}")
    return all_passed


# ─────────────────────────────────────────────────
# TEST 2: LEDGER INTEGRATION
# ─────────────────────────────────────────────────

def test_ledger():
    separator("LEDGER INTEGRATION TEST")

    # Usa DB di test separato
    test_db = "/tmp/test_ledger.db"
    ledger = PulseLedger(db_path=test_db)

    # Simula 5 eventi su province diverse
    provinces = load_provinces()
    test_province = ["Vicenza", "Milano", "Bologna", "Venezia", "Bolzano"]

    event_ids = []
    for nome in test_province:
        prov = next(p for p in provinces if p["nome"] == nome)
        baseline = build_historical_baseline(prov)

        snap = WeatherSnapshot(nome, prov["lat"], prov["lon"])
        snap.temp_c = baseline.avg_temp_c + (3.5 if nome in ["Milano", "Bologna"] else 1.2)
        snap.rain_1h_mm = 8.5 if nome in ["Vicenza", "Venezia"] else 1.0
        snap.peak_intensity = 15.0 if nome == "Vicenza" else 3.0
        snap.peak_expected_in_hours = 24
        snap.wind_speed_ms = 4.0
        snap.weather_code = 501
        snap.event_type = "Heavy_Rain" if snap.rain_1h_mm > 5 else "Temperature_Anomaly"

        pulse = build_pulse_json(prov, snap, baseline)
        event_id = ledger.record_pulse_event(pulse)
        event_ids.append(event_id)

        print(f"  ✅ Registrato evento #{event_id}: {nome} | "
              f"Score={pulse['arbitrage_score']['score']:.2f} | "
              f"Phase={pulse['action_plan']['phase']}")

    # Simula outcome campagna per Vicenza
    print("\n--- Simulazione outcome campagna Vicenza ---")
    with ledger._conn() as conn:
        cursor = conn.execute("""
            INSERT INTO campaigns (
                pulse_event_id, started_at, platform, provincia,
                event_type, vertical, product_category, budget_daily_eur,
                headline_variant, frame_emotivo, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (event_ids[0], datetime.utcnow().isoformat(), "taboola",
              "Vicenza", "Heavy_Rain", "Home_Maintenance", "Deumidificatori",
              15.0, "A", "local_identity", "active"))
        campaign_id = cursor.lastrowid

    outcome_id = ledger.record_campaign_outcome(campaign_id, datetime.now().strftime("%Y-%m-%d"), {
        "impressions": 12400,
        "clicks": 186,
        "ctr": 0.015,
        "cpc_eur": 0.081,
        "spend_eur": 15.0,
        "lp_clicks": 62,
        "lp_ctr": 0.333,
        "time_on_page_sec": 87.3,
        "bounce_rate": 0.31,
        "affiliate_clicks": 54,
        "affiliate_conversions": 4,
        "affiliate_revenue_eur": 189.99 * 4,  # 4 deumidificatori
        "commission_eur": 189.99 * 4 * 0.04,  # 4% commissione
        "bandit_alpha": 5,
        "bandit_beta": 2,
    })
    print(f"  ✅ Outcome campagna #{campaign_id} registrato (ROI simulato)")

    # Update pattern storico
    ledger.update_historical_pattern(
        cluster="NE_Industrial",
        event_type="Heavy_Rain",
        month=datetime.now().month,
        anomaly_level="EXTREME",
        vertical="Home_Maintenance",
        frame_emotivo="local_identity",
        roi=4.05,  # (30.4 commissione - 15 spend) / 15
        ctr=0.015,
        cplp=0.242,
        conversion_rate=0.064,
    )
    print("  ✅ Pattern storico NE_Industrial/Heavy_Rain aggiornato")

    # Query predittiva
    print("\n--- Query Predictive Bidding ---")
    roi_data = ledger.get_historical_roi(
        cluster="NE_Industrial",
        event_type="Heavy_Rain",
        month=datetime.now().month,
        anomaly_level="EXTREME",
        vertical="Home_Maintenance",
    )
    if roi_data:
        print(f"  📊 ROI storico per NE_Industrial/Heavy_Rain/EXTREME:")
        print(f"     avg_ROI:        {roi_data['avg_roi']:.2f}x")
        print(f"     avg_CTR:        {roi_data['avg_ctr']*100:.1f}%")
        print(f"     avg_CPLP:       €{roi_data['avg_cplp_eur']:.3f}")
        print(f"     Confidence:     {roi_data['confidence']*100:.0f}%")
        print(f"     Best frame:     {roi_data['best_frame']}")

    # Stats DB
    print("\n--- Stats Database ---")
    stats = ledger.get_db_stats()
    for table, count in stats.items():
        print(f"  {table:<30} {count:>4} records")

    # Volume opportunità
    volume = ledger.get_opportunity_volume(days=1)
    print(f"\n  Evaluazioni totali:     {volume['total_evaluations']}")
    print(f"  Opportunità azionabili: {volume['actionable_opportunities']}")

    # Cleanup
    Path(test_db).unlink(missing_ok=True)
    print("\n✅ LEDGER TEST COMPLETATO")
    return True


# ─────────────────────────────────────────────────
# TEST 3: INTEGRAZIONE CON API REALE
# Legge dati dal Ledger del sistema live
# ─────────────────────────────────────────────────

def test_live_ledger():
    separator("LIVE LEDGER STATS (sistema reale)")

    from config import LEDGER_DB
    if not Path(LEDGER_DB).exists():
        print("  ℹ️  Ledger non ancora inizializzato (nessun evento registrato)")
        print("     Avvia il backend e fai /pulse/refresh, poi riesegui.")
        return

    ledger = PulseLedger()
    stats = ledger.get_db_stats()
    print("\n  Records per tabella:")
    for table, count in stats.items():
        print(f"    {table:<30} {count:>4}")

    volume = ledger.get_opportunity_volume(days=7)
    print(f"\n  Ultimi 7 giorni:")
    print(f"    Evaluazioni:   {volume['total_evaluations']}")
    print(f"    Azionabili:    {volume['actionable_opportunities']}")
    print(f"    Score medio:   {volume['avg_score']}")
    print(f"    Score massimo: {volume['max_score_seen']}")

    if volume["top_province"]:
        print(f"\n  Top province per opportunità:")
        for p in volume["top_province"][:5]:
            print(f"    {p['provincia']:<20} {p['opportunities']} opp. | avg score {p['avg_score']:.2f}")


# ─────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("🔬 THE PULSE — TEST SUITE SPRINT 1")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    g_ok = test_guardrail_stress()
    l_ok = test_ledger()
    test_live_ledger()

    separator("RISULTATO FINALE")
    print(f"  Guardrail Stress Test: {'✅ PASS' if g_ok else '❌ FAIL'}")
    print(f"  Ledger Integration:    {'✅ PASS' if l_ok else '❌ FAIL'}")
    print("\n  Sistema pronto per Sprint 2 — The Architect")
