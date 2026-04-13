#!/usr/bin/env python3
"""
WeatherArb — Newsletter System Builder
Genera:
1. patch per api/main.py (endpoint subscribe con Resend)
2. patch per le landing (capture widget)
3. tools/send_weekly_briefing.py
"""

# ─── 1. ENDPOINT SUBSCRIBE (va in api/main.py) ───────────────────────────────

SUBSCRIBE_ENDPOINT = '''
# ─── NEWSLETTER ──────────────────────────────────────────────────────────────
import smtplib, csv as _csv2
from pathlib import Path as _Path

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
SUBSCRIBERS_FILE = "data/newsletter_subscribers.csv"

def _resend_send(to: str, subject: str, html: str):
    """Invia email via Resend API."""
    import urllib.request, json as _json
    payload = _json.dumps({
        "from": "WeatherArb Intelligence <alerts@weatherarb.com>",
        "to": [to],
        "subject": subject,
        "html": html
    }).encode()
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={"Authorization": f"Bearer {RESEND_API_KEY}",
                 "Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status == 200
    except Exception as e:
        logger.warning(f"Resend error: {e}")
        return False

@app.post("/api/newsletter/subscribe")
def newsletter_subscribe(email: str, city: str = "", country_code: str = "it"):
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Email non valida")

    # Salva su CSV
    f = _Path(SUBSCRIBERS_FILE)
    f.parent.mkdir(parents=True, exist_ok=True)
    existing = set()
    if f.exists():
        with open(f, newline="", encoding="utf-8") as fp:
            existing = {row[0].strip().lower() for row in _csv2.reader(fp) if row}

    email_lower = email.strip().lower()
    if email_lower in existing:
        return {"status": "already_subscribed", "message": "Sei già iscritto!"}

    with open(f, "a", newline="", encoding="utf-8") as fp:
        _csv2.writer(fp).writerow([
            email_lower, city, country_code,
            datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        ])
    logger.info(f"New subscriber: {email_lower} ({city})")

    # Welcome email
    city_label = city or "Europa"
    html = f"""<!DOCTYPE html>
<html><body style="background:#040608;color:#c8d6e5;font-family:-apple-system,sans-serif;max-width:600px;margin:0 auto;padding:40px 24px">
<div style="text-align:center;margin-bottom:32px">
  <h1 style="font-size:28px;font-weight:800;letter-spacing:-.02em;color:#fff">
    Weather<span style="color:#3b82f6">Arb</span>
  </h1>
  <p style="color:#4a5568;font-size:13px;text-transform:uppercase;letter-spacing:.15em">Intelligence Agency</p>
</div>
<div style="background:#0a0d12;border:1px solid #141920;border-radius:12px;padding:32px;margin-bottom:24px">
  <h2 style="font-size:20px;font-weight:700;margin-bottom:12px">✅ Iscrizione confermata</h2>
  <p style="font-size:15px;line-height:1.6;color:#c8d6e5;margin-bottom:16px">
    Ora monitoriamo le anomalie meteo per <strong style="color:#3b82f6">{city_label}</strong> e ti avvisiamo quando lo Z-Score supera la soglia critica.
  </p>
  <p style="font-size:13px;color:#4a5568;line-height:1.6">
    Riceverai:<br>
    • Alert immediati per anomalie CRITICAL (score ≥ 8.0)<br>
    • Briefing settimanale ogni lunedì con le top 5 anomalie EU<br>
    • Analisi tecnica basata su baseline NASA POWER 25 anni
  </p>
</div>
<div style="text-align:center;margin-bottom:24px">
  <a href="https://weatherarb.com/{country_code}/" 
     style="display:inline-block;background:#3b82f6;color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:700;font-size:14px">
    Vedi i segnali live →
  </a>
</div>
<p style="font-size:11px;color:#4a5568;text-align:center;border-top:1px solid #141920;padding-top:16px">
  WeatherArb · Independent Weather Intelligence Agency<br>
  <a href="https://weatherarb.com" style="color:#4a5568">weatherarb.com</a> · 
  Dati: NASA POWER, ERA5-Land, OpenWeatherMap<br>
  <a href="https://weatherarb.com/unsubscribe?email={email_lower}" style="color:#4a5568">Cancella iscrizione</a>
</p>
</body></html>"""

    if RESEND_API_KEY:
        _resend_send(email_lower, f"✅ WeatherArb Intelligence — Iscrizione confermata per {city_label}", html)

    return {"status": "subscribed", "message": f"Benvenuto! Riceverai alert per {city_label}"}

@app.post("/api/newsletter/unsubscribe")
def newsletter_unsubscribe(email: str):
    f = _Path(SUBSCRIBERS_FILE)
    if not f.exists():
        return {"status": "not_found"}
    rows = []
    removed = False
    with open(f, newline="", encoding="utf-8") as fp:
        for row in _csv2.reader(fp):
            if row and row[0].strip().lower() != email.strip().lower():
                rows.append(row)
            else:
                removed = True
    with open(f, "w", newline="", encoding="utf-8") as fp:
        _csv2.writer(fp).writerows(rows)
    return {"status": "unsubscribed" if removed else "not_found"}

@app.get("/api/newsletter/count")
def newsletter_count():
    f = _Path(SUBSCRIBERS_FILE)
    if not f.exists():
        return {"count": 0}
    with open(f, newline="", encoding="utf-8") as fp:
        count = sum(1 for row in _csv2.reader(fp) if row)
    return {"count": count}
'''

