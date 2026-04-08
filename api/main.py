"""
The Pulse — FastAPI Layer
Interfaccia REST per interrogare il sistema.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import OWM_API_KEY, SCORE_THRESHOLD_ACTIONABLE
from core.ingestor import (
    load_provinces,
    OWMFetcher,
    build_weather_snapshot,
    build_historical_baseline,
)
from core.delta_calculator import build_pulse_json
from core.product_mapper import ProductMapper

# ─────────────────────────────────────────────────
# SETUP
# ─────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Nano-Arbitrage Engine — The Pulse",
    description="Sistema di rilevamento anomalie meteo per affiliate marketing geo-localizzato",
    version="0.1.0-sprint1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────
# STATO GLOBALE (in produzione: Redis)
# ─────────────────────────────────────────────────

_province_index: Dict[str, Dict] = {}
_pulse_cache: Dict[str, Dict] = {}     # provincia → ultimo pulse json
_last_refresh: Optional[datetime] = None

USE_MOCK = OWM_API_KEY == "YOUR_OWM_KEY_HERE"


def _init_state():
    """Carica province e inizializza index."""
    global _province_index
    provinces = load_provinces()
    _province_index = {p["nome"].lower(): p for p in provinces}
    logger.info(f"Loaded {len(_province_index)} province")


_init_state()
fetcher = OWMFetcher(api_key=OWM_API_KEY, use_mock=USE_MOCK)
mapper = ProductMapper(use_chroma=True)

if USE_MOCK:
    logger.warning("⚠️  Running in MOCK mode — set OWM_API_KEY env var for real data")


# ─────────────────────────────────────────────────
# BACKGROUND TASK: REFRESH
# ─────────────────────────────────────────────────

def _refresh_provincia(provincia_nome: str):
    """Task in background: aggiorna pulse per una provincia."""
    provincia = _province_index.get(provincia_nome.lower())
    if not provincia:
        return

    try:
        snapshot = build_weather_snapshot(provincia, fetcher)
        baseline = build_historical_baseline(provincia)

        # Product suggestions via ChromaDB
        event_type = snapshot.event_type or "Heavy_Rain"
        products = mapper.get_products_for_event(event_type, n_results=5)
        product_categories = [p["categoria"] for p in products]

        pulse = build_pulse_json(
            provincia=provincia,
            snapshot=snapshot,
            baseline=baseline,
            product_suggestions=product_categories,
        )
        _pulse_cache[provincia_nome.lower()] = pulse
        logger.info(
            f"Refreshed {provincia_nome}: score={pulse['arbitrage_score']['score']} "
            f"phase={pulse['action_plan']['phase']}"
        )
    except Exception as e:
        logger.error(f"Refresh failed for {provincia_nome}: {e}")


def _refresh_all():
    """Refresh tutte le province del Nord Italia."""
    global _last_refresh
    logger.info(f"Starting full refresh for {len(_province_index)} province...")
    for nome in _province_index:
        _refresh_provincia(nome)
    _last_refresh = datetime.utcnow()
    logger.info("Full refresh complete")


# ─────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "system": "Nano-Arbitrage Engine — The Pulse",
        "version": "0.1.0-sprint1",
        "status": "operational",
        "mode": "MOCK" if USE_MOCK else "LIVE",
        "province_loaded": len(_province_index),
        "cache_entries": len(_pulse_cache),
        "last_refresh": _last_refresh.isoformat() if _last_refresh else None,
    }


@app.get("/pulse/{provincia}")
def get_pulse(
    provincia: str,
    background_tasks: BackgroundTasks,
    force_refresh: bool = Query(False, description="Forza aggiornamento dati"),
):
    """
    Restituisce il Pulse-JSON per una provincia specifica.
    Aggiorna i dati in background se la cache è vuota o force_refresh=True.
    """
    key = provincia.lower()

    if key not in _province_index:
        # Cerca match parziale
        matches = [k for k in _province_index if provincia.lower() in k]
        if matches:
            raise HTTPException(
                status_code=404,
                detail=f"Provincia '{provincia}' non trovata. Intendevi: {matches[:3]}?"
            )
        raise HTTPException(status_code=404, detail=f"Provincia '{provincia}' non trovata")

    # Se cache vuota o refresh forzato, calcola subito (sync per il primo hit)
    if key not in _pulse_cache or force_refresh:
        _refresh_provincia(key)
    else:
        # Aggiorna in background per il prossimo hit
        background_tasks.add_task(_refresh_provincia, key)

    pulse = _pulse_cache.get(key)
    if not pulse:
        raise HTTPException(status_code=503, detail="Dati non ancora disponibili, riprova tra 5 secondi")

    return pulse


@app.post("/pulse/refresh")
def refresh_all(background_tasks: BackgroundTasks):
    """
    Scatena il refresh completo di tutte le province in background.
    """
    background_tasks.add_task(_refresh_all)
    return {
        "status": "refresh_started",
        "province_count": len(_province_index),
        "message": "Il refresh è in corso. Interroga /pulse/{provincia} tra 30 secondi."
    }


@app.get("/pulse/heatmap/scores")
def get_heatmap():
    """
    Ritorna tutti gli arbitrage scores per la dashboard heatmap.
    """
    if not _pulse_cache:
        return {"message": "Cache vuota. Esegui POST /pulse/refresh prima.", "data": []}

    heatmap_data = []
    for nome, pulse in _pulse_cache.items():
        score_data = pulse.get("arbitrage_score", {})
        loc = pulse.get("location", {})
        trigger = pulse.get("weather_trigger", {})
        action = pulse.get("action_plan", {})

        heatmap_data.append({
            "provincia": loc.get("provincia"),
            "regione": loc.get("regione"),
            "lat": loc.get("coordinates", {}).get("lat"),
            "lon": loc.get("coordinates", {}).get("lon"),
            "score": score_data.get("score", 0),
            "confidence": score_data.get("confidence", 0),
            "actionable": score_data.get("actionable", False),
            "event_type": trigger.get("type"),
            "anomaly_level": trigger.get("anomaly_level"),
            "z_score": trigger.get("z_score"),
            "phase": action.get("phase"),
            "guardrail": action.get("guardrail"),
            "budget_eur": action.get("budget_recommendation", {}).get("daily_eur", 0),
            "vertical": action.get("recommended_vertical"),
        })

    # Ordina per score decrescente
    heatmap_data.sort(key=lambda x: x["score"], reverse=True)
    actionable_count = sum(1 for x in heatmap_data if x["actionable"])

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "total_province": len(heatmap_data),
        "actionable_opportunities": actionable_count,
        "top_opportunity": heatmap_data[0] if heatmap_data else None,
        "data": heatmap_data,
    }


@app.get("/pulse/heatmap/opportunities")
def get_opportunities(min_score: float = Query(SCORE_THRESHOLD_ACTIONABLE)):
    """
    Lista filtrata delle sole province con score >= min_score.
    """
    all_data = get_heatmap()
    opportunities = [
        item for item in all_data.get("data", [])
        if item["score"] >= min_score and item["guardrail"] != "HARD_BLOCK"
    ]

    return {
        "filter_score_min": min_score,
        "count": len(opportunities),
        "total_budget_suggested_eur": sum(o["budget_eur"] for o in opportunities),
        "opportunities": opportunities,
    }


@app.get("/province")
def list_province():
    """Lista tutte le province disponibili."""
    return {
        "count": len(_province_index),
        "province": sorted(_province_index.keys()),
    }


# ── Governor / Kill Switch endpoints ──────────────────────────────
from core.bid_manager import BidManager as _BidManager
_bid_manager = _BidManager()

@app.post("/emergency/kill")
def kill_switch_activate(reason: str = "Manual emergency stop"):
    return _bid_manager.activate_kill_switch(reason)

@app.post("/emergency/reset")
def kill_switch_reset(reason: str = "Manual reset after review"):
    return _bid_manager.deactivate_kill_switch(reason)

@app.get("/governor/status")
def governor_status():
    return _bid_manager.get_system_status()

@app.post("/governor/evaluate/{provincia}")
def evaluate_budget(provincia: str):
    key = provincia.lower()
    if key not in _pulse_cache:
        raise HTTPException(status_code=404, detail=f"Nessun dato pulse per {provincia}")
    from datetime import datetime as _dt
    alloc = _bid_manager.evaluate(_pulse_cache[key])
    return alloc.to_dict()


# ── PUBLIC API ──────────────────────────────────────────────────────
from collections import defaultdict
import time as _time
import csv as _csv

_api_calls = defaultdict(list)

@app.get("/api/v1/pulse/{provincia}")
def api_pulse(provincia: str):
    key = provincia.lower()
    if key not in _province_index:
        raise HTTPException(status_code=404, detail=f"Province '{provincia}' not found")
    if key not in _pulse_cache:
        _refresh_provincia(key)
    pulse = _pulse_cache.get(key)
    if not pulse:
        raise HTTPException(status_code=503, detail="Data not yet available")
    trig = pulse["weather_trigger"]
    arb = pulse["arbitrage_score"]
    return {
        "api_version": "v1",
        "province": pulse["location"]["provincia"],
        "region": pulse["location"]["regione"],
        "country": "IT",
        "timestamp": pulse["timestamp"],
        "weather": {
            "event_type": trig.get("type"),
            "severity": trig.get("severity"),
            "anomaly_level": trig.get("anomaly_level"),
            "z_score": trig.get("z_score"),
            "temperature_c": trig.get("current_temp_c"),
            "historical_avg_c": trig.get("historical_avg_temp_c"),
        },
        "signal": {
            "score": arb.get("score"),
            "confidence": arb.get("confidence"),
            "actionable": arb.get("actionable"),
        },
        "attribution": "WeatherArb.com · ERA5-Land ECMWF + OpenWeatherMap",
    }

@app.get("/api/v1/europe/top")
def api_top(limit: int = 10):
    signals = []
    for nome, pulse in _pulse_cache.items():
        loc = pulse.get("location", {})
        trig = pulse.get("weather_trigger", {})
        arb = pulse.get("arbitrage_score", {})
        signals.append({
            "province": loc.get("provincia"),
            "region": loc.get("regione"),
            "event_type": trig.get("type"),
            "z_score": trig.get("z_score", 0),
            "anomaly_level": trig.get("anomaly_level"),
            "score": arb.get("score", 0),
        })
    signals.sort(key=lambda x: abs(x["z_score"] or 0), reverse=True)
    return {"api_version": "v1", "count": min(limit, len(signals)), "data": signals[:limit]}

@app.get("/api/v1/widget/{provincia}")
def api_widget(provincia: str):
    key = provincia.lower()
    if key not in _pulse_cache:
        _refresh_provincia(key)
    pulse = _pulse_cache.get(key, {})
    trig = pulse.get("weather_trigger", {})
    arb = pulse.get("arbitrage_score", {})
    return {
        "p": pulse.get("location", {}).get("provincia", provincia),
        "e": (trig.get("type") or "").replace("_", " "),
        "z": trig.get("z_score", 0),
        "a": trig.get("anomaly_level", "NORMAL"),
        "s": arb.get("score", 0),
        "t": (pulse.get("timestamp") or "")[:10],
    }

@app.post("/api/newsletter/subscribe")
def newsletter_subscribe(email: str, provincia: str = ""):
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email")
    from pathlib import Path
    f = "data/newsletter_subscribers.csv"
    Path(f).parent.mkdir(exist_ok=True)
    existing = set()
    if Path(f).exists():
        with open(f) as fp:
            existing = {row[0] for row in _csv.reader(fp)}
    if email in existing:
        return {"status": "already_subscribed"}
    with open(f, "a", newline="") as fp:
        _csv.writer(fp).writerow([email, provincia, datetime.utcnow().isoformat()])
    return {"status": "subscribed", "message": f"Welcome! Alerts for {provincia or 'all Europe'}"}

@app.get("/api/v1/docs")
def api_docs():
    return {
        "name": "WeatherArb Public API",
        "version": "v1",
        "free_tier": "100 calls/day, no auth required",
        "endpoints": {
            "GET /api/v1/pulse/{province}": "Anomaly data for a province",
            "GET /api/v1/europe/top": "Top signals across Europe",
            "GET /api/v1/widget/{province}": "Lightweight widget data",
            "POST /api/newsletter/subscribe": "Subscribe to weekly digest",
        },
        "example": "curl https://weatherarb.com/api/v1/pulse/vicenza",
    }
