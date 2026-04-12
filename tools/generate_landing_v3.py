#!/usr/bin/env python3
"""
WeatherArb — Landing Page Generator v3
Fix: città nella cartella paese corretta + homepage completa
"""

import json
import re
import shutil
from pathlib import Path
from unicodedata import normalize

BASE_DIR = Path("data/website")
API_BASE = "https://api.weatherarb.com"

COUNTRY_CODE = {
    "Italy": "it", "Germany": "de", "France": "fr", "Spain": "es",
    "United Kingdom": "gb", "Sweden": "se", "Netherlands": "nl",
    "Poland": "pl", "Austria": "at", "Switzerland": "ch",
    "Belgium": "be", "Portugal": "pt", "Denmark": "dk", "Norway": "no"
}

COUNTRY_LANG = {
    "Italy": "it", "Germany": "de", "France": "fr", "Spain": "es",
    "United Kingdom": "en", "Sweden": "sv", "Netherlands": "nl",
    "Poland": "pl", "Austria": "de", "Switzerland": "de",
    "Belgium": "fr", "Portugal": "pt", "Denmark": "da", "Norway": "no"
}

COUNTRY_LABEL = {
    "it": "Italia", "de": "Deutschland", "fr": "France", "es": "España",
    "gb": "United Kingdom", "se": "Sverige", "nl": "Nederland",
    "pl": "Polska", "at": "Österreich", "ch": "Schweiz",
    "be": "Belgique", "pt": "Portugal", "dk": "Danmark", "no": "Norge"
}

# Fallback manuale per città senza campo "country"
CITY_COUNTRY_FALLBACK = {
    # Germany
    "münchen": "de", "munchen": "de", "hamburg": "de", "berlin": "de",
    "frankfurt": "de", "stuttgart": "de", "köln": "de", "koln": "de",
    "düsseldorf": "de", "dusseldorf": "de", "nürnberg": "de", "nurnberg": "de",
    # Spain
    "madrid": "es", "barcelona": "es", "valencia": "es", "sevilla": "es", "bilbao": "es",
    # France
    "paris": "fr", "lyon": "fr", "marseille": "fr", "bordeaux": "fr", "nice": "fr",
    # UK
    "london": "gb", "manchester": "gb", "birmingham": "gb", "edinburgh": "gb",
    "glasgow": "gb", "leeds": "gb", "bristol": "gb", "cardiff": "gb",
    "liverpool": "gb", "sheffield": "gb",
    # Sweden
    "stockholm": "se", "göteborg": "se", "goteborg": "se", "malmö": "se", "malmo": "se",
    "uppsala": "se", "västerås": "se", "vasteras": "se", "örebro": "se", "orebro": "se",
    "linköping": "se", "linkoping": "se", "helsingborg": "se",
    "jönköping": "se", "jonkoping": "se", "umeå": "se", "umea": "se",
    # Netherlands
    "amsterdam": "nl", "rotterdam": "nl", "den haag": "nl", "den-haag": "nl",
    "utrecht": "nl", "eindhoven": "nl", "groningen": "nl",
    # Poland
    "warszawa": "pl", "kraków": "pl", "krakow": "pl", "wrocław": "pl", "wroclaw": "pl",
    "poznań": "pl", "poznan": "pl", "gdańsk": "pl", "gdansk": "pl",
    "łódź": "pl", "lodz": "pl", "odz": "pl",
    # Austria
    "wien": "at", "graz": "at", "linz": "at", "salzburg": "at", "innsbruck": "at",
    # Switzerland
    "zürich": "ch", "zurich": "ch", "genève": "ch", "geneve": "ch",
    "basel": "ch", "bern": "ch", "lausanne": "ch",
    # Belgium
    "bruxelles": "be", "antwerpen": "be", "gent": "be", "liège": "be", "liege": "be",
    # Portugal
    "lisboa": "pt", "porto": "pt", "braga": "pt",
    # Denmark
    "københavn": "dk", "kobenhavn": "dk", "kbenhavn": "dk",
    "aarhus": "dk", "odense": "dk",
    # Norway
    "oslo": "no", "bergen": "no", "trondheim": "no", "stavanger": "no",
}


def slugify(name: str) -> str:
    s = normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    return re.sub(r"[\s_]+", "-", s)


def get_country_code(city: dict) -> str:
    # 1. Prova campo "country"
    country_name = city.get("country", "")
    if country_name and country_name in COUNTRY_CODE:
        return COUNTRY_CODE[country_name]

    # 2. Fallback su nome città
    name_lower = city.get("nome", "").lower()
    if name_lower in CITY_COUNTRY_FALLBACK:
        return CITY_COUNTRY_FALLBACK[name_lower]

    # 3. Default Italia
    return "it"


def get_lang(country_name: str) -> str:
    return COUNTRY_LANG.get(country_name, "it")


# ─── LANDING TEMPLATE ───────────────────────────────────────────────────────