# ─── 2. CAPTURE WIDGET HTML ───────────────────────────────────────────────────

def get_capture_widget(city: str, cc: str) -> str:
    return f"""
  <!-- NEWSLETTER CAPTURE -->
  <div style="background:linear-gradient(135deg,rgba(59,130,246,.08),rgba(16,185,129,.05));border:1px solid rgba(59,130,246,.2);border-radius:12px;padding:28px;margin:28px 0" id="nl-box">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
      <span style="font-size:20px">📬</span>
      <div>
        <div style="font-size:15px;font-weight:700;color:#fff">Intelligence Briefing per {city}</div>
        <div style="font-size:12px;color:#4a5568;margin-top:2px">Alert immediati + briefing settimanale · Gratuito</div>
      </div>
    </div>
    <p style="font-size:13px;color:#c8d6e5;line-height:1.6;margin-bottom:16px">
      Ricevi l'analisi dettagliata delle anomalie meteo per {city} direttamente nella tua inbox. Basato su Z-Score NASA POWER — non semplici previsioni.
    </p>
    <div id="nl-form" style="display:flex;gap:8px;flex-wrap:wrap">
      <input id="nl-email" type="email" placeholder="La tua email"
        style="flex:1;min-width:200px;background:rgba(255,255,255,.05);border:1px solid #1e2d3d;border-radius:8px;padding:10px 14px;color:#c8d6e5;font-size:13px;outline:none">
      <button onclick="nlSubscribe()"
        style="background:#3b82f6;color:#fff;border:none;border-radius:8px;padding:10px 20px;font-size:13px;font-weight:700;cursor:pointer;white-space:nowrap">
        Iscriviti Gratis →
      </button>
    </div>
    <div id="nl-msg" style="display:none;font-size:13px;margin-top:12px;padding:10px 14px;border-radius:8px"></div>
    <p style="font-size:10px;color:#4a5568;margin-top:10px">Nessuno spam. Cancellazione con un click.</p>
  </div>
  <script>
  async function nlSubscribe(){{
    const email = document.getElementById('nl-email').value.trim();
    const msg = document.getElementById('nl-msg');
    if(!email || !email.includes('@')){{
      msg.style.display='block';msg.style.background='rgba(239,68,68,.1)';msg.style.color='#ef4444';
      msg.textContent='Inserisci un email valida';return;
    }}
    try{{
      const r = await fetch('https://api.weatherarb.com/api/newsletter/subscribe?email='+encodeURIComponent(email)+'&city={city}&country_code={cc}',{{method:'POST'}});
      const d = await r.json();
      if(d.status==='subscribed'||d.status==='already_subscribed'){{
        document.getElementById('nl-form').style.display='none';
        msg.style.display='block';msg.style.background='rgba(16,185,129,.1)';msg.style.color='#10b981';
        msg.textContent=d.status==='subscribed'?'✅ Iscritto! Controlla la tua email.':'✅ Sei già iscritto!';
      }}
    }}catch(e){{
      msg.style.display='block';msg.style.background='rgba(239,68,68,.1)';msg.style.color='#ef4444';
      msg.textContent='Errore — riprova tra poco';
    }}
  }}
  document.getElementById('nl-email').addEventListener('keydown',e=>e.key==='Enter'&&nlSubscribe());
  </script>"""


# ─── 3. WEEKLY BRIEFING SCRIPT ───────────────────────────────────────────────

WEEKLY_BRIEFING = '''#!/usr/bin/env python3
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
            return re.sub(r"```json\\s*|\\s*```","",raw).strip()
    except Exception as e:
        log.error(f"Gemini error: {e}"); return None


def generate_briefing_html(signals):
    date_str = datetime.now(timezone.utc).strftime("%d %B %Y")
    week_num = datetime.now(timezone.utc).isocalendar()[1]

    # Gemini executive summary
    signals_txt = "\\n".join([
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
'''

