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

# ─── OWM FETCHER ──────────────────────────────────────────────────────────────
def fetch_owm(lat, lon):
    if not OWM_API_KEY:
        return None
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OWM_API_KEY}&units=metric"
        r = req_lib.get(url, timeout=10)
        d = r.json()
        return {
            "temperature_c": d["main"]["temp"],
            "humidity_pct": d["main"]["humidity"],
            "wind_ms": d["wind"]["speed"],
            "wind_kmh": round(d["wind"]["speed"] * 3.6, 1),
            "description": d["weather"][0]["description"] if d.get("weather") else "",
        }
    except Exception as e:
        logger.error(f"OWM error: {e}")
        return None

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
        _top_cache["space_weather"] = {"kp_current": round(kp, 2), "flare_class": "C", "solar_flux": 0, "timestamp": datetime.now(timezone.utc).isoformat()}
    except:
        pass
    _last_refresh = now
    logger.info(f"Refresh complete: {count} provinces cached")

def _cc(country):
    m = {"Italy":"it","Germany":"de","France":"fr","Spain":"es","United Kingdom":"gb",
         "Sweden":"se","Netherlands":"nl","Poland":"pl","Austria":"at","Switzerland":"ch",
         "Belgium":"be","Portugal":"pt","Denmark":"dk","Norway":"no","Greece":"gr",
         "Croatia":"hr","Czech Republic":"cz","Hungary":"hu","Romania":"ro","Finland":"fi",
         "Slovenia":"si","Slovakia":"sk","Serbia":"rs"}
    m.update({'USA': 'us', 'Canada': 'ca', 'Brazil': 'br', 'Argentina': 'ar', 'Mexico': 'mx', 'Colombia': 'co', 'Chile': 'cl', 'Australia': 'au', 'New Zealand': 'nz', 'Japan': 'jp', 'South Korea': 'kr', 'China': 'cn', 'India': 'in', 'Bangladesh': 'bd', 'Pakistan': 'pk', 'Sri Lanka': 'lk', 'Nepal': 'np', 'Indonesia': 'id', 'Philippines': 'ph', 'Vietnam': 'vn', 'Thailand': 'th', 'Malaysia': 'my', 'Singapore': 'sg', 'Taiwan': 'tw', 'Mongolia': 'mn', 'Iran': 'ir', 'Turkey': 'tr', 'Israel': 'il', 'UAE': 'ae', 'Saudi Arabia': 'sa', 'Egypt': 'eg', 'Morocco': 'ma', 'Nigeria': 'ng', 'Kenya': 'ke', 'South Africa': 'za'})
    return m.get(country, "eu")

# ─── SUPABASE HELPERS ─────────────────────────────────────────────────────────
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
    top = _top_cache.get("top", [])
    if not top:
        return {"error": "No data cached yet"}
    import math, unicodedata, re
    nearest = min(top, key=lambda n: math.sqrt((n["lat"]-lat)**2 + (n["lon"]-lon)**2))
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
    top = _top_cache.get("top", [])
    if not top:
        return {"error": "No data cached yet"}
    import math, unicodedata, re
    nearest = min(top, key=lambda n: math.sqrt((n["lat"]-lat)**2 + (n["lon"]-lon)**2))
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
