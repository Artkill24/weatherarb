#!/usr/bin/env python3
"""
WeatherArb — Auto Publisher
Genera articoli Gemini per anomalie EXTREME/CRITICAL e pulisce i vecchi
Eseguito da GitHub Actions ogni 6h
"""

import json
import os
import re
import sys
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unicodedata import normalize

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ─── CONFIG ─────────────────────────────────────────────────────────────────
API_BASE        = os.getenv("API_BASE", "https://api.weatherarb.com")
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL    = "gemini-2.5-flash-preview-04-17"
SCORE_THRESHOLD = float(os.getenv("SCORE_THRESHOLD", "6.0"))
MAX_ARTICLES    = int(os.getenv("MAX_ARTICLES", "6"))      # per run
KEEP_DAYS       = int(os.getenv("KEEP_DAYS", "30"))        # articoli più vecchi vengono eliminati
MAX_TOTAL       = int(os.getenv("MAX_TOTAL", "50"))        # max articoli totali nel sito

BLOG_DIR    = Path("data/blog_posts")
NEWS_DIR    = Path("data/website/news")
REPORTS_JSON = Path("data/website/data/latest_reports.json")
SITEMAP     = Path("data/website/sitemap.xml")

BLOG_DIR.mkdir(parents=True, exist_ok=True)
NEWS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_JSON.parent.mkdir(parents=True, exist_ok=True)

# ─── HELPERS ────────────────────────────────────────────────────────────────
def slugify(text: str) -> str:
    s = normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    return re.sub(r"[\s_]+", "-", s)

def today_str() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")

# ─── STEP 1: Fetch top anomalie ─────────────────────────────────────────────
def fetch_top_signals() -> list:
    try:
        r = requests.get(f"{API_BASE}/api/v1/europe/top?limit=50", timeout=15)
        r.raise_for_status()
        data = r.json()
        signals = data.get("reports") or data.get("data") or []
        filtered = [s for s in signals if (s.get("score") or 0) >= SCORE_THRESHOLD]
        log.info(f"Fetched {len(signals)} signals, {len(filtered)} above threshold {SCORE_THRESHOLD}")
        return filtered[:MAX_ARTICLES]
    except Exception as e:
        log.error(f"Failed to fetch signals: {e}")
        return []

# ─── STEP 2: Genera articolo con Gemini ─────────────────────────────────────
def generate_article(signal: dict) -> dict | None:
    if not GEMINI_API_KEY:
        log.warning("GEMINI_API_KEY non impostata — skip generazione")
        return None

    city     = signal.get("location") or signal.get("province", "—")
    country  = signal.get("country", "Europe")
    zscore   = signal.get("z_score", 0)
    score    = signal.get("score", 0)
    vertical = (signal.get("vertical") or signal.get("event_type") or "anomalia meteo").replace("_", " ")
    level    = signal.get("anomaly_level", "EXTREME")
    sign     = "+" if zscore >= 0 else ""

    prompt = f"""Sei un analista meteorologico senior di WeatherArb, un'agenzia indipendente di weather intelligence.

Scrivi un articolo giornalistico in italiano di circa 250 parole su questa anomalia:

Città: {city} ({country})
Evento: {vertical}
Z-Score: {sign}{zscore:.2f} (deviazione dalla media storica NASA POWER 25 anni)
Score WeatherArb: {score:.1f}/10
Livello: {level}

Struttura:
- Titolo accattivante e informativo (max 80 caratteri)
- Lead di 2 frasi che spiega l'anomalia in termini semplici
- Corpo: cosa significa questo Z-Score, perché è significativo statisticamente, impatti pratici attesi
- Conclusione: finestra temporale di monitoraggio

Tono: scientifico ma accessibile, autorevole, zero allarmismo.
NON menzionare prodotti, negozi, acquisti o affiliazioni.
Rispondi SOLO con JSON valido in questo formato esatto:
{{"title": "...", "lead": "...", "body": "...", "conclusion": "..."}}"""

    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"temperature": 0.7, "maxOutputTokens": 800}},
            timeout=30
        )
        r.raise_for_status()
        raw = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        # Strip markdown fences
        raw = re.sub(r"```json\s*|\s*```", "", raw).strip()
        content = json.loads(raw)
        return content
    except Exception as e:
        log.error(f"Gemini error for {city}: {e}")
        return None

