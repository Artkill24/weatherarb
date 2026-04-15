#!/usr/bin/env python3
"""
WeatherArb Space Weather Engine
Integra dati NOAA SWPC (Kp, Solar Flares) con Z-score meteo
per calcolare Grid Stress Score per ogni nodo EU
"""
import json, requests, math, logging
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

API_BASE = "https://api.weatherarb.com"
NOAA = "https://services.swpc.noaa.gov"

# ─── NOAA DATA FETCHERS ───────────────────────────────────────────────────────

def fetch_kp():
    """Fetch current Kp index (geomagnetic activity 0-9)."""
    try:
        r = requests.get(f"{NOAA}/json/planetary_k_index_1m.json", timeout=10)
        d = r.json()
        # Prendi media ultimi 30 minuti
        recent = [x for x in d[-30:] if x.get('kp_index') is not None]
        if not recent:
            return 0.0
        kp = sum(x['kp_index'] for x in recent) / len(recent)
        log.info(f"Kp index: {kp:.2f}")
        return round(kp, 2)
    except Exception as e:
        log.error(f"Kp fetch error: {e}"); return 0.0

def fetch_kp_forecast():
    """Fetch Kp forecast next 3 days."""
    try:
        r = requests.get(f"{NOAA}/products/noaa-planetary-k-index-forecast.json", timeout=10)
        d = r.json()
        now = datetime.now(timezone.utc)
        future = []
        for row in d[1:]:  # skip header
            if isinstance(row, dict):
                try:
                    ts = datetime.fromisoformat(row['time_tag'].replace('Z','+00:00'))
                    if ts > now and row.get('kp') is not None:
                        future.append(row)
                except: pass
        max_kp = max((x['kp'] for x in future[:24]), default=0)
        log.info(f"Max Kp forecast 24h: {max_kp:.2f}")
        return round(max_kp, 2), future[:8]
    except Exception as e:
        log.error(f"Kp forecast error: {e}"); return 0.0, []

def fetch_solar_flux():
    """Fetch solar X-ray flux (solar flares indicator)."""
    try:
        r = requests.get(f"{NOAA}/json/goes/primary/xrays-6-hour.json", timeout=10)
        d = r.json()
        recent = [x for x in d[-10:] if x.get('flux') is not None]
        if not recent:
            return 0.0, "A"
        flux = max(x['flux'] for x in recent)
        # Classifica flare: A<1e-8, B<1e-7, C<1e-6, M<1e-5, X>=1e-5
        if flux >= 1e-4:   flare_class = "X+"
        elif flux >= 1e-5: flare_class = "X"
        elif flux >= 1e-6: flare_class = "M"
        elif flux >= 1e-7: flare_class = "C"
        elif flux >= 1e-8: flare_class = "B"
        else:              flare_class = "A"
        log.info(f"Solar flux: {flux:.2e} ({flare_class})")
        return flux, flare_class
    except Exception as e:
        log.error(f"Solar flux error: {e}"); return 0.0, "A"

def fetch_geomagnetic_storm():
    """Fetch active geomagnetic storm level."""
    try:
        r = requests.get(f"{NOAA}/products/noaa-geomagnetic-storm-probability.json", timeout=10)
        d = r.json()
        if len(d) > 1 and isinstance(d[1], dict):
            g1 = float(d[1].get('G1', 0))
            g2 = float(d[1].get('G2', 0))
            g3 = float(d[1].get('G3', 0))
            return {"G1": g1, "G2": g2, "G3": g3}
    except: pass
    return {"G1": 0, "G2": 0, "G3": 0}

# ─── GRID STRESS SCORE ───────────────────────────────────────────────────────

def calc_grid_stress(kp, kp_forecast, flux, flare_class, z_score, hdd, cdd, hdd_delta):
    """
    Grid Stress Score 0-10 combinando:
    - Geomagnetic risk (Kp index)
    - Solar flare risk
    - Energy demand anomaly (HDD/CDD Z-score)
    """
    # 1. Geomagnetic component (0-4 points)
    geo_score = min(kp / 9.0 * 4.0, 4.0)
    # Boost se forecast alta
    if kp_forecast > 5:
        geo_score = min(geo_score + 1.0, 4.0)

    # 2. Solar flare component (0-2 points)
    flare_map = {"A": 0, "B": 0.2, "C": 0.5, "M": 1.2, "X": 2.0, "X+": 2.0}
    flare_score = flare_map.get(flare_class, 0)

    # 3. Energy demand anomaly (0-4 points)
    # HDD/CDD Z-score indica stress energetico sulla rete
    energy_z = abs(z_score) if z_score else 0
    if hdd_delta and abs(hdd_delta) > 3:
        energy_z = max(energy_z, abs(hdd_delta) / 5.0)
    energy_score = min(energy_z / 3.0 * 4.0, 4.0)

    total = geo_score + flare_score + energy_score

    # Risk label
    if total >= 7:   risk = "CRITICAL"
    elif total >= 5: risk = "HIGH"
    elif total >= 3: risk = "MODERATE"
    else:            risk = "LOW"

    # GIC risk (Geomagnetically Induced Currents) — peggiora con latitudine alta
    return {
        "grid_stress_score": round(min(total, 10), 2),
        "geo_component": round(geo_score, 2),
        "solar_component": round(flare_score, 2),
        "energy_component": round(energy_score, 2),
        "risk_level": risk,
        "kp_current": kp,
        "kp_forecast_max": kp_forecast,
        "flare_class": flare_class,
    }