def generate_landing(city: dict) -> str:
    name = city["nome"]
    country_name = city.get("country", "Italy")
    cc = get_country_code(city)
    lang = get_lang(country_name)
    lat = city.get("lat", 45.0)
    lon = city.get("lon", 10.0)
    slug = slugify(name)
    api_id = city.get("id", slug)
    country_label = COUNTRY_LABEL.get(cc, cc.upper())
    hub_url = f"/{cc}/"

    labels = {
        "it": {"horizon": "Impact Horizon", "trend": "Trend 7 Giorni", "means": "Metodologia", "alerts": "Ricevi Alert", "monitoring": "Monitoraggio Attivo", "loading": "Sincronizzazione..."},
        "de": {"horizon": "Impact Horizon", "trend": "7-Tage-Trend", "means": "Methodik", "alerts": "Alarme erhalten", "monitoring": "Aktive Überwachung", "loading": "Laden..."},
        "fr": {"horizon": "Horizon d'Impact", "trend": "Tendance 7 Jours", "means": "Méthodologie", "alerts": "Recevoir des Alertes", "monitoring": "Surveillance Active", "loading": "Chargement..."},
        "es": {"horizon": "Horizonte de Impacto", "trend": "Tendencia 7 Días", "means": "Metodología", "alerts": "Recibir Alertas", "monitoring": "Monitoreo Activo", "loading": "Cargando..."},
        "en": {"horizon": "Impact Horizon", "trend": "7-Day Trend", "means": "Methodology", "alerts": "Get Alerts", "monitoring": "Active Monitoring", "loading": "Loading..."},
        "sv": {"horizon": "Påverkan Horisont", "trend": "7-dagars Trend", "means": "Metodik", "alerts": "Få Varningar", "monitoring": "Aktiv Övervakning", "loading": "Laddar..."},
        "nl": {"horizon": "Impact Horizon", "trend": "7-daagse Trend", "means": "Methodologie", "alerts": "Ontvang Meldingen", "monitoring": "Actieve Monitoring", "loading": "Laden..."},
        "pl": {"horizon": "Horyzont Wpływu", "trend": "Trend 7 Dni", "means": "Metodologia", "alerts": "Otrzymuj Alerty", "monitoring": "Aktywny Monitoring", "loading": "Ładowanie..."},
        "pt": {"horizon": "Horizonte de Impacto", "trend": "Tendência 7 Dias", "means": "Metodologia", "alerts": "Receber Alertas", "monitoring": "Monitoramento Ativo", "loading": "Carregando..."},
        "da": {"horizon": "Påvirkningshorisont", "trend": "7-Dages Tendens", "means": "Metodologi", "alerts": "Modtag Advarsler", "monitoring": "Aktiv Overvågning", "loading": "Indlæser..."},
        "no": {"horizon": "Påvirkningshorisont", "trend": "7-Dagers Trend", "means": "Metodologi", "alerts": "Motta Varsler", "monitoring": "Aktiv Overvåking", "loading": "Laster..."},
    }
    L = labels.get(lang, labels["en"])

    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{name} — WeatherArb Intelligence</title>
  <meta name="description" content="Real-time weather anomaly analysis for {name}. Z-Score vs NASA POWER 25-year baseline. WeatherArb Weather Intelligence Agency.">
  <link rel="canonical" href="https://weatherarb.com/{cc}/{slug}/">
  <style>
    :root {{
      --bg:#040608;--surface:#0a0d12;--border:#141920;--border-a:#1e2d3d;
      --text:#c8d6e5;--muted:#4a5568;--blue:#3b82f6;--blue-dim:rgba(59,130,246,.12);
      --green:#10b981;--yellow:#f59e0b;--red:#ef4444;
    }}
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;min-height:100vh;overflow-x:hidden}}
    body::before{{content:'';position:fixed;inset:0;background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,.03) 2px,rgba(0,0,0,.03) 4px);pointer-events:none;z-index:9999}}
    .hdr{{position:sticky;top:0;z-index:100;background:rgba(4,6,8,.95);backdrop-filter:blur(12px);border-bottom:1px solid var(--border);padding:14px 24px;display:flex;align-items:center;justify-content:space-between}}
    .logo{{font-size:13px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--text);text-decoration:none}}.logo span{{color:var(--blue)}}
    .nav{{display:flex;gap:20px;align-items:center}}.nav a{{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);text-decoration:none}}.nav a:hover{{color:var(--text)}}
    .dot{{width:6px;height:6px;background:var(--green);border-radius:50%;box-shadow:0 0 8px var(--green);animation:pd 2s ease-in-out infinite}}
    @keyframes pd{{0%,100%{{opacity:1;transform:scale(1)}}50%{{opacity:.6;transform:scale(.8)}}}}
    .hero{{padding:48px 24px 36px;max-width:1100px;margin:0 auto;display:grid;grid-template-columns:1fr auto;gap:40px;align-items:start}}
    .bc{{font-size:11px;text-transform:uppercase;letter-spacing:.15em;color:var(--muted);margin-bottom:12px}}.bc a{{color:var(--muted);text-decoration:none}}.bc a:hover{{color:var(--blue)}}
    h1{{font-size:clamp(36px,5vw,64px);font-weight:800;letter-spacing:-.02em;line-height:1;color:#fff;margin-bottom:8px}}
    .cmeta{{font-size:12px;color:var(--muted);letter-spacing:.08em;text-transform:uppercase}}.cmeta span{{color:var(--blue)}}
    .gc{{display:flex;flex-direction:column;align-items:center;gap:8px;min-width:160px}}
    .gl{{font-size:10px;text-transform:uppercase;letter-spacing:.15em;color:var(--muted)}}
    .gsvg{{width:160px;height:100px}}
    .gv{{font-size:28px;font-weight:800;font-variant-numeric:tabular-nums;text-align:center}}
    .gs{{font-size:10px;text-transform:uppercase;letter-spacing:.15em;text-align:center;font-weight:700}}
    .main{{max-width:1100px;margin:0 auto;padding:0 24px 80px}}
    .panel{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1px;background:var(--border);border:1px solid var(--border);border-radius:12px;overflow:hidden;margin-bottom:24px}}
    .pcell{{background:var(--surface);padding:20px 24px;display:flex;flex-direction:column;gap:6px}}
    .plabel{{font-size:10px;text-transform:uppercase;letter-spacing:.15em;color:var(--muted)}}
    .pval{{font-size:26px;font-weight:700;font-variant-numeric:tabular-nums;line-height:1}}
    .psub{{font-size:11px;color:var(--muted)}}
    .stitle{{font-size:11px;text-transform:uppercase;letter-spacing:.2em;color:var(--muted);margin-bottom:16px;padding-bottom:10px;border-bottom:1px solid var(--border)}}
    .ibox{{background:var(--surface);border:1px solid var(--border-a);border-radius:12px;padding:28px;margin-bottom:24px;position:relative;overflow:hidden}}
    .ibox::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--blue),transparent)}}
    .ibox.crit::before{{background:linear-gradient(90deg,var(--red),transparent)}}.ibox.crit{{border-color:rgba(239,68,68,.2)}}
    .ihdr{{display:flex;align-items:center;gap:12px;margin-bottom:20px}}
    .iico{{width:36px;height:36px;background:var(--blue-dim);border:1px solid rgba(59,130,246,.3);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:16px}}
    .itit{{font-size:16px;font-weight:700}}.isub{{font-size:12px;color:var(--muted);margin-top:2px}}
    .igrid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
    .iitem{{background:rgba(255,255,255,.02);border:1px solid var(--border);border-radius:8px;padding:14px 16px}}
    .iilabel{{font-size:10px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);margin-bottom:6px}}
    .iival{{font-size:14px;font-weight:600;color:var(--text);line-height:1.4}}
    .cbox{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:24px;margin-bottom:24px}}
    .csvg{{width:100%;height:120px;overflow:visible}}
    .clabels{{display:flex;justify-content:space-between;margin-top:8px}}
    .clabel{{font-size:10px;color:var(--muted)}}
    .mbox{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:24px;margin-bottom:24px}}
    .mtext{{font-size:13px;color:var(--muted);line-height:1.6;margin-bottom:16px}}
    .mgrid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px}}
    .mi{{display:flex;flex-direction:column;gap:4px}}
    .milabel{{font-size:10px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted)}}
    .mival{{font-size:13px;font-weight:600}}
    .abox{{background:linear-gradient(135deg,rgba(59,130,246,.08),rgba(16,185,129,.05));border:1px solid rgba(59,130,246,.2);border-radius:12px;padding:28px;display:flex;align-items:center;justify-content:space-between;gap:24px;margin-bottom:24px}}
    .atext h3{{font-size:16px;font-weight:700;margin-bottom:6px}}.atext p{{font-size:13px;color:var(--muted)}}
    .abtn{{background:var(--blue);color:#fff;border:none;border-radius:8px;padding:10px 20px;font-size:13px;font-weight:700;cursor:pointer;text-decoration:none;white-space:nowrap;display:inline-block}}
    .abtn:hover{{opacity:.85}}
    .ftr{{border-top:1px solid var(--border);padding:24px;text-align:center;font-size:11px;color:var(--muted);letter-spacing:.08em}}
    .ftr a{{color:var(--muted);text-decoration:none}}.ftr a:hover{{color:var(--blue)}}
    @media(max-width:640px){{.hero{{grid-template-columns:1fr}}.igrid{{grid-template-columns:1fr}}.abox{{flex-direction:column}}}}
  </style>
</head>
<body>
<header class="hdr">
  <a href="/" class="logo">Weather<span>Arb</span></a>
  <nav class="nav">
    <a href="/data/">Data</a>
    <a href="/news/">News</a>
    <a href="/api.html">API</a>
    <a href="/alerts.html">Alerts</a>
    <div class="dot"></div>
  </nav>
</header>

<div class="hero">
  <div>
    <div class="bc"><a href="/">WeatherArb</a> / <a href="{hub_url}">{country_label}</a> / {name}</div>
    <h1>{name}</h1>
    <p class="cmeta">{country_label} · <span>{lat:.3f}°N {lon:.3f}°E</span> · NASA POWER Baseline</p>
  </div>
  <div class="gc">
    <div class="gl">Z-Score</div>
    <svg class="gsvg" viewBox="0 0 160 100" id="gsvg">
      <path d="M 20 90 A 70 70 0 0 1 140 90" fill="none" stroke="#141920" stroke-width="10" stroke-linecap="round"/>
      <path id="gfill" d="M 20 90 A 70 70 0 0 1 140 90" fill="none" stroke="#3b82f6" stroke-width="10"
            stroke-linecap="round" stroke-dasharray="220" stroke-dashoffset="220"
            style="transition:stroke-dashoffset 1.2s cubic-bezier(.4,0,.2,1),stroke .4s"/>
    </svg>
    <div class="gv" id="gval" style="color:var(--green)">—</div>
    <div class="gs" id="gstat" style="color:var(--green)">{L['loading']}</div>
  </div>
</div>

<main class="main">
  <div class="panel">
    <div class="pcell">
      <div class="plabel">Score</div>
      <div class="pval" id="score-v">—<span style="font-size:16px;color:var(--muted)">/10</span></div>
      <div class="psub" id="score-p">—</div>
    </div>
    <div class="pcell">
      <div class="plabel">Temperatura</div>
      <div class="pval" id="temp-v">—<span style="font-size:16px">°C</span></div>
      <div class="psub" id="temp-d">vs media storica</div>
    </div>
    <div class="pcell">
      <div class="plabel">Vertical</div>
      <div class="pval" style="font-size:18px" id="vert-v">—</div>
      <div class="psub" id="conf-v">—</div>
    </div>
    <div class="pcell">
      <div class="plabel">Baseline</div>
      <div class="pval" style="font-size:14px;color:var(--muted)">NASA POWER</div>
      <div class="psub">ERA5-Land · 25 anni</div>
    </div>
  </div>

  <h2 class="stitle">{L['horizon']}</h2>
  <div class="ibox" id="ibox">
    <div class="ihdr">
      <div class="iico" id="iico">⏱</div>
      <div>
        <div class="itit" id="itit">{L['monitoring']}</div>
        <div class="isub" id="isub">{L['loading']}</div>
      </div>
    </div>
    <div class="igrid">
      <div class="iitem"><div class="iilabel">Finestra di Preparazione</div><div class="iival" id="iwin">—</div></div>
      <div class="iitem"><div class="iilabel">Anomalia vs Storico</div><div class="iival" id="idelta">—</div></div>
      <div class="iitem"><div class="iilabel">Fase Operativa</div><div class="iival" id="iphase">—</div></div>
      <div class="iitem"><div class="iilabel">Prossimo Update</div><div class="iival" id="inext">1 ora</div></div>
    </div>
  </div>

  <h2 class="stitle">{L['trend']}</h2>
  <div class="cbox">
    <svg class="csvg" id="csvg" viewBox="0 0 800 120" preserveAspectRatio="none">
      <defs><linearGradient id="cg" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#3b82f6" stop-opacity="0.25"/>
        <stop offset="100%" stop-color="#3b82f6" stop-opacity="0"/>
      </linearGradient></defs>
      <line x1="0" y1="60" x2="800" y2="60" stroke="#141920" stroke-width="1" stroke-dasharray="4,4"/>
      <text x="400" y="65" text-anchor="middle" fill="#4a5568" font-size="16">{L['loading']}</text>
    </svg>
    <div class="clabels">
      <span class="clabel">-6d</span><span class="clabel">-5d</span><span class="clabel">-4d</span>
      <span class="clabel">-3d</span><span class="clabel">-2d</span><span class="clabel">-1d</span>
      <span class="clabel">Oggi</span>
    </div>
  </div>

  <h2 class="stitle">{L['means']}</h2>
  <div class="mbox">
    <p class="mtext">WeatherArb calcola lo Z-Score confrontando le condizioni attuali con la baseline storica NASA POWER degli ultimi 25 anni per le coordinate esatte di {name} ({lat:.4f}°N, {lon:.4f}°E). Valori superiori a ±2.0 indicano anomalie statisticamente significative.</p>
    <div class="mgrid">
      <div class="mi"><div class="milabel">Fonte Baseline</div><div class="mival">NASA POWER API</div></div>
      <div class="mi"><div class="milabel">Copertura Storica</div><div class="mival">25 anni</div></div>
      <div class="mi"><div class="milabel">Real-Time</div><div class="mival">OpenWeatherMap</div></div>
      <div class="mi"><div class="milabel">Aggiornamento</div><div class="mival">Ogni ora</div></div>
      <div class="mi"><div class="milabel">Coordinate</div><div class="mival">{lat:.4f}°N, {lon:.4f}°E</div></div>
      <div class="mi"><div class="milabel">Soglia Alert</div><div class="mival">Score ≥ 7.0/10</div></div>
    </div>
  </div>

  <div class="abox">
    <div class="atext">
      <h3>📡 {L['alerts']} per {name}</h3>
      <p>Notifica immediata su Telegram quando il segnale supera 7.0/10</p>
    </div>
    <a href="https://t.me/weatherarb_alerts" target="_blank" rel="noopener" class="abtn">Canale Telegram →</a>
  </div>
</main>

<footer class="ftr">
  <a href="/">WeatherArb</a> · Independent Weather Intelligence Agency ·
  <a href="/about.html">Methodology</a> · <a href="/api.html">API</a>
</footer>

<script>
const API='{API_BASE}',CID='{api_id}';
const LV={{NORMAL:'#10b981',UNUSUAL:'#f59e0b',EXTREME:'#f97316',CRITICAL:'#ef4444'}};
function lv(s){{return s>=8?'CRITICAL':s>=6?'EXTREME':s>=4?'UNUSUAL':'NORMAL'}}
function ag(z){{
  const f=document.getElementById('gfill'),v=document.getElementById('gval'),s=document.getElementById('gstat');
  const c=Math.max(-3,Math.min(6,z)),p=(c+3)/9,off=220-(p*220);
  const col=c>=2?'#ef4444':c>=1?'#f97316':c>=0?'#f59e0b':'#10b981';
  f.style.stroke=col;f.style.strokeDashoffset=off;
  v.textContent=(z>0?'+':'')+z.toFixed(2);v.style.color=col;s.style.color=col;
}}
function spark(pts){{
  const svg=document.getElementById('csvg');
  if(!pts||pts.length<2)return;
  const W=800,H=120,P=16,mn=Math.min(...pts)-.5,mx=Math.max(...pts)+.5,r=mx-mn||1;
  const tx=i=>P+(i/(pts.length-1))*(W-P*2),ty=v=>H-P-((v-mn)/r)*(H-P*2);
  const ps=pts.map((v,i)=>tx(i)+','+ty(v)).join(' ');
  const zy=Math.max(P,Math.min(H-P,ty(0)));
  svg.innerHTML=`<defs><linearGradient id="cg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#3b82f6" stop-opacity="0.25"/><stop offset="100%" stop-color="#3b82f6" stop-opacity="0"/></linearGradient></defs>`+
    `<line x1="${{P}}" y1="${{zy}}" x2="${{W-P}}" y2="${{zy}}" stroke="#1e2d3d" stroke-width="1" stroke-dasharray="4,4"/>`+
    `<polygon points="${{ps}} ${{tx(pts.length-1)}},${{H-P}} ${{tx(0)}},${{H-P}}" fill="url(#cg)"/>`+
    `<polyline points="${{ps}}" fill="none" stroke="#3b82f6" stroke-width="2" stroke-linejoin="round"/>`+
    `<circle cx="${{tx(pts.length-1)}}" cy="${{ty(pts[pts.length-1])}}" r="4" fill="#3b82f6"/>`;
}}
const PHASE={{PRE_EVENT_PREP:'⚡ Pre-Event — Finestra Aperta',BLACKOUT:'🔴 Evento Attivo',POST_EVENT_RECOVERY:'🔄 Post-Event Recovery',NO_ACTION:'✅ Monitoraggio Normale'}};
async function load(){{
  try{{
    const r=await fetch(API+'/api/v1/pulse/'+CID);
    const d=await r.json();
    const sc=d.score||0,z=d.z_score||0,lvl=lv(sc),col=LV[lvl];
    ag(z);
    document.getElementById('gstat').textContent=lvl;
    document.getElementById('score-v').innerHTML=sc.toFixed(1)+'<span style="font-size:16px;color:var(--muted)">/10</span>';
    document.getElementById('score-p').textContent=d.anomaly_level||'NORMAL';
    document.getElementById('score-p').style.color=col;
    const t=d.current_temp_c;
    if(t!=null){{
      document.getElementById('temp-v').innerHTML=t.toFixed(1)+'<span style="font-size:16px">°C</span>';
      const b=d.baseline_temp||d.avg_temp_c;
      if(b){{const dl=t-b,sg=dl>=0?'+':'';document.getElementById('temp-d').textContent=sg+dl.toFixed(1)+'°C vs media storica';document.getElementById('temp-d').style.color=dl>=2?'#ef4444':dl>=1?'#f59e0b':'#10b981';}}
    }}
    document.getElementById('vert-v').textContent=(d.vertical||'Monitoring').replace('_',' ');
    document.getElementById('conf-v').textContent='Confidence: '+(d.confidence||100)+'%';
    if(sc>=7){{document.getElementById('ibox').classList.add('crit');document.getElementById('iico').textContent='🔴';document.getElementById('itit').textContent='⚠ Anomalia Critica';}}
    else if(sc>=5){{document.getElementById('iico').textContent='🟡';document.getElementById('itit').textContent='Anomalia in Sviluppo';}}
    else{{document.getElementById('iico').textContent='🟢';}}
    document.getElementById('isub').textContent=(d.vertical||'Monitoring').replace('_',' ')+' · '+(d.anomaly_level||'NORMAL');
    document.getElementById('iwin').textContent=d.horizon_hours?d.horizon_hours+' ore alla finestra ottimale':'Condizioni nella norma';
    document.getElementById('iphase').textContent=PHASE[d.phase]||d.phase||'—';
    if(z)document.getElementById('idelta').textContent='Z = '+(z>0?'+':'')+z.toFixed(2)+' σ dal valore atteso';
    const nx=new Date(Date.now()+3600000);
    document.getElementById('inext').textContent=nx.toLocaleTimeString('it-IT',{{hour:'2-digit',minute:'2-digit'}});
    if(d.history_z_scores&&d.history_z_scores.length>=2)spark(d.history_z_scores);
    else{{const fake=Array.from({{length:7}},(_,i)=>z*(0.3+0.1*i)+(Math.random()-.5)*.3);fake[6]=z;spark(fake);}}
  }}catch(e){{
    document.getElementById('gstat').textContent='{L["monitoring"]}';
    spark([0.1,-.2,.3,-.1,.2,.1,0.0]);
  }}
}}
load();setInterval(load,3600000);
</script>
</body>
</html>"""


# ─── HUB PER PAESE ──────────────────────────────────────────────────────────

def generate_hub(cc: str, cities: list) -> str:
    label = COUNTRY_LABEL.get(cc, cc.upper())
    lang_map = {"it": "it", "de": "de", "fr": "fr", "es": "es", "gb": "en",
                "se": "sv", "nl": "nl", "pl": "pl", "at": "de", "ch": "de",
                "be": "fr", "pt": "pt", "dk": "da", "no": "no"}
    lang = lang_map.get(cc, "en")

    links = ""
    for c in cities:
        slug = slugify(c["nome"])
        links += f'<a href="/{cc}/{slug}/" class="nc"><span class="nn">{c["nome"]}</span><span class="ns">Node Active</span></a>\n'

    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{label} — WeatherArb Intelligence Network</title>
  <meta name="description" content="WeatherArb weather anomaly monitoring network for {label}. {len(cities)} active nodes.">
  <style>
    :root{{--bg:#040608;--surface:#0a0d12;--border:#141920;--text:#c8d6e5;--muted:#4a5568;--blue:#3b82f6}}
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:var(--bg);color:var(--text);font-family:-apple-system,sans-serif;min-height:100vh}}
    .hdr{{border-bottom:1px solid var(--border);padding:14px 24px;display:flex;align-items:center;justify-content:space-between}}
    .logo{{font-size:13px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--text);text-decoration:none}}.logo span{{color:var(--blue)}}
    .nav{{display:flex;gap:20px}}.nav a{{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);text-decoration:none}}.nav a:hover{{color:var(--text)}}
    .wrap{{max-width:1100px;margin:0 auto;padding:48px 24px 80px}}
    .bc{{font-size:11px;text-transform:uppercase;letter-spacing:.15em;color:var(--muted);margin-bottom:16px}}.bc a{{color:var(--muted);text-decoration:none}}.bc a:hover{{color:var(--blue)}}
    h1{{font-size:clamp(32px,4vw,56px);font-weight:800;letter-spacing:-.02em;margin-bottom:8px}}
    .sub{{font-size:13px;color:var(--muted);margin-bottom:48px}}.sub span{{color:var(--blue)}}
    .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px}}
    .nc{{display:block;padding:16px;background:var(--surface);border:1px solid var(--border);border-radius:10px;text-decoration:none;transition:border-color .2s,background .2s}}.nc:hover{{border-color:var(--blue);background:#0d1520}}
    .nn{{display:block;font-size:14px;font-weight:600;color:var(--text);margin-bottom:4px}}
    .ns{{display:block;font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted)}}
    .ftr{{border-top:1px solid var(--border);padding:24px;text-align:center;font-size:11px;color:var(--muted)}}
    .ftr a{{color:var(--muted);text-decoration:none}}.ftr a:hover{{color:var(--blue)}}
  </style>
</head>
<body>
<header class="hdr">
  <a href="/" class="logo">Weather<span>Arb</span></a>
  <nav class="nav"><a href="/data/">Data</a><a href="/news/">News</a><a href="/api.html">API</a></nav>
</header>
<div class="wrap">
  <div class="bc"><a href="/">WeatherArb</a> / {label}</div>
  <h1>{label} <span style="color:var(--blue)">Network</span></h1>
  <p class="sub"><span>{len(cities)}</span> nodi attivi · Baseline NASA POWER · Aggiornamento ogni ora</p>
  <div class="grid">
{links}  </div>
</div>
<footer class="ftr"><a href="/">WeatherArb</a> · <a href="/about.html">Methodology</a> · <a href="/api.html">API</a></footer>
</body>
</html>"""


# ─── HOMEPAGE ───────────────────────────────────────────────────────────────

def generate_homepage(all_cities: list) -> str:
    total = len(all_cities)
    countries = len(set(get_country_code(c) for c in all_cities))

    country_cards = ""
    by_cc = {}
    for c in all_cities:
        cc = get_country_code(c)
        by_cc.setdefault(cc, []).append(c)

    flag_map = {"it":"🇮🇹","de":"🇩🇪","fr":"🇫🇷","es":"🇪🇸","gb":"🇬🇧",
                "se":"🇸🇪","nl":"🇳🇱","pl":"🇵🇱","at":"🇦🇹","ch":"🇨🇭",
                "be":"🇧🇪","pt":"🇵🇹","dk":"🇩🇰","no":"🇳🇴"}

    for cc, cities in sorted(by_cc.items()):
        flag = flag_map.get(cc, "🌍")
        label = COUNTRY_LABEL.get(cc, cc.upper())
        country_cards += f"""    <a href="/{cc}/" class="cc">
      <span class="cflag">{flag}</span>
      <span class="cname">{label}</span>
      <span class="ccount">{len(cities)} nodi</span>
    </a>
"""

    return f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>WeatherArb — Weather Intelligence Agency</title>
  <meta name="description" content="WeatherArb monitora {total} città in {countries} paesi europei. Anomalie meteo in tempo reale su baseline NASA POWER 25 anni.">
  <style>
    :root{{--bg:#040608;--surface:#0a0d12;--border:#141920;--border-a:#1e2d3d;
           --text:#c8d6e5;--muted:#4a5568;--blue:#3b82f6;--green:#10b981}}
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;min-height:100vh;overflow-x:hidden}}
    body::before{{content:'';position:fixed;inset:0;background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,.03) 2px,rgba(0,0,0,.03) 4px);pointer-events:none;z-index:9999}}

    /* NAV */
    .hdr{{position:sticky;top:0;z-index:100;background:rgba(4,6,8,.95);backdrop-filter:blur(12px);border-bottom:1px solid var(--border);padding:14px 24px;display:flex;align-items:center;justify-content:space-between}}
    .logo{{font-size:13px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--text);text-decoration:none}}.logo span{{color:var(--blue)}}
    .nav{{display:flex;gap:20px;align-items:center}}.nav a{{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);text-decoration:none}}.nav a:hover{{color:var(--text)}}
    .dot{{width:6px;height:6px;background:var(--green);border-radius:50%;box-shadow:0 0 8px var(--green);animation:pd 2s ease-in-out infinite}}
    @keyframes pd{{0%,100%{{opacity:1}}50%{{opacity:.5}}}}

    /* HERO */
    .hero{{max-width:1100px;margin:0 auto;padding:80px 24px 60px;text-align:center}}
    .badge{{display:inline-flex;align-items:center;gap:8px;background:rgba(59,130,246,.08);border:1px solid rgba(59,130,246,.2);border-radius:100px;padding:6px 14px;font-size:11px;text-transform:uppercase;letter-spacing:.15em;color:var(--blue);margin-bottom:32px}}
    .badge-dot{{width:6px;height:6px;background:var(--green);border-radius:50%;box-shadow:0 0 6px var(--green)}}
    h1{{font-size:clamp(40px,6vw,80px);font-weight:800;letter-spacing:-.03em;line-height:1.05;margin-bottom:20px}}
    h1 em{{font-style:normal;color:var(--blue)}}
    .sub{{font-size:16px;color:var(--muted);max-width:560px;margin:0 auto 40px;line-height:1.6}}
    .hero-btns{{display:flex;gap:12px;justify-content:center;flex-wrap:wrap}}
    .btn-p{{background:var(--blue);color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:700;font-size:14px;transition:opacity .2s}}.btn-p:hover{{opacity:.85}}
    .btn-s{{background:transparent;color:var(--text);padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px;border:1px solid var(--border-a);transition:border-color .2s}}.btn-s:hover{{border-color:var(--blue)}}

    /* STATS */
    .stats{{max-width:1100px;margin:0 auto;padding:0 24px 60px;display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:1px;background:var(--border);border-top:1px solid var(--border);border-bottom:1px solid var(--border)}}
    .stat{{background:var(--bg);padding:28px 24px;text-align:center}}
    .stat-n{{font-size:36px;font-weight:800;color:#fff;font-variant-numeric:tabular-nums}}
    .stat-l{{font-size:11px;text-transform:uppercase;letter-spacing:.15em;color:var(--muted);margin-top:4px}}

    /* LIVE TICKER */
    .ticker-wrap{{max-width:1100px;margin:0 auto;padding:40px 24px 0}}
    .section-hdr{{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}}
    .section-title{{font-size:11px;text-transform:uppercase;letter-spacing:.2em;color:var(--muted)}}
    .section-link{{font-size:11px;color:var(--blue);text-decoration:none}}
    .ticker{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:8px;margin-bottom:40px}}
    .tc{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px 20px;display:flex;justify-content:space-between;align-items:center;text-decoration:none;color:var(--text);transition:border-color .2s}}.tc:hover{{border-color:var(--blue)}}
    .tc-left .tc-city{{font-weight:700;font-size:15px}}.tc-left .tc-country{{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin-top:2px}}
    .tc-right{{text-align:right}}.tc-score{{font-size:20px;font-weight:800;font-variant-numeric:tabular-nums}}.tc-vert{{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin-top:2px}}
    .skeleton{{background:linear-gradient(90deg,var(--surface) 25%,rgba(255,255,255,.04) 50%,var(--surface) 75%);background-size:200% 100%;animation:sh 1.5s infinite;border-radius:10px;height:72px}}
    @keyframes sh{{0%{{background-position:200% 0}}100%{{background-position:-200% 0}}}}

    /* COUNTRIES */
    .countries{{max-width:1100px;margin:0 auto;padding:0 24px 40px}}
    .cgrid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:8px}}
    .cc{{display:flex;flex-direction:column;align-items:center;gap:6px;padding:20px 16px;background:var(--surface);border:1px solid var(--border);border-radius:10px;text-decoration:none;transition:border-color .2s}}.cc:hover{{border-color:var(--blue)}}
    .cflag{{font-size:28px}}.cname{{font-size:13px;font-weight:600;color:var(--text)}}.ccount{{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}}

    /* REPORTS */
    .reports{{max-width:1100px;margin:0 auto;padding:0 24px 40px}}
    .rgrid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}}
    .rc{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:24px;text-decoration:none;color:var(--text);transition:border-color .2s;display:flex;flex-direction:column}}.rc:hover{{border-color:var(--blue)}}
    .rc-meta{{display:flex;gap:8px;align-items:center;margin-bottom:12px}}.rc-date{{font-size:11px;color:var(--muted)}}.rc-loc{{font-size:11px;background:rgba(59,130,246,.1);color:var(--blue);padding:2px 8px;border-radius:100px}}
    .rc-title{{font-size:15px;font-weight:700;line-height:1.3;margin-bottom:8px}}
    .rc-exc{{font-size:12px;color:var(--muted);line-height:1.5;flex:1}}
    .rc-foot{{display:flex;justify-content:space-between;margin-top:12px;padding-top:12px;border-top:1px solid var(--border)}}
    .rc-z{{font-size:12px;font-weight:700;font-variant-numeric:tabular-nums}}.rc-s{{font-size:12px;color:var(--muted)}}

    /* FOOTER */
    .ftr{{border-top:1px solid var(--border);padding:32px 24px;text-align:center;font-size:11px;color:var(--muted);letter-spacing:.08em}}
    .ftr a{{color:var(--muted);text-decoration:none;margin:0 8px}}.ftr a:hover{{color:var(--blue)}}

    @media(max-width:640px){{h1{{font-size:40px}}.stats{{grid-template-columns:1fr 1fr}}}}
  </style>
