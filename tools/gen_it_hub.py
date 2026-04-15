#!/usr/bin/env python3
"""
Rigenera data/website/it/index.html con province ordinate per regione
+ hub per ogni regione italiana con link comuni
SOLO regioni italiane — le regioni europee vanno nei loro path /de/ /fr/ ecc.
"""
import json, re
from pathlib import Path
from unicodedata import normalize

def sl(t):
    s = normalize('NFKD', t).encode('ascii','ignore').decode('ascii')
    return re.sub(r'[\s_]+','-', re.sub(r'[^\w\s-]','',s).strip().lower())

REGIONI_ITALIANE = {
    'Piemonte', "Valle d'Aosta", 'Lombardia', 'Trentino-Alto Adige',
    'Veneto', 'Friuli-Venezia Giulia', 'Liguria', 'Emilia-Romagna',
    'Toscana', 'Umbria', 'Marche', 'Lazio', 'Abruzzo', 'Molise',
    'Campania', 'Puglia', 'Basilicata', 'Calabria', 'Sicilia', 'Sardegna'
}

PROV_REG = {
    'Firenze':'Toscana','Prato':'Toscana','Pistoia':'Toscana','Lucca':'Toscana',
    'Pisa':'Toscana','Livorno':'Toscana','Arezzo':'Toscana','Siena':'Toscana',
    'Grosseto':'Toscana','Massa-Carrara':'Toscana',
    'Perugia':'Umbria','Terni':'Umbria',
    'Ancona':'Marche','Pesaro e Urbino':'Marche','Macerata':'Marche',
    'Fermo':'Marche','Ascoli Piceno':'Marche',
    'Roma':'Lazio','Latina':'Lazio','Frosinone':'Lazio','Viterbo':'Lazio','Rieti':'Lazio',
    "L'Aquila":'Abruzzo','Teramo':'Abruzzo','Pescara':'Abruzzo','Chieti':'Abruzzo',
    'Campobasso':'Molise','Isernia':'Molise',
    'Napoli':'Campania','Salerno':'Campania','Caserta':'Campania',
    'Avellino':'Campania','Benevento':'Campania',
    'Bari':'Puglia','Taranto':'Puglia','Foggia':'Puglia','Lecce':'Puglia',
    'Brindisi':'Puglia','Barletta-Andria-Trani':'Puglia',
    'Potenza':'Basilicata','Matera':'Basilicata',
    'Catanzaro':'Calabria','Cosenza':'Calabria','Reggio Calabria':'Calabria',
    'Crotone':'Calabria','Vibo Valentia':'Calabria',
    'Palermo':'Sicilia','Catania':'Sicilia','Messina':'Sicilia','Siracusa':'Sicilia',
    'Ragusa':'Sicilia','Trapani':'Sicilia','Agrigento':'Sicilia',
    'Caltanissetta':'Sicilia','Enna':'Sicilia',
    'Cagliari':'Sardegna','Sassari':'Sardegna','Nuoro':'Sardegna',
    'Oristano':'Sardegna','Sud Sardegna':'Sardegna',
}

with open('data/province_coords.json') as f:
    raw = json.load(f)
all_p = raw['province'] if 'province' in raw else raw

# Solo province italiane
it_p = [p for p in all_p if p.get('country', 'Italy') == 'Italy']

# Assegna regione corretta
for p in it_p:
    reg = p.get('regione', '')
    if reg not in REGIONI_ITALIANE:
        p['regione'] = PROV_REG.get(p['nome'], '')

# Raggruppa per regione (solo regioni italiane)
regioni = {}
for p in it_p:
    reg = p.get('regione', '')
    if reg not in REGIONI_ITALIANE:
        continue
    if reg not in regioni:
        regioni[reg] = []
    regioni[reg].append(p)

regioni_sorted = sorted(regioni.items())

with open('data/comuni_italy.json') as f:
    comuni = json.load(f)

comuni_per_regione = {}
for c in comuni:
    reg = c.get('regione', '')
    if reg not in comuni_per_regione:
        comuni_per_regione[reg] = []
    comuni_per_regione[reg].append(c)

total_p = len(it_p)
total_c = len(comuni)

print(f"Regioni trovate: {[r for r,_ in regioni_sorted]}")

reg_nav = ''.join(
    f'<a href="#{sl(r)}">{r}</a>'
    for r, _ in regioni_sorted
)

