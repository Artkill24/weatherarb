#!/usr/bin/env python3
"""WeatherArb Alert Engine — invia email quando Z-Score supera soglia"""
import os, requests, logging
from datetime import datetime, timezone, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

API_BASE = os.getenv("API_BASE", "https://api.weatherarb.com")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")

def sb(method, table, data=None, params=None):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
    r = requests.request(method, url, json=data, params=params, headers=headers, timeout=10)
    return r.json() if r.content else []

def send_alert_email(email, city, cc, z, level, event_type, score):
    if not RESEND_API_KEY:
        log.warning("No RESEND_API_KEY")
        return False
    slug = city.lower().replace(" ", "-")
    color = {"CRITICAL":"#ef4444","EXTREME":"#f97316","UNUSUAL":"#eab308"}.get(level, "#3b82f6")
    sign = "+" if z >= 0 else ""
    html = f"""
<div style="background:#040608;padding:32px;font-family:-apple-system,sans-serif;color:#c8d6e5;max-width:600px">
  <div style="font-size:24px;font-weight:700;margin-bottom:8px">⚡ WeatherArb Alert</div>
  <div style="font-size:14px;color:#4a5568;margin-bottom:24px">Anomalia rilevata — {datetime.now(timezone.utc).strftime('%d %b %Y %H:%M')} UTC</div>
  <div style="background:#0a0d12;border:1px solid {color};border-radius:12px;padding:24px;margin-bottom:24px">
    <div style="font-size:28px;font-weight:700;margin-bottom:4px">{city}</div>
    <div style="font-size:14px;color:#4a5568;margin-bottom:16px">{event_type.replace('_',' ').title()}</div>
    <div style="display:flex;gap:24px">
      <div><div style="font-size:11px;color:#4a5568">Z-SCORE</div><div style="font-size:32px;font-weight:700;color:{color}">{sign}{z:.2f}σ</div></div>
      <div><div style="font-size:11px;color:#4a5568">LIVELLO</div><div style="font-size:20px;font-weight:700;color:{color}">{level}</div></div>
      <div><div style="font-size:11px;color:#4a5568">SCORE</div><div style="font-size:20px;font-weight:700">{score:.1f}/10</div></div>
    </div>
  </div>
  <a href="https://weatherarb.com/{cc}/{slug}/" style="display:block;background:#2563eb;color:white;padding:14px;border-radius:8px;text-align:center;font-size:14px;font-weight:700;text-decoration:none;margin-bottom:16px">Analisi completa →</a>
  <div style="font-size:11px;color:#4a5568;text-align:center">WeatherArb Intelligence · <a href="https://weatherarb.com" style="color:#4a5568">weatherarb.com</a></div>
</div>"""
    r = requests.post("https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
        json={"from":"WeatherArb Alerts <alerts@weatherarb.com>","to":[email],
              "subject":f"⚡ Alert {level}: {city} Z={sign}{z:.2f}σ","html":html})
    return r.status_code == 200

def run():
    log.info("=== Alert Engine START ===")
    try:
        r = requests.get(f"{API_BASE}/api/v1/europe/top?limit=500", timeout=15)
        signals = {s["location"].lower(): s for s in r.json().get("reports", [])}
    except Exception as e:
        log.error(f"API error: {e}"); return

    alerts = sb("GET", "user_alerts", params={"active": "eq.true"})
    log.info(f"Alert attivi: {len(alerts)}")
    sent = 0
    now = datetime.now(timezone.utc)

    for alert in alerts:
        city = alert.get("city", "")
        threshold = float(alert.get("threshold_zscore", 2.0))
        email = alert.get("email", "")
        cc = alert.get("country_code", "it")
        last_sent = alert.get("last_sent")

        if last_sent:
            last_dt = datetime.fromisoformat(last_sent.replace("Z", "+00:00"))
            if (now - last_dt) < timedelta(hours=6):
                continue

        sig = signals.get(city.lower())
        if not sig:
            continue

        z = sig.get("z_score", 0)
        if abs(z) < threshold:
            continue

        level = sig.get("anomaly_level", "NORMAL")
        event_type = sig.get("event_type", "anomaly")
        score = sig.get("score", 0)

        log.info(f"Sending alert: {email} → {city} Z={z:.2f}")
        if send_alert_email(email, city, cc, z, level, event_type, score):
            sb("PATCH", "user_alerts", data={"last_sent": now.isoformat()},
               params={"id": f"eq.{alert['id']}"})
            sent += 1

    log.info(f"=== Alert Engine END — {sent} email inviate ===")

if __name__ == "__main__":
    run()
