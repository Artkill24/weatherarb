"""
The Pulse — Delta Calculator
Calcola Z-Score anomalia meteo vs baseline ERA5 storica.
Produce il Pulse-JSON con arbitrage_score e action_plan.
"""

import logging
import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from config import (
    THRESHOLDS,
    GUARDRAIL,
    SCORE_WEIGHTS,
    SCORE_THRESHOLD_ACTIONABLE,
    SCORE_THRESHOLD_AGGRESSIVE,
    CLUSTER_ROI_MULTIPLIER,
    EVENT_PRODUCT_MAP,
)
from core.ingestor import WeatherSnapshot, HistoricalBaseline

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────
# CLASSIFICAZIONE ANOMALIA
# ─────────────────────────────────────────────────

class AnomalyLevel:
    NORMAL = "NORMAL"
    UNUSUAL = "UNUSUAL"
    EXTREME = "EXTREME"
    CRITICAL = "CRITICAL"  # Z > 3.0


class CampaignPhase:
    NO_ACTION = "NO_ACTION"
    PRE_EVENT_PREP = "PRE_EVENT_PREP"
    PRE_EVENT_LAUNCH = "PRE_EVENT_LAUNCH"
    BLACKOUT = "BLACKOUT"           # Evento attivo: solo contenuto informativo
    POST_EVENT_RECOVERY = "POST_EVENT_RECOVERY"


class GuardrailDecision:
    APPROVED = "APPROVED"
    SOFT_BLOCK = "SOFT_BLOCK"       # Rigenera copy
    HARD_BLOCK = "HARD_BLOCK"       # Stop assoluto (allerta rossa + prodotto sensibile)


# ─────────────────────────────────────────────────
# Z-SCORE ENGINE
# ─────────────────────────────────────────────────

def compute_z_score(observed: float, mean: float, std: float, floor: float = 1.5) -> float:
    """Z-Score con safety floor sulla deviazione standard."""
    safe_std = max(std, floor)
    if safe_std <= 0:
        return 0.0
    return round((observed - mean) / safe_std, 2)


def classify_anomaly(z_score: float) -> str:
    """Classifica il livello di anomalia da Z-Score."""
    abs_z = abs(z_score)
    if abs_z >= 3.0:
        return AnomalyLevel.CRITICAL
    elif abs_z >= THRESHOLDS.extreme_min:
        return AnomalyLevel.EXTREME
    elif abs_z >= THRESHOLDS.unusual_min:
        return AnomalyLevel.UNUSUAL
    else:
        return AnomalyLevel.NORMAL


# ─────────────────────────────────────────────────
# DELTA ANALYSIS
# ─────────────────────────────────────────────────

class DeltaResult:
    """Risultato analisi delta per una singola variabile meteo."""

    def __init__(self, variable: str, observed: float, historical_mean: float,
                 historical_std: float, z_score: float, anomaly_level: str):
        self.variable = variable
        self.observed = observed
        self.historical_mean = historical_mean
        self.historical_std = historical_std
        self.z_score = z_score
        self.anomaly_level = anomaly_level
        self.delta_pct = ((observed - historical_mean) / historical_mean * 100
                          if historical_mean != 0 else 0)

    def to_dict(self) -> Dict:
        return {
            "variable": self.variable,
            "observed": round(self.observed, 2),
            "historical_mean": round(self.historical_mean, 2),
            "delta_pct": f"{self.delta_pct:+.1f}%",
            "z_score": round(self.z_score, 2),
            "anomaly_level": self.anomaly_level,
        }



# ─── ANOMALY LABELS MULTILINGUA ──────────────────────────────────────────────