def grid_stress_label(score, risk, kp, flare_class, city):
    """Genera label descrittiva per la UI."""
    if risk == "CRITICAL":
        return f"Rischio saturazione rete critico a {city}: stress energetico elevato + attività geomagnetica G{int(kp//3)+1}"
    elif risk == "HIGH":
        return f"Rischio rete elevato a {city}: combinazione domanda anomala + perturbazione magnetica (Kp={kp:.1f})"
    elif risk == "MODERATE":
        return f"Attenzione rete a {city}: condizioni di stress moderate — monitorare nelle prossime 6h"
    else:
        return f"Rete stabile a {city}: nessuna perturbazione geomagnetica significativa"

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def run():
    log.info("=== Space Weather Engine START ===")

    # Fetch NOAA data (una sola volta per tutti i nodi)
    kp = fetch_kp()
    kp_max_forecast, kp_forecast_data = fetch_kp_forecast()
    flux, flare_class = fetch_solar_flux()
    storm_prob = fetch_geomagnetic_storm()

    space_weather = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "kp_current": kp,
        "kp_forecast_max_24h": kp_max_forecast,
        "solar_flux": flux,
        "flare_class": flare_class,
        "storm_probability": storm_prob,
        "kp_forecast": kp_forecast_data,
    }

    # Salva dati globali
    out = Path("data/website/data")
    out.mkdir(parents=True, exist_ok=True)
    (out / "space_weather.json").write_text(
        json.dumps(space_weather, ensure_ascii=False, indent=2)
    )
    log.info(f"Space weather saved: Kp={kp}, Flare={flare_class}, StormG1={storm_prob['G1']}%")

    # Fetch top anomalie da API
    try:
        r = requests.get(f"{API_BASE}/api/v1/europe/top?limit=30", timeout=15)
        signals = r.json().get("reports") or r.json().get("data") or []
    except Exception as e:
        log.error(f"API error: {e}"); signals = []

    # Calcola Grid Stress per ogni nodo
    grid_scores = []
    for sig in signals:
        city = sig.get("location", "")
        z    = sig.get("z_score", 0)
        hdd  = sig.get("hdd") or 0
        cdd  = sig.get("cdd") or 0
        hdd_delta = sig.get("hdd_delta") or 0
        cc   = sig.get("country_code", "it")

        gs = calc_grid_stress(kp, kp_max_forecast, flux, flare_class, z, hdd, cdd, hdd_delta)
        gs["location"] = city
        gs["country_code"] = cc
        gs["z_score"] = z
        gs["label"] = grid_stress_label(
            gs["grid_stress_score"], gs["risk_level"], kp, flare_class, city
        )
        grid_scores.append(gs)

    # Ordina per grid stress score
    grid_scores.sort(key=lambda x: -x["grid_stress_score"])

    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "space_weather": space_weather,
        "grid_stress": grid_scores[:20],
        "total_nodes": len(grid_scores),
    }

    (out / "grid_stress.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2)
    )

    log.info(f"Grid stress scores calcolati: {len(grid_scores)} nodi")
    if grid_scores:
        top = grid_scores[0]
        log.info(f"Top risk: {top['location']} — Score {top['grid_stress_score']} ({top['risk_level']})")

    log.info("=== Space Weather Engine END ===")
    return output

if __name__ == "__main__":
    result = run()
    print(json.dumps(result["space_weather"], indent=2))
    print(f"\nTop 5 Grid Stress:")
    for g in result["grid_stress"][:5]:
        print(f"  {g['location']:20} Score:{g['grid_stress_score']:5.2f} Risk:{g['risk_level']:8} Kp:{g['kp_current']:.1f} Flare:{g['flare_class']}")
