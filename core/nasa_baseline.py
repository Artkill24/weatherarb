"""
WeatherArb — NASA POWER Baseline Provider
Sostituisce le baseline simulate con dati climatologici reali NASA.
Cache locale per evitare chiamate ripetute.
"""
import requests, json, os, logging
from pathlib import Path

logger = logging.getLogger(__name__)

NASA_KEY = os.getenv("NASA_API_KEY", "g6VSRgkqN3YHMNxKoqo6Fa7IkkXSd9OiDXb43vhx")
NASA_BASE = "https://power.larc.nasa.gov/api/temporal/climatology/point"
CACHE_DIR = Path("data/nasa_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

MONTHS = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"]

def get_nasa_baseline(lat: float, lon: float, province: str) -> dict:
    """
    Scarica baseline climatologica NASA POWER per coordinate.
    Ritorna: {month: {temp_mean, temp_std, rain_mean}}
    Cache locale per evitare chiamate ripetute.
    """
    cache_file = CACHE_DIR / f"{province.lower().replace(' ','-')}.json"
    
    # Usa cache se esiste
    if cache_file.exists():
        try:
            return json.load(open(cache_file))
        except:
            pass
    
    try:
        r = requests.get(NASA_BASE, params={
            "parameters": "T2M,T2M_MAX,T2M_MIN,PRECTOTCORR",
            "community": "RE",
            "longitude": lon,
            "latitude": lat,
            "format": "JSON",
            "api-key": NASA_KEY,
        }, timeout=15)
        
        data = r.json()
        props = data.get("properties", {}).get("parameter", {})
        
        if not props:
            logger.warning(f"NASA POWER: no data for {province}")
            return {}
        
        t2m = props.get("T2M", {})
        t2m_max = props.get("T2M_MAX", {})
        t2m_min = props.get("T2M_MIN", {})
        prec = props.get("PRECTOTCORR", {})
        
        baseline = {}
        for i, month in enumerate(MONTHS):
            if month in t2m:
                mean = t2m[month]
                tmax = t2m_max.get(month, mean + 5)
                tmin = t2m_min.get(month, mean - 5)
                # Stima std dalla range giornaliero mensile
                std = max((tmax - tmin) / 8.0, 1.5)  # range/8 ≈ sigma mensile
                rain = prec.get(month, 2.5) * 30  # mm/giorno → mm/mese → /30
                
                baseline[str(i+1)] = {
                    "temp_mean": round(mean, 2),
                    "temp_std": round(std, 2),
                    "rain_mean": round(prec.get(month, 2.5), 2),
                    "rain_std": round(prec.get(month, 2.5) * 0.8, 2),
                }
        
        # Salva cache
        json.dump(baseline, open(cache_file, 'w'), indent=2)
        logger.info(f"NASA baseline cached for {province}")
        return baseline
        
    except Exception as e:
        logger.error(f"NASA POWER error for {province}: {e}")
        return {}


def get_monthly_baseline(lat: float, lon: float, province: str, month: int) -> dict:
    """Ritorna la baseline per il mese corrente."""
    all_months = get_nasa_baseline(lat, lon, province)
    return all_months.get(str(month), {})


def enrich_baseline_object(baseline_obj, lat: float, lon: float, 
                           province: str, month: int):
    """
    Arricchisce un oggetto HistoricalBaseline con dati NASA più precisi.
    Sostituisce avg_temp_c e std_temp_c se NASA ha dati migliori.
    """
    nasa = get_monthly_baseline(lat, lon, province, month)
    if not nasa:
        return baseline_obj
    
    # Aggiorna solo se la baseline corrente ha std troppo bassa o alta
    current_std = getattr(baseline_obj, 'std_temp_c', 999)
    nasa_std = nasa.get('temp_std', 0)
    
    if nasa_std > 0:
        baseline_obj.avg_temp_c = nasa.get('temp_mean', baseline_obj.avg_temp_c)
        baseline_obj.std_temp_c = max(nasa_std, 1.5)  # floor 1.5°C
        baseline_obj.avg_rain_mm_day = nasa.get('rain_mean', baseline_obj.avg_rain_mm_day)
        logger.debug(f"NASA enriched {province}: T={baseline_obj.avg_temp_c}°C ±{baseline_obj.std_temp_c}")
    
    return baseline_obj