def describe_anomaly(z_score: float, event_type: str, lang: str = "it") -> str:
    """
    Restituisce una frase descrittiva dell'anomalia in base a:
    - z_score: valore Z (positivo = sopra media, negativo = sotto media)
    - event_type: tipo evento (Heat_Wave, Heavy_Rain, Clear, Fog_Dense, ecc.)
    - lang: lingua (it, en, de, fr, es, nl, pl, pt, sv, da, no)
    """
    pos = z_score >= 0
    intensity = abs(z_score)

    # Mappa event_type → categoria
    ev = (event_type or "").lower()
    if any(x in ev for x in ["heat", "warm", "hot", "clear"]):
        cat = "heat"
    elif any(x in ev for x in ["rain", "flood", "storm", "precip", "heavy"]):
        cat = "rain"
    elif any(x in ev for x in ["cold", "frost", "snow", "freeze"]):
        cat = "cold"
    elif any(x in ev for x in ["wind", "gust", "storm"]):
        cat = "wind"
    elif any(x in ev for x in ["fog", "mist"]):
        cat = "fog"
    elif any(x in ev for x in ["dry", "drought"]):
        cat = "dry"
    else:
        # Fallback basato su Z-score
        cat = "heat" if pos else "cold"

    # Intensità
    if intensity >= 3.5:
        lvl = "critical"
    elif intensity >= 2.0:
        lvl = "extreme"
    elif intensity >= 1.0:
        lvl = "unusual"
    else:
        lvl = "normal"

    LABELS = {
        "it": {
            ("heat", "critical"):  "Caldo estremo anomalo",
            ("heat", "extreme"):   "Caldo anomalo",
            ("heat", "unusual"):   "Temperatura sopra la media",
            ("heat", "normal"):    "Temperatura nella norma",
            ("cold", "critical"):  "Freddo estremo anomalo",
            ("cold", "extreme"):   "Freddo anomalo",
            ("cold", "unusual"):   "Temperatura sotto la media",
            ("cold", "normal"):    "Temperatura nella norma",
            ("rain", "critical"):  "Piogge estreme",
            ("rain", "extreme"):   "Piogge anomale",
            ("rain", "unusual"):   "Piogge sopra la media",
            ("rain", "normal"):    "Precipitazioni nella norma",
            ("wind", "critical"):  "Vento estremo",
            ("wind", "extreme"):   "Vento anomalo",
            ("wind", "unusual"):   "Vento sopra la media",
            ("wind", "normal"):    "Vento nella norma",
            ("fog", "critical"):   "Nebbia densa persistente",
            ("fog", "extreme"):    "Nebbia anomala",
            ("fog", "unusual"):    "Visibilita ridotta",
            ("fog", "normal"):     "Condizioni nella norma",
            ("dry", "critical"):   "Siccita estrema",
            ("dry", "extreme"):    "Siccita anomala",
            ("dry", "unusual"):    "Secco sopra la media",
            ("dry", "normal"):     "Umidita nella norma",
        },
        "en": {
            ("heat", "critical"):  "Extreme heat anomaly",
            ("heat", "extreme"):   "Unusual heat",
            ("heat", "unusual"):   "Above average temperature",
            ("heat", "normal"):    "Normal temperature",
            ("cold", "critical"):  "Extreme cold anomaly",
            ("cold", "extreme"):   "Unusual cold",
            ("cold", "unusual"):   "Below average temperature",
            ("cold", "normal"):    "Normal temperature",
            ("rain", "critical"):  "Extreme rainfall",
            ("rain", "extreme"):   "Unusual rainfall",
            ("rain", "unusual"):   "Above average rainfall",
            ("rain", "normal"):    "Normal precipitation",
            ("wind", "critical"):  "Extreme wind",
            ("wind", "extreme"):   "Unusual wind",
            ("wind", "unusual"):   "Above average wind",
            ("wind", "normal"):    "Normal wind",
            ("fog", "critical"):   "Extreme dense fog",
            ("fog", "extreme"):    "Unusual fog",
            ("fog", "unusual"):    "Reduced visibility",
            ("fog", "normal"):     "Normal conditions",
            ("dry", "critical"):   "Extreme drought",
            ("dry", "extreme"):    "Unusual dryness",
            ("dry", "unusual"):    "Above average dryness",
            ("dry", "normal"):     "Normal humidity",
        },
        "de": {
            ("heat", "critical"):  "Extreme Hitzeanomalie",
            ("heat", "extreme"):   "Ungewohnliche Hitze",
            ("heat", "unusual"):   "Uberdurchschnittliche Temperatur",
            ("heat", "normal"):    "Normale Temperatur",
            ("cold", "critical"):  "Extreme Kalte",
            ("cold", "extreme"):   "Ungewohnliche Kalte",
            ("cold", "unusual"):   "Unterdurchschnittliche Temperatur",
            ("cold", "normal"):    "Normale Temperatur",
            ("rain", "critical"):  "Extremer Regen",
            ("rain", "extreme"):   "Ungewohnlicher Regen",
            ("rain", "unusual"):   "Uberdurchschnittlicher Regen",
            ("rain", "normal"):    "Normaler Niederschlag",
            ("wind", "critical"):  "Extremer Wind",
            ("wind", "extreme"):   "Ungewohnlicher Wind",
            ("wind", "unusual"):   "Uberdurchschnittlicher Wind",
            ("wind", "normal"):    "Normaler Wind",
            ("fog", "critical"):   "Extremer dichter Nebel",
            ("fog", "extreme"):    "Ungewohnlicher Nebel",
            ("fog", "unusual"):    "Eingeschrankte Sicht",
            ("fog", "normal"):     "Normale Bedingungen",
            ("dry", "critical"):   "Extreme Durre",
            ("dry", "extreme"):    "Ungewohnliche Trockenheit",
            ("dry", "unusual"):    "Uberdurchschnittliche Trockenheit",
            ("dry", "normal"):     "Normale Feuchtigkeit",
        },
        "fr": {
            ("heat", "critical"):  "Anomalie de chaleur extreme",
            ("heat", "extreme"):   "Chaleur inhabituelle",
            ("heat", "unusual"):   "Temperature au-dessus de la moyenne",
            ("heat", "normal"):    "Temperature normale",
            ("cold", "critical"):  "Froid extreme",
            ("cold", "extreme"):   "Froid inhabituel",
            ("cold", "unusual"):   "Temperature en dessous de la moyenne",
            ("cold", "normal"):    "Temperature normale",
            ("rain", "critical"):  "Pluies extremes",
            ("rain", "extreme"):   "Pluies inhabituelles",
            ("rain", "unusual"):   "Precipitations au-dessus de la moyenne",
            ("rain", "normal"):    "Precipitations normales",
            ("wind", "critical"):  "Vent extreme",
            ("wind", "extreme"):   "Vent inhabituel",
            ("wind", "unusual"):   "Vent au-dessus de la moyenne",
            ("wind", "normal"):    "Vent normal",
            ("fog", "critical"):   "Brouillard dense extreme",
            ("fog", "extreme"):    "Brouillard inhabituel",
            ("fog", "unusual"):    "Visibilite reduite",
            ("fog", "normal"):     "Conditions normales",
            ("dry", "critical"):   "Secheresse extreme",
            ("dry", "extreme"):    "Secheresse inhabituelle",
            ("dry", "unusual"):    "Secheresse au-dessus de la moyenne",
            ("dry", "normal"):     "Humidite normale",
        },
        "es": {
            ("heat", "critical"):  "Anomalia de calor extremo",
            ("heat", "extreme"):   "Calor inusual",
            ("heat", "unusual"):   "Temperatura por encima de la media",
            ("heat", "normal"):    "Temperatura normal",
            ("cold", "critical"):  "Frio extremo",
            ("cold", "extreme"):   "Frio inusual",
            ("cold", "unusual"):   "Temperatura por debajo de la media",
            ("cold", "normal"):    "Temperatura normal",
            ("rain", "critical"):  "Lluvias extremas",
            ("rain", "extreme"):   "Lluvias inusuales",
            ("rain", "unusual"):   "Precipitaciones por encima de la media",
            ("rain", "normal"):    "Precipitaciones normales",
            ("wind", "critical"):  "Viento extremo",
            ("wind", "extreme"):   "Viento inusual",
            ("wind", "unusual"):   "Viento por encima de la media",
            ("wind", "normal"):    "Viento normal",
            ("fog", "critical"):   "Niebla densa extrema",
            ("fog", "extreme"):    "Niebla inusual",
            ("fog", "unusual"):    "Visibilidad reducida",
            ("fog", "normal"):     "Condiciones normales",
            ("dry", "critical"):   "Sequia extrema",
            ("dry", "extreme"):    "Sequia inusual",
            ("dry", "unusual"):    "Sequia por encima de la media",
            ("dry", "normal"):     "Humedad normal",
        },
    }

    # Fallback per lingue non mappate
    lang_map = {
        "sv": "en", "nl": "en", "pl": "en",
        "pt": "es", "da": "en", "no": "en",
    }
    use_lang = lang_map.get(lang, lang) if lang not in LABELS else lang
    table = LABELS.get(use_lang, LABELS["en"])
    return table.get((cat, lvl), f"Z={z_score:+.2f}")