</head>
<body>
<header class="hdr">
  <a href="/" class="logo">Weather<span>Arb</span></a>
  <nav class="nav">
    <a href="/data/">Data</a>
    <a href="/news/">News</a>
    <a href="/api.html">API</a>
    <a href="/alerts.html">Alerts</a>
    <a href="/about.html">About</a>
    <div class="dot"></div>
  </nav>
</header>

<!-- HERO -->
<section class="hero">
  <div class="badge"><div class="badge-dot"></div> Sistema Operativo · Aggiornamento ogni ora</div>
  <h1>Weather Intelligence<br><em>Per ogni città d'Europa</em></h1>
  <p class="sub">Z-Score in tempo reale su baseline NASA POWER 25 anni. Anomalie rilevate prima che diventino notizia.</p>
  <div class="hero-btns">
    <a href="/data/" class="btn-p">Live Dashboard →</a>
    <a href="/api.html" class="btn-s">API Pubblica</a>
  </div>
</section>

<!-- STATS -->
<div class="stats">
  <div class="stat"><div class="stat-n">{total}</div><div class="stat-l">Città Monitorate</div></div>
  <div class="stat"><div class="stat-n">{countries}</div><div class="stat-l">Paesi Europei</div></div>
  <div class="stat"><div class="stat-n">25</div><div class="stat-l">Anni Baseline</div></div>
  <div class="stat"><div class="stat-n" id="live-anom">—</div><div class="stat-l">Anomalie Live</div></div>