sections = ""
for regione, province in regioni_sorted:
    reg_slug = sl(regione)
    reg_comuni = comuni_per_regione.get(regione, [])
    n_comuni = len(reg_comuni)
    comuni_label = f' <span style="font-size:11px;color:var(--m);font-weight:400">+{n_comuni} comuni</span>' if n_comuni else ''

    prov_cards = ''.join(
        f'<a href="/it/{sl(p["nome"])}/" class="nc">'
        f'<span class="nn">{p["nome"]}</span>'
        f'<span class="ns">Provincia</span>'
        f'</a>'
        for p in sorted(province, key=lambda x: x['nome'])
    )

    comuni_cards = ''.join(
        f'<a href="/it/{reg_slug}/{sl(c["nome"])}/" class="nc nc-c">'
        f'<span class="nn">{c["nome"]}</span>'
        f'<span class="ns">{c.get("provincia","")[:14]}</span>'
        f'</a>'
        for c in sorted(reg_comuni, key=lambda x: -x.get('pop', 0))[:6]
    )

    sections += f'''
<div class="reg-section" id="{reg_slug}">
  <div class="reg-hdr">
    <span class="reg-name">{regione}{comuni_label}</span>
    <a href="/it/{reg_slug}/" class="reg-link">Vedi tutto →</a>
  </div>
  <div class="grid">{prov_cards}{comuni_cards}</div>
</div>'''

html = f'''<!DOCTYPE html>
<html lang="it"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Italia — WeatherArb Intelligence Network</title>
<meta name="description" content="Anomalie meteo per {total_p} province e {total_c} comuni italiani. Z-Score NASA POWER 25 anni. HDD/CDD energy data. WeatherArb.">
<style>
:root{{--bg:#040608;--s:#0a0d12;--b:#141920;--t:#c8d6e5;--m:#4a5568;--bl:#3b82f6}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--t);font-family:-apple-system,sans-serif;min-height:100vh}}
.hdr{{border-bottom:1px solid var(--b);padding:14px 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:10;background:rgba(4,6,8,.95);backdrop-filter:blur(12px)}}
.logo{{font-size:13px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--t);text-decoration:none}}.logo span{{color:var(--bl)}}
.nav a{{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:var(--m);text-decoration:none;margin-left:16px}}
.wrap{{max-width:1100px;margin:0 auto;padding:48px 24px 80px}}
.bc{{font-size:11px;text-transform:uppercase;letter-spacing:.15em;color:var(--m);margin-bottom:16px}}.bc a{{color:var(--m);text-decoration:none}}
h1{{font-size:clamp(32px,4vw,56px);font-weight:800;letter-spacing:-.02em;margin-bottom:8px}}
.sub{{font-size:13px;color:var(--m);margin-bottom:28px}}.sub b{{color:var(--bl)}}
.reg-nav{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:36px;padding:14px;background:var(--s);border:1px solid var(--b);border-radius:10px}}
.reg-nav a{{font-size:11px;color:var(--m);text-decoration:none;padding:4px 10px;border:1px solid var(--b);border-radius:100px;transition:.15s}}
.reg-nav a:hover{{border-color:var(--bl);color:var(--bl)}}
.reg-section{{margin-bottom:32px}}
.reg-hdr{{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid var(--b)}}
.reg-name{{font-size:15px;font-weight:700}}
.reg-link{{font-size:11px;color:var(--bl);text-decoration:none}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(148px,1fr));gap:7px}}
.nc{{display:block;padding:13px 15px;background:var(--s);border:1px solid var(--b);border-radius:9px;text-decoration:none;transition:.15s}}
.nc:hover{{border-color:var(--bl);background:#0d1520}}
.nc-c{{border-style:dashed;opacity:.85}}.nc-c:hover{{border-style:solid;opacity:1}}
.nn{{display:block;font-size:13px;font-weight:600;color:var(--t);margin-bottom:2px}}
.ns{{display:block;font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--m)}}
.ftr{{border-top:1px solid var(--b);padding:20px;text-align:center;font-size:11px;color:var(--m)}}
.ftr a{{color:var(--m);text-decoration:none}}
</style></head>
<body>
<header class="hdr">
  <a href="/" class="logo">Weather<span>Arb</span></a>
  <nav class="nav"><a href="/">Home</a><a href="/data/">Data</a><a href="/news/">News</a><a href="/pricing/">API</a></nav>
</header>
<div class="wrap">
  <div class="bc"><a href="/">WeatherArb</a> / Italia</div>
  <h1>Italia</h1>
  <p class="sub"><b>{total_p}</b> province &middot; <b>{total_c}</b> comuni &middot; Z-Score NASA POWER 25 anni</p>
  <div class="reg-nav">{reg_nav}</div>
  {sections}
</div>
<footer class="ftr">
  <a href="/">WeatherArb</a> &middot; <a href="/data/">Dashboard</a> &middot; <a href="/pricing/">API Pro</a>
</footer>
</body></html>'''

