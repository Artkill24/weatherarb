"""
WeatherArb — Content Generator + SEO Utils
Genera articoli con Gemini, aggiorna sitemap.xml e RSS feed.
"""

import json, os, logging
from datetime import datetime, timezone
from pathlib import Path
from slugify import slugify

logger = logging.getLogger(__name__)

BLOG_DIR = "data/blog_posts"
WEBSITE_DIR = "data/website"
BASE_URL = "https://weatherarb.com"


def generate_article(pulse: dict, gemini_client=None) -> dict:
    """Genera articolo completo da Pulse-JSON."""
    loc = pulse.get("location", {})
    trig = pulse.get("weather_trigger", {})
    arb = pulse.get("arbitrage_score", {})
    action = pulse.get("action_plan", {})

    provincia = loc.get("provincia", "")
    regione = loc.get("regione", "")
    evento = trig.get("type", "").replace("_", " ")
    z_score = trig.get("z_score", 0)
    anomaly = trig.get("anomaly_level", "")
    score = arb.get("score", 0)
    vertical = action.get("recommended_vertical", "").replace("_", " ")
    temp = trig.get("current_temp_c")
    temp_avg = trig.get("historical_avg_temp_c")

    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = f"{date_str}-{slugify(provincia)}-{slugify(evento)}"

    # Genera testo con Gemini o fallback
    if gemini_client:
        body = _generate_with_gemini(gemini_client, provincia, regione,
                                      evento, z_score, anomaly, temp, temp_avg, vertical)
    else:
        body = _fallback_body(provincia, evento, z_score, anomaly, temp, temp_avg, vertical)

    # Determina URL landing page
    codice = loc.get("codice_istat", "")
    country = "de" if codice.startswith("DE") else "it"
    slug_prov = slugify(provincia)
    landing_url = f"{BASE_URL}/{country}/{slug_prov}/"

    article = {
        "slug": slug,
        "title": f"{evento} anomalo a {provincia}: analisi WeatherArb del {datetime.now().strftime('%d/%m/%Y')}",
        "meta_description": f"Anomalia meteo a {provincia}. Z-Score {z_score:+.2f}, livello {anomaly}. Analisi tecnica e consigli pratici.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provincia": provincia,
        "regione": regione,
        "evento": evento,
        "z_score": z_score,
        "anomaly_level": anomaly,
        "score": score,
        "vertical": vertical,
        "body": body,
        "landing_url": landing_url,
        "tags": [provincia, regione, evento, "meteo anomalo", "WeatherArb"],
    }

    # Salva JSON
    Path(BLOG_DIR).mkdir(parents=True, exist_ok=True)
    path = f"{BLOG_DIR}/{slug}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(article, f, ensure_ascii=False, indent=2)

    # Genera HTML dell'articolo
    html_path = _render_article_html(article)

    logger.info(f"Article generated: {slug}")
    return article


def _generate_with_gemini(client, provincia, regione, evento, z_score,
                           anomaly, temp, temp_avg, vertical) -> str:
    prompt = f"""Scrivi un articolo di cronaca meteo locale di 250 parole per il sito WeatherArb.
Stile: giornale locale informativo, dati tecnici integrati nel testo naturalmente.
NON usare toni allarmistici. NON usare parole come emergenza, pericolo, paura.

Dati:
- Località: {provincia} ({regione})
- Evento: {evento}
- Z-Score: {z_score:+.2f} (anomalia {anomaly} rispetto alla media storica)
- Temperatura attuale: {temp}°C vs media storica {temp_avg}°C
- Vertical prodotto consigliato: {vertical}

Struttura: 3 paragrafi. Primo: contesto meteo attuale. Secondo: analisi statistica (cita lo Z-Score).
Terzo: consigli pratici per i residenti. Termina con frase che invita a vedere i prodotti consigliati."""

    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return response.text.strip()
    except Exception as e:
        logger.warning(f"Gemini failed: {e}")
        return _fallback_body(provincia, evento, z_score, anomaly, temp, temp_avg, vertical)