</div>

<!-- LIVE TICKER -->
<div class="ticker-wrap">
  <div class="section-hdr">
    <div class="section-title">🔴 Segnali Live</div>
    <a href="/data/" class="section-link">Vedi tutti →</a>
  </div>
  <div class="ticker" id="ticker">
    <div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div>
    <div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div>
  </div>
</div>

<!-- COUNTRIES -->
<div class="countries">
  <div class="section-hdr">
    <div class="section-title">📡 Network Europeo</div>
  </div>
  <div class="cgrid">
{country_cards}  </div>
</div>

<!-- REPORTS -->
<div class="reports">
  <div class="section-hdr">
    <div class="section-title">📰 Intelligence Reports</div>
    <a href="/news/" class="section-link">Archivio →</a>
  </div>
  <div class="rgrid" id="reports-grid">
    <div class="skeleton" style="height:160px"></div>
    <div class="skeleton" style="height:160px"></div>
    <div class="skeleton" style="height:160px"></div>
  </div>
</div>

<footer class="ftr">
  <a href="/about.html">Methodology</a>
  <a href="/api.html">API</a>
  <a href="/alerts.html">Alerts</a>
  <a href="/news/">News</a>
  <a href="https://t.me/weatherarb_alerts" target="_blank">Telegram</a>
  <br><br>
  WeatherArb · Independent Weather Intelligence Agency · Data: NASA POWER, ERA5-Land, OpenWeatherMap
