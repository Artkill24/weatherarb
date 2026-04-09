"""
The Pulse — Ingestor
Recupera dati meteo real-time (OWM) e storici (ERA5 simulato/cache).
Produce dati normalizzati pronti per il DeltaCalculator.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

from config import (
    OWM_API_KEY,
    PROVINCE_FILE,
    ERA5_CACHE_DIR,
    owm_code_to_event,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────
# MODELLI DATI
# ─────────────────────────────────────────────────

# Baseline corrette per città tedesche (ERA5 aprile)
DE_BASELINES = {
    "München":    {"temp_mean": 10.5, "temp_std": 4.2, "rain_mean": 2.1, "rain_std": 3.5},
    "Hamburg":    {"temp_mean": 8.8,  "temp_std": 3.8, "rain_mean": 3.2, "rain_std": 4.1},
    "Berlin":     {"temp_mean": 9.2,  "temp_std": 4.0, "rain_mean": 2.4, "rain_std": 3.8},
    "Frankfurt":  {"temp_mean": 10.2, "temp_std": 4.1, "rain_mean": 2.8, "rain_std": 3.9},
    "Stuttgart":  {"temp_mean": 9.8,  "temp_std": 4.3, "rain_mean": 3.1, "rain_std": 4.0},
    "Köln":       {"temp_mean": 10.1, "temp_std": 3.9, "rain_mean": 3.0, "rain_std": 4.2},
    "Düsseldorf": {"temp_mean": 10.0, "temp_std": 3.8, "rain_mean": 3.1, "rain_std": 4.1},
    "Nürnberg":   {"temp_mean": 9.5,  "temp_std": 4.2, "rain_mean": 2.6, "rain_std": 3.7},
}

class WeatherSnapshot:
    """Snapshot meteo real-time per una provincia."""

    def __init__(self, provincia: str, lat: float, lon: float):
        self.provincia = provincia
        self.lat = lat
        self.lon = lon
        self.timestamp = datetime.utcnow()

        # Dati correnti
        self.temp_c: Optional[float] = None
        self.feels_like_c: Optional[float] = None
        self.humidity_pct: Optional[float] = None
        self.rain_1h_mm: Optional[float] = None
        self.rain_3h_mm: Optional[float] = None
        self.wind_speed_ms: Optional[float] = None
        self.weather_code: Optional[int] = None
        self.weather_desc: Optional[str] = None

        # Previsione 72h (lista di snapshot orari)
        self.forecast_72h: List[Dict] = []

        # Evento classificato
        self.event_type: Optional[str] = None

        # Peak previsto
        self.peak_intensity: Optional[float] = None
        self.peak_expected_in_hours: Optional[int] = None

    def to_dict(self) -> Dict:
        return {
            "provincia": self.provincia,
            "timestamp": self.timestamp.isoformat(),
            "current": {
                "temp_c": self.temp_c,
                "feels_like_c": self.feels_like_c,
                "humidity_pct": self.humidity_pct,
                "rain_1h_mm": self.rain_1h_mm,
                "wind_kmh": round(self.wind_speed_ms * 3.6, 1) if self.wind_speed_ms else None,
                "weather_code": self.weather_code,
                "weather_desc": self.weather_desc,
            },
            "event_type": self.event_type,
            "peak_expected_in_hours": self.peak_expected_in_hours,
        }


class HistoricalBaseline:
    """Media storica ERA5 per una provincia/mese."""

    def __init__(self, provincia: str, month: int):
        self.provincia = provincia
        self.month = month

        # Medie storiche (da ERA5 o simulazione calibrata)
        self.avg_temp_c: float = 0.0
        self.std_temp_c: float = 0.0
        self.avg_rain_mm_day: float = 0.0
        self.std_rain_mm_day: float = 0.0
        self.avg_wind_ms: float = 0.0
        self.std_wind_ms: float = 0.0
        self.avg_humidity_pct: float = 0.0

        # Percentili storici
        self.p95_rain_mm: float = 0.0  # 95° percentile pioggia
        self.p95_temp_c: float = 0.0


# ─────────────────────────────────────────────────
# ERA5 BASELINE: Dati statistici calibrati per cluster
# In produzione: sostituire con download CDS API
# Valori derivati da climatologie ERA5-Land 2000-2020
# ─────────────────────────────────────────────────

ERA5_CLUSTER_BASELINES = {
    # cluster → {mese: {temp_avg, temp_std, rain_avg_mm, rain_std, wind_avg}}
    "Po_Valley": {
        1:  {"temp": 1.5,  "temp_std": 3.5, "rain": 2.1, "rain_std": 3.2, "wind": 2.1, "hum": 82},
        2:  {"temp": 3.8,  "temp_std": 3.8, "rain": 2.0, "rain_std": 2.9, "wind": 2.3, "hum": 78},
        3:  {"temp": 8.5,  "temp_std": 3.2, "rain": 2.8, "rain_std": 3.5, "wind": 2.8, "hum": 72},
        4:  {"temp": 13.2, "temp_std": 2.8, "rain": 3.5, "rain_std": 4.1, "wind": 2.6, "hum": 68},
        5:  {"temp": 17.8, "temp_std": 2.5, "rain": 4.2, "rain_std": 5.0, "wind": 2.4, "hum": 65},
        6:  {"temp": 22.1, "temp_std": 2.3, "rain": 3.8, "rain_std": 6.2, "wind": 2.2, "hum": 60},
        7:  {"temp": 24.8, "temp_std": 2.1, "rain": 2.9, "rain_std": 5.8, "wind": 2.0, "hum": 55},
        8:  {"temp": 24.2, "temp_std": 2.4, "rain": 3.1, "rain_std": 5.5, "wind": 2.1, "hum": 57},
        9:  {"temp": 19.5, "temp_std": 2.6, "rain": 3.9, "rain_std": 5.0, "wind": 2.3, "hum": 65},
        10: {"temp": 13.8, "temp_std": 2.9, "rain": 4.5, "rain_std": 5.8, "wind": 2.4, "hum": 74},
        11: {"temp": 7.2,  "temp_std": 3.2, "rain": 3.8, "rain_std": 4.5, "wind": 2.2, "hum": 80},
        12: {"temp": 2.8,  "temp_std": 3.6, "rain": 2.5, "rain_std": 3.5, "wind": 2.0, "hum": 83},
    },
    "NE_Industrial": {
        1:  {"temp": 2.1,  "temp_std": 3.8, "rain": 2.5, "rain_std": 3.5, "wind": 2.3, "hum": 80},
        2:  {"temp": 4.2,  "temp_std": 4.0, "rain": 2.3, "rain_std": 3.1, "wind": 2.5, "hum": 76},
        3:  {"temp": 9.0,  "temp_std": 3.5, "rain": 3.2, "rain_std": 4.0, "wind": 3.0, "hum": 70},
        4:  {"temp": 13.8, "temp_std": 3.0, "rain": 4.0, "rain_std": 5.0, "wind": 2.8, "hum": 66},
        5:  {"temp": 18.5, "temp_std": 2.8, "rain": 5.5, "rain_std": 6.5, "wind": 2.6, "hum": 62},
        6:  {"temp": 22.8, "temp_std": 2.5, "rain": 5.8, "rain_std": 8.0, "wind": 2.3, "hum": 58},
        7:  {"temp": 25.5, "temp_std": 2.2, "rain": 4.5, "rain_std": 7.5, "wind": 2.1, "hum": 52},
        8:  {"temp": 24.8, "temp_std": 2.4, "rain": 4.8, "rain_std": 7.2, "wind": 2.2, "hum": 54},
        9:  {"temp": 20.2, "temp_std": 2.7, "rain": 5.5, "rain_std": 6.5, "wind": 2.4, "hum": 62},
        10: {"temp": 14.5, "temp_std": 3.0, "rain": 6.0, "rain_std": 7.0, "wind": 2.5, "hum": 72},
        11: {"temp": 8.0,  "temp_std": 3.5, "rain": 5.0, "rain_std": 5.5, "wind": 2.3, "hum": 78},
        12: {"temp": 3.5,  "temp_std": 4.0, "rain": 3.0, "rain_std": 4.0, "wind": 2.1, "hum": 81},
    },
    "Metro_Hub": {
        1:  {"temp": 3.0,  "temp_std": 3.5, "rain": 1.8, "rain_std": 2.8, "wind": 2.0, "hum": 78},
        2:  {"temp": 5.0,  "temp_std": 3.8, "rain": 1.7, "rain_std": 2.5, "wind": 2.2, "hum": 74},
        3:  {"temp": 10.0, "temp_std": 3.2, "rain": 2.5, "rain_std": 3.2, "wind": 2.7, "hum": 68},
        4:  {"temp": 14.5, "temp_std": 2.8, "rain": 3.2, "rain_std": 4.0, "wind": 2.5, "hum": 64},
        5:  {"temp": 19.0, "temp_std": 2.6, "rain": 4.0, "rain_std": 5.2, "wind": 2.3, "hum": 60},
        6:  {"temp": 23.5, "temp_std": 2.4, "rain": 3.5, "rain_std": 6.5, "wind": 2.0, "hum": 55},
        7:  {"temp": 26.2, "temp_std": 2.0, "rain": 2.5, "rain_std": 5.8, "wind": 1.8, "hum": 50},
        8:  {"temp": 25.5, "temp_std": 2.2, "rain": 2.8, "rain_std": 5.5, "wind": 1.9, "hum": 52},
        9:  {"temp": 21.0, "temp_std": 2.5, "rain": 3.5, "rain_std": 5.0, "wind": 2.1, "hum": 60},
        10: {"temp": 15.0, "temp_std": 2.8, "rain": 4.0, "rain_std": 5.5, "wind": 2.2, "hum": 70},
        11: {"temp": 8.5,  "temp_std": 3.2, "rain": 3.5, "rain_std": 4.2, "wind": 2.0, "hum": 76},
        12: {"temp": 4.0,  "temp_std": 3.5, "rain": 2.2, "rain_std": 3.2, "wind": 1.8, "hum": 79},
    },
    "Alpine_Extreme": {
        1:  {"temp": -4.0, "temp_std": 4.5, "rain": 3.5, "rain_std": 4.5, "wind": 3.5, "hum": 75},
        2:  {"temp": -2.5, "temp_std": 4.8, "rain": 3.0, "rain_std": 4.0, "wind": 3.8, "hum": 70},
        3:  {"temp": 2.0,  "temp_std": 4.0, "rain": 4.5, "rain_std": 5.5, "wind": 4.0, "hum": 65},
        4:  {"temp": 7.0,  "temp_std": 3.5, "rain": 6.0, "rain_std": 7.0, "wind": 3.8, "hum": 60},
        5:  {"temp": 12.0, "temp_std": 3.0, "rain": 8.0, "rain_std": 9.0, "wind": 3.5, "hum": 58},
        6:  {"temp": 16.5, "temp_std": 2.8, "rain": 9.5, "rain_std": 11.0, "wind": 3.2, "hum": 55},
        7:  {"temp": 19.0, "temp_std": 2.5, "rain": 9.0, "rain_std": 10.5, "wind": 3.0, "hum": 52},
        8:  {"temp": 18.5, "temp_std": 2.7, "rain": 8.5, "rain_std": 10.0, "wind": 3.1, "hum": 54},
        9:  {"temp": 14.0, "temp_std": 3.0, "rain": 7.0, "rain_std": 8.5, "wind": 3.3, "hum": 60},
        10: {"temp": 8.0,  "temp_std": 3.5, "rain": 6.5, "rain_std": 8.0, "wind": 3.5, "hum": 68},
        11: {"temp": 1.5,  "temp_std": 4.0, "rain": 5.0, "rain_std": 6.0, "wind": 3.6, "hum": 73},
        12: {"temp": -3.0, "temp_std": 4.5, "rain": 4.0, "rain_std": 5.0, "wind": 3.4, "hum": 76},
    },
}

# Fallback per cluster non specificati
_DEFAULT_CLUSTER = "Po_Valley"

def _get_cluster_baseline(cluster: str, month: int) -> Dict:
    data = ERA5_CLUSTER_BASELINES.get(cluster, ERA5_CLUSTER_BASELINES[_DEFAULT_CLUSTER])
    return data.get(month, data[6])  # fallback a giugno se mese non trovato


# ─────────────────────────────────────────────────
# PROVINCE LOADER
# ─────────────────────────────────────────────────

def load_provinces() -> List[Dict]:
    """Carica le province dal JSON."""
    with open(PROVINCE_FILE) as f:
        return json.load(f)["province"]


# ─────────────────────────────────────────────────
# OWM FETCHER
# ─────────────────────────────────────────────────

class OWMFetcher:
    """
    Fetcher OpenWeatherMap per dati current + forecast 5gg.
    Usa One Call API 3.0 se disponibile, fallback a Current + Forecast.
    """

    BASE_URL = "https://api.openweathermap.org/data/2.5"
    ONECALL_URL = "https://api.openweathermap.org/data/3.0/onecall"

    def __init__(self, api_key: str, use_mock: bool = False):
        self.api_key = api_key
        self.use_mock = use_mock  # True in dev senza API key
        self._cache: Dict[str, Tuple[Dict, float]] = {}
        self.cache_ttl = 3600  # 1 ora

    def _cached_get(self, url: str, params: Dict) -> Optional[Dict]:
        """GET con cache TTL 1h per non sprecare chiamate API."""
        cache_key = f"{url}_{json.dumps(params, sort_keys=True)}"
        if cache_key in self._cache:
            data, ts = self._cache[cache_key]
            if time.time() - ts < self.cache_ttl:
                return data

        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            self._cache[cache_key] = (data, time.time())
            return data
        except requests.RequestException as e:
            logger.warning(f"OWM request failed for {url}: {e}")
            return None

    def fetch_current(self, lat: float, lon: float) -> Optional[Dict]:
        """Fetch dati correnti."""
        if self.use_mock:
            return self._mock_current(lat, lon)

        params = {
            "lat": lat, "lon": lon,
            "appid": self.api_key,
            "units": "metric",
            "lang": "it"
        }
        return self._cached_get(f"{self.BASE_URL}/weather", params)

    def fetch_forecast_72h(self, lat: float, lon: float) -> Optional[Dict]:
        """Fetch previsioni 72h (step 3h = 24 punti)."""
        if self.use_mock:
            return self._mock_forecast(lat, lon)

        params = {
            "lat": lat, "lon": lon,
            "appid": self.api_key,
            "units": "metric",
            "cnt": 24  # 24 × 3h = 72h
        }
        return self._cached_get(f"{self.BASE_URL}/forecast", params)

    def _mock_current(self, lat: float, lon: float) -> Dict:
        """Mock realistico per development senza API key."""
        import math, random
        month = datetime.now().month
        # Simula temperatura stagionale + rumore
        base_temp = 5 + 15 * math.sin((month - 3) * math.pi / 6)
        temp = base_temp + random.gauss(0, 3)

        # Simula evento: 30% probabilità di pioggia
        has_rain = random.random() < 0.3
        rain_1h = max(0, random.gauss(8, 5)) if has_rain else 0.0

        weather_code = 501 if rain_1h > 10 else (500 if has_rain else 800)

        return {
            "main": {
                "temp": round(temp, 1),
                "feels_like": round(temp - 2, 1),
                "humidity": random.randint(55, 85),
            },
            "rain": {"1h": round(rain_1h, 2)} if has_rain else {},
            "wind": {"speed": round(random.uniform(1, 8), 1)},
            "weather": [{"id": weather_code, "description": "pioggia moderata" if has_rain else "cielo sereno"}],
        }

    def _mock_forecast(self, lat: float, lon: float) -> Dict:
        """Mock forecast 72h."""
        import math, random
        month = datetime.now().month
        base_temp = 5 + 15 * math.sin((month - 3) * math.pi / 6)

        # Simula una perturbazione che arriva tra 24 e 48 ore
        peak_hour = random.randint(18, 40)  # ore da ora
        items = []
        for i in range(24):
            h = i * 3
            # Intensità pioggia gaussiana attorno al peak
            rain_intensity = max(0, random.gauss(0, 2))
            if abs(h - peak_hour) < 12:
                rain_intensity = max(0, random.gauss(12, 4))

            items.append({
                "dt": int(datetime.now().timestamp()) + h * 3600,
                "main": {
                    "temp": round(base_temp + random.gauss(0, 2), 1),
                    "humidity": random.randint(60, 90),
                },
                "rain": {"3h": round(rain_intensity, 2)} if rain_intensity > 0 else {},
                "wind": {"speed": round(random.uniform(2, 10), 1)},
                "weather": [{"id": 501 if rain_intensity > 5 else 800}],
            })

        return {"list": items}


# ─────────────────────────────────────────────────
# WEATHER SNAPSHOT BUILDER
# ─────────────────────────────────────────────────

def build_weather_snapshot(provincia: Dict, fetcher: OWMFetcher) -> WeatherSnapshot:
    """
    Costruisce uno WeatherSnapshot completo per una provincia.
    """
    snap = WeatherSnapshot(
        provincia=provincia["nome"],
        lat=provincia["lat"],
        lon=provincia["lon"]
    )

    # Dati correnti
    current = fetcher.fetch_current(provincia["lat"], provincia["lon"])
    if current:
        snap.temp_c = current.get("main", {}).get("temp")
        snap.feels_like_c = current.get("main", {}).get("feels_like")
        snap.humidity_pct = current.get("main", {}).get("humidity")
        snap.rain_1h_mm = current.get("rain", {}).get("1h", 0.0)
        wind = current.get("wind", {})
        snap.wind_speed_ms = wind.get("speed", 0.0)

        weather_list = current.get("weather", [{}])
        if weather_list:
            snap.weather_code = weather_list[0].get("id")
            snap.weather_desc = weather_list[0].get("description", "")
            snap.event_type = owm_code_to_event(snap.weather_code or 800)

    # Previsione 72h
    forecast = fetcher.fetch_forecast_72h(provincia["lat"], provincia["lon"])
    if forecast:
        snap.forecast_72h = forecast.get("list", [])
        # Calcola peak pioggia nelle prossime 72h
        rain_values = []
        for item in snap.forecast_72h:
            rain_3h = item.get("rain", {}).get("3h", 0.0)
            rain_values.append((rain_3h, item.get("dt", 0)))

        if rain_values:
            peak_rain, peak_dt = max(rain_values, key=lambda x: x[0])
            if peak_rain > 0:  # Solo se c'e' pioggia reale
                snap.peak_intensity = peak_rain
                hours_to_peak = (peak_dt - int(datetime.now().timestamp())) / 3600
                snap.peak_expected_in_hours = max(1, int(hours_to_peak))

    return snap


def build_historical_baseline(provincia: Dict) -> HistoricalBaseline:
    """
    Costruisce la baseline storica ERA5 per la provincia corrente.
    In produzione: query al CDS API con cdsapi.
    """
    month = datetime.now().month
    cluster = provincia.get("cluster", "Po_Valley")

    bl = HistoricalBaseline(provincia=provincia["nome"], month=month)
    era5_data = _get_cluster_baseline(cluster, month)

    bl.avg_temp_c = era5_data["temp"]
    bl.std_temp_c = era5_data["temp_std"]
    bl.avg_rain_mm_day = era5_data["rain"]
    bl.std_rain_mm_day = era5_data["rain_std"]
    bl.avg_wind_ms = era5_data["wind"]
    bl.std_wind_ms = era5_data["wind"] * 0.5  # stima std
    bl.avg_humidity_pct = era5_data["hum"]

    # Percentili approssimati (media + 1.65σ ≈ P95)
    bl.p95_rain_mm = bl.avg_rain_mm_day + 1.65 * bl.std_rain_mm_day
    bl.p95_temp_c = bl.avg_temp_c + 1.65 * bl.std_temp_c

    return bl