# ─── 4. PATCH API/MAIN.PY ────────────────────────────────────────────────────

def patch_main():
    path = "api/main.py"
    content = open(path).read()

    if "newsletter/subscribe" in content:
        print("ℹ️  Endpoint subscribe già presente in main.py")
        return True

    # Inserisci prima dell'ultimo endpoint o alla fine prima di if __name__
    anchor = '\nif __name__ == "__main__":'
    if anchor in content:
        content = content.replace(anchor, SUBSCRIBE_ENDPOINT + anchor)
    else:
        content += SUBSCRIBE_ENDPOINT

    open(path, "w").write(content)
    print("✅ Endpoint newsletter aggiunto a api/main.py")
    return True


# ─── 5. PATCH LANDING PAGES ──────────────────────────────────────────────────

def patch_landings():
    import re, json
    from pathlib import Path
    from unicodedata import normalize

    def slugify(t):
        s = normalize("NFKD", t).encode("ascii","ignore").decode("ascii")
        return re.sub(r"[\s_]+","-", re.sub(r"[^\w\s-]","",s).strip().lower())

    COUNTRY_CODE = {
        "Italy":"it","Germany":"de","France":"fr","Spain":"es",
        "United Kingdom":"gb","Sweden":"se","Netherlands":"nl",
        "Poland":"pl","Austria":"at","Switzerland":"ch",
        "Belgium":"be","Portugal":"pt","Denmark":"dk","Norway":"no"
    }
    CITY_FALLBACK = {
        "münchen":"de","hamburg":"de","berlin":"de","frankfurt":"de",
        "madrid":"es","barcelona":"es","paris":"fr","london":"gb",
        "stockholm":"se","amsterdam":"nl","warszawa":"pl","wien":"at",
        "zürich":"ch","bruxelles":"be","lisboa":"pt","københavn":"dk","oslo":"no"
    }

    with open("data/province_coords.json") as f:
        raw = json.load(f)
    provinces = raw["province"] if "province" in raw else raw

    patched = 0
    skipped = 0

    for city in provinces:
        name = city.get("nome","")
        cn = city.get("country","Italy")
        cc = COUNTRY_CODE.get(cn, CITY_FALLBACK.get(name.lower(), "it"))
        slug = slugify(name)
        path = Path(f"data/website/{cc}/{slug}/index.html")

        if not path.exists():
            skipped += 1
            continue

        content = path.read_text(encoding="utf-8")
        if "nl-box" in content or "nlSubscribe" in content:
            skipped += 1
            continue

        widget = get_capture_widget(name, cc)

        # Inserisci prima del footer o prima di </main>
        if "</main>" in content:
            content = content.replace("</main>", widget + "\n</main>")
        elif '<div class="abox"' in content:
            content = content.replace('<div class="abox"', widget + '\n<div class="abox"')
        elif "</body>" in content:
            content = content.replace("</body>", widget + "\n</body>")
        else:
            content += widget

        path.write_text(content, encoding="utf-8")
        patched += 1

    print(f"✅ Widget cattura email aggiunto a {patched} landing ({skipped} saltate)")
    return patched


# ─── MAIN ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    from pathlib import Path

    print("WeatherArb — Newsletter System Builder\n")

    # 1. Weekly briefing script
    Path("tools/send_weekly_briefing.py").write_text(WEEKLY_BRIEFING)
    print("✅ tools/send_weekly_briefing.py creato")

    # 2. Patch api/main.py
    if Path("api/main.py").exists():
        patch_main()
    else:
        print("⚠️  api/main.py non trovato — skip")

    # 3. Patch landing pages
    if Path("data/province_coords.json").exists():
        patch_landings()
    else:
        print("⚠️  province_coords.json non trovato — skip")

    print(f"""
╔══════════════════════════════════════════════════════╗
║  Newsletter System — Setup Completato                ║
╚══════════════════════════════════════════════════════╝

📋 Prossimi step:

1. Aggiungi RESEND_API_KEY su Railway:
   → railway.app → Variables → RESEND_API_KEY

2. Aggiungi RESEND_API_KEY su GitHub Secrets:
   → Settings → Secrets → RESEND_API_KEY

3. Push tutto:
   git add -A
   git commit -m "feat: newsletter system — subscribe endpoint + capture widget"
   git push origin main

4. Testa iscrizione:
   curl -X POST "https://api.weatherarb.com/api/newsletter/subscribe?email=test@example.com&city=Milano&country_code=it"

5. Conta iscritti:
   curl "https://api.weatherarb.com/api/newsletter/count"

6. Invia briefing manuale:
   GEMINI_API_KEY=xxx RESEND_API_KEY=xxx python3 tools/send_weekly_briefing.py
""")