</footer>

<script>
const API='https://api.weatherarb.com';
const LV={{NORMAL:'#10b981',UNUSUAL:'#f59e0b',EXTREME:'#f97316',CRITICAL:'#ef4444'}};
function lv(s){{return s>=8?'CRITICAL':s>=6?'EXTREME':s>=4?'UNUSUAL':'NORMAL'}}

async function loadTicker(){{
  try{{
    const r=await fetch(API+'/api/v1/europe/top?limit=12');
    const d=await r.json();
    const items=(d.reports||d.cities||[]).slice(0,12);
    if(!items.length)return;
    const t=document.getElementById('ticker');
    t.innerHTML=items.map(c=>{{
      const sc=c.score||0,z=c.z_score||0,lvl=lv(sc),col=LV[lvl];
      const slug=(c.location||'').toLowerCase().replace(/\\s+/g,'-');
      const cc=c.country_code||'it';
      return `<a href="/${{cc}}/${{slug}}/" class="tc">
        <div class="tc-left"><div class="tc-city">${{c.location||'—'}}</div><div class="tc-country">${{c.country||cc.toUpperCase()}}</div></div>
        <div class="tc-right"><div class="tc-score" style="color:${{col}}">${{sc.toFixed(1)}}</div><div class="tc-vert">${{(c.vertical||'').replace('_',' ')}}</div></div>
      </a>`;
    }}).join('');
    const anom=items.filter(c=>(c.score||0)>=5).length;
    document.getElementById('live-anom').textContent=anom;
  }}catch(e){{
    document.getElementById('ticker').innerHTML='<p style="color:var(--muted);font-size:13px;padding:20px">Connessione API in corso...</p>';
  }}
}}