def analyze_deltas(snapshot: WeatherSnapshot,
                   baseline: HistoricalBaseline) -> List[DeltaResult]:
    """
    Calcola Z-Score per temperatura, pioggia e vento.
    Ritorna lista di DeltaResult ordinata per z-score decrescente.
    """
    results = []

    # --- Temperatura ---
    if snapshot.temp_c is not None:
        z = compute_z_score(snapshot.temp_c, baseline.avg_temp_c, baseline.std_temp_c)
        results.append(DeltaResult(
            variable="temperature",
            observed=snapshot.temp_c,
            historical_mean=baseline.avg_temp_c,
            historical_std=baseline.std_temp_c,
            z_score=z,
            anomaly_level=classify_anomaly(z),
        ))

    # --- Pioggia (usa peak 72h se disponibile, altrimenti 1h × 24) ---
    rain_observed = 0.0
    if False:  # peak_intensity disabilitato - valori OWM non affidabili
        # Converti da mm/3h a mm/giorno (stimato)
        rain_observed = min(snapshot.peak_intensity * 3, 100)  # cap 100mm/g
    elif snapshot.rain_1h_mm is not None:
        rain_observed = snapshot.rain_1h_mm * 8  # 8h stima evento

    if rain_observed > 0 or baseline.avg_rain_mm_day > 0:
        z = compute_z_score(rain_observed, baseline.avg_rain_mm_day, baseline.std_rain_mm_day)
        results.append(DeltaResult(
            variable="precipitation",
            observed=rain_observed,
            historical_mean=baseline.avg_rain_mm_day,
            historical_std=baseline.std_rain_mm_day,
            z_score=max(z, 0),  # Solo anomalie positive per pioggia
            anomaly_level=classify_anomaly(z),
        ))

    # --- Vento ---
    if snapshot.wind_speed_ms is not None:
        z = compute_z_score(snapshot.wind_speed_ms, baseline.avg_wind_ms,
                            baseline.std_wind_ms)
        results.append(DeltaResult(
            variable="wind",
            observed=snapshot.wind_speed_ms,
            historical_mean=baseline.avg_wind_ms,
            historical_std=baseline.std_wind_ms,
            z_score=max(z, 0),
            anomaly_level=classify_anomaly(z),
        ))

    # Ordina per z-score assoluto decrescente
    results.sort(key=lambda r: abs(r.z_score), reverse=True)
    return results


