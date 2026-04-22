#!/usr/bin/env python3
"""WeatherArb Weekly Pulse — newsletter automatica ogni lunedì"""
import os, requests, logging
from datetime import datetime, timezone

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

def run():
    log.info("=== Weekly Pulse START ===")
    
    # Fetch top anomalie globali
    try:
        r = requests.get(f"{API_BASE}/api/v1/europe/top?limit=500", timeout=15)
        signals = r.json().get("reports", [])[:5]
    except Exception as e:
        log.error(f"API error: {e}"); return

    # Fetch subscribers newsletter
    subscribers = sb("GET", "newsletter_subscribers", params={"select": "email"})
    if not subscribers:
        log.info("Nessun iscritto"); return

    log.info(f"Invio a {len(subscribers)} iscritti")

    # Build email
    date_str = datetime.now(timezone.utc).strftime("%d %B %Y")
    colors = {"CRITICAL":"#ef4444","EXTREME":"#f97316","UNUSUAL":"#eab308","NORMAL":"#3b82f6"}
    
    rows = ""
    for s in signals:
        z = s.get("z_score", 0)
        sign = "+" if z >= 0 else ""
        level = s.get("anomaly_level", "NORMAL")
        color = colors.get(level, "#3b82f6")
        cc = s.get("country_code", "eu")
        slug = s.get("location","").lower().replace(" ","-")
        rows += f"""
        <tr>
          <td style="padding:12px;border-bottom:1px solid #141920">
            <a href="https://weatherarb.com/{cc}/{slug}/" style="color:#fff;text-decoration:none;font-weight:700">{s.get('location','')}</a>
            <div style="font-size:11px;color:#4a5568">{s.get('event_type','').replace('_',' ').title()}</div>
          </td>
          <td style="padding:12px;border-bottom:1px solid #141920;font-size:20px;font-weight:700;color:{color};text-align:right">{sign}{z:.2f}σ</td>
          <td style="padding:12px;border-bottom:1px solid #141920;color:{color};text-align:right;font-weight:700">{level}</td>
        </tr>"""

    html = f"""<div style="font-family:-apple-system,sans-serif;max-width:600px;margin:0 auto;padding:32px;background:#040608;color:#c8d6e5">
  <div style="border-bottom:1px solid #141920;padding-bottom:20px;margin-bottom:24px">
    <div style="font-size:13px;font-weight:700;letter-spacing:.2em;color:#3b82f6">WEATHERARB</div>
    <h1 style="color:#fff;margin:8px 0 4px;font-size:24px">The Weekly Pulse ⚡</h1>
    <div style="font-size:13px;color:#4a5568">{date_str} · Top 5 Anomalie Globali</div>
  </div>
  <table style="width:100%;border-collapse:collapse;margin-bottom:24px">
    <tr><th style="text-align:left;font-size:11px;color:#4a5568;padding:8px 12px;text-transform:uppercase">Città</th>
    <th style="text-align:right;font-size:11px;color:#4a5568;padding:8px 12px;text-transform:uppercase">Z-Score</th>
    <th style="text-align:right;font-size:11px;color:#4a5568;padding:8px 12px;text-transform:uppercase">Livello</th></tr>
    {rows}
  </table>
  <a href="https://weatherarb.com/data/" style="display:block;background:#2563eb;color:white;padding:14px;border-radius:8px;text-align:center;font-size:14px;font-weight:700;text-decoration:none;margin-bottom:24px">Vedi Dashboard Completo →</a>
  <div style="font-size:11px;color:#4a5568;text-align:center;border-top:1px solid #141920;padding-top:16px">
    WeatherArb Intelligence · <a href="https://weatherarb.com" style="color:#4a5568">weatherarb.com</a>
  </div>
</div>"""

    sent = 0
    for sub in subscribers:
        email = sub.get("email","")
        if not email: continue
        try:
            r = requests.post("https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
                json={"from":"WeatherArb <alerts@weatherarb.com>",
                      "to":[email],
                      "subject":f"⚡ Weekly Pulse — Top 5 Anomalie {date_str}",
                      "html":html}, timeout=10)
            if r.status_code == 200: sent += 1
        except: pass

    log.info(f"=== Weekly Pulse END — {sent}/{len(subscribers)} email inviate ===")

if __name__ == "__main__":
    run()
