#!/usr/bin/env python3
"""
WeatherArb — Weekly Intelligence Briefing
Genera e invia il briefing settimanale agli iscritti via Resend
"""

import csv, json, os, re, logging, urllib.request
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

API_BASE       = os.getenv("API_BASE", "https://api.weatherarb.com")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
SUBSCRIBERS    = Path("data/newsletter_subscribers.csv")
FROM_EMAIL     = "WeatherArb Intelligence <alerts@weatherarb.com>"
GEMINI_MODEL   = "gemini-2.5-flash-lite"


def fetch_top_signals(n=8):
    import urllib.request as ur
    try:
        with ur.urlopen(f"{API_BASE}/api/v1/europe/top?limit={n}", timeout=15) as r:
            d = json.loads(r.read())
        return (d.get("reports") or d.get("data") or [])[:n]
    except Exception as e:
        log.error(f"Fetch error: {e}"); return []


def gemini(prompt):
    if not GEMINI_API_KEY: return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = json.dumps({"contents":[{"parts":[{"text":prompt}]}],
        "generationConfig":{"temperature":0.6,"maxOutputTokens":1000}}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = json.loads(r.read())["candidates"][0]["content"]["parts"][0]["text"]
            return re.sub(r"```json\s*|\s*```","",raw).strip()
    except Exception as e:
        log.error(f"Gemini error: {e}"); return None


def generate_briefing_html(signals):
    date_str = datetime.now(timezone.utc).strftime("%d %B %Y")
    week_num = datetime.now(timezone.utc).isocalendar()[1]

    # Gemini executive summary
    signals_txt = "\n".join([
        f"- {s.get('location','?')} ({s.get('country','?')}): Z={s.get('z_score',0):.2f}, Score={s.get('score',0):.1f}/10, Evento={s.get('vertical','?')}, Livello={s.get('anomaly_level','?')}"
        for s in signals
    ])
    summary = gemini(f"""Sei un analista senior di WeatherArb. Scrivi un executive summary di 120 parole in italiano per manager e professionisti su queste anomalie meteo europee della settimana:

{signals_txt}

Tono: autorevole, conciso, focalizzato su rischi operativi e logistici.
Nessun prodotto o acquisto. Solo intelligence pura.""") or "Il sistema ha rilevato anomalie significative in Europa questa settimana. I segnali più critici sono riportati di seguito."

    # Genera card per ogni segnale
    cards = ""
    col_map = {"CRITICAL":"#ef4444","EXTREME":"#f97316","UNUSUAL":"#f59e0b","NORMAL":"#10b981"}
    for s in signals[:6]:
        city = s.get("location","—"); cc = s.get("country_code","it")
        z = s.get("z_score",0); sc = s.get("score",0)
        lvl = s.get("anomaly_level","NORMAL"); col = col_map.get(lvl,"#10b981")
        sign = "+" if z>=0 else ""
        vert = (s.get("vertical") or s.get("event_type") or "—").replace("_"," ")
        slug = city.lower().replace(" ","-")
        cards += f"""
<tr>
  <td style="padding:16px;border-bottom:1px solid #141920">
    <div style="display:flex;justify-content:space-between;align-items:flex-start">
      <div>
        <div style="font-weight:700;font-size:15px;color:#fff;margin-bottom:4px">{city}</div>
        <div style="font-size:12px;color:#4a5568;text-transform:uppercase;letter-spacing:.08em">{s.get("country","EU")} · {vert}</div>
      </div>
      <div style="text-align:right">
        <div style="font-size:22px;font-weight:800;color:{col}">{sign}{z:.2f}σ</div>
        <div style="font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:{col}">{lvl}</div>
      </div>
    </div>
    <div style="margin-top:10px;background:#0a0d12;border-radius:6px;height:4px;overflow:hidden">
      <div style="height:100%;width:{min(sc*10,100):.0f}%;background:{col};border-radius:6px"></div>
    </div>
    <div style="display:flex;justify-content:space-between;margin-top:6px">
      <span style="font-size:11px;color:#4a5568">Score {sc:.1f}/10</span>
      <a href="https://weatherarb.com/{cc}/{slug}/" style="font-size:11px;color:#3b82f6;text-decoration:none">Analisi completa →</a>
    </div>
  </td>
</tr>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>WeatherArb Intelligence Briefing — Settimana {week_num}</title>
</head>
<body style="background:#040608;color:#c8d6e5;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;margin:0;padding:0">
<div style="max-width:600px;margin:0 auto;padding:40px 24px">

  <!-- HEADER -->
  <div style="text-align:center;margin-bottom:40px;border-bottom:1px solid #141920;padding-bottom:32px">
    <h1 style="font-size:32px;font-weight:800;letter-spacing:-.02em;color:#fff;margin:0 0 6px">
      Weather<span style="color:#3b82f6">Arb</span>
    </h1>
    <p style="font-size:11px;text-transform:uppercase;letter-spacing:.2em;color:#4a5568;margin:0 0 16px">
      Intelligence Agency · Settimana {week_num}
    </p>
    <p style="font-size:13px;color:#4a5568">{date_str} · Z-Score su baseline NASA POWER 25 anni</p>
  </div>

  <!-- SUMMARY -->
  <div style="background:#0a0d12;border:1px solid #1e2d3d;border-left:3px solid #3b82f6;border-radius:8px;padding:24px;margin-bottom:32px">
    <div style="font-size:10px;text-transform:uppercase;letter-spacing:.2em;color:#3b82f6;margin-bottom:10px">📊 Executive Summary</div>
    <p style="font-size:14px;line-height:1.7;color:#c8d6e5;margin:0">{summary}</p>
  </div>

  <!-- SIGNALS -->
  <div style="font-size:10px;text-transform:uppercase;letter-spacing:.2em;color:#4a5568;margin-bottom:12px">🔴 Top Anomalie Settimana</div>
  <table style="width:100%;border-collapse:collapse;background:#0a0d12;border:1px solid #141920;border-radius:12px;overflow:hidden">
    {cards}
  </table>

  <!-- CTA -->
  <div style="text-align:center;margin:32px 0">
    <a href="https://weatherarb.com/data/" 
       style="display:inline-block;background:#3b82f6;color:#fff;padding:14px 32px;border-radius:8px;text-decoration:none;font-weight:700;font-size:14px">
      Dashboard Live →
    </a>
    <div style="margin-top:12px">
      <a href="https://weatherarb.com/map.html" style="font-size:12px;color:#4a5568;text-decoration:none;margin:0 8px">Mappa Europa</a>
      <a href="https://weatherarb.com/api.html" style="font-size:12px;color:#4a5568;text-decoration:none;margin:0 8px">API Pubblica</a>
      <a href="https://t.me/weatherarb_alerts" style="font-size:12px;color:#4a5568;text-decoration:none;margin:0 8px">Telegram</a>
    </div>
  </div>

  <!-- FOOTER -->
  <div style="border-top:1px solid #141920;padding-top:20px;text-align:center;font-size:11px;color:#4a5568">
    <p>WeatherArb · Independent Weather Intelligence Agency</p>
    <p>Dati: NASA POWER, ERA5-Land, OpenWeatherMap</p>
    <p style="margin-top:8px">
      <a href="https://weatherarb.com" style="color:#4a5568;text-decoration:none">weatherarb.com</a> · 
      <a href="https://weatherarb.com/unsubscribe?email={{email}}" style="color:#4a5568;text-decoration:none">Cancella iscrizione</a>
    </p>
  </div>

</div>
</body></html>"""


def send_email(to, subject, html):
    if not RESEND_API_KEY:
        log.warning("RESEND_API_KEY non impostata"); return False
    payload = json.dumps({
        "from": FROM_EMAIL, "to": [to],
        "subject": subject, "html": html
    }).encode()
    req = urllib.request.Request(
        "https://api.resend.com/emails", data=payload,
        headers={"Authorization":f"Bearer {RESEND_API_KEY}","Content-Type":"application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            ok = r.status == 200
            log.info(f"{'✅' if ok else '❌'} Sent to {to}")
            return ok
    except Exception as e:
        log.error(f"Send error to {to}: {e}"); return False


def get_subscribers():
    if not SUBSCRIBERS.exists(): return []
    with open(SUBSCRIBERS, newline="", encoding="utf-8") as f:
        return [row[0].strip() for row in csv.reader(f) if row and row[0].strip()]


def main():
    log.info("=== WeatherArb Weekly Briefing START ===")
    subs = get_subscribers()
    log.info(f"Subscribers: {len(subs)}")

    if not subs:
        log.info("Nessun iscritto — nessuna email inviata")
        return

    signals = fetch_top_signals(8)
    if not signals:
        log.error("Nessun segnale disponibile"); return

    week = datetime.now(timezone.utc).isocalendar()[1]
    subject = f"🌩 WeatherArb Intelligence — Settimana {week}: {len(signals)} anomalie EU"
    html = generate_briefing_html(signals)

    sent = 0
    for email in subs:
        personalized = html.replace("{email}", email)
        if send_email(email, subject, personalized):
            sent += 1

    log.info(f"✅ Briefing inviato a {sent}/{len(subs)} iscritti")
    log.info("=== WeatherArb Weekly Briefing END ===")


if __name__ == "__main__":
    main()
