"""
WeatherArb — Telegram Alert System
Invia notifiche automatiche quando score >= 7.0
"""

import requests
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8721245580:AAFwa0EU95RZxgWtt58feBCNx9zQOMTBNC4")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1003525776340")
ALERT_SCORE_THRESHOLD = 7.0

COUNTRY_FLAGS = {
    "IT": "🇮🇹", "DE": "🇩🇪", "ES": "🇪🇸", "FR": "🇫🇷", "UK": "🇬🇧",
}

ANOMALY_EMOJI = {
    "CRITICAL": "🔴", "EXTREME": "🟠", "UNUSUAL": "🟡", "NORMAL": "⚫",
}

def get_country_flag(codice_istat: str) -> str:
    for prefix, flag in COUNTRY_FLAGS.items():
        if codice_istat.startswith(prefix):
            return flag
    return "🇮🇹"

def get_landing_url(provincia: str, codice_istat: str) -> str:
    slug = provincia.lower().replace(" ", "-").replace("ü", "u").replace("ö", "o").replace("ä", "a")
    if codice_istat.startswith("DE"):
        return f"https://weatherarb.com/de/{slug}/"
    return f"https://weatherarb.com/it/{slug}/"

def send_alert(pulse_json: dict) -> bool:
    """Invia alert Telegram per un Pulse-JSON con score >= threshold."""
    score = pulse_json.get("arbitrage_score", {}).get("score", 0)
    if score < ALERT_SCORE_THRESHOLD:
        return False

    loc = pulse_json.get("location", {})
    trig = pulse_json.get("weather_trigger", {})
    arb = pulse_json.get("arbitrage_score", {})
    action = pulse_json.get("action_plan", {})

    provincia = loc.get("provincia", "")
    codice = loc.get("codice_istat", "")
    flag = get_country_flag(codice)
    anomaly = trig.get("anomaly_level", "")
    anomaly_emoji = ANOMALY_EMOJI.get(anomaly, "🟡")
    evento = trig.get("type", "").replace("_", " ")
    z_score = trig.get("z_score", 0)
    confidence = arb.get("confidence", 0)
    vertical = action.get("recommended_vertical", "").replace("_", " ")
    budget = action.get("budget_recommendation", {}).get("daily_eur", 0)
    phase = action.get("phase", "")
    url = get_landing_url(provincia, codice)

    # Fase in emoji
    phase_label = {
        "PRE_EVENT_PREP": "🟡 Pre-Event (Warm-up)",
        "PRE_EVENT_LAUNCH": "🟠 Pre-Event (Launch)",
        "POST_EVENT_RECOVERY": "🟢 Recovery",
    }.get(phase, phase)

    msg = (
        f"{flag} <b>WeatherArb Signal</b> — {anomaly_emoji} {anomaly}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📍 <b>{provincia}</b> · {evento}\n"
        f"📊 Z-Score: <b>{z_score:+.2f}</b> · Score: <b>{score:.1f}/10</b>\n"
        f"🎯 Confidence: {confidence*100:.0f}%\n"
        f"💼 Vertical: {vertical}\n"
        f"💰 Budget suggerito: €{budget:.0f}/g\n"
        f"📅 Fase: {phase_label}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <a href='{url}'>Apri landing page</a>\n"
        f"<i>{datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC</i>"
    )

    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML",
                  "disable_web_page_preview": False},
            timeout=10
        )
        if r.ok:
            logger.info(f"Alert inviato: {provincia} score={score}")
            return True
        else:
            logger.warning(f"Telegram error: {r.text}")
            return False
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return False

def send_daily_summary(opportunities: list) -> bool:
    """Invia riepilogo giornaliero delle opportunità."""
    if not opportunities:
        return False

    top3 = sorted(opportunities, key=lambda x: x.get("score", 0), reverse=True)[:3]

    lines = ["⚡ <b>WeatherArb Daily Summary</b>\n━━━━━━━━━━━━━━━━━━"]
    for i, opp in enumerate(top3, 1):
        flag = get_country_flag(opp.get("codice_istat", ""))
        lines.append(
            f"{i}. {flag} <b>{opp['provincia']}</b> · {opp.get('event_type','').replace('_',' ')}\n"
            f"   Score: {opp['score']:.1f} · Z={opp.get('z_score',0):+.2f} · €{opp.get('budget_eur',0):.0f}/g"
        )

    lines.append(f"\n━━━━━━━━━━━━━━━━━━")
    lines.append(f"🌍 {len(opportunities)} opportunità totali monitorate")
    lines.append(f"🔗 weatherarb.com")

    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": "\n".join(lines),
                  "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=10
        )
        return r.ok
    except Exception as e:
        logger.error(f"Daily summary failed: {e}")
        return False
