#!/usr/bin/env python3
"""
Rigenera data/website/it/index.html con province ordinate per regione
+ hub per ogni regione con link comuni
"""
import json, re
from pathlib import Path
from unicodedata import normalize

def sl(t):
    s = normalize('NFKD', t).encode('ascii','ignore').decode('ascii')
    return re.sub(r'[\s_]+','-', re.sub(r'[^\w\s-]','',s).strip().lower())

with open('data/province_coords.json') as f:
    raw = json.load(f)
all_provinces = raw['province'] if 'province' in raw else raw
it_provinces = [p for p in all_provinces if p.get('country','Italy') == 'Italy']

# Raggruppa per regione
regioni = {}
for p in it_provinces:
    reg = p.get('regione', 'Altre')
    if reg not in regioni:
        regioni[reg] = []
    regioni[reg].append(p)

# Ordina regioni alfabeticamente
REGIONI_VALIDE = {'Piemonte',"Valle d'Aosta",'Lombardia','Trentino-Alto Adige','Veneto','Friuli-Venezia Giulia','Liguria','Emilia-Romagna','Toscana','Umbria','Marche','Lazio','Abruzzo','Molise','Campania','Puglia','Basilicata','Calabria','Sicilia','Sardegna'}
regioni_sorted = sorted((k,v) for k,v in regioni.items() if k in REGIONI_VALIDE)

# Carica comuni se disponibili
comuni = []
try:
    with open('data/comuni_italy.json') as f:
        comuni = json.load(f)
    print(f"Comuni caricati: {len(comuni)}")
except:
    print("Nessun comuni.json trovato")

# Raggruppa comuni per regione
comuni_per_regione = {}
for c in comuni:
    reg = c.get('regione','')
    if reg not in comuni_per_regione:
        comuni_per_regione[reg] = []
    comuni_per_regione[reg].append(c)

# ─── GENERA HUB ITALIA ───
sections = ""
for regione, province in regioni_sorted:
    reg_slug = sl(regione)
    reg_comuni = comuni_per_regione.get(regione, [])

    # Card province
    prov_cards = ""
    for p in sorted(province, key=lambda x: x['nome']):
        pslug = sl(p['nome'])
        prov_cards += (
            f'<a href="/it/{pslug}/" class="nc">'
            f'<span class="nn">{p["nome"]}</span>'
            f'<span class="ns">Provincia</span>'
            f'</a>'
        )

    # Card comuni (max 8 per regione)
    comuni_cards = ""
    for c in sorted(reg_comuni, key=lambda x: -x.get('pop',0))[:8]:
        cslug = sl(c['nome'])
        comuni_cards += (
            f'<a href="/it/{reg_slug}/{cslug}/" class="nc nc-comune">'
            f'<span class="nn">{c["nome"]}</span>'
            f'<span class="ns">Comune &middot; {c.get("provincia","")[:12]}</span>'
            f'</a>'
        )

    n_comuni = len(reg_comuni)
    comuni_label = f'<span style="font-size:11px;color:var(--muted);margin-left:8px">+ {n_comuni} comuni</span>' if n_comuni else ''

    sections += f'''
<div class="reg-section" id="{reg_slug}">
  <div class="reg-header">
    <h2 class="reg-title">{regione}{comuni_label}</h2>
    <a href="/it/{reg_slug}/" class="reg-link">Hub regionale →</a>
  </div>
  <div class="grid">
    {prov_cards}
    {comuni_cards}
  </div>
</div>'''

total_province = len(it_provinces)
total_comuni = len(comuni)

