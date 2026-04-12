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
SCORE_MIN      = float(os.getenv("SCORE_THRESHOLD", "6.0"))
MAX_NEW        = int(os.getenv("MAX_ARTICLES", "6"))
KEEP_DAYS      = int(os.getenv("KEEP_DAYS", "30"))
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

def gemini(prompt):
    if not GEMINI_API_KEY: return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    try:
        r = requests.post(url, json={"contents":[{"parts":[{"text":prompt}]}],
            "generationConfig":{"temperature":0.7,"maxOutputTokens":600}}, timeout=30)
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
    prompt = f"""Sei un analista meteo di WeatherArb. Scrivi in italiano ~200 parole su:
Città: {city}, Evento: {vert}, Z-Score: {sign}{z:.2f}, Score: {sc:.1f}/10, Livello: {lvl}
Rispondi SOLO JSON: {{"title":"...","lead":"...","body":"...","conclusion":"..."}}
Niente prodotti o acquisti. Tono scientifico accessibile."""
    return gemini(prompt)

def save(sig, content):
    city = sig.get("location") or sig.get("province","unknown")
    vert = (sig.get("vertical") or sig.get("event_type") or "meteo").replace("_","-").lower()
    date = now().strftime("%Y-%m-%d")
    slug = f"{date}-{slugify(city)}-{slugify(vert)}"
    if (BLOG/f"{slug}.json").exists():
        log.info(f"Skip duplicate: {slug}"); return None
    z  = sig.get("z_score",0); sc = sig.get("score",0)
    cc = sig.get("country_code","it")
    sign = "+" if z >= 0 else ""
    col = "#ef4444" if sc>=7 else "#f97316" if sc>=5 else "#f59e0b"
    meta = {"slug":slug,"title":content.get("title",f"{vert} a {city}"),
            "lead":content.get("lead",""),"body":content.get("body",""),
            "conclusion":content.get("conclusion",""),
            "location":city,"country_code":cc,"vertical":vert,
            "z_score":round(z,2),"score":round(sc,2),
            "anomaly_level":sig.get("anomaly_level","EXTREME"),
            "timestamp":now().isoformat(),"date":date}
    (BLOG/f"{slug}.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2))
    html = f"""<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{meta['title']} | WeatherArb</title>
<meta name="description" content="{meta['lead'][:160]}">
<style>:root{{--bg:#040608;--s:#0a0d12;--b:#141920;--t:#c8d6e5;--m:#4a5568;--bl:#3b82f6}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--t);font-family:-apple-system,sans-serif;min-height:100vh}}
.hdr{{border-bottom:1px solid var(--b);padding:14px 24px;display:flex;align-items:center;justify-content:space-between}}
.logo{{font-size:13px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--t);text-decoration:none}}.logo span{{color:var(--bl)}}
.nav a{{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:var(--m);text-decoration:none;margin-left:16px}}
.wrap{{max-width:720px;margin:0 auto;padding:48px 24px 80px}}
.bc{{font-size:11px;color:var(--m);margin-bottom:20px}}.bc a{{color:var(--m);text-decoration:none}}
.badge{{display:inline-block;background:rgba(59,130,246,.1);border:1px solid rgba(59,130,246,.2);border-radius:100px;padding:4px 12px;font-size:11px;color:var(--bl);margin-bottom:16px}}
h1{{font-size:clamp(22px,4vw,38px);font-weight:800;letter-spacing:-.02em;line-height:1.2;margin-bottom:16px}}
.meta{{font-size:12px;color:var(--m);margin-bottom:28px}}
.zbox{{font-size:44px;font-weight:800;color:{col};text-align:center;padding:20px;background:var(--s);border:1px solid var(--b);border-radius:12px;margin-bottom:28px}}
.zbox small{{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.15em;color:var(--m);margin-top:4px}}
.lead{{font-size:17px;line-height:1.6;color:#fff;margin-bottom:20px;font-weight:500}}
.body{{font-size:15px;line-height:1.7;margin-bottom:20px}}
.concl{{font-size:14px;line-height:1.6;color:var(--m);padding:16px 20px;background:var(--s);border-left:3px solid var(--bl);border-radius:0 8px 8px 0;margin-bottom:28px}}
.back{{display:inline-block;padding:10px 20px;border:1px solid var(--b);border-radius:8px;color:var(--m);text-decoration:none;font-size:13px}}
.ftr{{border-top:1px solid var(--b);padding:20px;text-align:center;font-size:11px;color:var(--m)}}.ftr a{{color:var(--m);text-decoration:none}}</style>
</head><body>
<header class="hdr"><a href="/" class="logo">Weather<span>Arb</span></a>
<nav class="nav"><a href="/news/">News</a><a href="/data/">Data</a><a href="/api.html">API</a></nav></header>
<div class="wrap">
<div class="bc"><a href="/">WeatherArb</a> / <a href="/news/">Reports</a> / {city}</div>
<div class="badge">📡 {meta['anomaly_level']} · {date}</div>
<h1>{meta['title']}</h1>
<div class="meta">📍 {city} &nbsp;·&nbsp; ⚡ {vert.replace('-',' ').title()} &nbsp;·&nbsp; Score {sc}/10</div>
<div class="zbox">{sign}{z:.2f}σ<small>Z-Score vs baseline NASA POWER 25 anni</small></div>
<p class="lead">{meta['lead']}</p>
<div class="body">{meta['body']}</div>
<div class="concl">{meta['conclusion']}</div>
<a href="/news/" class="back">← Tutti i Reports</a>
</div>
<footer class="ftr"><a href="/">WeatherArb</a> · Independent Weather Intelligence Agency · <a href="/about.html">Methodology</a></footer>
</body></html>"""
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
                f.unlink(); removed += 1; log.info(f"🗑  {slug} (limit)")
            except: pass
    log.info(f"Cleanup: {removed} rimossi")

def update_feed():
    posts = []
    for f in sorted(BLOG.glob("*.json"), reverse=True):
        try:
            m = json.loads(f.read_text())
            posts.append({"slug":m.get("slug"),"title":m.get("title"),
                "lead":m.get("lead","")[:160]+"...","location":m.get("location"),
                "country_code":m.get("country_code","it"),"vertical":m.get("vertical"),
                "z_score":m.get("z_score",0),"score":m.get("score",0),
                "anomaly_level":m.get("anomaly_level"),"date":m.get("date"),
                "url":f"/news/{m.get('slug')}/","excerpt":m.get("lead","")[:180]})
        except: pass
    FEED.write_text(json.dumps({"last_updated":now().isoformat(),"count":len(posts),"reports":posts[:20]},ensure_ascii=False,indent=2))
    log.info(f"✅ feed aggiornato — {len(posts)} articoli")

def update_news_index():
    posts = list(sorted(BLOG.glob("*.json"), reverse=True))[:50]
    cards = ""
    for f in posts:
        try:
            m = json.loads(f.read_text())
            z=m.get("z_score",0); sc=m.get("score",0)
            sign="+" if z>=0 else ""
            col="#ef4444" if sc>=7 else "#f97316" if sc>=5 else "#f59e0b"
            cards += f'<a href="/news/{m["slug"]}/" class="card"><div class="ct"><span class="loc">{m.get("location","—")}</span><span class="ev">{(m.get("vertical") or "").replace("-"," ").upper()}</span></div><h2>{m.get("title","—")}</h2><p>{m.get("lead","")[:110]}...</p><div class="cf"><span style="color:{col};font-weight:700">{sign}{z:.2f}σ</span><span style="color:{col};font-size:10px;font-weight:700;text-transform:uppercase">{m.get("anomaly_level","")}</span><span class="dt">{m.get("date","")}</span></div></a>\n'
        except: pass
    html = f"""<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Intelligence Reports | WeatherArb</title>
<meta name="description" content="Anomalie meteo in Europa. Z-Score su baseline NASA POWER 25 anni. WeatherArb Weather Intelligence Agency.">
<style>:root{{--bg:#040608;--s:#0a0d12;--b:#141920;--t:#c8d6e5;--m:#4a5568;--bl:#3b82f6}}
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
<p class="sub">{len(posts)} analisi · ERA5-Land + NASA POWER · Aggiornato ogni 6 ore</p>
<div class="grid">{cards}</div></div>
<footer class="ftr"><a href="/">WeatherArb</a> · <a href="/about.html">Methodology</a> · <a href="/api.html">API</a></footer>
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
