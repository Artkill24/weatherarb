#!/usr/bin/env python3
"""WeatherArb X (Twitter) Bot — posta alert quando Z-Score >= 8.0"""
import os, requests, logging, re
from unicodedata import normalize

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

API_BASE   = os.getenv("API_BASE", "https://api.weatherarb.com")
BEARER     = os.getenv("TWITTER_BEARER_TOKEN", "")
CK         = os.getenv("TWITTER_CONSUMER_KEY", "")
CS         = os.getenv("TWITTER_CONSUMER_SECRET", "")
AT         = os.getenv("TWITTER_ACCESS_TOKEN", "")
ATS        = os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "")
SCORE_MIN  = float(os.getenv("TWEET_SCORE_MIN", "8.0"))

def slugify(t):
    s = normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[\s_]+", "-", re.sub(r"[^\w\s-]", "", s).strip().lower())

def get_flag(cc):
    flags = {
        "it":"🇮🇹","de":"🇩🇪","fr":"🇫🇷","es":"🇪🇸","gb":"🇬🇧",
        "us":"🇺🇸","ca":"🇨🇦","jp":"🇯🇵","cn":"🇨🇳","in":"🇮🇳",
        "kr":"🇰🇷","au":"🇦🇺","br":"🇧🇷","sg":"🇸🇬","ae":"🇦🇪",
        "tr":"🇹🇷","se":"🇸🇪","pl":"🇵🇱","nl":"🇳🇱","pt":"🇵🇹",
        "no":"🇳🇴","ch":"🇨🇭","at":"🇦🇹","be":"🇧🇪","mx":"🇲🇽",
    }
    return flags.get(cc, "🌍")

def post_tweet(text):
    if not all([CK, CS, AT, ATS]):
        log.warning("Access Token mancante — solo lettura. Aggiungi TWITTER_ACCESS_TOKEN e TWITTER_ACCESS_TOKEN_SECRET")
        log.info(f"[DRY RUN] Tweet:\n{text}")
        return False
    try:
        import tweepy
        client = tweepy.Client(
            consumer_key=CK,
            consumer_secret=CS,
            access_token=AT,
            access_token_secret=ATS
        )
        r = client.create_tweet(text=text)
        log.info(f"Tweet postato: {r.data['id']}")
        return True
    except Exception as e:
        log.error(f"Tweet error: {e}")
        return False

def run():
    log.info("=== WeatherArb X Bot START ===")
    try:
        r = requests.get(f"{API_BASE}/api/v1/europe/top?limit=50", timeout=15)
        data = r.json()
        signals = data.get("reports", data.get("data", []))
    except Exception as e:
        log.error(f"API error: {e}")
        return

    critical = [s for s in signals if s.get("score", 0) >= SCORE_MIN]
    log.info(f"Anomalie >= {SCORE_MIN}: {len(critical)}")

    if not critical:
        log.info("Nessuna anomalia sopra soglia — nessun tweet")
        return

    posted = 0
    for sig in critical[:3]:
        city  = sig.get("location", "")
        cc    = sig.get("country_code", "eu")
        z     = sig.get("z_score", 0)
        sc    = sig.get("score", 0)
        ev    = (sig.get("vertical") or sig.get("event_type") or "anomaly").replace("_", " ").title()
        sign  = "+" if z >= 0 else ""
        level = sig.get("anomaly_level", "EXTREME")
        hdd   = sig.get("hdd", 0) or 0
        hum   = sig.get("humidity_pct", 0) or 0

        flag_emoji = get_flag(cc)

        if z > 0:
            ev_emoji = "🔥"
        elif "rain" in ev.lower():
            ev_emoji = "🌧️"
        elif "wind" in ev.lower():
            ev_emoji = "💨"
        else:
            ev_emoji = "❄️"

        city_slug = slugify(city)
        url = f"https://weatherarb.com/{cc}/{city_slug}/"
        hashtag = city.replace(" ", "").replace("'", "")

        tweet = (
            f"{ev_emoji} WEATHER ALERT {flag_emoji} {city.upper()}\n"
            f"Z-Score: {sign}{z:.2f}σ | Score: {sc:.1f}/10\n"
            f"Event: {ev} | Level: {level}\n"
            f"HDD: {hdd:.1f} | Humidity: {hum}%\n"
            f"🔗 {url}\n"
            f"#WeatherArb #ClimateRisk #EnergyTrading #{hashtag}"
        )

        if len(tweet) > 280:
            tweet = tweet[:277] + "..."

        log.info(f"Tweet ({len(tweet)} chars):\n{tweet}\n")
        if post_tweet(tweet):
            posted += 1

    log.info(f"=== X Bot END — {posted} tweet postati ===")

if __name__ == "__main__":
    run()
