"""
Nano-Arbitrage Engine — The Pulse
Configurazione centrale del sistema.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List


# ─────────────────────────────────────────────
# API KEYS (leggi da environment, mai hardcoded)
# ─────────────────────────────────────────────
OWM_API_KEY = os.getenv("OWM_API_KEY", "YOUR_OWM_KEY_HERE")
CDS_API_KEY = os.getenv("CDS_API_KEY", "YOUR_CDS_KEY_HERE")  # Copernicus


# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ERA5_CACHE_DIR = os.path.join(DATA_DIR, "era5_cache")
PROVINCE_FILE = os.path.join(DATA_DIR, "province_coords.json")
PRODUCTS_FILE = os.path.join(DATA_DIR, "products_seed.csv")
CHROMA_DIR = os.path.join(DATA_DIR, "chroma_db")
LEDGER_DB = os.path.join(DATA_DIR, "ledger.db")


# ─────────────────────────────────────────────
# SOGLIE DELTA ANOMALIA
# Basate su Z-Score rispetto alla media storica ERA5
# ─────────────────────────────────────────────
@dataclass
class AnomalyThresholds:
    # Z-Score minimo per classificazione
    normal_max: float = 1.0       # Z < 1.0   → normale, nessuna azione
    unusual_min: float = 1.0      # 1.0 ≤ Z < 2.0 → inusuale, test budget
    extreme_min: float = 2.0      # Z ≥ 2.0   → anomalia estrema, scale aggressivo

    # Soglie assolute come fallback (quando ERA5 non disponibile)
    rain_mm_unusual: float = 30.0    # mm/24h
    rain_mm_extreme: float = 60.0
    temp_delta_unusual: float = 5.0  # °C sopra/sotto media
    temp_delta_extreme: float = 10.0
    wind_kmh_unusual: float = 50.0
    wind_kmh_extreme: float = 80.0


THRESHOLDS = AnomalyThresholds()


# ─────────────────────────────────────────────
# MAPPING EVENTI → CATEGORIE DI PRODOTTO
# Usato come fallback se ChromaDB non disponibile
# ─────────────────────────────────────────────
EVENT_PRODUCT_MAP: Dict[str, List[str]] = {
    "Heavy_Rain": ["Deumidificatori", "Impermeabili", "Stivali", "Aspiratori", "Teli waterproof"],
    "Flooding_Risk": ["Pompe", "Stivali", "Aspiratori", "Deumidificatori"],
    "Heat_Wave": ["Ventilatori", "Condizionatori", "Idratazione", "Tende oscuranti", "Protezione solare"],
    "UV_Extreme": ["Protezione solare", "Tende oscuranti"],
    "Pollen_High": ["Purificatori aria", "Mascherine", "Antistaminici"],
    "Pollen_Extreme": ["Purificatori aria", "Mascherine", "Antistaminici"],
    "Snowfall": ["Catene neve", "Pneumatici", "Raschietti neve", "Luci emergenza"],
    "Ice_Risk": ["Antigelo", "Catene neve", "Raschietti neve"],
    "Storm": ["Generatori", "Torce", "Power bank", "Luci emergenza", "Teli waterproof"],
    "Power_Outage": ["Generatori", "Torce", "Power bank", "Luci emergenza", "Termocoperte"],
    "Cold_Snap": ["Termocoperte", "Antigelo", "Generatori"],
    "Fog_Dense": ["Purificatori aria", "Luci emergenza"],
}


# ─────────────────────────────────────────────
# CLASSIFICAZIONE SEVERITY PER GUARDRAIL
# ─────────────────────────────────────────────
@dataclass
class GuardrailConfig:
    # Categorie bloccate durante allerta rossa attiva
    red_alert_banned_categories: List[str] = field(default_factory=lambda: [
        "Pompe", "Generatori"  # Gouging risk durante disastro attivo
    ])

    # Fase temporale per campagne
    pre_event_hours: int = 72       # Da quando iniziare campagne pre-evento
    blackout_start_hours: int = 6   # Ore prima del picco: stop campagne
    post_event_hours: int = 24      # Ore dopo fine evento: ripartenza recovery

    # Copy scorer
    max_fear_exploitation_score: float = 0.6
    max_urgency_score_orange: float = 0.4
    max_urgency_score_yellow: float = 0.7

    # Reputation monitor
    bounce_rate_warning: float = 0.40    # +40% spike → warning
    complaint_rate_max: float = 0.003    # 0.3% → pausa automatica


GUARDRAIL = GuardrailConfig()


# ─────────────────────────────────────────────
# ARBITRAGE SCORE WEIGHTS
# Formula: (urgency * population_weight) / competition_proxy
# ─────────────────────────────────────────────
SCORE_WEIGHTS = {
    "z_score": 0.35,
    "population_log": 0.20,
    "lead_time_factor": 0.25,   # Più anticipo = più valore
    "historical_roi": 0.20,     # Se presente nel Ledger
}

SCORE_THRESHOLD_ACTIONABLE = 6.0   # Sotto: nessuna azione
SCORE_THRESHOLD_AGGRESSIVE = 8.0   # Sopra: scale budget aggressivo


# ─────────────────────────────────────────────
# OWM WEATHER CODE → EVENTO INTERNO
# https://openweathermap.org/weather-conditions
# ─────────────────────────────────────────────
OWM_CODE_TO_EVENT = {
    # Thunderstorm
    range(200, 233): "Storm",
    # Drizzle
    range(300, 322): "Light_Rain",
    # Rain
    range(500, 502): "Heavy_Rain",
    range(502, 532): "Heavy_Rain",
    # Snow
    range(600, 623): "Snowfall",
    # Atmosphere
    range(741, 742): "Fog_Dense",
    # Clear/Clouds → gestiti dal delta termico, non dal codice meteo
    range(800, 805): "Clear",
}


def owm_code_to_event(code: int) -> str:
    """Converte codice OWM in tipo evento interno."""
    for code_range, event in OWM_CODE_TO_EVENT.items():
        if code in code_range:
            return event
    return "Unknown"


# ─────────────────────────────────────────────
# BACKTESTING CONFIG
# ─────────────────────────────────────────────
BACKTEST_YEARS = 2          # Anni di storia da analizzare
BACKTEST_SCORE_MIN = 6.0    # Soglia minima per contare come "opportunità"

# Cluster socio-demografici e loro moltiplicatori ROI storici stimati
CLUSTER_ROI_MULTIPLIER = {
    "Metro_Hub": 1.3,
    "NE_Industrial": 1.2,
    "NW_Industrial": 1.15,
    "Po_Valley": 1.1,
    "Coastal_NE": 1.05,
    "Coastal_NW": 1.0,
    "Alpine_Extreme": 0.85,
    "NW_Alpine": 0.90,
    "NW_Rural": 0.95,
    "Apennine_NE": 0.90,
    "NE_Border": 1.0,
}

# Cluster tedeschi
CLUSTER_ROI_MULTIPLIER.update({
    "DE_Metro": 1.4,
    "DE_Industrial": 1.25,
    "DE_Alpine": 1.15,
    "DE_Coastal": 1.1,
})