# ─── STEP 3: Salva articolo ──────────────────────────────────────────────────
def save_article(signal: dict, content: dict) -> dict | None:
    city     = signal.get("location") or signal.get("province", "unknown")
    vertical = (signal.get("vertical") or signal.get("event_type") or "anomalia").replace("_", "-").lower()
    zscore   = signal.get("z_score", 0)
    score    = signal.get("score", 0)
    cc       = signal.get("country_code", "it")
    date     = today_str()
    slug     = f"{date}-{slugify(city)}-{slugify(vertical)}"

    # Evita duplicati: stesso slug già pubblicato oggi
    if (BLOG_DIR / f"{slug}.json").exists():
        log.info(f"Skip duplicate: {slug}")
        return None

    meta = {
        "slug": slug,
        "title": content.get("title", f"{vertical.title()} a {city}"),
        "lead": content.get("lead", ""),
        "body": content.get("body", ""),
        "conclusion": content.get("conclusion", ""),
        "location": city,
        "country_code": cc,
        "vertical": vertical,
        "z_score": round(zscore, 2),
        "score": round(score, 2),
        "anomaly_level": signal.get("anomaly_level", "EXTREME"),
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "date": date,
    }

    # Salva JSON blog post
    (BLOG_DIR / f"{slug}.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # Genera pagina HTML
    html = build_article_html(meta)
    article_dir = NEWS_DIR / slug
    article_dir.mkdir(parents=True, exist_ok=True)
    (article_dir / "index.html").write_text(html, encoding="utf-8")

    log.info(f"✅ Pubblicato: {slug}")
    return meta

def build_article_html(meta: dict) -> str:
    city = meta["location"]
    cc   = meta["country_code"]
    slug_city = slugify(city)
    z    = meta["z_score"]
    sign = "+" if z >= 0 else ""
    col  = "#ef4444" if meta["score"] >= 7 else "#f97316" if meta["score"] >= 5 else "#f59e0b"

    return f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{meta['title']} | WeatherArb</title>
  <meta name="description" content="{meta['lead'][:160]}">
  <link rel="canonical" href="https://weatherarb.com/news/{meta['slug']}/">
  <style>
    :root{{--bg:#040608;--surface:#0a0d12;--border:#141920;--text:#c8d6e5;--muted:#4a5568;--blue:#3b82f6}}
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;min-height:100vh}}
    .hdr{{border-bottom:1px solid var(--border);padding:14px 24px;display:flex;align-items:center;justify-content:space-between}}
    .logo{{font-size:13px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--text);text-decoration:none}}.logo span{{color:var(--blue)}}
    .nav{{display:flex;gap:20px}}.nav a{{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);text-decoration:none}}
    .wrap{{max-width:720px;margin:0 auto;padding:48px 24px 80px}}
    .bc{{font-size:11px;text-transform:uppercase;letter-spacing:.15em;color:var(--muted);margin-bottom:20px}}.bc a{{color:var(--muted);text-decoration:none}}
    .badge{{display:inline-flex;gap:8px;align-items:center;background:rgba(59,130,246,.08);border:1px solid rgba(59,130,246,.2);border-radius:100px;padding:4px 12px;font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:var(--blue);margin-bottom:16px}}
    h1{{font-size:clamp(24px,4vw,40px);font-weight:800;letter-spacing:-.02em;line-height:1.2;margin-bottom:16px}}
    .meta{{font-size:12px;color:var(--muted);margin-bottom:32px;display:flex;gap:16px;flex-wrap:wrap}}
    .zscore{{font-size:48px;font-weight:800;font-variant-numeric:tabular-nums;color:{col};text-align:center;padding:24px;background:var(--surface);border:1px solid var(--border);border-radius:12px;margin-bottom:32px}}
    .zscore-label{{font-size:11px;text-transform:uppercase;letter-spacing:.15em;color:var(--muted);margin-top:4px}}
    .lead{{font-size:18px;line-height:1.6;color:#fff;margin-bottom:24px;font-weight:500}}
    .body{{font-size:15px;line-height:1.7;color:var(--text);margin-bottom:24px}}
    .conclusion{{font-size:14px;line-height:1.6;color:var(--muted);padding:20px;background:var(--surface);border-left:3px solid var(--blue);border-radius:0 8px 8px 0;margin-bottom:32px}}
    .back{{display:inline-block;padding:10px 20px;border:1px solid var(--border);border-radius:8px;color:var(--muted);text-decoration:none;font-size:13px}}.back:hover{{border-color:var(--blue);color:var(--blue)}}
    .ftr{{border-top:1px solid var(--border);padding:24px;text-align:center;font-size:11px;color:var(--muted)}}.ftr a{{color:var(--muted);text-decoration:none}}
  </style>
</head>
<body>
<header class="hdr">
  <a href="/" class="logo">Weather<span>Arb</span></a>
  <nav class="nav"><a href="/news/">News</a><a href="/data/">Data</a><a href="/api.html">API</a></nav>
</header>
<div class="wrap">
  <div class="bc"><a href="/">WeatherArb</a> / <a href="/news/">Intelligence Reports</a> / {city}</div>
  <div class="badge">📡 {meta['anomaly_level']} · {meta['date']}</div>
  <h1>{meta['title']}</h1>
  <div class="meta">
    <span>📍 <a href="/{cc}/{slugify(city)}/" style="color:var(--blue);text-decoration:none">{city}</a></span>
    <span>⚡ {meta['vertical'].replace('-',' ').title()}</span>
    <span>Score: {meta['score']}/10</span>
  </div>
  <div class="zscore">
    {sign}{z:.2f}σ
    <div class="zscore-label">Z-Score vs baseline NASA POWER 25 anni</div>
  </div>
  <p class="lead">{meta['lead']}</p>
  <div class="body">{meta['body']}</div>
  <div class="conclusion">{meta['conclusion']}</div>
  <a href="/news/" class="back">← Tutti gli Intelligence Reports</a>
</div>
<footer class="ftr">
  <a href="/">WeatherArb</a> · Independent Weather Intelligence Agency ·
  Data: NASA POWER, ERA5-Land, OpenWeatherMap ·
  <a href="/about.html">Methodology</a>
</footer>
</body>
</html>"""

# ─── STEP 4: Pulizia articoli vecchi ────────────────────────────────────────
def cleanup_old_articles():
    cutoff = datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)
    removed = 0

    all_posts = sorted(BLOG_DIR.glob("*.json"))

    # Rimuovi quelli troppo vecchi
    for f in all_posts:
        try:
            meta = json.loads(f.read_text())
            ts = datetime.fromisoformat(meta.get("timestamp", "2020-01-01T00:00:00+00:00").replace("Z", "+00:00"))
            if ts < cutoff:
                slug = meta.get("slug", f.stem)
                # Rimuovi HTML
                article_dir = NEWS_DIR / slug
                if article_dir.exists():
                    import shutil
                    shutil.rmtree(article_dir)
                f.unlink()
                removed += 1
                log.info(f"🗑  Rimosso vecchio articolo: {slug}")
        except Exception as e:
            log.warning(f"Cleanup error on {f}: {e}")

    # Se ancora troppi, rimuovi i più vecchi fino a MAX_TOTAL
    all_posts = sorted(BLOG_DIR.glob("*.json"))
    if len(all_posts) > MAX_TOTAL:
        to_remove = all_posts[:len(all_posts) - MAX_TOTAL]
        for f in to_remove:
            try:
                meta = json.loads(f.read_text())
                slug = meta.get("slug", f.stem)
                article_dir = NEWS_DIR / slug
                if article_dir.exists():
                    import shutil
                    shutil.rmtree(article_dir)
                f.unlink()
                removed += 1
                log.info(f"🗑  Rimosso (limite max): {slug}")
            except Exception as e:
                log.warning(f"Cleanup error: {e}")

    log.info(f"Cleanup: {removed} articoli rimossi")
    return removed

# ─── STEP 5: Aggiorna latest_reports.json ───────────────────────────────────
def update_latest_reports():
    all_posts = []
    for f in sorted(BLOG_DIR.glob("*.json"), reverse=True):
        try:
            meta = json.loads(f.read_text())
            all_posts.append({
                "slug": meta.get("slug"),
                "title": meta.get("title"),
                "lead": meta.get("lead", "")[:160] + "...",
                "location": meta.get("location"),
                "country_code": meta.get("country_code", "it"),
                "vertical": meta.get("vertical"),
                "z_score": meta.get("z_score", 0),
                "score": meta.get("score", 0),
                "anomaly_level": meta.get("anomaly_level"),
                "date": meta.get("date"),
                "url": f"/news/{meta.get('slug')}/",
                "excerpt": meta.get("lead", "")[:180],
            })
        except Exception:
            continue

    report = {
        "last_updated": datetime.now(timezone.utc).isoformat() + "Z",
        "count": len(all_posts),
        "reports": all_posts[:20],  # Max 20 nella homepage
    }
    REPORTS_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info(f"✅ latest_reports.json aggiornato — {len(all_posts)} articoli")

# ─── STEP 6: Aggiorna news/index.html ───────────────────────────────────────
def update_news_index():
    all_posts = sorted(BLOG_DIR.glob("*.json"), reverse=True)
    cards = ""
    for f in all_posts[:50]:
        try:
            m = json.loads(f.read_text())
            z = m.get("z_score", 0)
            sign = "+" if z >= 0 else ""
            sc = m.get("score", 0)
            col = "#ef4444" if sc >= 7 else "#f97316" if sc >= 5 else "#f59e0b"
            lvl = m.get("anomaly_level", "")
            cards += f"""  <a href="/news/{m['slug']}/" class="card">
    <div class="card-top">
      <span class="loc">{m.get('location','—')}</span>
      <span class="ev">{(m.get('vertical') or '').replace('-',' ').upper()}</span>
    </div>
    <h2>{m.get('title','—')}</h2>
    <p>{m.get('lead','')[:120]}...</p>
    <div class="card-foot">
      <span style="color:{col};font-weight:700">{sign}{z:.2f}σ</span>
      <span class="lvl" style="color:{col}">{lvl}</span>
      <span class="date">{m.get('date','')}</span>
    </div>
  </a>\n"""
        except Exception:
            continue

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Intelligence Reports | WeatherArb</title>
  <meta name="description" content="Analisi delle anomalie meteo in Europa. Z-Score in tempo reale su baseline NASA POWER 25 anni. WeatherArb Weather Intelligence Agency.">
  <style>
    :root{{--bg:#040608;--surface:#0a0d12;--border:#141920;--text:#c8d6e5;--muted:#4a5568;--blue:#3b82f6}}
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:var(--bg);color:var(--text);font-family:-apple-system,sans-serif;min-height:100vh}}
    .hdr{{border-bottom:1px solid var(--border);padding:14px 24px;display:flex;align-items:center;justify-content:space-between}}
    .logo{{font-size:13px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--text);text-decoration:none}}.logo span{{color:var(--blue)}}
    .nav{{display:flex;gap:20px}}.nav a{{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);text-decoration:none}}
    .wrap{{max-width:1100px;margin:0 auto;padding:48px 24px 80px}}
    h1{{font-size:clamp(28px,4vw,48px);font-weight:800;letter-spacing:-.02em;margin-bottom:8px}}
    .sub{{font-size:13px;color:var(--muted);margin-bottom:40px}}
    .filters{{display:flex;gap:8px;margin-bottom:32px;flex-wrap:wrap}}
    .filt{{padding:6px 14px;border:1px solid var(--border);border-radius:100px;font-size:12px;color:var(--muted);cursor:pointer;background:transparent;transition:.2s}}.filt:hover,.filt.active{{border-color:var(--blue);color:var(--blue)}}
    .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}}
    .card{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:24px;text-decoration:none;color:var(--text);display:flex;flex-direction:column;gap:10px;transition:border-color .2s}}.card:hover{{border-color:var(--blue)}}
    .card-top{{display:flex;gap:8px;align-items:center}}.loc{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:var(--blue)}}.ev{{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}}
    .card h2{{font-size:16px;font-weight:700;line-height:1.3}}
    .card p{{font-size:13px;color:var(--muted);line-height:1.5;flex:1}}
    .card-foot{{display:flex;gap:12px;align-items:center;padding-top:10px;border-top:1px solid var(--border);font-size:12px}}.date{{margin-left:auto;color:var(--muted)}}.lvl{{font-size:10px;font-weight:700;text-transform:uppercase}}
    .ftr{{border-top:1px solid var(--border);padding:24px;text-align:center;font-size:11px;color:var(--muted)}}.ftr a{{color:var(--muted);text-decoration:none}}
  </style>
</head>
<body>
<header class="hdr">
  <a href="/" class="logo">Weather<span>Arb</span></a>
  <nav class="nav"><a href="/data/">Data</a><a href="/map.html">Map</a><a href="/api.html">API</a><a href="/alerts.html">Alerts</a></nav>
</header>
<div class="wrap">
  <h1>Intelligence Reports</h1>
  <p class="sub">{len(all_posts)} analisi pubblicate · ERA5-Land + NASA POWER · Aggiornato ogni ora</p>
  <div class="filters">
    <button class="filt active" onclick="filter('all')">All</button>
    <button class="filt" onclick="filter('critical')" style="color:#ef4444;border-color:#ef4444">● Critical</button>
    <button class="filt" onclick="filter('extreme')" style="color:#f97316;border-color:#f97316">● Extreme</button>
    <button class="filt" onclick="filter('unusual')" style="color:#f59e0b;border-color:#f59e0b">● Unusual</button>
  </div>
  <div class="grid" id="grid">
{cards}  </div>
</div>
<footer class="ftr">
  <a href="/">WeatherArb</a> · <a href="/about.html">Methodology</a> · <a href="/api.html">API</a>
</footer>
<script>
function filter(lvl){{
  document.querySelectorAll('.filt').forEach(b=>b.classList.remove('active'));
  event.target.classList.add('active');
  document.querySelectorAll('.card').forEach(c=>{{
    if(lvl==='all'){{c.style.display='';return;}}
    const t=c.querySelector('.lvl');
    c.style.display=(t&&t.textContent.toLowerCase().includes(lvl))?'':'none';
  }});
}}
</script>
</body>
</html>"""

    (NEWS_DIR / "index.html").write_text(html, encoding="utf-8")
    log.info(f"✅ news/index.html aggiornato — {len(all_posts)} articoli")

# ─── MAIN ────────────────────────────────────────────────────────────────────
def main():
    log.info("=== WeatherArb Auto-Publisher START ===")

    # 1. Pulizia
    removed = cleanup_old_articles()

    # 2. Fetch segnali
    signals = fetch_top_signals()
    if not signals:
        log.info("Nessuna anomalia sopra soglia — nessun articolo generato")
    else:
        # 3. Genera e pubblica
        published = 0
        for sig in signals:
            content = generate_article(sig)
            if content:
                meta = save_article(sig, content)
                if meta:
                    published += 1
        log.info(f"Pubblicati {published} nuovi articoli")

    # 4. Aggiorna feed e indice
    update_latest_reports()
    update_news_index()

    log.info("=== WeatherArb Auto-Publisher END ===")

if __name__ == "__main__":
    main()