# ─────────────────────────────────────────────────
# ARBITRAGE SCORE
# ─────────────────────────────────────────────────

def compute_arbitrage_score(
    deltas: List[DeltaResult],
    provincia: Dict,
    lead_time_hours: Optional[int],
    historical_roi: Optional[float] = None,
) -> Tuple[float, float]:
    """
    Calcola l'Arbitrage Score (0-10) e la confidence (0-1).

    Formula:
    score = (z_component * w1) + (pop_component * w2) +
            (lead_time_component * w3) + (roi_component * w4)

    Ritorna (score, confidence).
    """
    if not deltas:
        return 0.0, 0.0

    # Componente 1: Z-Score massimo (normalizzato 0-1 con cap a 3.0)
    max_z = max(abs(d.z_score) for d in deltas)
    z_component = min(max_z / 3.0, 1.0) * 10

    # Componente 2: Popolazione (log-normalizzata, cap a 3M)
    pop = provincia.get("popolazione", 200000)
    pop_normalized = math.log10(min(pop, 3_000_000)) / math.log10(3_000_000)
    pop_component = pop_normalized * 10

    # Componente 3: Lead Time (valore picco tra 24h e 72h)
    if lead_time_hours is not None:
        if 18 <= lead_time_hours <= 72:
            # Picco ottimale a 48h → parabola
            lead_factor = 1 - ((lead_time_hours - 48) / 48) ** 2
            lead_factor = max(0, min(lead_factor, 1))
        elif lead_time_hours < 18:
            lead_factor = 0.3  # Troppo tardi per preparare
        else:
            lead_factor = 0.6  # Troppo presto, incertezza alta
    else:
        lead_factor = 0.5
    lead_component = lead_factor * 10

    # Componente 4: ROI storico dal Ledger
    if historical_roi is not None:
        roi_component = min(historical_roi / 5.0, 1.0) * 10
    else:
        # Usa moltiplicatore cluster come prior
        cluster = provincia.get("cluster", "Po_Valley")
        cluster_mult = CLUSTER_ROI_MULTIPLIER.get(cluster, 1.0)
        roi_component = cluster_mult * 5.0  # Prior conservativo

    # Score pesato
    w = SCORE_WEIGHTS
    score = (
        z_component * w["z_score"] +
        pop_component * w["population_log"] +
        lead_component * w["lead_time_factor"] +
        roi_component * w["historical_roi"]
    )
    score = round(min(score, 10.0), 2)

    # Confidence: alta se z_score alto + lead time buono
    confidence = min((max_z / 2.5) * 0.7 + lead_factor * 0.3, 1.0)
    confidence = round(confidence, 2)

    return score, confidence


