#!/usr/bin/env python3
import json, os, re, logging, shutil, requests
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unicodedata import normalize

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

API_BASE       = os.getenv("API_BASE", "https://api.weatherarb.com")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = "gemini-2.5-flash-lite"
SCORE_MIN      = float(os.getenv("SCORE_THRESHOLD", "5.0"))
MAX_NEW        = int(os.getenv("MAX_ARTICLES", "10"))
KEEP_DAYS      = int(os.getenv("KEEP_DAYS", "7"))
MAX_TOTAL      = int(os.getenv("MAX_TOTAL", "50"))

BLOG  = Path("data/blog_posts");  BLOG.mkdir(parents=True, exist_ok=True)
NEWS  = Path("data/website/news"); NEWS.mkdir(parents=True, exist_ok=True)
FEED  = Path("data/website/data/latest_reports.json"); FEED.parent.mkdir(parents=True, exist_ok=True)

def slugify(t):
    s = normalize("NFKD", t).encode("ascii","ignore").decode("ascii")
    return re.sub(r"[\s_]+","-", re.sub(r"[^\w\s-]","", s).strip().lower())

def now(): return datetime.now(timezone.utc)

def fetch_signals():
    try:
        r = requests.get(f"{API_BASE}/api/v1/europe/top?limit=50", timeout=15)
        data = r.json()
        all_s = data.get("reports") or data.get("data") or []
        ok = [s for s in all_s if (s.get("score") or 0) >= SCORE_MIN]
        log.info(f"Fetched {len(all_s)} signals, {len(ok)} above {SCORE_MIN}")
        return ok[:MAX_NEW]
    except Exception as e:
        log.error(f"Fetch error: {e}"); return []

def fetch_related(city, cc, current_slug, n=3):
    """Fetch related articles for the same city/country."""
    related = []
    try:
        for f in sorted(BLOG.glob("*.json"), reverse=True):
            if len(related) >= n: break
            try:
                m = json.loads(f.read_text())
                if m.get("slug") == current_slug: continue
                if m.get("location") == city or m.get("country_code") == cc:
                    related.append(m)
            except: pass
    except: pass
    return related

def gemini(prompt):
    if not GEMINI_API_KEY: return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    try:
        r = requests.post(url, json={"contents":[{"parts":[{"text":prompt}]}],
            "generationConfig":{"temperature":0.7,"maxOutputTokens":800}}, timeout=30)
        r.raise_for_status()
        raw = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        raw = re.sub(r"```json\s*|\s*```","",raw).strip()
        return json.loads(raw)
    except Exception as e:
        log.error(f"Gemini error: {e}"); return None

def make_article(sig):
    city = sig.get("location") or sig.get("province","—")
    z    = sig.get("z_score", 0)
    sc   = sig.get("score", 0)
    vert = (sig.get("vertical") or sig.get("event_type") or "anomalia").replace("_"," ")
    lvl  = sig.get("anomaly_level","EXTREME")
    sign = "+" if z >= 0 else ""
    hdd  = sig.get("hdd")
    cdd  = sig.get("cdd")
    hum  = sig.get("humidity_pct")
    wind = sig.get("wind_kmh")
    energy_ctx = ""
    if hdd is not None: energy_ctx += f", HDD={hdd:.1f} GG"
    if cdd is not None: energy_ctx += f", CDD={cdd:.1f} GG"
    if hum is not None: energy_ctx += f", Umidita={hum}%"
    if wind is not None: energy_ctx += f", Vento={wind} km/h"
    prompt = f"""Sei un analista meteo senior di WeatherArb. Scrivi in italiano ~250 parole su:
Citta: {city}, Evento: {vert}, Z-Score: {sign}{z:.2f}, Score: {sc:.1f}/10, Livello: {lvl}{energy_ctx}
Rispondi SOLO JSON: {{"title":"...","lead":"...","body":"...","conclusion":"...","agri_impact":"...","logistica_impact":"...","energia_impact":"..."}}
- title: titolo SEO accattivante con citta e evento
- lead: 2 frasi che spiegano l'anomalia in modo chiaro
- body: 3 paragrafi di analisi tecnica accessibile
- conclusion: 1 frase di raccomandazione operativa
- agri_impact: 1 frase impatto per settore agricoltura (max 20 parole)
- logistica_impact: 1 frase impatto per logistica/trasporti (max 20 parole)
- energia_impact: 1 frase impatto per settore energia (max 20 parole)
Tono scientifico accessibile. Nessun prodotto o acquisto."""
    return gemini(prompt)