def _fallback_body(provincia, evento, z_score, anomaly, temp, temp_avg, vertical) -> str:
    return (
        f"Le stazioni meteorologiche rilevano condizioni inusuali su {provincia} nelle ultime ore. "
        f"L'evento {evento} in corso presenta caratteristiche statisticamente anomale rispetto "
        f"alle medie storiche stagionali per questa area geografica.\n\n"
        f"L'analisi WeatherArb registra uno Z-Score di {z_score:+.2f}, classificando l'anomalia "
        f"come livello {anomaly}. La temperatura attuale di {temp}°C si discosta significativamente "
        f"dalla media storica di {temp_avg}°C per questo periodo dell'anno.\n\n"
        f"I residenti di {provincia} possono prepararsi con i prodotti del vertical {vertical}. "
        f"Le consegne Prime sono generalmente disponibili entro 24-48 ore dall'ordine."
    )


def _render_article_html(article: dict) -> str:
    """Genera pagina HTML dell'articolo."""
    slug = article["slug"]
    country = "de" if article.get("regione", "").startswith("Bay") else "it"
    prov_slug = slugify(article["provincia"])
    out_dir = Path(f"{WEBSITE_DIR}/news/{slug}")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = str(out_dir / "index.html")

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{article['title']} | WeatherArb</title>
<meta name="description" content="{article['meta_description']}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
  :root {{ --ink:#0f1117; --paper:#f5f3ee; --storm:#1a3a5c; --electric:#2563eb; --mist:#e8e5de; --muted:#6b6560; }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:'DM Sans',sans-serif; background:var(--paper); color:var(--ink); }}
  nav {{ display:flex; align-items:center; justify-content:space-between; padding:20px 48px; border-bottom:1px solid var(--mist); background:rgba(245,243,238,0.95); }}
  .logo {{ font-family:'Instrument Serif',serif; font-size:20px; display:flex; align-items:center; gap:8px; text-decoration:none; color:var(--ink); }}
  .logo-icon {{ width:28px; height:28px; background:var(--storm); border-radius:6px; display:flex; align-items:center; justify-content:center; font-size:14px; }}
  .container {{ max-width:720px; margin:0 auto; padding:48px 24px; }}
  .tag {{ font-size:11px; font-weight:600; letter-spacing:2px; text-transform:uppercase; color:var(--electric); margin-bottom:16px; }}
  h1 {{ font-family:'Instrument Serif',serif; font-size:clamp(24px,4vw,38px); line-height:1.2; letter-spacing:-0.5px; margin-bottom:16px; }}
  .byline {{ font-size:13px; color:var(--muted); margin-bottom:32px; padding-bottom:24px; border-bottom:1px solid var(--mist); }}
  .data-box {{ background:var(--storm); color:white; border-radius:12px; padding:20px 24px; margin:28px 0; display:grid; grid-template-columns:repeat(3,1fr); gap:16px; }}
  .data-item span {{ display:block; font-size:11px; opacity:0.6; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px; }}
  .data-item strong {{ font-family:'Instrument Serif',serif; font-size:22px; }}
  .body-text p {{ font-size:17px; line-height:1.75; margin-bottom:20px; }}
  .cta-box {{ background:white; border:2px solid var(--mist); border-radius:12px; padding:24px; margin:32px 0; text-align:center; }}
  .cta-box h3 {{ font-family:'Instrument Serif',serif; font-size:20px; margin-bottom:12px; }}
  .cta-btn {{ display:inline-block; background:#ff9900; color:#111; padding:12px 28px; border-radius:8px; font-weight:600; text-decoration:none; }}
  footer {{ text-align:center; font-size:12px; color:var(--muted); padding:32px; border-top:1px solid var(--mist); }}
</style>
</head>
<body>
<nav>
  <a href="/" class="logo"><div class="logo-icon">⛈</div>WeatherArb</a>
  <span style="font-size:11px;color:var(--muted);letter-spacing:2px;text-transform:uppercase">Weather Intelligence</span>
</nav>
<div class="container">
  <div class="tag">📍 {article['provincia']} · {article['evento']}</div>
  <h1>{article['title']}</h1>
  <div class="byline">WeatherArb News · {datetime.now().strftime('%d %B %Y')} · Dati: ERA5 + OpenWeatherMap</div>
  <div class="data-box">
    <div class="data-item"><span>Z-Score</span><strong>{article['z_score']:+.2f}</strong></div>
    <div class="data-item"><span>Livello</span><strong>{article['anomaly_level']}</strong></div>
    <div class="data-item"><span>Arb Score</span><strong>{article['score']:.1f}/10</strong></div>
  </div>
  <div class="body-text">
    {''.join(f'<p>{p}</p>' for p in article['body'].split(chr(10)+chr(10)) if p.strip())}
  </div>
  <div class="cta-box">
    <h3>Prodotti consigliati per {article['provincia']}</h3>
    <p style="color:var(--muted);font-size:14px;margin-bottom:16px">Selezionati dal sistema WeatherArb per questo evento meteo</p>
    <a href="{article['landing_url']}" class="cta-btn">Vedi i prodotti →</a>
  </div>
</div>
<footer>WeatherArb.com · Weather intelligence for local decisions · <a href="/sitemap.xml">Sitemap</a></footer>
</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def update_sitemap(articles: list):
    """Aggiorna sitemap.xml con gli articoli."""
    static_urls = [
        ("https://weatherarb.com/", "hourly", "1.0"),
        ("https://weatherarb.com/it/trento/", "daily", "0.9"),
        ("https://weatherarb.com/it/vicenza/", "daily", "0.9"),
        ("https://weatherarb.com/it/milano/", "daily", "0.9"),
    ]
    news_urls = [
        (f"https://weatherarb.com/news/{a['slug']}/", "weekly", "0.7")
        for a in articles[-50:]  # Ultimi 50 articoli
    ]

    all_urls = static_urls + news_urls
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, freq, priority in all_urls:
        lines += [f"  <url>",
                  f"    <loc>{url}</loc>",
                  f"    <lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod>",
                  f"    <changefreq>{freq}</changefreq>",
                  f"    <priority>{priority}</priority>",
                  f"  </url>"]
    lines.append("</urlset>")

    path = f"{WEBSITE_DIR}/sitemap.xml"
    with open(path, "w") as f:
        f.write("\n".join(lines))
    logger.info(f"Sitemap updated: {len(all_urls)} URLs")
    return path


def update_rss(articles: list):
    """Genera RSS feed per Google News e aggregatori."""
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    items = []
    for a in articles[-20:]:
        pub = datetime.fromisoformat(a["timestamp"]).strftime("%a, %d %b %Y %H:%M:%S +0000")
        items.append(f"""  <item>
    <title>{a['title']}</title>
    <link>https://weatherarb.com/news/{a['slug']}/</link>
    <description>{a['meta_description']}</description>
    <pubDate>{pub}</pubDate>
    <guid>https://weatherarb.com/news/{a['slug']}/</guid>
    <category>{a['evento']}</category>
  </item>""")

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>WeatherArb — Weather Intelligence Alerts</title>
  <link>https://weatherarb.com</link>
  <description>Real-time weather anomaly alerts for Europe</description>
  <language>it</language>
  <lastBuildDate>{now}</lastBuildDate>
  <atom:link href="https://weatherarb.com/feed.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(items)}
</channel>
</rss>"""

    path = f"{WEBSITE_DIR}/feed.xml"
    with open(path, "w", encoding="utf-8") as f:
        f.write(rss)
    logger.info(f"RSS updated: {len(items)} items")
    return path
