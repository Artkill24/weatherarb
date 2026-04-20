#!/usr/bin/env python3
"""
WeatherArb — Generatore Landing Comuni v7
Shadow Node technique: ogni comune usa i dati della provincia più vicina
URL: /it/{regione}/{comune}/
Genera top comuni per popolazione — file statici per SEO
"""
import json, re, math
from pathlib import Path
from unicodedata import normalize

def sl(t):
    s = normalize('NFKD', t).encode('ascii','ignore').decode('ascii')
    return re.sub(r'[\s_]+','-', re.sub(r'[^\w\s-]','',s).strip().lower())

API = 'https://api.weatherarb.com'

# Carica province italiane come shadow nodes
with open('data/province_coords.json') as f:
    raw = json.load(f)
all_prov = raw['province'] if 'province' in raw else raw
it_prov = [p for p in all_prov if p.get('country','Italy') == 'Italy']

def nearest_prov(lat, lon):
    return min(it_prov, key=lambda p: math.sqrt((p['lat']-lat)**2+(p['lon']-lon)**2))

# Carica comuni esistenti
with open('data/comuni_italy.json') as f:
    comuni = json.load(f)

print(f"Comuni nel database: {len(comuni)}")

ok = sk = 0
for comune in comuni:
    name = comune.get('nome','')
    regione = comune.get('regione','')
    lat = comune.get('lat', 45.0)
    lon = comune.get('lon', 10.0)
    pop = comune.get('pop', 0)

    # Trova provincia shadow node più vicina
    shadow = nearest_prov(lat, lon)
    shadow_slug = sl(shadow['nome'])
    shadow_name = shadow['nome']
    shadow_regione = shadow.get('regione', regione)

    # Usa regione del comune (più precisa) o del shadow
    reg = regione or shadow_regione
    reg_slug = sl(reg)
    comune_slug = sl(name)

    # Salta se già esiste
    d = Path(f'data/website/it/{reg_slug}/{comune_slug}')
    d.mkdir(parents=True, exist_ok=True)
    p = d / 'index.html'

    if p.exists():
        sk += 1
        continue

    # Salta se nome == shadow (già ha landing provincia)
    if sl(name) == shadow_slug:
        sk += 1
        continue

    city_safe = name.replace('"','').replace("'","")
    prov_safe = comune.get('provincia','').replace('"','').replace("'","")

    css = (
        '*{box-sizing:border-box;margin:0;padding:0}'
        'body{background:#040608;color:#c8d6e5;font-family:-apple-system,sans-serif;min-height:100vh}'
        '.hdr{border-bottom:1px solid #141920;padding:14px 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:10;background:rgba(4,6,8,.95);backdrop-filter:blur(12px)}'
        '.logo{font-size:13px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:#c8d6e5;text-decoration:none}.logo span{color:#3b82f6}'
        '.nav a{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:#4a5568;text-decoration:none;margin-left:16px}'
        '.hero{max-width:1100px;margin:0 auto;padding:48px 24px 32px}'
        '.bc{font-size:11px;text-transform:uppercase;letter-spacing:.15em;color:#4a5568;margin-bottom:12px}.bc a{color:#4a5568;text-decoration:none}'
        'h1{font-size:clamp(28px,5vw,52px);font-weight:800;letter-spacing:-.02em;line-height:1;color:#fff;margin-bottom:8px}'
        '.cmeta{font-size:12px;color:#4a5568;letter-spacing:.08em;text-transform:uppercase}.cmeta span{color:#3b82f6}'
        '.main{max-width:1100px;margin:0 auto;padding:0 24px 80px}'
        '.shadow-badge{display:inline-flex;align-items:center;gap:8px;background:rgba(59,130,246,.06);border:1px solid rgba(59,130,246,.15);border-radius:8px;padding:10px 16px;margin-bottom:24px;font-size:13px;color:#c8d6e5}'
        '.shadow-badge span{color:#3b82f6;font-weight:700}'
        '.panel{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:1px;background:#141920;border:1px solid #141920;border-radius:12px;overflow:hidden;margin-bottom:24px}'
        '.pcell{background:#0a0d12;padding:14px 16px}'
        '.plabel{font-size:9px;text-transform:uppercase;letter-spacing:.15em;color:#4a5568;margin-bottom:5px}'
        '.pval{font-size:18px;font-weight:700;line-height:1.2}'
        '.psub{font-size:9px;color:#4a5568;margin-top:3px}'
        '.energy-row{grid-column:1/-1;background:#0a0d12;border-top:1px solid #141920;padding:14px 16px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}'
        '.energy-label{font-size:9px;text-transform:uppercase;letter-spacing:.12em;color:#4a5568;margin-bottom:3px}'
        '.energy-val{font-size:15px;font-weight:700}'
        '.energy-sub{font-size:9px;color:#4a5568;margin-top:2px}'
        '.analysis-bar{grid-column:1/-1;background:#0a0d12;padding:12px 16px;border-top:1px solid #141920}'
        '.alabel{font-size:9px;text-transform:uppercase;letter-spacing:.15em;color:#4a5568;margin-bottom:3px}'
        '.aval{font-size:14px;font-weight:700;color:#3b82f6}'
        '.mbox{background:#0a0d12;border:1px solid #141920;border-radius:10px;padding:20px;margin-bottom:20px}'
        '.stitle{font-size:10px;text-transform:uppercase;letter-spacing:.2em;color:#4a5568;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #141920}'
        '.sectors{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-bottom:20px}'
        '.sector{background:#0a0d12;border:1px solid #141920;border-radius:9px;padding:14px}'
        '.sector-icon{font-size:16px;margin-bottom:5px}'
        '.sector-name{font-size:11px;font-weight:700;color:#fff;margin-bottom:3px;text-transform:uppercase;letter-spacing:.08em}'
        '.sector-status{font-size:11px;color:#4a5568;line-height:1.4}'
        '.nl-box{background:linear-gradient(135deg,rgba(59,130,246,.08),rgba(16,185,129,.05));border:1px solid rgba(59,130,246,.2);border-radius:10px;padding:20px;margin-bottom:20px}'
        '.nl-title{font-size:14px;font-weight:700;color:#fff;margin-bottom:6px}'
        '.nl-sub{font-size:12px;color:#c8d6e5;line-height:1.5;margin-bottom:12px}'
        '.nl-row{display:flex;gap:8px;flex-wrap:wrap}'
        '.nl-input{flex:1;min-width:160px;background:rgba(255,255,255,.05);border:1px solid #1e2d3d;border-radius:7px;padding:9px 12px;color:#c8d6e5;font-size:13px;outline:none}'
        '.nl-btn{background:#3b82f6;color:#fff;border:none;border-radius:7px;padding:9px 18px;font-size:13px;font-weight:700;cursor:pointer}'
        '.nl-msg{display:none;font-size:12px;margin-top:8px;padding:7px;border-radius:5px}'
        '.ftr{border-top:1px solid #141920;padding:20px;text-align:center;font-size:11px;color:#4a5568}'
        '.ftr a{color:#4a5568;text-decoration:none}'
    )

    nl_js = (
        'function nlsub(){'
        'var e=document.getElementById("nle").value.trim();'
        'var m=document.getElementById("nlm");'
        'if(!e||e.indexOf("@")<0){'
        'm.style.display="block";m.style.background="rgba(239,68,68,.1)";'
        'm.style.color="#ef4444";m.textContent="Email non valida";return;}'
        f'fetch("{API}/api/newsletter/subscribe?email="+encodeURIComponent(e)+"&city={city_safe}&country_code=it",'
        '{method:"POST"})'
        '.then(function(r){return r.json();})'
        '.then(function(d){'
        'document.getElementById("nl-row").style.display="none";'
        'm.style.display="block";m.style.background="rgba(16,185,129,.1)";'
        'm.style.color="#10b981";'
        'm.textContent=d.status==="already_subscribed"?"Sei gia iscritto!":"Iscritto!";'
        '}).catch(function(){'
        'm.style.display="block";m.style.background="rgba(239,68,68,.1)";'
        'm.style.color="#ef4444";m.textContent="Errore";});}'
    )

    pulse_js = (
        'function updateSectors(sc,hdd,cdd,wind,hum){'
        'var agr=document.getElementById("sector-agr");'
        'var log=document.getElementById("sector-log");'
        'var ene=document.getElementById("sector-ene");'
        'if(agr){agr.textContent=(hum>80||hum<30)?"Rischio stress idrico":"Condizioni normali";}'
        'if(log){log.textContent=(wind>50||sc>7)?"Condizioni avverse":"Condizioni ottimali";}'
        'if(ene){ene.textContent=(hdd>5)?"Alta domanda riscaldamento":(cdd>5)?"Alta domanda raffreddamento":"Domanda nella norma";}'
        '}'
        f'async function loadPulse(){{'
        f'try{{'
        f'var r=await fetch("{API}/api/v1/pulse/{shadow_slug}");'
        f'var d=await r.json();'
        f'var w=d.weather||{{}};'
        f'var z=w.z_score||0;var sc=d.signal?d.signal.score:0;'
        f'var t=w.temperature_c;var hum=w.humidity_pct;var wind=w.wind_kmh;'
        f'var hdd=w.hdd;var cdd=w.cdd;var hdd_delta=w.hdd_delta;'
        f'var lbl=w.anomaly_label||w.anomaly_level||"";'
        f'var col=sc>=7?"#ef4444":sc>=5?"#f97316":sc>=3?"#f59e0b":"#10b981";'
        f'var ids=["pz","psc","pt","phum","pwind","phdd","pcdd","phdd_delta","plbl"];'
        f'var els={{}};ids.forEach(function(id){{els[id]=document.getElementById(id);}});'
        f'if(els.pz){{els.pz.textContent=(z>=0?"+":"")+z.toFixed(2)+"s";els.pz.style.color=col;}}'
        f'if(els.psc){{els.psc.textContent=sc.toFixed(1)+"/10";els.psc.style.color=col;}}'
        f'if(els.pt&&t!=null){{els.pt.textContent=t.toFixed(1)+"C";}}'
        f'if(els.phum&&hum!=null){{els.phum.textContent=hum+"%";}}'
        f'if(els.pwind&&wind!=null){{els.pwind.textContent=wind+" kmh";}}'
        f'if(els.phdd&&hdd!=null){{els.phdd.textContent=hdd.toFixed(1)+" GG";}}'
        f'if(els.pcdd&&cdd!=null){{els.pcdd.textContent=cdd.toFixed(1)+" GG";}}'
        f'if(els.phdd_delta&&hdd_delta!=null){{'
        f'els.phdd_delta.textContent=(hdd_delta>=0?"+":"")+hdd_delta.toFixed(1)+" GG";'
        f'els.phdd_delta.style.color=hdd_delta>2?"#ef4444":hdd_delta<-2?"#10b981":"#f59e0b";}}'
        f'if(els.plbl&&lbl){{els.plbl.textContent=lbl;els.plbl.style.color=col;}}'
        f'updateSectors(sc,hdd||0,cdd||0,wind||0,hum||50);'
        f'}}catch(e){{console.warn("pulse unavailable");}}}}'
        f'loadPulse();setInterval(loadPulse,3600000);'
    )

    pop_str = f"{pop:,}".replace(",",".") if pop > 0 else ""
    pop_meta = f" &middot; {pop_str} abitanti" if pop_str else ""

    html = (
        f'<!DOCTYPE html>'
        f'<html lang="it">'
        f'<head>'
        f'<meta charset="UTF-8">'
        f'<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{name} Meteo Anomalie | WeatherArb Intelligence</title>'
        f'<meta name="description" content="Anomalie meteo in tempo reale per {name} ({prov_safe}, {reg}). Z-Score, HDD/CDD energia, vento e umidita. Dati dal nodo {shadow_name}. WeatherArb.">'
        f'<link rel="canonical" href="https://weatherarb.com/it/{reg_slug}/{comune_slug}/">'
        f'<style>{css}</style>'
        f'</head>'
        f'<body>'
        f'<header class="hdr">'
        f'<a href="/" class="logo">Weather<span>Arb</span></a>'
        f'<nav class="nav"><a href="/it/">Italia</a><a href="/data/">Data</a><a href="/news/">News</a></nav>'
        f'</header>'
        f'<div class="hero">'
        f'<div class="bc"><a href="/">WeatherArb</a> / <a href="/it/">Italia</a> / <a href="/it/{reg_slug}/">{reg}</a> / {name}</div>'
        f'<h1>{name}</h1>'
        f'<p class="cmeta">{prov_safe} &middot; {reg} &middot; <span>{round(lat,4)}&deg;N {round(lon,4)}&deg;E</span>{pop_meta}</p>'
        f'</div>'
        f'<main class="main">'
        f'<div class="shadow-badge">Dati rilevati dal nodo <span>{shadow_name}</span> &mdash; stazione meteo piu vicina a {name}</div>'
        f'<div class="panel">'
        f'<div class="pcell"><div class="plabel">Z-Score</div><div class="pval" id="pz" style="color:#10b981">...</div><div class="psub">vs media 25 anni</div></div>'
        f'<div class="pcell"><div class="plabel">Score</div><div class="pval" id="psc">...</div><div class="psub">0-10</div></div>'
        f'<div class="pcell"><div class="plabel">Temperatura</div><div class="pval" id="pt">...</div><div class="psub">corrente</div></div>'
        f'<div class="pcell"><div class="plabel">Umidita</div><div class="pval" id="phum">...</div><div class="psub">relativa</div></div>'
        f'<div class="pcell"><div class="plabel">Vento</div><div class="pval" id="pwind">...</div><div class="psub">km/h</div></div>'
        f'<div class="energy-row">'
        f'<div><div class="energy-label">HDD oggi</div><div class="energy-val" id="phdd">...</div><div class="energy-sub">riscaldamento GG</div></div>'
        f'<div><div class="energy-label">CDD oggi</div><div class="energy-val" id="pcdd">...</div><div class="energy-sub">raffresc. GG</div></div>'
        f'<div><div class="energy-label">Delta HDD</div><div class="energy-val" id="phdd_delta">...</div><div class="energy-sub">vs storico</div></div>'
        f'</div>'
        f'<div class="analysis-bar"><div class="alabel">Analisi WeatherArb</div><div class="aval" id="plbl">Caricamento...</div></div>'
        f'</div>'
        f'<div class="stitle" style="font-size:10px;text-transform:uppercase;letter-spacing:.2em;color:#4a5568;margin:20px 0 12px;padding-bottom:8px;border-bottom:1px solid #141920">Settori Impattati</div>'
        f'<div class="sectors">'
        f'<div class="sector"><div class="sector-icon">&#127806;</div><div class="sector-name">Agricoltura</div><div class="sector-status" id="sector-agr">Caricamento...</div></div>'
        f'<div class="sector"><div class="sector-icon">&#128665;</div><div class="sector-name">Logistica</div><div class="sector-status" id="sector-log">Caricamento...</div></div>'
        f'<div class="sector"><div class="sector-icon">&#9889;</div><div class="sector-name">Energia</div><div class="sector-status" id="sector-ene">Caricamento...</div></div>'
        f'</div>'
        f'<div class="mbox">'
        f'<div class="stitle">Informazioni su {name}</div>'
        f'<p style="font-size:13px;color:#4a5568;line-height:1.7">'
        f'{name} e un comune della provincia di {prov_safe}, {reg}. '
        f'WeatherArb monitora le condizioni meteo per {name} tramite il nodo di rilevazione piu vicino: {shadow_name} ({round(lat,2)}&deg;N, {round(lon,2)}&deg;E). '
        f'I dati includono Z-Score su baseline NASA POWER 25 anni, Heating Degree Days (HDD) e Cooling Degree Days (CDD) secondo lo standard EN ISO 15927.'
        f'</p>'
        f'</div>'
        f'<div class="nl-box">'
        f'<div class="nl-title">Alert Meteo per {name}</div>'
        f'<div class="nl-sub">Z-Score, HDD/CDD e anomalie meteo per {name} nella tua inbox. Gratuito.</div>'
        f'<div class="nl-row" id="nl-row">'
        f'<input id="nle" class="nl-input" type="email" placeholder="La tua email" onkeydown="if(event.key===\'Enter\')nlsub()">'
        f'<button class="nl-btn" onclick="nlsub()">Iscriviti</button>'
        f'</div>'
        f'<div id="nlm" class="nl-msg"></div>'
        f'</div>'
        f'</main>'
        f'<footer class="ftr">'
        f'<a href="/">WeatherArb</a> &middot; <a href="/it/">Italia</a> &middot; <a href="/it/{reg_slug}/">{reg}</a> &middot; <a href="/pricing/">API Pro</a>'
        f'</footer>'
        f'<script>{nl_js}{pulse_js}</script>'
        f'</body></html>'
    )

    p.write_text(html, encoding='utf-8')
    ok += 1

print(f'Generati: {ok} nuovi comuni | Saltati (esistenti): {sk}')
print(f'Totale landing comuni IT: {ok + sk}')