html = f'''<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Italia — WeatherArb Intelligence Network</title>
  <meta name="description" content="Anomalie meteo in tempo reale per {total_province} province italiane e {total_comuni} comuni. Z-Score NASA POWER, HDD/CDD energy data. WeatherArb.">
  <style>
    :root{{--bg:#040608;--s:#0a0d12;--b:#141920;--ba:#1e2d3d;--t:#c8d6e5;--m:#4a5568;--bl:#3b82f6}}
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:var(--bg);color:var(--t);font-family:-apple-system,sans-serif;min-height:100vh}}
    .hdr{{border-bottom:1px solid var(--b);padding:14px 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;background:rgba(4,6,8,.95);backdrop-filter:blur(12px)}}
    .logo{{font-size:13px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--t);text-decoration:none}}.logo span{{color:var(--bl)}}
    .nav a{{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:var(--m);text-decoration:none;margin-left:16px}}.nav a:hover{{color:var(--t)}}
    .wrap{{max-width:1100px;margin:0 auto;padding:48px 24px 80px}}
    .bc{{font-size:11px;text-transform:uppercase;letter-spacing:.15em;color:var(--m);margin-bottom:16px}}.bc a{{color:var(--m);text-decoration:none}}
    h1{{font-size:clamp(32px,4vw,56px);font-weight:800;letter-spacing:-.02em;margin-bottom:8px}}
    .sub{{font-size:13px;color:var(--m);margin-bottom:32px}}.sub span{{color:var(--bl)}}

    /* REGIONI NAV */
    .reg-nav{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:40px;padding:16px;background:var(--s);border:1px solid var(--b);border-radius:10px}}
    .reg-nav a{{font-size:11px;color:var(--m);text-decoration:none;padding:4px 10px;border:1px solid var(--b);border-radius:100px;transition:.15s}}
    .reg-nav a:hover{{border-color:var(--bl);color:var(--bl)}}

    .reg-section{{margin-bottom:40px}}
    .reg-header{{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid var(--b)}}
    .reg-title{{font-size:16px;font-weight:700;color:var(--t)}}
    .reg-link{{font-size:11px;color:var(--bl);text-decoration:none}}
    .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}}
    .nc{{display:block;padding:14px 16px;background:var(--s);border:1px solid var(--b);border-radius:10px;text-decoration:none;transition:.15s}}
    .nc:hover{{border-color:var(--bl);background:#0d1520}}
    .nc-comune{{border-style:dashed;opacity:.85}}
    .nc-comune:hover{{opacity:1;border-style:solid}}
    .nn{{display:block;font-size:13px;font-weight:600;color:var(--t);margin-bottom:3px}}
    .ns{{display:block;font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:var(--m)}}
    .ftr{{border-top:1px solid var(--b);padding:24px;text-align:center;font-size:11px;color:var(--m)}}
    .ftr a{{color:var(--m);text-decoration:none}}
    @media(max-width:640px){{.grid{{grid-template-columns:repeat(auto-fill,minmax(130px,1fr))}}}}
  </style>
</head>
<body>
<header class="hdr">
  <a href="/" class="logo">Weather<span>Arb</span></a>
  <nav class="nav"><a href="/data/">Data</a><a href="/news/">News</a><a href="/pricing/">API</a></nav>
</header>
<div class="wrap">
  <div class="bc"><a href="/">WeatherArb</a> / Italia</div>
  <h1>Italia</h1>
  <p class="sub"><span>{total_province}</span> province &middot; <span>{total_comuni}</span> comuni &middot; dati live Z-Score NASA POWER</p>

  <!-- NAVIGAZIONE REGIONI -->
  <div class="reg-nav">
    {''.join(f'<a href="#{sl(r)}">{r}</a>' for r,_ in regioni_sorted)}
  </div>

  {sections}
</div>
<footer class="ftr">
  <a href="/">WeatherArb</a> &middot; <a href="/data/">Dashboard</a> &middot; <a href="/pricing/">API Pro</a>
</footer>
</body>
</html>'''

Path('data/website/it/index.html').write_text(html, encoding='utf-8')
print(f"✅ it/index.html generato — {len(regioni_sorted)} regioni, {total_province} province, {total_comuni} comuni")