# ─────────────────────────────────────────────────
# CAMPAIGN PHASE LOGIC
# ─────────────────────────────────────────────────

def determine_campaign_phase(
    lead_time_hours: Optional[int],
    event_active: bool,
    anomaly_level: str,
) -> str:
    """
    Determina la fase della campagna basandosi sul timing.
    Implementa il Temporal Decoupling (core del guardrail etico).
    """
    if event_active:
        return CampaignPhase.BLACKOUT

    if lead_time_hours is None:
        return CampaignPhase.NO_ACTION

    if lead_time_hours < 0:
        # Evento passato da meno di GUARDRAIL.post_event_hours
        if abs(lead_time_hours) < GUARDRAIL.post_event_hours:
            return CampaignPhase.POST_EVENT_RECOVERY
        return CampaignPhase.NO_ACTION

    if lead_time_hours <= GUARDRAIL.blackout_start_hours:
        return CampaignPhase.BLACKOUT

    if lead_time_hours <= 24:
        return CampaignPhase.PRE_EVENT_LAUNCH

    if lead_time_hours <= GUARDRAIL.pre_event_hours:
        return CampaignPhase.PRE_EVENT_PREP

    return CampaignPhase.NO_ACTION


def check_guardrail(
    event_type: str,
    anomaly_level: str,
    recommended_products: List[str],
    phase: str,
) -> GuardrailDecision:
    """
    Gate 1 deterministico: controlla condizioni di hard block.
    """
    # Hard block: prodotti sensibili durante eventi critici
    if anomaly_level == AnomalyLevel.CRITICAL:
        for prod in recommended_products:
            if prod in GUARDRAIL.red_alert_banned_categories:
                logger.warning(
                    f"HARD_BLOCK: {prod} bloccato durante anomalia CRITICAL ({event_type})"
                )
                return GuardrailDecision.HARD_BLOCK

    # Hard block: nessuna campagna durante blackout
    if phase == CampaignPhase.BLACKOUT:
        return GuardrailDecision.HARD_BLOCK

    return GuardrailDecision.APPROVED


# ─────────────────────────────────────────────────
# PULSE JSON BUILDER
# ─────────────────────────────────────────────────

def build_pulse_json(
    provincia: Dict,
    snapshot: WeatherSnapshot,
    baseline: HistoricalBaseline,
    product_suggestions: Optional[List[str]] = None,
    historical_roi: Optional[float] = None,
) -> Dict:
    """
    Assembla il Pulse-JSON finale pronto per The Architect.
    """
    now = datetime.utcnow()

    # Delta analysis
    deltas = analyze_deltas(snapshot, baseline)

    # Variabile più anomala
    primary_delta = deltas[0] if deltas else None
    primary_z = primary_delta.z_score if primary_delta else 0.0
    anomaly_level = classify_anomaly(primary_z)

    # Lead time
    lead_time_hours = snapshot.peak_expected_in_hours

    # Arbitrage score
    score, confidence = compute_arbitrage_score(
        deltas, provincia, lead_time_hours, historical_roi
    )

    # Event type (priorità: snapshot corrente o variabile più anomala)
    event_type = snapshot.event_type or "Temperature_Anomaly"
    if primary_delta and primary_delta.variable == "temperature":
        if primary_z > 1.5:
            event_type = "Heat_Wave" if snapshot.temp_c and snapshot.temp_c > baseline.avg_temp_c else "Cold_Snap"

    # Prodotti raccomandati (ChromaDB o fallback da config)
    if product_suggestions:
        top_products = product_suggestions[:5]
    else:
        top_products = EVENT_PRODUCT_MAP.get(event_type, [])[:4]

    # Campaign phase
    event_active = (lead_time_hours is not None and lead_time_hours <= 0 and snapshot.event_type not in ["Clear", "Unknown", None])
    phase = determine_campaign_phase(lead_time_hours, event_active, anomaly_level)

    # Guardrail check
    guardrail = check_guardrail(event_type, anomaly_level, top_products, phase)

    # Budget recommendation
    budget_daily = _recommend_budget(score, phase)

    # Costruzione JSON
    pulse_json = {
        "timestamp": now.isoformat() + "Z",
        "location": {
            "provincia": provincia["nome"],
            "regione": provincia.get("regione", ""),
            "codice_istat": provincia.get("codice_istat", ""),
            "cluster": provincia.get("cluster", ""),
            "popolazione": provincia.get("popolazione", 0),
            "coordinates": {"lat": provincia["lat"], "lon": provincia["lon"]},
        },
        "weather_trigger": {
            "type": event_type,
            "severity": round(min(abs(primary_z) / 3.0, 1.0), 2) if primary_delta else 0.0,
            "anomaly_level": anomaly_level,
            "primary_variable": primary_delta.variable if primary_delta else None,
            "delta_historical": primary_delta.delta_pct if primary_delta else "0%",
            "z_score": round(primary_z, 2),
            "peak_expected_in": f"{lead_time_hours}h" if lead_time_hours else "N/A",
            "current_temp_c": snapshot.temp_c,
            "historical_avg_temp_c": round(baseline.avg_temp_c, 1),
        },
        "delta_breakdown": [d.to_dict() for d in deltas],
        "arbitrage_score": {
            "score": score,
            "confidence": confidence,
            "historical_roi_estimate": historical_roi or round(CLUSTER_ROI_MULTIPLIER.get(
                provincia.get("cluster", "Po_Valley"), 1.0
            ) * 2.5, 1),
            "actionable": score >= SCORE_THRESHOLD_ACTIONABLE,
            "aggressive_scale": score >= SCORE_THRESHOLD_AGGRESSIVE,
        },
        "action_plan": {
            "phase": phase,
            "guardrail": guardrail,
            "recommended_vertical": _event_to_vertical(event_type),
            "top_product_categories": top_products,
            "budget_recommendation": {
                "daily_eur": budget_daily,
                "strategy": _budget_strategy(score, phase),
            },
        },
        "meta": {
            "engine_version": "0.1.0-sprint1",
            "data_sources": ["OpenWeatherMap", "ERA5-Land-Cluster-Baseline"],
            "next_refresh_in": "1h",
        }
    }

    return pulse_json


