#!/usr/bin/env python3
"""WeatherArb X (Twitter) Bot — posta alert quando Z-Score >= 8.0"""
import os, json, requests, logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

API_BASE = os.getenv("API_BASE", "https://api.weatherarb.com")
BEARER   = os.getenv("TWITTER_BEARER_TOKEN", "")
CK       = os.getenv("TWITTER_CONSUMER_KEY", "")
CS       = os.getenv("TWITTER_CONSUMER_SECRET", "")
SCORE_MIN = float(os.getenv("TWEET_SCORE_MIN", "8.0"))

def post_tweet(text):
    if not all([CK, CS]):
        log.warning("Twitter credentials missing"); return False
    try:
        import tweepy
        auth = tweepy.OAuth2BearerHandler(BEARER)
        client = tweepy.Client(
            bearer_token=BEARER,
            consumer_key=CK,
            consumer_secret=CS
        )
        r = client.create_tweet(text=text)
        log.info(f"Tweet posted: {r.data['id']}")
        return True
    except Exception as e:
        log.error(f"Tweet error: {e}"); return False

def flag(cc):
    flags = {
        'it':'🇮🇹','de':'🇩🇪','fr':'🇫🇷','es':'🇪🇸','gb':'🇬🇧',
        'us':'🇺🇸','ca':'🇨🇦','jp':'🇯🇵','cn':'🇨🇳','in':'🇮🇳',
        'kr':'🇰🇷','au':'🇦🇺','br':'🇧🇷','sg':'🇸🇬','ae':'🇦🇪',
        'tr':'🇹🇷','se':'🇸🇪','pl':'🇵🇱','nl':'🇳🇱','pt':'🇵🇹',
    }
    return flags.get(cc, '🌍')

def run():
    log.info("=== WeatherArb X Bot START ===")
    try:
        r = requests.get(f"{API_BASE}/api/v1/europe/top?limit=50", timeout=15)
        signals = r.json().get("reports", r.json().get("data", []))
    except Exception as e:
        log.error(f"API error: {e}"); return

    critical = [s for s in signals if s.get("score", 0) >= SCORE_MIN]
    log.info(f"Anomalie >= {SCORE_MIN}: {len(critical)}")

    posted = 0
    for sig in critical[:3]:  # max 3 tweet per run
        city  = sig.get("location", "")
        cc    = sig.get("country_code", "eu")
        z     = sig.get("z_score", 0)
        sc    = sig.get("score", 0)
        ev    = (sig.get("vertical") or sig.get("event_type") or "anomaly").replace("_", " ").title()
        sign  = "+" if z >= 0 else ""
        level = sig.get("anomaly_level", "EXTREME")
        emoji = flag(cc)

        # Emoji evento
        ev_emoji = "🔥" if z > 0 else "❄️"
        if "rain" in ev.lower(): ev_emoji = "🌧️"
        if "wind" in ev.lower(): ev_emoji = "💨"

        url = f"https://weatherarb.com/{cc}/{city.lower().replace(' ','-').replace(\"'\",'')}/"

        tweet = (
            f"{ev_emoji} WEATHER ALERT {emoji} {city.upper()}\n"
            f"Z-Score: {sign}{z:.2f}σ | Score: {sc:.1f}/10\n"
            f"Event: {ev} | Level: {level}\n"
            f"HDD: {sig.get('hdd', 0):.1f} | Humidity: {sig.get('humidity_pct', 0)}%\n"
            f"🔗 {url}\n"
            f"#WeatherArb #ClimateRisk #EnergyTrading #{city.replace(' ','')}"
        )

        # Trunca a 280 char
        if len(tweet) > 280:
            tweet = tweet[:277] + "..."

        log.info(f"Tweet ({len(tweet)} chars):\n{tweet}")
        if post_tweet(tweet):
            posted += 1

    log.info(f"=== X Bot END — {posted} tweet postati ===")

if __name__ == "__main__":
    run()
