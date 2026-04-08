import os
from datetime import datetime, date
from pathlib import Path
from typing import Optional
from jinja2 import Environment, BaseLoader

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "landing_pages")

def decorate_affiliate_link(asin, provincia, evento, amazon_tag="meteoguida-21", network="amazon", awin_id=""):
    date_str = date.today().strftime("%Y%m%d")
    subid = f"{provincia.lower()}_{evento.lower()}_{date_str}"
    if network == "amazon":
        return f"https://www.amazon.it/dp/{asin}?tag={amazon_tag}&ascsubtag={subid}&linkCode=ogi"
    return f"https://www.amazon.it/dp/{asin}?tag={amazon_tag}&ascsubtag={subid}"

def get_product_link_with_fallback(primary_asin, fallback_asins, provincia, evento, amazon_tag, auditor_check_fn=None):
    candidates = [primary_asin] + fallback_asins
    for asin in candidates:
        if auditor_check_fn and not auditor_check_fn(asin):
            continue
        is_fallback = asin != primary_asin
        link = decorate_affiliate_link(asin, provincia, evento, amazon_tag)
        return link, asin, is_fallback
    return None, None, False

from jinja2 import Environment, BaseLoader
from pathlib import Path
import os

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "landing_pages")

class LandingPageRenderer:
    def __init__(self, output_dir=OUTPUT_DIR):
        self.output_dir = output_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    def render(self, pulse_json, variant, product, body_texts=None):
        from datetime import datetime
        loc = pulse_json.get("location", {})
        trig = pulse_json.get("weather_trigger", {})
        provincia = loc.get("provincia", "")
        evento = trig.get("type", "")
        z_score = float(trig.get("z_score", 0))
        temp = trig.get("current_temp_c")
        peak_str = trig.get("peak_expected_in", "N/A")
        peak_ore = None
        try:
            peak_ore = int(peak_str.replace("h","")) if peak_str != "N/A" else None
        except: pass

        asin = product.get("asin", "")
        amazon_tag = product.get("amazon_tag", "meteoguida-21")
        affiliate_url = decorate_affiliate_link(asin, provincia, evento, amazon_tag) if asin else "#"

        html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{variant.headline} | WeatherArb</title>
<meta name="description" content="{variant.subheadline}">
<style>
  body{{font-family:Georgia,serif;max-width:680px;margin:0 auto;padding:20px;color:#1a1a2e;background:#f9fafb}}
  .header{{background:#1a1a2e;color:white;padding:12px 20px;margin:-20px -20px 0;font-size:13px;letter-spacing:2px}}
  .weather-bar{{background:linear-gradient(135deg,#1e3a5f,#2563eb);color:white;padding:16px 20px;margin:0 -20px 24px;display:flex;gap:16px;flex-wrap:wrap}}
  .badge{{background:rgba(255,255,255,.15);border-radius:8px;padding:8px 14px;text-align:center}}
  .badge strong{{display:block;font-size:20px}}
  .badge span{{font-size:11px;opacity:.8}}
  h1{{font-size:26px;line-height:1.3;margin:0 0 12px}}
  .sub{{font-size:17px;color:#6b7280;font-style:italic;margin-bottom:24px}}
  .body p{{font-size:16px;line-height:1.7;margin-bottom:16px}}
  .card{{border:2px solid #e5e7eb;border-radius:12px;padding:24px;margin:32px 0;background:white;position:relative}}
  .card::before{{content:"CONSIGLIATO";position:absolute;top:-10px;left:20px;background:#e94560;color:white;font-size:10px;padding:2px 10px;border-radius:4px;font-family:sans-serif;letter-spacing:1px}}
  .price{{font-size:24px;color:#e94560;font-weight:bold;margin:8px 0 16px}}
  .cta{{display:block;background:#ff9900;color:#111;text-align:center;padding:14px;border-radius:8px;font-size:16px;font-weight:bold;text-decoration:none}}
  .note{{font-size:11px;color:#9ca3af;text-align:center;margin-top:8px}}
  footer{{font-size:11px;color:#9ca3af;text-align:center;margin-top:48px;padding-top:20px;border-top:1px solid #e5e7eb}}
</style>
</head>
<body>
<div class="header">WEATHERARB.COM — {loc.get('regione','').upper()}</div>
<div class="weather-bar">
  <div style="flex:1"><div style="font-size:11px;opacity:.7;margin-bottom:4px">METEO ATTUALE — {provincia.upper()}</div>
  <div style="font-size:15px;font-weight:bold">{evento.replace('_',' ')}</div></div>
  {'<div class="badge"><strong>'+str(round(temp,1))+'°C</strong><span>Temperatura</span></div>' if temp else ''}
  <div class="badge"><strong>Z={z_score:+.1f}</strong><span>Anomalia</span></div>
  {'<div class="badge"><strong>'+str(peak_ore)+'h</strong><span>Al picco</span></div>' if peak_ore else ''}
</div>
<h1>{variant.headline}</h1>
<p class="sub">{variant.subheadline}</p>
<div class="body">
<p>Le condizioni meteo attuali su {provincia} mostrano un'anomalia {trig.get('anomaly_level','').lower()} rispetto alle medie stagionali storiche. Con uno Z-Score di {z_score:+.1f}, il sistema ha identificato questa come un'opportunità di preparazione prima del picco previsto.</p>
<p>Per chi vive in {provincia}, la scelta giusta adesso può fare la differenza nelle prossime ore.</p>
</div>
<div class="card">
  <div style="font-size:18px;font-weight:bold;margin-bottom:8px">{product.get('nome','')}</div>
  <div class="price">€{float(product.get('prezzo_medio',0)):.0f}</div>
  <a href="{affiliate_url}" class="cta" rel="nofollow sponsored">Vedi su Amazon →</a>
  <p class="note">Link affiliato Amazon · Nessun costo aggiuntivo</p>
</div>
<div class="body">
<p>Le consegne Prime su {provincia} sono generalmente disponibili entro 24-48 ore. Ordina prima del picco per riceverlo in tempo utile.</p>
</div>
<footer>WeatherArb.com — Contenuto informativo · {__import__('datetime').datetime.now().strftime('%d/%m/%Y')} · Prezzi indicativi soggetti a variazione</footer>
</body></html>"""

        slug = f"{provincia.lower()}-{evento.lower()}-{variant.label}"
        path = os.path.join(self.output_dir, f"{slug}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return html, path