Path('data/website/it/index.html').write_text(html, encoding='utf-8')
print(f"✅ it/index.html — {len(regioni_sorted)} regioni italiane, {total_p} province, {total_c} comuni")

# ─── HUB REGIONALI ITALIANI ───
for regione, province in regioni_sorted:
    reg_slug = sl(regione)
    reg_comuni = comuni_per_regione.get(regione, [])
    reg_dir = Path(f'data/website/it/{reg_slug}')
    reg_dir.mkdir(parents=True, exist_ok=True)

    prov_cards = ''.join(
        f'<a href="/it/{sl(p["nome"])}/" class="nc">'
        f'<span class="nn">{p["nome"]}</span>'
        f'<span class="ns">Provincia &middot; nodo dati</span>'
        f'</a>'
        for p in sorted(province, key=lambda x: x['nome'])
    )

    comuni_cards = ''.join(
        f'<a href="/it/{reg_slug}/{sl(c["nome"])}/" class="nc nc-c">'
        f'<span class="nn">{c["nome"]}</span>'
        f'<span class="ns">{c.get("provincia","")[:15]}</span>'
        f'</a>'
        for c in sorted(reg_comuni, key=lambda x: -x.get('pop', 0))
    )

    hub_html = f'''<!DOCTYPE html>
<html lang="it"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{regione} Meteo Anomalie | WeatherArb</title>
<meta name="description" content="Anomalie meteo in {regione}: {len(province)} province e {len(reg_comuni)} comuni monitorati. Z-Score NASA POWER 25 anni. WeatherArb.">
<link rel="canonical" href="https://weatherarb.com/it/{reg_slug}/">
<style>
:root{{--bg:#040608;--s:#0a0d12;--b:#141920;--t:#c8d6e5;--m:#4a5568;--bl:#3b82f6}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--t);font-family:-apple-system,sans-serif;min-height:100vh}}
.hdr{{border-bottom:1px solid var(--b);padding:14px 24px;display:flex;align-items:center;justify-content:space-between}}
.logo{{font-size:13px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--t);text-decoration:none}}.logo span{{color:var(--bl)}}
.nav a{{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:var(--m);text-decoration:none;margin-left:16px}}
.wrap{{max-width:1100px;margin:0 auto;padding:48px 24px 80px}}
.bc{{font-size:11px;text-transform:uppercase;letter-spacing:.15em;color:var(--m);margin-bottom:16px}}.bc a{{color:var(--m);text-decoration:none}}
h1{{font-size:clamp(28px,4vw,48px);font-weight:800;letter-spacing:-.02em;margin-bottom:8px}}
.sub{{font-size:13px;color:var(--m);margin-bottom:28px}}
.stitle{{font-size:11px;text-transform:uppercase;letter-spacing:.2em;color:var(--m);margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid var(--b)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(148px,1fr));gap:7px;margin-bottom:28px}}
.nc{{display:block;padding:13px 15px;background:var(--s);border:1px solid var(--b);border-radius:9px;text-decoration:none;transition:.15s}}
.nc:hover{{border-color:var(--bl);background:#0d1520}}
.nc-c{{border-style:dashed;opacity:.85}}.nc-c:hover{{border-style:solid;opacity:1}}
.nn{{display:block;font-size:13px;font-weight:600;color:var(--t);margin-bottom:2px}}
.ns{{display:block;font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--m)}}
.ftr{{border-top:1px solid var(--b);padding:20px;text-align:center;font-size:11px;color:var(--m)}}
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
  <p class="sub">{len(province)} province &middot; {len(reg_comuni)} comuni &middot; Z-Score live</p>
  <div class="stitle">Province — Nodi di rilevazione</div>
  <div class="grid">{prov_cards}</div>
  {'<div class="stitle">Comuni</div><div class="grid">'+comuni_cards+'</div>' if comuni_cards else ''}
</div>
<footer class="ftr">
  <a href="/">WeatherArb</a> &middot; <a href="/it/">Italia</a> &middot; <a href="/pricing/">API Pro</a>
</footer>
</body></html>'''

    (reg_dir / 'index.html').write_text(hub_html, encoding='utf-8')

print(f"✅ {len(regioni_sorted)} hub regionali italiani generati")