# ─── GENERA HUB PER OGNI REGIONE ───
reg_ok = 0
for regione, province in regioni_sorted:
    reg_slug = sl(regione)
    reg_comuni = comuni_per_regione.get(regione, [])
    reg_dir = Path(f'data/website/it/{reg_slug}')
    reg_dir.mkdir(parents=True, exist_ok=True)

    prov_cards = ""
    for p in sorted(province, key=lambda x: x['nome']):
        pslug = sl(p['nome'])
        prov_cards += (
            f'<a href="/it/{pslug}/" class="nc">'
            f'<span class="nn">{p["nome"]}</span>'
            f'<span class="ns">Provincia &middot; nodo dati</span>'
            f'</a>'
        )

    comuni_cards = ""
    for c in sorted(reg_comuni, key=lambda x: -x.get('pop',0)):
        cslug = sl(c['nome'])
        comuni_cards += (
            f'<a href="/it/{reg_slug}/{cslug}/" class="nc nc-comune">'
            f'<span class="nn">{c["nome"]}</span>'
            f'<span class="ns">{c.get("provincia","")[:15]}</span>'
            f'</a>'
        )

    html_reg = f'''<!DOCTYPE html>
<html lang="it"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{regione} Meteo Anomalie | WeatherArb</title>
<meta name="description" content="Anomalie meteo in {regione}: {len(province)} province e {len(reg_comuni)} comuni monitorati. Z-Score NASA POWER 25 anni. WeatherArb.">
<link rel="canonical" href="https://weatherarb.com/it/{reg_slug}/">
<style>
:root{{--bg:#040608;--s:#0a0d12;--b:#141920;--ba:#1e2d3d;--t:#c8d6e5;--m:#4a5568;--bl:#3b82f6}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--t);font-family:-apple-system,sans-serif;min-height:100vh}}
.hdr{{border-bottom:1px solid var(--b);padding:14px 24px;display:flex;align-items:center;justify-content:space-between}}
.logo{{font-size:13px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--t);text-decoration:none}}.logo span{{color:var(--bl)}}
.nav a{{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:var(--m);text-decoration:none;margin-left:16px}}
.wrap{{max-width:1100px;margin:0 auto;padding:48px 24px 80px}}
.bc{{font-size:11px;text-transform:uppercase;letter-spacing:.15em;color:var(--m);margin-bottom:16px}}.bc a{{color:var(--m);text-decoration:none}}
h1{{font-size:clamp(32px,4vw,48px);font-weight:800;letter-spacing:-.02em;margin-bottom:8px}}
.sub{{font-size:13px;color:var(--m);margin-bottom:32px}}
.section-title{{font-size:11px;text-transform:uppercase;letter-spacing:.2em;color:var(--m);margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid var(--b)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;margin-bottom:32px}}
.nc{{display:block;padding:14px 16px;background:var(--s);border:1px solid var(--b);border-radius:10px;text-decoration:none;transition:.15s}}
.nc:hover{{border-color:var(--bl);background:#0d1520}}
.nc-comune{{border-style:dashed}}
.nc-comune:hover{{border-style:solid}}
.nn{{display:block;font-size:13px;font-weight:600;color:var(--t);margin-bottom:3px}}
.ns{{display:block;font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:var(--m)}}
.ftr{{border-top:1px solid var(--b);padding:24px;text-align:center;font-size:11px;color:var(--m)}}
.ftr a{{color:var(--m);text-decoration:none}}
</style></head>
<body>
<header class="hdr">
  <a href="/" class="logo">Weather<span>Arb</span></a>
  <nav class="nav"><a href="/it/">Italia</a><a href="/data/">Data</a><a href="/news/">News</a></nav>
</header>
<div class="wrap">
  <div class="bc"><a href="/">WeatherArb</a> / <a href="/it/">Italia</a> / {regione}</div>
  <h1>{regione}</h1>
  <p class="sub">{len(province)} province &middot; {len(reg_comuni)} comuni &middot; dati live Z-Score</p>
  <div class="section-title">Province — Nodi di rilevazione</div>
  <div class="grid">{prov_cards}</div>
  {'<div class="section-title">Comuni</div><div class="grid">'+comuni_cards+'</div>' if comuni_cards else ''}
</div>
<footer class="ftr">
  <a href="/">WeatherArb</a> &middot; <a href="/it/">Italia</a> &middot; <a href="/pricing/">API Pro</a>
</footer>
</body></html>'''

    (reg_dir / 'index.html').write_text(html_reg, encoding='utf-8')
    reg_ok += 1

print(f"✅ {reg_ok} hub regionali generati")
