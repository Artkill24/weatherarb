import hmac
import hashlib
#!/usr/bin/env python3
"""WeatherArb FastAPI Backend — Railway"""
import os, json, math, logging, secrets, hashlib, hmac
from datetime import datetime, timezone
from typing import Optional
import requests as req_lib
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ─── CONFIG ───────────────────────────────────────────────────────────────────
OWM_API_KEY          = os.getenv("OWM_API_KEY", "")
GEMINI_API_KEY       = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY         = os.getenv("GROQ_API_KEY", "")
SUPABASE_URL         = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY         = os.getenv("SUPABASE_ANON_KEY", "")
RESEND_API_KEY       = os.getenv("RESEND_API_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
USE_MOCK             = os.getenv("USE_MOCK", "false").lower() == "true"
ADMIN_SECRET         = "weatherarb2026"
ADMIN_SECRET_FULL    = "weatherarb2026admin"

app = FastAPI(title="WeatherArb API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ─── IN-MEMORY CACHE ──────────────────────────────────────────────────────────
_cache = {}          # slug -> weather data
_top_cache = {}      # "top" -> list
_last_refresh = None

# ─── PROVINCE COORDS ──────────────────────────────────────────────────────────
# Comuni italiani per geolocalizzazione precisa
_COMUNI = []
def load_comuni():
    global _COMUNI
    try:
        import json, pathlib
        p = pathlib.Path(__file__).parent.parent / "data" / "comuni_italy.json"
        if p.exists():
            _COMUNI = json.loads(p.read_text())
            logger.info(f"Loaded {len(_COMUNI)} comuni")
    except Exception as e:
        logger.warning(f"Comuni load error: {e}")

def load_provinces():
    try:
        with open("data/province_coords.json") as f:
            raw = json.load(f)
        return raw["province"] if "province" in raw else raw
    except Exception as e:
        logger.error(f"Province load error: {e}")
        return []

PROVINCES = load_provinces()
logger.info(f"Loaded {len(PROVINCES)} provinces")

# ─── OPEN-METEO BATCH FETCHER (free, no key, 1000 cities/call) ───────────────
_weather_cache = {}  # lat,lon -> weather data

def fetch_all_weather_batch(provinces):
    """Fetch weather for all provinces using Open-Meteo batch API"""
    global _weather_cache
    _weather_cache = {}
    batch_size = 100
    
    for i in range(0, len(provinces), batch_size):
        batch = provinces[i:i+batch_size]
        lats = ",".join(str(p["lat"]) for p in batch)
        lons = ",".join(str(p["lon"]) for p in batch)
        try:
            url = (f"https://api.open-meteo.com/v1/forecast"
                   f"?latitude={lats}&longitude={lons}"
                   f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation,weather_code,cloud_cover"
                   f"&wind_speed_unit=ms&timezone=auto&forecast_days=1")
            r = req_lib.get(url, timeout=30)
            data = r.json()
            # Handle both single and multiple responses
            if isinstance(data, dict): data = [data]
            for j, d in enumerate(data):
                p = batch[j]
                key = (round(p["lat"],4), round(p["lon"],4))
                cur = d.get("current", {})
                temp = cur.get("temperature_2m", 15.0)
                hum = cur.get("relative_humidity_2m", 60)
                wind_ms = cur.get("wind_speed_10m", 0)
                _weather_cache[key] = {
                    "temperature_c": temp,
                    "humidity_pct": hum,
                    "wind_ms": wind_ms,
                    "wind_kmh": round(wind_ms * 3.6, 1),
                    "precipitation_mm": cur.get("precipitation", 0) or 0,
                    "cloud_cover_pct": cur.get("cloud_cover", 0) or 0,
                    "weather_code": cur.get("weather_code", 0) or 0,
                    "description": "",
                }
            logger.info(f"Open-Meteo batch {i//batch_size+1}: fetched {len(data)} cities")
        except Exception as e:
            logger.error(f"Open-Meteo batch error: {e}")
        import time; time.sleep(0.5)  # avoid rate limiting

def fetch_owm(lat, lon):
    """Lookup from pre-fetched batch cache"""
    key = (round(lat,4), round(lon,4))
    return _weather_cache.get(key)

# ─── Z-SCORE & HDD/CDD ────────────────────────────────────────────────────────
HISTORICAL_AVG = {
    1: 5.0, 2: 6.0, 3: 9.0, 4: 13.0, 5: 17.0, 6: 22.0,
    7: 25.0, 8: 24.0, 9: 20.0, 10: 15.0, 11: 10.0, 12: 6.0
}
HISTORICAL_STD = {
    1: 3.5, 2: 3.5, 3: 4.0, 4: 4.0, 5: 3.5, 6: 3.0,
    7: 2.5, 8: 2.5, 9: 3.0, 10: 3.5, 11: 3.5, 12: 3.0
}

def calc_z_score(temp_c, month):
    avg = HISTORICAL_AVG.get(month, 15.0)
    std = HISTORICAL_STD.get(month, 3.5)
    z = (temp_c - avg) / std
    # Floor at 1.5 to avoid near-zero z-scores
    if abs(z) < 1.5: z = math.copysign(1.5, z) if abs(z) > 0.3 else z
    return round(z, 2)

def calc_hdd_cdd(temp_c, month):
    BASE = 18.0
    hdd = max(0, BASE - temp_c)
    cdd = max(0, temp_c - BASE)
    # Historical baseline HDD
    hist_temp = HISTORICAL_AVG.get(month, 15.0)
    hdd_baseline = max(0, BASE - hist_temp)
    cdd_baseline = max(0, hist_temp - BASE)
    hdd_delta = round(hdd - hdd_baseline, 2)
    cdd_delta = round(cdd - cdd_baseline, 2)
    return round(hdd, 2), round(cdd, 2), round(hdd_baseline, 2), round(cdd_baseline, 2), hdd_delta, cdd_delta

def anomaly_level(z):
    az = abs(z)
    if az >= 3.0: return "CRITICAL"
    if az >= 2.0: return "EXTREME"
    if az >= 1.0: return "UNUSUAL"
    return "NORMAL"

def anomaly_label(z, event_type, lang="it"):
    level = anomaly_level(z)
    sign = "+" if z >= 0 else ""
    labels = {
        "it": {
            "CRITICAL": f"Anomalia CRITICA ({sign}{z}σ) — evento statisticamente raro",
            "EXTREME": f"Anomalia ESTREMA ({sign}{z}σ) — deviazione significativa",
            "UNUSUAL": f"Condizioni INSOLITE ({sign}{z}σ) — attenzione consigliata",
            "NORMAL": f"Condizioni nella norma ({sign}{z}σ)",
        },
        "en": {
            "CRITICAL": f"CRITICAL anomaly ({sign}{z}σ) — statistically rare event",
            "EXTREME": f"EXTREME anomaly ({sign}{z}σ) — significant deviation",
            "UNUSUAL": f"UNUSUAL conditions ({sign}{z}σ) — attention advised",
            "NORMAL": f"Normal conditions ({sign}{z}σ)",
        },
        "de": {
            "CRITICAL": f"KRITISCHE Anomalie ({sign}{z}σ) — statistisch seltenes Ereignis",
            "EXTREME": f"EXTREME Anomalie ({sign}{z}σ) — signifikante Abweichung",
            "UNUSUAL": f"UNGEWOEHNLICHE Bedingungen ({sign}{z}σ)",
            "NORMAL": f"Normale Bedingungen ({sign}{z}σ)",
        }
    }
    lang_labels = labels.get(lang, labels["en"])
    return lang_labels.get(level, lang_labels["NORMAL"])

def calc_score(z):
    return round(min(abs(z) / 3.0 * 10.0, 10.0), 2)

def event_type(z, wind_kmh=0, hum=50):
    if wind_kmh and wind_kmh > 60: return "wind_storm"
    if hum and hum > 85: return "heavy_rain"
    if z > 0: return "heat_wave"
    return "cold_snap"

# ─── REFRESH ENGINE ───────────────────────────────────────────────────────────
def refresh_all():
    global _last_refresh
    logger.info(f"Refreshing {len(PROVINCES)} provinces...")
    now = datetime.now(timezone.utc)
    month = now.month
    count = 0
    top_list = []

    # Fetch weather in small batches, saving progress
    logger.info("Fetching weather incrementally from Open-Meteo...")
    # Rotating cache: load different 500-city group each refresh
    import time
    batch_size = 750
    total = len(PROVINCES)
    num_groups = (total + batch_size - 1) // batch_size
    group_idx = int(time.time() / 3600) % num_groups  # rotates every hour
    start = group_idx * batch_size
    end = min(start + batch_size, total)
    logger.info(f"Loading group {group_idx+1}/{num_groups} ({start}-{end} of {total})")
    fetch_all_weather_batch(PROVINCES[start:end])
    logger.info(f"Weather cache loaded: {len(_weather_cache)} cities")

    for p in PROVINCES:
        slug = p["nome"].lower().replace(" ", "-").replace("'", "")
        # Remove non-ascii
        import unicodedata, re
        slug = unicodedata.normalize("NFKD", slug).encode("ascii","ignore").decode("ascii")
        slug = re.sub(r"[^\w-]", "", slug)

        owm = fetch_owm(p["lat"], p["lon"])
        if not owm:
            continue

        temp = owm["temperature_c"]
        hum = owm["humidity_pct"]
        wind_kmh = owm["wind_kmh"]

        z = calc_z_score(temp, month)
        hdd, cdd, hdd_bl, cdd_bl, hdd_delta, cdd_delta = calc_hdd_cdd(temp, month)
        level = anomaly_level(z)
        score = calc_score(z)
        ev = event_type(z, wind_kmh, hum)
        label = anomaly_label(z, ev)

        hist_avg = HISTORICAL_AVG.get(month, 15.0)

        data = {
            "location": p["nome"],
            "country_code": _cc(p.get("country", "Italy")),
            "lat": p.get("lat"), "lon": p.get("lon"),
            "weather": {
                "event_type": ev,
                "severity": level,
                "anomaly_level": level,
                "anomaly_label": label,
                "z_score": z,
                "temperature_c": round(temp, 2),
                "historical_avg_c": hist_avg,
                "humidity_pct": hum,
                "wind_kmh": wind_kmh,
                "wind_ms": owm["wind_ms"],
                "hdd": hdd, "cdd": cdd,
                "hdd_baseline": hdd_bl, "cdd_baseline": cdd_bl,
                "hdd_delta": hdd_delta, "cdd_delta": cdd_delta,
            },
            "signal": {"score": score, "level": level},
            "timestamp": now.isoformat()
        }
        _cache[slug] = data
        count += 1

        top_list.append({
            "location": p["nome"],
            "country_code": _cc(p.get("country","Italy")),
            "lat": p.get("lat"), "lon": p.get("lon"),
            "z_score": z, "score": score,
            "anomaly_level": level,
            "vertical": ev,
            "event_type": ev,
            "hdd": hdd, "cdd": cdd,
            "hdd_delta": hdd_delta,
            "humidity_pct": hum,
            "wind_kmh": wind_kmh,
        })

    top_list.sort(key=lambda x: -x["score"])
    _top_cache["top"] = top_list
    # Cache space weather
    try:
        r_sw = req_lib.get("https://services.swpc.noaa.gov/json/planetary_k_index_1m.json", timeout=10)
        kp_data = r_sw.json()
        recent = [x for x in kp_data[-30:] if x.get("kp_index") is not None]
        kp = sum(x["kp_index"] for x in recent) / len(recent) if recent else 0
        # Solar flare real data
        flare_class = "A"
        try:
            r_flare = req_lib.get("https://services.swpc.noaa.gov/json/goes/primary/xrays-7-day.json", timeout=8)
            xray = r_flare.json()
            if xray:
                flux = max((x.get("flux",0) or 0) for x in xray[-60:])
                if flux >= 1e-4: flare_class = "X"
                elif flux >= 1e-5: flare_class = "M"
                elif flux >= 1e-6: flare_class = "C"
                elif flux >= 1e-7: flare_class = "B"
                else: flare_class = "A"
        except: pass
        # NOAA alerts count
        alerts_count = 0
        try:
            r_alerts = req_lib.get("https://api.weather.gov/alerts/active?status=actual&message_type=alert&limit=50", timeout=8)
            alerts_data = r_alerts.json()
            alerts_count = len(alerts_data.get("features", []))
        except: pass
        _top_cache["space_weather"] = {
            "kp_current": round(kp, 2),
            "flare_class": flare_class,
            "solar_flux": 0,
            "noaa_alerts_us": alerts_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except:
        pass
    _last_refresh = now
    logger.info(f"Refresh complete: {count} provinces cached")
    # Save to Supabase for persistence
    if top_list:
        sb_data = []
        for city in top_list:
            import unicodedata, re
            slug = unicodedata.normalize("NFKD", city["location"].lower()).encode("ascii","ignore").decode("ascii")
            slug = re.sub(r"[^\w-]","", slug.replace(" ","-"))
            sb_data.append({
                "slug": slug,
                "location": city.get("location",""),
                "country_code": city.get("country_code",""),
                "lat": city.get("lat",0), "lon": city.get("lon",0),
                "z_score": city.get("z_score",0), "score": city.get("score",0),
                "anomaly_level": city.get("anomaly_level","NORMAL"),
                "event_type": city.get("event_type","normal"),
                "temperature_c": city.get("temperature_c"),
                "humidity_pct": city.get("humidity_pct"),
                "wind_kmh": city.get("wind_kmh"),
                "hdd": city.get("hdd"), "cdd": city.get("cdd"),
                "hdd_delta": city.get("hdd_delta"),
                "precipitation_mm": city.get("precipitation_mm",0),
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
        save_weather_cache_supabase(sb_data)

def _cc(country):
    m = {"Italy":"it","Germany":"de","France":"fr","Spain":"es","United Kingdom":"gb",
         "Sweden":"se","Netherlands":"nl","Poland":"pl","Austria":"at","Switzerland":"ch",
         "Belgium":"be","Portugal":"pt","Denmark":"dk","Norway":"no","Greece":"gr",
         "Croatia":"hr","Czech Republic":"cz","Hungary":"hu","Romania":"ro","Finland":"fi",
         "Slovenia":"si","Slovakia":"sk","Serbia":"rs"}
    m.update({'USA': 'us', 'Canada': 'ca', 'Brazil': 'br', 'Argentina': 'ar', 'Mexico': 'mx', 'Colombia': 'co', 'Chile': 'cl', 'Australia': 'au', 'New Zealand': 'nz', 'Japan': 'jp', 'South Korea': 'kr', 'China': 'cn', 'India': 'in', 'Bangladesh': 'bd', 'Pakistan': 'pk', 'Sri Lanka': 'lk', 'Nepal': 'np', 'Indonesia': 'id', 'Philippines': 'ph', 'Vietnam': 'vn', 'Thailand': 'th', 'Malaysia': 'my', 'Singapore': 'sg', 'Taiwan': 'tw', 'Mongolia': 'mn', 'Iran': 'ir', 'Turkey': 'tr', 'Israel': 'il', 'UAE': 'ae', 'Saudi Arabia': 'sa', 'Egypt': 'eg', 'Morocco': 'ma', 'Nigeria': 'ng', 'Kenya': 'ke', 'South Africa': 'za'})
    return m.get(country, "eu")

# ─── SUPABASE HELPERS ─────────────────────────────────────────────────────────
def save_weather_cache_supabase(cities_data: list):
    """Save weather cache to Supabase for persistence"""
    if not SUPABASE_URL or not SUPABASE_KEY: return
    try:
        url = f"{SUPABASE_URL}/rest/v1/weather_cache"
        headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                   "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"}
        batch_size = 200
        for i in range(0, len(cities_data), batch_size):
            batch = cities_data[i:i+batch_size]
            req_lib.post(url, json=batch, headers=headers, timeout=15)
        logger.info(f"Saved {len(cities_data)} cities to Supabase cache")
    except Exception as e:
        logger.error(f"Supabase cache save error: {e}")

def load_weather_cache_supabase(slug: str) -> dict:
    """Load single city from Supabase cache"""
    if not SUPABASE_URL or not SUPABASE_KEY: return {}
    try:
        url = f"{SUPABASE_URL}/rest/v1/weather_cache"
        headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
        r = req_lib.get(url, headers=headers,
                        params={"slug": f"eq.{slug}", "select": "*", "limit": "1"}, timeout=8)
        data = r.json()
        if data and isinstance(data, list) and len(data) > 0:
            d = data[0]
            return {
                "location": d.get("location",""),
                "country_code": d.get("country_code",""),
                "lat": d.get("lat",0), "lon": d.get("lon",0),
                "z_score": d.get("z_score",0), "score": d.get("score",0),
                "anomaly_level": d.get("anomaly_level","NORMAL"),
                "event_type": d.get("event_type","normal"),
                "temperature_c": d.get("temperature_c"), "humidity_pct": d.get("humidity_pct"),
                "wind_kmh": d.get("wind_kmh"), "hdd": d.get("hdd"), "cdd": d.get("cdd"),
                "hdd_delta": d.get("hdd_delta"), "precipitation_mm": d.get("precipitation_mm"),
            }
    except Exception as e:
        logger.error(f"Supabase cache load error: {e}")
    return {}

def load_top_from_supabase(limit=500) -> list:
    """Load top anomalies from Supabase"""
    if not SUPABASE_URL or not SUPABASE_KEY: return []
    try:
        url = f"{SUPABASE_URL}/rest/v1/weather_cache"
        headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
        r = req_lib.get(url, headers=headers,
                        params={"select": "*", "order": "score.desc", "limit": str(limit)}, timeout=10)
        return r.json() if r.json() else []
    except: return []


def sb(method, table, data=None, params=None):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    try:
        if method == "GET":
            r = req_lib.get(url, headers=headers, params=params, timeout=10)
        elif method == "POST":
            r = req_lib.post(url, headers=headers, json=data, timeout=10)
        elif method == "PATCH":
            r = req_lib.patch(url, headers=headers, json=data, params=params, timeout=10)
        return r.json() if r.content else []
    except Exception as e:
        logger.error(f"Supabase {method} {table}: {e}")
        return []

# ─── API ENDPOINTS ────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"service": "WeatherArb API", "version": "2.0.0", "provinces": len(PROVINCES)}

@app.get("/health")
def health():
    return {"status": "ok", "provinces": len(PROVINCES), "cached": len(_cache)}

@app.post("/pulse/refresh")
async def trigger_refresh(background_tasks: BackgroundTasks):
    background_tasks.add_task(refresh_all)
    return {"status": "refresh_started", "province_count": len(PROVINCES),
            "message": "Il refresh è in corso. Interroga /pulse/{provincia} tra 30 secondi."}

@app.post("/admin/clear-cache")
def clear_cache():
    _cache.clear()
    _top_cache.clear()
    return {"status": "cache_cleared", "timestamp": datetime.now(timezone.utc).isoformat()}
@app.get("/api/v1/pulse/nearby")
def get_nearby(lat: float, lon: float, key: Optional[str] = None):
    if key:
        _check_and_increment_key(key)
    import math, unicodedata, re
    # Use all PROVINCES for precise geolocation, not just cached top
    all_nodes = PROVINCES if PROVINCES else _top_cache.get("top", [])
    if not all_nodes:
        return {"error": "No data cached yet"}
    nearest_p = min(all_nodes, key=lambda n: math.sqrt((n["lat"]-lat)**2 + (n["lon"]-lon)**2))
    # Get weather data from cache
    top = _top_cache.get("top", [])
    nearest = next((n for n in top if n["location"]==nearest_p["nome"]), None)
    if not nearest:
        nearest = {"location": nearest_p["nome"], "country_code": _cc(nearest_p.get("country","Italy")),
                   "lat": nearest_p["lat"], "lon": nearest_p["lon"],
                   "z_score": 0, "anomaly_level": "NORMAL", "event_type": "normal", "score": 0}
    dist = round(math.sqrt((nearest["lat"]-lat)**2 + (nearest["lon"]-lon)**2) * 111, 1)
    slug = nearest["location"].lower().replace(" ", "-").replace("'", "")
    slug = unicodedata.normalize("NFKD", slug).encode("ascii","ignore").decode("ascii")
    slug = re.sub(r"[^\w-]", "", slug)
    data = _cache.get(slug, {})
    weather = data.get("weather", {})
    # Trova comune più vicino se disponibile
    comune_name = nearest["location"]
    comune_dist = dist
    if _COMUNI:
        nc = min(_COMUNI, key=lambda c: math.sqrt((c["lat"]-lat)**2 + (c["lon"]-lon)**2))
        nc_dist = round(math.sqrt((nc["lat"]-lat)**2 + (nc["lon"]-lon)**2) * 111, 1)
        if nc_dist < dist:
            comune_name = nc["nome"]
            comune_dist = nc_dist
    return {"province": nearest["location"], "comune": comune_name, "distance_km": comune_dist, "country_code": nearest["country_code"], "lat": nearest["lat"], "lon": nearest["lon"], "z_score": nearest["z_score"], "anomaly_level": nearest["anomaly_level"], "event_type": nearest["event_type"], "score": nearest["score"], "temperature_c": weather.get("temperature_c"), "precipitation": weather.get("precipitation", 0), "humidity_pct": nearest.get("humidity_pct"), "wind_kmh": nearest.get("wind_kmh")}


@app.get("/api/v1/pulse/{slug}")
def get_pulse(slug: str, key: Optional[str] = None):
    # Rate limit check if key provided
    if key:
        _check_and_increment_key(key)

    # Normalize slug
    import unicodedata, re
    s = unicodedata.normalize("NFKD", slug.lower()).encode("ascii","ignore").decode("ascii")
    s = re.sub(r"[^\w-]","", s.replace(" ","-"))

    if s not in _cache:
        # Try refresh for this specific province
        for p in PROVINCES:
            pslug = unicodedata.normalize("NFKD", p["nome"].lower()).encode("ascii","ignore").decode("ascii")
            pslug = re.sub(r"[^\w-]","", pslug.replace(" ","-"))
            if pslug == s:
                owm = fetch_owm(p["lat"], p["lon"])
                if owm:
                    month = datetime.now().month
                    temp = owm["temperature_c"]
                    z = calc_z_score(temp, month)
                    hdd, cdd, hdd_bl, cdd_bl, hdd_delta, cdd_delta = calc_hdd_cdd(temp, month)
                    level = anomaly_level(z)
                    score = calc_score(z)
                    ev = event_type(z, owm["wind_kmh"], owm["humidity_pct"])
                    _cache[s] = {
                        "location": p["nome"],
                        "country_code": _cc(p.get("country","Italy")),
                        "lat": p["lat"], "lon": p["lon"],
                        "weather": {
                            "event_type": ev, "severity": level,
                            "anomaly_level": level,
                            "anomaly_label": anomaly_label(z, ev),
                            "z_score": z,
                            "temperature_c": round(temp, 2),
                            "historical_avg_c": HISTORICAL_AVG.get(month, 15.0),
                            "humidity_pct": owm["humidity_pct"],
                            "wind_kmh": owm["wind_kmh"],
                            "wind_ms": owm["wind_ms"],
                            "hdd": hdd, "cdd": cdd,
                            "hdd_baseline": hdd_bl, "cdd_baseline": cdd_bl,
                            "hdd_delta": hdd_delta, "cdd_delta": cdd_delta,
                        },
                        "signal": {"score": score, "level": level},
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                break

    if s not in _cache:
        raise HTTPException(status_code=404, detail=f"Province '{slug}' not found or not yet cached")
    return _cache[s]

@app.get("/api/v1/europe/top")
def get_top(limit: int = 10, key: Optional[str] = None):
    if key:
        _check_and_increment_key(key)
    top = _top_cache.get("top", [])
    sw = _top_cache.get("space_weather", {})
    return {"count": len(top), "reports": top[:min(limit, 500)], "data": top[:min(limit, 500)], "space_weather": sw}

@app.get("/api/v1/pulse/nearby")
def get_nearby(lat: float, lon: float, key: Optional[str] = None):
    if key:
        _check_and_increment_key(key)
    import math, unicodedata, re
    # Use all PROVINCES for precise geolocation, not just cached top
    all_nodes = PROVINCES if PROVINCES else _top_cache.get("top", [])
    if not all_nodes:
        return {"error": "No data cached yet"}
    nearest_p = min(all_nodes, key=lambda n: math.sqrt((n["lat"]-lat)**2 + (n["lon"]-lon)**2))
    # Get weather data from cache
    top = _top_cache.get("top", [])
    nearest = next((n for n in top if n["location"]==nearest_p["nome"]), None)
    if not nearest:
        nearest = {"location": nearest_p["nome"], "country_code": _cc(nearest_p.get("country","Italy")),
                   "lat": nearest_p["lat"], "lon": nearest_p["lon"],
                   "z_score": 0, "anomaly_level": "NORMAL", "event_type": "normal", "score": 0}
    dist = round(math.sqrt((nearest["lat"]-lat)**2 + (nearest["lon"]-lon)**2) * 111, 1)
    slug = nearest["location"].lower().replace(" ", "-").replace("'", "")
    slug = unicodedata.normalize("NFKD", slug).encode("ascii","ignore").decode("ascii")
    slug = re.sub(r"[^\w-]", "", slug)
    data = _cache.get(slug, {})
    weather = data.get("weather", {})
    # Trova comune più vicino se disponibile
    comune_name = nearest["location"]
    comune_dist = dist
    if _COMUNI:
        nc = min(_COMUNI, key=lambda c: math.sqrt((c["lat"]-lat)**2 + (c["lon"]-lon)**2))
        nc_dist = round(math.sqrt((nc["lat"]-lat)**2 + (nc["lon"]-lon)**2) * 111, 1)
        if nc_dist < dist:
            comune_name = nc["nome"]
            comune_dist = nc_dist
    return {"province": nearest["location"], "comune": comune_name, "distance_km": comune_dist, "country_code": nearest["country_code"], "lat": nearest["lat"], "lon": nearest["lon"], "z_score": nearest["z_score"], "anomaly_level": nearest["anomaly_level"], "event_type": nearest["event_type"], "score": nearest["score"], "temperature_c": weather.get("temperature_c"), "precipitation": weather.get("precipitation", 0), "humidity_pct": nearest.get("humidity_pct"), "wind_kmh": nearest.get("wind_kmh")}

# ─── NEWSLETTER ───────────────────────────────────────────────────────────────
@app.post("/api/newsletter/subscribe")
def newsletter_subscribe(email: str, city: str = "Europa", country_code: str = "it"):
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email")
    existing = sb("GET", "newsletter_subscribers", params={"email": f"eq.{email}", "select": "email"})
    if existing:
        return {"status": "already_subscribed", "email": email}
    sb("POST", "newsletter_subscribers", data={
        "email": email, "city": city, "country_code": country_code,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    # Welcome email
    if RESEND_API_KEY:
        try:
            req_lib.post("https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
                json={
                    "from": "WeatherArb <alerts@weatherarb.com>",
                    "to": [email],
                    "subject": "Benvenuto in WeatherArb Intelligence",
                    "html": f"<h2>Benvenuto in WeatherArb!</h2><p>Riceverai anomalie meteo, Z-Score e HDD/CDD per {city} ogni settimana.</p><p><a href='https://weatherarb.com'>weatherarb.com</a></p>"
                }, timeout=10)
        except Exception as e:
            logger.error(f"Welcome email error: {e}")
    return {"status": "subscribed", "email": email}

@app.get("/api/newsletter/list")
def newsletter_list(secret: str = ""):
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    result = sb("GET", "newsletter_subscribers", params={"select": "email,city,country_code,created_at", "order": "created_at.desc"})
    return {"count": len(result), "subscribers": result}

# ─── API KEY MANAGEMENT ───────────────────────────────────────────────────────
def generate_api_key():
    return f"wa_{secrets.token_hex(24)}"

def _check_and_increment_key(key: str):
    """Validate API key and increment call counter."""
    if not key.startswith("wa_"):
        raise HTTPException(status_code=401, detail="Invalid API key")
    result = sb("GET", "api_keys", params={"api_key": f"eq.{key}", "select": "active,calls_today,calls_limit,email"})
    if not result:
        raise HTTPException(status_code=401, detail="API key not found")
    info = result[0]
    if not info.get("active"):
        raise HTTPException(status_code=403, detail="API key inactive")
    if info.get("calls_today", 0) >= info.get("calls_limit", 10000):
        raise HTTPException(status_code=429, detail="Daily limit reached")
    # Increment counter
    sb("PATCH", "api_keys",
        data={"calls_today": info["calls_today"] + 1, "last_used": datetime.now(timezone.utc).isoformat()},
        params={"api_key": f"eq.{key}"}
    )

@app.get("/api/me")
def get_my_info(key: str = ""):
    """Dashboard: get API key info."""
    if not key or not key.startswith("wa_"):
        raise HTTPException(status_code=401, detail="Invalid API key")
    result = sb("GET", "api_keys", params={
        "api_key": f"eq.{key}",
        "select": "email,plan,calls_today,calls_limit,active,created_at,last_used"
    })
    if not result:
        raise HTTPException(status_code=404, detail="API key not found")
    info = result[0]
    if not info.get("active"):
        raise HTTPException(status_code=403, detail="API key inactive — check subscription")
    return {
        "email": info["email"],
        "plan": info["plan"],
        "calls_today": info.get("calls_today", 0),
        "calls_limit": info.get("calls_limit", 10000),
        "calls_remaining": info.get("calls_limit", 10000) - info.get("calls_today", 0),
        "active": info["active"],
        "member_since": (info.get("created_at") or "")[:10],
        "last_used": (info.get("last_used") or "mai")[:10]
    }

@app.post("/api/generate-key-manual")
async def generate_key_manual(request: Request):
    """Manual key generation for testing."""
    data = await request.json()
    if data.get("secret") != ADMIN_SECRET_FULL or not data.get("email"):
        raise HTTPException(status_code=403, detail="Forbidden")
    email = data["email"]
    existing = sb("GET", "api_keys", params={"email": f"eq.{email}"})
    if existing:
        return {"api_key": existing[0]["api_key"], "status": "existing"}
    api_key = generate_api_key()
    sb("POST", "api_keys", data={
        "email": email, "api_key": api_key,
        "plan": "professional", "calls_today": 0,
        "calls_limit": 10000, "active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    return {"api_key": api_key, "status": "created"}

@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe payment events."""
    body = await request.body()
    sig = request.headers.get("stripe-signature", "")

    # Verify signature
    if STRIPE_WEBHOOK_SECRET and sig:
        try:
            parts = {p.split("=")[0]: p.split("=")[1] for p in sig.split(",") if "=" in p}
            ts = parts.get("t", "")
            payload = f"{ts}.{body.decode()}"
            expected = hmac.new(STRIPE_WEBHOOK_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
            received = parts.get("v1", "")
            if not hmac.compare_digest(expected, received):
                raise HTTPException(status_code=400, detail="Invalid Stripe signature")
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Webhook sig error: {e}")

    try:
        event = json.loads(body)
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type_str = event.get("type", "")
    logger.info(f"Stripe event: {event_type_str}")

    if event_type_str in ("checkout.session.completed", "customer.subscription.created", "invoice.paid"):
        obj = event.get("data", {}).get("object", {})
        email = (obj.get("customer_email") or
                 obj.get("customer_details", {}).get("email") or "")
        customer_id = obj.get("customer", "")

        if email:
            existing = sb("GET", "api_keys", params={"email": f"eq.{email}", "select": "api_key,active"})
            if existing:
                sb("PATCH", "api_keys",
                    data={"active": True, "stripe_customer_id": customer_id},
                    params={"email": f"eq.{email}"})
                api_key = existing[0]["api_key"]
            else:
                api_key = generate_api_key()
                sb("POST", "api_keys", data={
                    "email": email, "api_key": api_key,
                    "plan": "professional", "calls_today": 0,
                    "calls_limit": 10000, "active": True,
                    "stripe_customer_id": customer_id,
                    "created_at": datetime.now(timezone.utc).isoformat()
                })

            logger.info(f"API key ready for {email}")

            # Send welcome email
            if RESEND_API_KEY:
                try:
                    req_lib.post("https://api.resend.com/emails",
                        headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
                        json={
                            "from": "WeatherArb <alerts@weatherarb.com>",
                            "to": [email],
                            "subject": "La tua API Key WeatherArb Professional",
                            "html": f"""<div style="font-family:-apple-system,sans-serif;max-width:580px;margin:0 auto;padding:32px;background:#040608;color:#c8d6e5">
<h1 style="color:#fff;margin-bottom:8px">WeatherArb Professional ✅</h1>
<p style="color:#4a5568;margin-bottom:24px">Benvenuto! Il tuo accesso API è attivo.</p>
<div style="background:#0a0d12;border:1px solid #141920;border-radius:10px;padding:20px;margin-bottom:24px">
  <p style="font-size:11px;text-transform:uppercase;color:#4a5568;margin-bottom:8px">La tua API Key</p>
  <code style="font-size:15px;font-weight:700;color:#3b82f6;word-break:break-all">{api_key}</code>
</div>
<p style="color:#4a5568;margin-bottom:8px"><strong style="color:#c8d6e5">Uso rapido:</strong></p>
<pre style="background:#0a0d12;border:1px solid #141920;border-radius:8px;padding:14px;font-size:12px">curl "https://api.weatherarb.com/api/v1/pulse/milano?key={api_key}"</pre>
<p style="margin-top:20px"><a href="https://weatherarb.com/dashboard/" style="color:#3b82f6">Dashboard →</a> &nbsp;|&nbsp; <a href="https://weatherarb.com/api.html" style="color:#3b82f6">Documentazione →</a></p>
<p style="font-size:11px;color:#4a5568;margin-top:24px;border-top:1px solid #141920;padding-top:16px">WeatherArb · alerts@weatherarb.com</p>
</div>"""
                        }, timeout=10)
                except Exception as e:
                    logger.error(f"Welcome email error: {e}")

    elif event_type_str == "customer.subscription.deleted":
        obj = event.get("data", {}).get("object", {})
        customer_id = obj.get("customer", "")
        if customer_id:
            sb("PATCH", "api_keys",
                data={"active": False},
                params={"stripe_customer_id": f"eq.{customer_id}"})
            logger.info(f"Key deactivated for customer {customer_id}")

    return {"status": "ok"}

# ─── SPACE WEATHER PROXY ──────────────────────────────────────────────────────
@app.get("/api/space-weather")
def space_weather(key: Optional[str] = None):
    """Return latest space weather data."""
    if key:
        _check_and_increment_key(key)
    try:
        r = req_lib.get("https://services.swpc.noaa.gov/json/planetary_k_index_1m.json", timeout=10)
        kp_data = r.json()
        recent = [x for x in kp_data[-30:] if x.get("kp_index") is not None]
        kp = sum(x["kp_index"] for x in recent) / len(recent) if recent else 0

        r2 = req_lib.get("https://services.swpc.noaa.gov/json/goes/primary/xrays-6-hour.json", timeout=10)
        xray = r2.json()
        flux = max((x["flux"] for x in xray[-10:] if x.get("flux")), default=0)
        if flux >= 1e-5: flare = "X"
        elif flux >= 1e-6: flare = "M"
        elif flux >= 1e-7: flare = "C"
        elif flux >= 1e-8: flare = "B"
        else: flare = "A"

        return {
            "kp_current": round(kp, 2),
            "flare_class": flare,
            "solar_flux": flux,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {"error": str(e), "kp_current": 0, "flare_class": "A"}

# ─── STARTUP ──────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    from fastapi.concurrency import run_in_threadpool
    logger.info("WeatherArb API starting...")
    await run_in_threadpool(refresh_all)
    load_comuni()

# ─── USER ALERTS ──────────────────────────────────────────────────────────────
@app.post("/api/alerts/subscribe")
async def alert_subscribe(request: Request):
    data = await request.json()
    key = data.get("api_key", "")
    city = data.get("city", "")
    country_code = data.get("country_code", "it")
    threshold = float(data.get("threshold_zscore", 2.0))
    if not key or not city:
        raise HTTPException(status_code=400, detail="api_key and city required")
    key_data = sb("GET", "api_keys", params={"api_key": f"eq.{key}", "select": "email,active"})
    if not key_data or not key_data[0].get("active"):
        raise HTTPException(status_code=403, detail="Invalid or inactive API key")
    email = key_data[0]["email"]
    existing = sb("GET", "user_alerts", params={"api_key": f"eq.{key}", "city": f"eq.{city}"})
    if existing:
        sb("PATCH", "user_alerts", data={"threshold_zscore": threshold, "active": True}, params={"api_key": f"eq.{key}", "city": f"eq.{city}"})
        return {"status": "updated", "city": city, "threshold": threshold}
    sb("POST", "user_alerts", data={"email": email, "api_key": key, "city": city, "country_code": country_code, "threshold_zscore": threshold, "active": True})
    return {"status": "created", "city": city, "threshold": threshold, "email": email}

@app.get("/api/alerts/list")
def alert_list(key: str = ""):
    if not key:
        raise HTTPException(status_code=400, detail="api_key required")
    key_data = sb("GET", "api_keys", params={"api_key": f"eq.{key}", "select": "email,active"})
    if not key_data or not key_data[0].get("active"):
        raise HTTPException(status_code=403, detail="Invalid or inactive API key")
    alerts = sb("GET", "user_alerts", params={"api_key": f"eq.{key}", "active": "eq.true"})
    return {"alerts": alerts or []}

@app.delete("/api/alerts/delete")
async def alert_delete(request: Request):
    data = await request.json()
    key = data.get("api_key", "")
    city = data.get("city", "")
    if not key or not city:
        raise HTTPException(status_code=400, detail="api_key and city required")
    sb("PATCH", "user_alerts", data={"active": False}, params={"api_key": f"eq.{key}", "city": f"eq.{city}"})
    return {"status": "deleted", "city": city}

# ─── LINKEDIN OAuth ───────────────────────────────────────────────────────────
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")

@app.get("/auth/linkedin/callback")
async def linkedin_callback(code: str = "", error: str = ""):
    if error or not code:
        return {"error": error}
    r = req_lib.post("https://www.linkedin.com/oauth/v2/accessToken", data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": "https://api.weatherarb.com/auth/linkedin/callback",
        "client_id": LINKEDIN_CLIENT_ID,
        "client_secret": LINKEDIN_CLIENT_SECRET
    })
    data = r.json()
    token = data.get("access_token", "")
    if token:
        _top_cache["linkedin_token"] = token
        logger.info(f"LinkedIn token saved")
        return {"status": "ok", "message": "Token salvato! Puoi chiudere questa pagina."}
    return {"error": data}

# ─── ENRICHED SIGNALS ENDPOINT ───────────────────────────────────────────────
@app.get("/api/v1/signals/{slug}")
async def get_signals(slug: str):
    """Enriched signals: weather + air quality + earthquakes nearby"""
    import re, unicodedata
    s = unicodedata.normalize("NFKD", slug.lower()).encode("ascii","ignore").decode("ascii")
    s = re.sub(r"[^\w-]","", s.replace(" ","-"))

    # Find province
    province = None
    for p in PROVINCES:
        pslug = unicodedata.normalize("NFKD", p["nome"].lower()).encode("ascii","ignore").decode("ascii")
        pslug = re.sub(r"[^\w-]","", pslug.replace(" ","-"))
        if pslug == s:
            province = p
            break

    if not province:
        raise HTTPException(404, "City not found")

    lat, lon = province["lat"], province["lon"]
    result = {"city": province["nome"], "lat": lat, "lon": lon}

    # 1. Weather from cache
    cached = _cache.get(s, {})
    result["weather"] = cached.get("weather", {})
    result["signal"] = cached.get("signal", {})

    # 2. Air Quality from Open-Meteo (free)
    try:
        r_aq = req_lib.get(
            f"https://air-quality-api.open-meteo.com/v1/air-quality"
            f"?latitude={lat}&longitude={lon}"
            f"&current=pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,ozone,european_aqi"
            f"&timezone=auto",
            timeout=8
        )
        aq = r_aq.json().get("current", {})
        result["air_quality"] = {
            "pm10": aq.get("pm10"),
            "pm2_5": aq.get("pm2_5"),
            "ozone": aq.get("ozone"),
            "nitrogen_dioxide": aq.get("nitrogen_dioxide"),
            "european_aqi": aq.get("european_aqi"),
            "aqi_label": (
                "Good" if (aq.get("european_aqi") or 0) <= 20 else
                "Fair" if (aq.get("european_aqi") or 0) <= 40 else
                "Moderate" if (aq.get("european_aqi") or 0) <= 60 else
                "Poor" if (aq.get("european_aqi") or 0) <= 80 else "Very Poor"
            )
        }
    except Exception as e:
        result["air_quality"] = {"error": str(e)}

    # 3. Recent earthquakes nearby (USGS, free)
    try:
        r_eq = req_lib.get(
            f"https://earthquake.usgs.gov/fdsnws/event/1/query"
            f"?format=geojson&latitude={lat}&longitude={lon}"
            f"&maxradius=3&minmagnitude=2.0&limit=5&orderby=time",
            timeout=8
        )
        eq_data = r_eq.json()
        quakes = []
        for f in eq_data.get("features", [])[:5]:
            p = f.get("properties", {})
            quakes.append({
                "magnitude": p.get("mag"),
                "place": p.get("place"),
                "time": p.get("time"),
                "depth_km": f.get("geometry",{}).get("coordinates",[None,None,None])[2]
            })
        result["earthquakes_nearby"] = quakes
    except Exception as e:
        result["earthquakes_nearby"] = []

    # 4. UV Index from Open-Meteo
    try:
        r_uv = req_lib.get(
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&daily=uv_index_max,precipitation_sum,wind_speed_10m_max"
            f"&timezone=auto&forecast_days=3",
            timeout=8
        )
        uv_data = r_uv.json()
        daily = uv_data.get("daily", {})
        result["forecast_3d"] = {
            "uv_index_max": daily.get("uv_index_max", []),
            "precipitation_mm": daily.get("precipitation_sum", []),
            "wind_max_kmh": [round(w*3.6,1) for w in (daily.get("wind_speed_10m_max") or [])],
            "dates": daily.get("time", [])
        }
    except Exception as e:
        result["forecast_3d"] = {}

    result["sources"] = ["WeatherArb/Open-Meteo", "Open-Meteo AQ", "USGS Earthquakes"]
    result["timestamp"] = datetime.now(timezone.utc).isoformat()
    return result

# ─── DAILY WEATHER CARD ───────────────────────────────────────────────────────
@app.get("/api/v1/today/{slug}")
async def daily_card(slug: str):
    """Daily Weather Card: rarity + health score + world rank"""
    import re, unicodedata, math

    s = unicodedata.normalize("NFKD", slug.lower()).encode("ascii","ignore").decode("ascii")
    s = re.sub(r"[^\w-]","", s.replace(" ","-"))

    # Find in cache
    top = _top_cache.get("top", [])
    city_data = next((n for n in top if
        re.sub(r"[^\w-]","", unicodedata.normalize("NFKD", n["location"].lower()).encode("ascii","ignore").decode("ascii").replace(" ","-")) == s
    ), None)

    if not city_data:
        # Try Supabase cache
        sb = load_weather_cache_supabase(s)
        if sb:
            city_data = sb
        else:
            raise HTTPException(404, "City not found or not yet cached")

    z = city_data.get("z_score", 0)
    score = city_data.get("score", 0)
    temp = city_data.get("temperature_c", 20)
    hum = city_data.get("humidity_pct", 60)
    wind = city_data.get("wind_kmh", 10)
    az = abs(z)

    # 1. RARITY — how rare is today's weather
    if az >= 4:   rarity_pct, rarity_label, rarity_color = 0.003, "Evento storico", "#FF006E"
    elif az >= 3: rarity_pct, rarity_label, rarity_color = 0.3,   "Rarissimo", "#ef4444"
    elif az >= 2: rarity_pct, rarity_label, rarity_color = 2.3,   "Insolito", "#f97316"
    elif az >= 1: rarity_pct, rarity_label, rarity_color = 15.9,  "Non comune", "#f59e0b"
    else:         rarity_pct, rarity_label, rarity_color = 68.0,  "Normale", "#10b981"
    occurs_per_year = round(365 * rarity_pct / 100, 1)

    # 2. OUTDOOR ACTIVITY SCORE (0-100)
    activity = 100
    if temp > 35: activity -= 40
    elif temp > 30: activity -= 20
    elif temp < 0: activity -= 35
    elif temp < 5: activity -= 15
    if wind > 60: activity -= 30
    elif wind > 40: activity -= 15
    elif wind > 25: activity -= 5
    if hum > 85: activity -= 15
    elif hum > 70: activity -= 5
    if hum < 20: activity -= 10
    activity = max(0, min(100, activity))
    if activity >= 80:   activity_label, activity_icon = "Perfetto per uscire", "🏃"
    elif activity >= 60: activity_label, activity_icon = "Buono", "🚶"
    elif activity >= 40: activity_label, activity_icon = "Discreto", "⚠️"
    elif activity >= 20: activity_label, activity_icon = "Difficile", "🌧️"
    else:                activity_label, activity_icon = "Resta a casa", "🏠"

    # 3. HEALTH SCORE
    health = 100
    if temp > 38: health -= 40
    elif temp > 33: health -= 20
    elif temp < -10: health -= 35
    elif temp < 0: health -= 15
    if hum > 90: health -= 20
    elif hum > 80: health -= 10
    if wind > 70: health -= 15
    if az >= 3: health -= 20
    elif az >= 2: health -= 10
    health = max(0, min(100, health))
    if health >= 80:   health_label = "Ottimale per la salute"
    elif health >= 60: health_label = "Accettabile"
    elif health >= 40: health_label = "Attenzione"
    else:              health_label = "Rischio per la salute"

    # 4. WORLD RANK
    sorted_top = sorted(top, key=lambda x: -abs(x.get("z_score",0)))
    world_rank = next((i+1 for i,n in enumerate(sorted_top) if
        re.sub(r"[^\w-]","", unicodedata.normalize("NFKD", n["location"].lower()).encode("ascii","ignore").decode("ascii").replace(" ","-")) == s
    ), None)
    total_cities = len(top)

    # 5. HUMAN DESCRIPTION
    city_name = city_data["location"]
    if z >= 3:   desc = f"🔥 {city_name} vive oggi un'ondata di calore estrema che accade meno di {rarity_pct:.1f}% delle volte — circa {occurs_per_year} giorni all'anno."
    elif z >= 2: desc = f"🌡️ {city_name} è significativamente più calda del solito. Un evento che si verifica circa {occurs_per_year} giorni l'anno."
    elif z <= -3: desc = f"❄️ {city_name} vive oggi un'ondata di freddo estrema rarissima — circa {occurs_per_year} giorni all'anno."
    elif z <= -2: desc = f"🧊 {city_name} è significativamente più fredda del normale, circa {occurs_per_year} giorni così all'anno."
    else:         desc = f"✅ Il meteo di {city_name} oggi è nella norma stagionale. Nessuna anomalia rilevante."

    return {
        "city": city_name,
        "country_code": city_data.get("country_code",""),
        "z_score": round(z, 2),
        "rarity": {
            "percent": rarity_pct,
            "label": rarity_label,
            "color": rarity_color,
            "occurs_per_year": occurs_per_year,
            "description": desc
        },
        "outdoor": {
            "score": activity,
            "label": activity_label,
            "icon": activity_icon
        },
        "health": {
            "score": health,
            "label": health_label
        },
        "world_rank": world_rank,
        "total_cities": total_cities,
        "top_percentile": round((1 - (world_rank or total_cities)/total_cities)*100, 1) if world_rank else 0,
        "temperature_c": temp,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