def save(sig, content):
    city = sig.get("location") or sig.get("province","unknown")
    vert = (sig.get("vertical") or sig.get("event_type") or "meteo").replace("_","-").lower()
    date = now().strftime("%Y-%m-%d")
    slug = f"{date}-{slugify(city)}-{slugify(vert)}"
    if (BLOG/f"{slug}.json").exists():
        log.info(f"Skip duplicate: {slug}"); return None

    z  = sig.get("z_score",0)
    sc = sig.get("score",0)
    cc = sig.get("country_code","it")
    sign = "+" if z >= 0 else ""
    col = "#ef4444" if sc>=7 else "#f97316" if sc>=5 else "#f59e0b"
    hdd = sig.get("hdd")
    cdd = sig.get("cdd")
    hum = sig.get("humidity_pct")
    wind = sig.get("wind_kmh")
    hdd_delta = sig.get("hdd_delta")

    meta = {
        "slug": slug,
        "title": content.get("title", f"{vert} a {city}"),
        "lead": content.get("lead",""),
        "body": content.get("body",""),
        "conclusion": content.get("conclusion",""),
        "agri_impact": content.get("agri_impact",""),
        "logistica_impact": content.get("logistica_impact",""),
        "energia_impact": content.get("energia_impact",""),
        "location": city,
        "country_code": cc,
        "vertical": vert,
        "z_score": round(z,2),
        "score": round(sc,2),
        "anomaly_level": sig.get("anomaly_level","EXTREME"),
        "hdd": hdd, "cdd": cdd, "hdd_delta": hdd_delta,
        "humidity_pct": hum, "wind_kmh": wind,
        "timestamp": now().isoformat(),
        "date": date
    }
    (BLOG/f"{slug}.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2))

    # Fetch related articles
    related = fetch_related(city, cc, slug, 3)
    related_html = ""
    if related:
        col_map = {"CRITICAL":"#ef4444","EXTREME":"#f97316","UNUSUAL":"#f59e0b","NORMAL":"#10b981"}
        related_html = '<div class="rel-grid">'
        for r in related:
            rz = r.get("z_score",0)
            rsign = "+" if rz>=0 else ""
            rcol = col_map.get(r.get("anomaly_level","NORMAL"),"#10b981")
            related_html += (
                f'<a href="/news/{r["slug"]}/" class="rel-card">'
                f'<div class="rel-loc">{r.get("location","—")}</div>'
                f'<div class="rel-title">{r.get("title","—")[:60]}...</div>'
                f'<div class="rel-z" style="color:{rcol}">{rsign}{rz:.2f}σ</div>'
                f'</a>'
            )
        related_html += '</div>'

    # Energy/sector badges
    sector_html = ""
    if any([content.get("agri_impact"), content.get("logistica_impact"), content.get("energia_impact")]):
        sector_html = '<div class="sectors">'
        if content.get("agri_impact"):
            sector_html += f'<div class="sector"><div class="sector-icon">🌾</div><div class="sector-name">Agricoltura</div><div class="sector-desc">{content["agri_impact"]}</div></div>'
        if content.get("logistica_impact"):
            sector_html += f'<div class="sector"><div class="sector-icon">🚛</div><div class="sector-name">Logistica</div><div class="sector-desc">{content["logistica_impact"]}</div></div>'
        if content.get("energia_impact"):
            sector_html += f'<div class="sector"><div class="sector-icon">⚡</div><div class="sector-name">Energia</div><div class="sector-desc">{content["energia_impact"]}</div></div>'
        sector_html += '</div>'

    # Energy data row
    energy_html = ""
    energy_items = []
    if hdd is not None: energy_items.append(f'<div class="eitem"><div class="elabel">HDD oggi</div><div class="eval">{hdd:.1f} GG</div></div>')
    if cdd is not None: energy_items.append(f'<div class="eitem"><div class="elabel">CDD oggi</div><div class="eval">{cdd:.1f} GG</div></div>')
    if hum is not None: energy_items.append(f'<div class="eitem"><div class="elabel">Umidita</div><div class="eval">{hum}%</div></div>')
    if wind is not None: energy_items.append(f'<div class="eitem"><div class="elabel">Vento</div><div class="eval">{wind} km/h</div></div>')
    if hdd_delta is not None:
        delta_col = "#ef4444" if hdd_delta>2 else "#10b981" if hdd_delta<-2 else "#f59e0b"
        energy_items.append(f'<div class="eitem"><div class="elabel">Delta HDD</div><div class="eval" style="color:{delta_col}">{"+"+str(round(hdd_delta,1)) if hdd_delta>=0 else round(hdd_delta,1)} GG</div></div>')
    if energy_items:
        energy_html = '<div class="energy-row">'+''.join(energy_items)+'</div>'

    city_slug = slugify(city)

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{meta['title']} | WeatherArb</title>
  <meta name="description" content="{meta['lead'][:160]}">
  <link rel="canonical" href="https://weatherarb.com/news/{slug}/">
  <style>
    :root{{--bg:#040608;--s:#0a0d12;--b:#141920;--ba:#1e2d3d;--t:#c8d6e5;--m:#4a5568;--bl:#3b82f6;--g:#10b981}}
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:var(--bg);color:var(--t);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;min-height:100vh}}
    .hdr{{border-bottom:1px solid var(--b);padding:14px 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;background:rgba(4,6,8,.95);backdrop-filter:blur(12px)}}
    .logo{{font-size:13px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--t);text-decoration:none}}.logo span{{color:var(--bl)}}
    .nav a{{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:var(--m);text-decoration:none;margin-left:16px}}.nav a:hover{{color:var(--t)}}
    .layout{{max-width:1100px;margin:0 auto;padding:48px 24px 80px;display:grid;grid-template-columns:1fr 320px;gap:48px}}
    @media(max-width:900px){{.layout{{grid-template-columns:1fr;gap:32px}}.sidebar{{order:2}}}}
    .bc{{font-size:11px;text-transform:uppercase;letter-spacing:.15em;color:var(--m);margin-bottom:20px}}.bc a{{color:var(--m);text-decoration:none}}
    .badge{{display:inline-flex;align-items:center;gap:8px;background:rgba(59,130,246,.08);border:1px solid rgba(59,130,246,.18);border-radius:100px;padding:5px 14px;font-size:11px;text-transform:uppercase;letter-spacing:.15em;color:var(--bl);margin-bottom:16px}}
    h1{{font-size:clamp(24px,4vw,42px);font-weight:800;letter-spacing:-.02em;line-height:1.15;margin-bottom:16px;color:#fff}}
    .meta{{font-size:12px;color:var(--m);margin-bottom:28px;display:flex;gap:16px;flex-wrap:wrap}}
    .meta span{{display:flex;align-items:center;gap:4px}}
    .zbox{{font-size:52px;font-weight:800;color:{col};text-align:center;padding:24px;background:var(--s);border:1px solid var(--b);border-radius:14px;margin-bottom:24px;letter-spacing:-.02em}}
    .zbox small{{display:block;font-size:10px;text-transform:uppercase;letter-spacing:.15em;color:var(--m);margin-top:6px}}
    .energy-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(80px,1fr));gap:1px;background:var(--b);border:1px solid var(--b);border-radius:10px;overflow:hidden;margin-bottom:24px}}
    .eitem{{background:var(--s);padding:12px 14px;text-align:center}}
    .elabel{{font-size:9px;text-transform:uppercase;letter-spacing:.12em;color:var(--m);margin-bottom:4px}}
    .eval{{font-size:15px;font-weight:700}}
    .lead{{font-size:17px;line-height:1.6;color:#fff;margin-bottom:20px;font-weight:500}}
    .body-text{{font-size:15px;line-height:1.75;margin-bottom:20px;color:var(--t)}}
    .body-text p{{margin-bottom:16px}}
    .concl{{font-size:14px;line-height:1.6;color:var(--m);padding:16px 20px;background:var(--s);border-left:3px solid var(--bl);border-radius:0 8px 8px 0;margin-bottom:28px}}
    .stitle{{font-size:10px;text-transform:uppercase;letter-spacing:.2em;color:var(--m);margin-bottom:14px;padding-bottom:8px;border-bottom:1px solid var(--b)}}
    .sectors{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-bottom:28px}}
    .sector{{background:var(--s);border:1px solid var(--b);border-radius:10px;padding:14px}}
    .sector-icon{{font-size:18px;margin-bottom:6px}}
    .sector-name{{font-size:11px;font-weight:700;color:#fff;margin-bottom:4px;text-transform:uppercase;letter-spacing:.08em}}
    .sector-desc{{font-size:12px;color:var(--m);line-height:1.4}}
    .back{{display:inline-flex;align-items:center;gap:6px;padding:10px 20px;border:1px solid var(--b);border-radius:8px;color:var(--m);text-decoration:none;font-size:13px;margin-bottom:28px;transition:.2s}}.back:hover{{border-color:var(--ba);color:var(--t)}}
    /* SIDEBAR */
    .sidebar{{}}
    .sidebar-box{{background:var(--s);border:1px solid var(--b);border-radius:12px;padding:20px;margin-bottom:20px}}
    .sidebar-title{{font-size:10px;text-transform:uppercase;letter-spacing:.15em;color:var(--m);margin-bottom:14px}}
    .live-z{{font-size:36px;font-weight:800;text-align:center;padding:12px 0;font-variant-numeric:tabular-nums}}
    .live-label{{font-size:10px;text-transform:uppercase;letter-spacing:.12em;color:var(--m);text-align:center;margin-bottom:4px}}
    .live-lbl{{font-size:13px;font-weight:600;text-align:center;margin-bottom:12px}}
    .live-sub{{font-size:11px;color:var(--m);text-align:center}}
    /* NEWSLETTER */
    .nl-box{{background:linear-gradient(135deg,rgba(59,130,246,.08),rgba(16,185,129,.05));border:1px solid rgba(59,130,246,.2);border-radius:12px;padding:20px;margin-bottom:20px}}
    .nl-title{{font-size:14px;font-weight:700;color:#fff;margin-bottom:6px}}
    .nl-sub{{font-size:12px;color:var(--m);line-height:1.5;margin-bottom:12px}}
    .nl-input{{width:100%;background:rgba(255,255,255,.05);border:1px solid var(--b);border-radius:8px;padding:9px 12px;color:var(--t);font-size:13px;outline:none;margin-bottom:8px}}
    .nl-btn{{width:100%;background:var(--bl);color:#fff;border:none;border-radius:8px;padding:10px;font-size:13px;font-weight:700;cursor:pointer}}
    .nl-msg{{display:none;font-size:12px;margin-top:8px;padding:8px;border-radius:6px}}
    /* RELATED */
    .rel-grid{{display:flex;flex-direction:column;gap:8px}}
    .rel-card{{background:var(--s);border:1px solid var(--b);border-radius:8px;padding:12px;text-decoration:none;color:var(--t);transition:.2s}}.rel-card:hover{{border-color:var(--ba)}}
    .rel-loc{{font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:var(--m);margin-bottom:4px}}
    .rel-title{{font-size:13px;font-weight:600;line-height:1.3;margin-bottom:6px}}
    .rel-z{{font-size:13px;font-weight:700}}
    /* SHARE */
    .share-btns{{display:flex;gap:8px}}
    .share-btn{{flex:1;padding:9px;border-radius:8px;border:1px solid var(--b);background:var(--s);color:var(--m);text-decoration:none;font-size:12px;font-weight:600;text-align:center;transition:.2s;cursor:pointer}}.share-btn:hover{{border-color:var(--ba);color:var(--t)}}
    .ftr{{border-top:1px solid var(--b);padding:20px;text-align:center;font-size:11px;color:var(--m)}}.ftr a{{color:var(--m);text-decoration:none}}
  </style>
</head>
<body>
<header class="hdr">
  <a href="/" class="logo">Weather<span>Arb</span></a>
  <nav class="nav"><a href="/news/">News</a><a href="/data/">Data</a><a href="/api.html">API</a></nav>
</header>

<div class="layout">
  <!-- MAIN CONTENT -->
  <main>
    <div class="bc"><a href="/">WeatherArb</a> / <a href="/news/">Reports</a> / {city}</div>
    <div class="badge">📡 {meta['anomaly_level']} &middot; {date}</div>
    <h1>{meta['title']}</h1>
    <div class="meta">
      <span>📍 {city}</span>
      <span>⚡ {vert.replace('-',' ').title()}</span>
      <span>Score {sc}/10</span>
    </div>

    <div class="zbox">{sign}{z:.2f}σ<small>Z-Score vs baseline NASA POWER 25 anni</small></div>

    {energy_html}

    <p class="lead">{meta['lead']}</p>
    <div class="body-text">{''.join(f'<p>{para}</p>' for para in (meta['body'] if isinstance(meta['body'], list) else meta['body'].split(chr(10))) if str(para).strip())}</div>
    <div class="concl">{meta['conclusion']}</div>

    {f'<div class="stitle">Settori Impattati</div>{sector_html}' if sector_html else ''}

    <a href="/news/" class="back">← Tutti i Reports</a>

    {f'<div class="stitle">Altri Report Correlati</div>{related_html}' if related_html else ''}
  </main>

  <!-- SIDEBAR -->
  <aside class="sidebar">
    <!-- LIVE DATA -->
    <div class="sidebar-box">
      <div class="sidebar-title">Z-Score Live &mdash; {city}</div>
      <div class="live-z" id="live-z" style="color:{col}">...</div>
      <div class="live-label">Score</div>
      <div class="live-lbl" id="live-lbl">Caricamento...</div>
      <div class="live-sub" id="live-sub">vs baseline NASA POWER 25 anni</div>
    </div>

    <!-- NEWSLETTER -->
    <div class="nl-box">
      <div class="nl-title">Alert per {city}</div>
      <div class="nl-sub">Ricevi anomalie meteo per {city} nella tua inbox. Gratuito.</div>
      <input id="nl-email" class="nl-input" type="email" placeholder="La tua email" onkeydown="if(event.key==='Enter')nlsub()">
      <button class="nl-btn" onclick="nlsub()">Iscriviti →</button>
      <div id="nl-msg" class="nl-msg"></div>
    </div>

    <!-- SHARE -->
    <div class="sidebar-box">
      <div class="sidebar-title">Condividi</div>
      <div class="share-btns">
        <a class="share-btn" href="https://twitter.com/intent/tweet?text={meta['title']}&url=https://weatherarb.com/news/{slug}/" target="_blank">𝕏 Twitter</a>
        <a class="share-btn" href="https://www.linkedin.com/sharing/share-offsite/?url=https://weatherarb.com/news/{slug}/" target="_blank">in LinkedIn</a>
      </div>
    </div>

    <!-- LANDING LINK -->
    <div class="sidebar-box">
      <div class="sidebar-title">Intelligence per {city}</div>
      <a href="/{cc}/{city_slug}/" style="display:block;background:var(--bl);color:#fff;text-align:center;padding:10px;border-radius:8px;text-decoration:none;font-size:13px;font-weight:700">Dashboard {city} →</a>
    </div>
  </aside>
</div>

<footer class="ftr">
  <a href="/">WeatherArb</a> &middot; Independent Weather Intelligence Agency &middot;
  <a href="/about.html">Methodology</a> &middot; <a href="/api.html">API</a>
</footer>

<script>
// Live Z-Score
async function loadLive(){{
  try{{
    var r = await fetch('{API_BASE}/api/v1/pulse/{city_slug}');
    var d = await r.json();
    var w = d.weather||{{}};
    var z = w.z_score||0;
    var sc = d.signal?d.signal.score:0;
    var lbl = w.anomaly_label||w.anomaly_level||'';
    var col = sc>=7?'#ef4444':sc>=5?'#f97316':sc>=3?'#f59e0b':'#10b981';
    var el = document.getElementById('live-z');
    if(el){{ el.textContent=(z>=0?'+':'')+z.toFixed(2)+'σ'; el.style.color=col; }}
    var ll = document.getElementById('live-lbl');
    if(ll){{ ll.textContent=lbl; ll.style.color=col; }}
    var ls = document.getElementById('live-sub');
    if(ls){{ ls.textContent='Score '+sc.toFixed(1)+'/10 &middot; aggiornato ora'; }}
  }}catch(e){{}}
}}
loadLive(); setInterval(loadLive, 3600000);

// Newsletter
function nlsub(){{
  var e = document.getElementById('nl-email').value.trim();
  var m = document.getElementById('nl-msg');
  if(!e||e.indexOf('@')<0){{m.style.display='block';m.style.background='rgba(239,68,68,.1)';m.style.color='#ef4444';m.textContent='Email non valida';return;}}
  fetch('{API_BASE}/api/newsletter/subscribe?email='+encodeURIComponent(e)+'&city={city}&country_code={cc}',{{method:'POST'}})
    .then(r=>r.json())
    .then(d=>{{m.style.display='block';m.style.background='rgba(16,185,129,.1)';m.style.color='#10b981';m.textContent=d.status==='already_subscribed'?'Sei gia iscritto!':'Iscritto!';document.getElementById('nl-email').style.display='none';document.querySelector('.nl-btn').style.display='none';}})
    .catch(()=>{{m.style.display='block';m.style.background='rgba(239,68,68,.1)';m.style.color='#ef4444';m.textContent='Errore - riprova';}});
}}
</script>
</body>
</html>"""

    d = NEWS/slug; d.mkdir(parents=True, exist_ok=True)
    (d/"index.html").write_text(html)
    log.info(f"✅ {slug}"); return meta

def cleanup():
    cutoff = now() - timedelta(days=KEEP_DAYS)
    removed = 0
    for f in sorted(BLOG.glob("*.json")):
        try:
            m = json.loads(f.read_text())
            ts = datetime.fromisoformat(m.get("timestamp","2020-01-01T00:00:00+00:00").replace("Z","+00:00"))
            if ts < cutoff:
                slug = m.get("slug", f.stem)
                nd = NEWS/slug
                if nd.exists(): shutil.rmtree(nd)
                f.unlink(); removed += 1
                log.info(f"🗑  {slug}")
        except Exception as e:
            log.warning(f"Cleanup skip {f.name}: {e}")
    all_p = sorted(BLOG.glob("*.json"))
    if len(all_p) > MAX_TOTAL:
        for f in all_p[:len(all_p)-MAX_TOTAL]:
            try:
                m = json.loads(f.read_text()); slug = m.get("slug",f.stem)
                nd = NEWS/slug
                if nd.exists(): shutil.rmtree(nd)
                f.unlink(); removed += 1
            except: pass
    log.info(f"Cleanup: {removed} rimossi")

def update_feed():
    posts = []
    for f in sorted(BLOG.glob("*.json"), reverse=True):
        try:
            m = json.loads(f.read_text())
            posts.append({
                "slug":m.get("slug"),"title":m.get("title"),
                "lead":m.get("lead","")[:160]+"...","location":m.get("location"),
                "country_code":m.get("country_code","it"),"vertical":m.get("vertical"),
                "z_score":m.get("z_score",0),"score":m.get("score",0),
                "anomaly_level":m.get("anomaly_level"),"date":m.get("date"),
                "url":f"/news/{m.get('slug')}/","excerpt":m.get("lead","")[:180]
            })
        except: pass
    FEED.write_text(json.dumps({"last_updated":now().isoformat(),"count":len(posts),"reports":posts[:20]},ensure_ascii=False,indent=2))
    log.info(f"✅ feed aggiornato — {len(posts)} articoli")

def update_news_index():
    posts = list(sorted(BLOG.glob("*.json"), reverse=True))[:50]
    col_map = {"CRITICAL":"#ef4444","EXTREME":"#f97316","UNUSUAL":"#f59e0b","NORMAL":"#10b981"}
    cards = ""
    for f in posts:
        try:
            m = json.loads(f.read_text())
            z=m.get("z_score",0); sc=m.get("score",0)
            sign="+" if z>=0 else ""
            col=col_map.get(m.get("anomaly_level","NORMAL"),"#10b981")
            cards += (
                f'<a href="/news/{m["slug"]}/" class="card">'
                f'<div class="ct"><span class="loc">{m.get("location","—")}</span>'
                f'<span class="ev">{(m.get("vertical") or "").replace("-"," ").upper()}</span></div>'
                f'<h2>{m.get("title","—")}</h2>'
                f'<p>{m.get("lead","")[:110]}...</p>'
                f'<div class="cf"><span style="color:{col};font-weight:700">{sign}{z:.2f}σ</span>'
                f'<span style="color:{col};font-size:10px;font-weight:700;text-transform:uppercase">{m.get("anomaly_level","")}</span>'
                f'<span class="dt">{m.get("date","")}</span></div>'
                f'</a>\n'
            )
        except: pass

    html = f"""<!DOCTYPE html>
<html lang="it"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Intelligence Reports | WeatherArb</title>
<meta name="description" content="Anomalie meteo in Europa. Z-Score su baseline NASA POWER 25 anni. WeatherArb Weather Intelligence Agency.">
<style>
:root{{--bg:#040608;--s:#0a0d12;--b:#141920;--t:#c8d6e5;--m:#4a5568;--bl:#3b82f6}}
*{{box-sizing:border-box;margin:0;padding:0}}body{{background:var(--bg);color:var(--t);font-family:-apple-system,sans-serif}}
.hdr{{border-bottom:1px solid var(--b);padding:14px 24px;display:flex;align-items:center;justify-content:space-between}}
.logo{{font-size:13px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--t);text-decoration:none}}.logo span{{color:var(--bl)}}
.nav a{{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:var(--m);text-decoration:none;margin-left:16px}}
.wrap{{max-width:1100px;margin:0 auto;padding:48px 24px 80px}}
h1{{font-size:clamp(28px,4vw,48px);font-weight:800;letter-spacing:-.02em;margin-bottom:8px}}
.sub{{font-size:13px;color:var(--m);margin-bottom:32px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}}
.card{{background:var(--s);border:1px solid var(--b);border-radius:12px;padding:22px;text-decoration:none;color:var(--t);display:flex;flex-direction:column;gap:10px;transition:border-color .2s}}.card:hover{{border-color:var(--bl)}}
.ct{{display:flex;gap:8px}}.loc{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:var(--bl)}}.ev{{font-size:10px;color:var(--m);text-transform:uppercase}}
.card h2{{font-size:15px;font-weight:700;line-height:1.3}}.card p{{font-size:13px;color:var(--m);line-height:1.5;flex:1}}
.cf{{display:flex;gap:10px;align-items:center;padding-top:10px;border-top:1px solid var(--b);font-size:12px}}.dt{{margin-left:auto;color:var(--m)}}
.ftr{{border-top:1px solid var(--b);padding:20px;text-align:center;font-size:11px;color:var(--m)}}.ftr a{{color:var(--m);text-decoration:none}}
</style></head><body>
<header class="hdr"><a href="/" class="logo">Weather<span>Arb</span></a>
<nav class="nav"><a href="/data/">Data</a><a href="/map.html">Map</a><a href="/alerts.html">Alerts</a></nav></header>
<div class="wrap"><h1>Intelligence Reports</h1>
<p class="sub">{len(posts)} analisi &middot; ERA5-Land + NASA POWER &middot; Aggiornato ogni 6 ore</p>
<div class="grid">{cards}</div></div>
<footer class="ftr"><a href="/">WeatherArb</a> &middot; <a href="/about.html">Methodology</a> &middot; <a href="/api.html">API</a></footer>
</body></html>"""
    (NEWS/"index.html").write_text(html)
    log.info(f"✅ news/index.html — {len(posts)} articoli")

def main():
    log.info("=== WeatherArb Auto-Publisher START ===")
    cleanup()
    sigs = fetch_signals()
    published = 0
    for sig in sigs:
        content = make_article(sig)
        if content:
            meta = save(sig, content)
            if meta: published += 1
    if not sigs: log.info("Nessuna anomalia sopra soglia")
    else: log.info(f"Pubblicati {published} nuovi articoli")
    update_feed()
    update_news_index()
    log.info("=== WeatherArb Auto-Publisher END ===")

if __name__ == "__main__":
    main()