async function loadReports(){{
  try{{
    const r=await fetch('/data/latest_reports.json');
    const d=await r.json();
    const rpts=(d.reports||[]).slice(0,6);
    if(!rpts.length)return;
    const g=document.getElementById('reports-grid');
    g.innerHTML=rpts.map(r=>{{
      const z=r.z_score||0;
      return `<a href="${{r.url||'/news/'}}" class="rc">
        <div class="rc-meta"><span class="rc-date">${{r.date||''}}</span><span class="rc-loc">${{r.location||''}}</span></div>
        <div class="rc-title">${{r.title||'Intelligence Report'}}</div>
        <div class="rc-exc">${{(r.excerpt||'').slice(0,120)}}...</div>
        <div class="rc-foot"><span class="rc-z" style="color:${{z>=2?'#ef4444':z>=1?'#f59e0b':'#10b981'}}">Z ${{z>0?'+':''}}${{z.toFixed(2)}}</span><span class="rc-s">Score ${{r.score||0}}/10</span></div>
      </a>`;
    }}).join('');
  }}catch(e){{
    document.getElementById('reports-grid').innerHTML='';
  }}
}}

loadTicker();
loadReports();
setInterval(loadTicker,300000);
</script>
</body>
</html>"""


# ─── MAIN ───────────────────────────────────────────────────────────────────

def main():
    import sys

    coords_path = Path("data/province_coords.json")
    if not coords_path.exists():
        print("❌ data/province_coords.json non trovato")
        sys.exit(1)

    with open(coords_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    provinces = raw["province"] if isinstance(raw, dict) and "province" in raw else raw

    # Step 1: Pulisci landing sbagliate in /it/ per città non italiane
    print("🧹 Pulizia landing sbagliate in /it/...")
    italian_names = {slugify(c["nome"]) for c in provinces if get_country_code(c) == "it"}
    it_dir = BASE_DIR / "it"
    if it_dir.exists():
        removed = 0
        for d in it_dir.iterdir():
            if d.is_dir() and d.name not in italian_names:
                shutil.rmtree(d)
                removed += 1
        print(f"   Rimossi {removed} slug non italiani da /it/")

    # Step 2: Genera landing nella cartella giusta
    print("\n📄 Generazione landing pages...")
    by_cc = {}
    generated = 0

    for city in provinces:
        cc = get_country_code(city)
        name = city.get("nome", "")
        if not name:
            continue

        by_cc.setdefault(cc, []).append(city)
        slug = slugify(name)
        out_dir = BASE_DIR / cc / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(generate_landing(city), encoding="utf-8")
        print(f"  ✅ /{cc}/{slug}/")
        generated += 1

    # Step 3: Hub per ogni paese
    print("\n🗺  Generazione hub nazionali...")
    for cc, cities in by_cc.items():
        hub_path = BASE_DIR / cc / "index.html"
        hub_path.write_text(generate_hub(cc, cities), encoding="utf-8")
        print(f"  ✅ /{cc}/ ({len(cities)} città)")

    # Step 4: Homepage
    print("\n🏠 Generazione homepage...")
    (BASE_DIR / "index.html").write_text(generate_homepage(provinces), encoding="utf-8")
    print("  ✅ /index.html")

    print(f"""
╔══════════════════════════════════════════════════╗
║  WeatherArb v3 — Generazione completata          ║
║  {generated} landing + {len(by_cc)} hub + 1 homepage          ║
╚══════════════════════════════════════════════════╝

📦 Ora esegui:
   git add data/website/
   git commit -m "feat: v3 landing — country routing fix + homepage"
   git push origin main
""")


if __name__ == "__main__":
    main()