def _event_to_vertical(event_type: str) -> str:
    """Mappa tipo evento al vertical affiliate."""
    mapping = {
        "Heavy_Rain": "Home_Maintenance",
        "Flooding_Risk": "Home_Emergency",
        "Heat_Wave": "Cooling_Comfort",
        "UV_Extreme": "Sun_Protection",
        "Pollen_High": "Health_Wellness",
        "Pollen_Extreme": "Health_Wellness",
        "Snowfall": "Winter_Safety",
        "Ice_Risk": "Winter_Safety",
        "Storm": "Emergency_Preparedness",
        "Power_Outage": "Emergency_Preparedness",
        "Cold_Snap": "Heating_Comfort",
        "Temperature_Anomaly": "Seasonal_Comfort",
    }
    return mapping.get(event_type, "General_Seasonal")


def _recommend_budget(score: float, phase: str) -> float:
    """Budget giornaliero raccomandato in EUR."""
    if phase in [CampaignPhase.BLACKOUT, CampaignPhase.NO_ACTION]:
        return 0.0
    if score >= SCORE_THRESHOLD_AGGRESSIVE:
        return 50.0  # Scala aggressivo
    elif score >= SCORE_THRESHOLD_ACTIONABLE:
        return 15.0  # Test budget
    else:
        return 0.0


def _budget_strategy(score: float, phase: str) -> str:
    if phase == CampaignPhase.BLACKOUT:
        return "BLACKOUT_INFORMATIONAL_ONLY"
    if phase == CampaignPhase.POST_EVENT_RECOVERY:
        return "RECOVERY_SCALE_UP"
    if phase == CampaignPhase.PRE_EVENT_PREP:
        return "EDUCATIONAL_WARMUP"
    if score >= SCORE_THRESHOLD_AGGRESSIVE:
        return "AGGRESSIVE_SCALE_THOMPSON_BANDIT"
    if score >= SCORE_THRESHOLD_ACTIONABLE:
        return "TEST_BUDGET_VALIDATE"
    return "HOLD"

def estimate_impact_horizon(z_score: float, score: float) -> dict:
    if z_score > 3.0 or score > 8.5:
        return {"hours": 0, "label": "IMMEDIATO", "status": "critical"}
    if score >= 7.0:
        # Stima lineare: 10 score -> 0h, 7 score -> 24h
        h = max(6, int(24 * (1 - (score - 7) / 3)))
        return {"hours": h, "label": f"{h} ore", "status": "warning"}
    return {"hours": None, "label": "Stabile", "status": "nominal"}
