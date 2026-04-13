#!/usr/bin/env python3
"""Genera data/website/data/index.html — dashboard live 121 città"""

content = r"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Live Data Dashboard | WeatherArb Intelligence</title>
  <meta name="description" content="Dashboard in tempo reale delle anomalie meteo in 121 città europee. Z-Score su baseline NASA POWER 25 anni. WeatherArb Weather Intelligence Agency.">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <style>
    :root{
      --bg:#040608;--s:#0a0d12;--b:#141920;--ba:#1e2d3d;
      --t:#c8d6e5;--m:#4a5568;--bl:#3b82f6;
      --g:#10b981;--y:#f59e0b;--o:#f97316;--r:#ef4444;
    }
    *{box-sizing:border-box;margin:0;padding:0}
    html{scroll-behavior:smooth}
    body{background:var(--bg);color:var(--t);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;min-height:100vh;overflow-x:hidden}
    body::before{content:'';position:fixed;inset:0;background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,.03) 2px,rgba(0,0,0,.03) 4px);pointer-events:none;z-index:9999}

    /* HEADER */
    .hdr{position:sticky;top:0;z-index:100;background:rgba(4,6,8,.95);backdrop-filter:blur(12px);border-bottom:1px solid var(--b);padding:14px 24px;display:flex;align-items:center;justify-content:space-between}
    .logo{font-size:13px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--t);text-decoration:none}.logo span{color:var(--bl)}
    .nav{display:flex;gap:20px;align-items:center}
    .nav a{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:var(--m);text-decoration:none}.nav a:hover{color:var(--t)}
    .dot{width:6px;height:6px;background:var(--g);border-radius:50%;box-shadow:0 0 8px var(--g);animation:pd 2s ease-in-out infinite}
    @keyframes pd{0%,100%{opacity:1}50%{opacity:.4}}

    /* HERO */
    .hero{max-width:1200px;margin:0 auto;padding:40px 24px 24px;display:flex;align-items:flex-end;justify-content:space-between;gap:24px;flex-wrap:wrap}
    .hero-left h1{font-size:clamp(24px,3vw,36px);font-weight:800;letter-spacing:-.02em;margin-bottom:6px}
    .hero-left p{font-size:13px;color:var(--m)}
    .hero-stats{display:flex;gap:32px}
    .hs{text-align:center}
    .hs-n{font-size:28px;font-weight:800;font-variant-numeric:tabular-nums}
    .hs-l{font-size:10px;text-transform:uppercase;letter-spacing:.15em;color:var(--m);margin-top:2px}

    /* CONTROLS */
    .controls{max-width:1200px;margin:0 auto;padding:0 24px 20px;display:flex;gap:12px;flex-wrap:wrap;align-items:center}
    .search{flex:1;min-width:200px;background:var(--s);border:1px solid var(--b);border-radius:8px;padding:9px 14px;color:var(--t);font-size:13px;outline:none;transition:border-color .2s}
    .search:focus{border-color:var(--bl)}
    .filter-group{display:flex;gap:6px;flex-wrap:wrap}
    .filt{padding:7px 14px;background:transparent;border:1px solid var(--b);border-radius:100px;font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--m);cursor:pointer;transition:.2s}
    .filt:hover,.filt.on{border-color:var(--bl);color:var(--bl);background:rgba(59,130,246,.08)}
    .filt.crit.on{border-color:var(--r);color:var(--r);background:rgba(239,68,68,.08)}
    .filt.ext.on{border-color:var(--o);color:var(--o);background:rgba(249,115,22,.08)}
    .filt.unu.on{border-color:var(--y);color:var(--y);background:rgba(245,158,11,.08)}
    .sort-sel{background:var(--s);border:1px solid var(--b);border-radius:8px;padding:8px 12px;color:var(--t);font-size:12px;outline:none;cursor:pointer}

    /* MAP */
    .map-wrap{max-width:1200px;margin:0 auto;padding:0 24px 24px}
    #map{height:320px;border-radius:12px;border:1px solid var(--b);background:var(--s)}
    .leaflet-container{background:#0a0d12!important}
    .wa-popup{background:#0a0d12;border:1px solid #1e2d3d;border-radius:8px;padding:10px 14px;color:#c8d6e5;font-family:-apple-system,sans-serif;min-width:160px}
    .wa-popup b{display:block;font-size:14px;margin-bottom:4px}
    .wa-popup small{font-size:10px;color:#4a5568;text-transform:uppercase;letter-spacing:.08em}
    .wa-popup a{display:block;margin-top:8px;font-size:11px;color:#3b82f6;text-decoration:none}
    .leaflet-popup-content-wrapper,.leaflet-popup-tip{background:transparent!important;box-shadow:none!important;padding:0!important}
    .leaflet-popup-content{margin:0!important}

    /* TABLE */
    .table-wrap{max-width:1200px;margin:0 auto;padding:0 24px 80px;overflow-x:auto}
    .stitle{font-size:11px;text-transform:uppercase;letter-spacing:.2em;color:var(--m);margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid var(--b);display:flex;align-items:center;justify-content:space-between}
    .refresh-btn{font-size:11px;color:var(--bl);cursor:pointer;background:none;border:none;padding:0}
    table{width:100%;border-collapse:collapse;font-size:13px}
    th{font-size:10px;text-transform:uppercase;letter-spacing:.15em;color:var(--m);padding:10px 14px;text-align:left;border-bottom:1px solid var(--b);white-space:nowrap;cursor:pointer;user-select:none}
    th:hover{color:var(--t)}
    td{padding:12px 14px;border-bottom:1px solid rgba(20,25,32,.8);vertical-align:middle}
    tr:hover td{background:rgba(59,130,246,.03)}
    .city-link{text-decoration:none;color:var(--t);font-weight:600}.city-link:hover{color:var(--bl)}
    .country-tag{font-size:10px;color:var(--m);text-transform:uppercase;letter-spacing:.08em}
    .z-val{font-variant-numeric:tabular-nums;font-weight:700;font-size:15px}
    .score-bar-wrap{display:flex;align-items:center;gap:10px}
    .score-bar{height:4px;background:var(--b);border-radius:2px;flex:1;min-width:60px;overflow:hidden}
    .score-fill{height:100%;border-radius:2px;transition:width .6s}
    .score-num{font-size:13px;font-weight:700;font-variant-numeric:tabular-nums;min-width:28px}
    .badge{display:inline-block;padding:3px 8px;border-radius:100px;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.1em}
    .badge-N{background:rgba(16,185,129,.12);color:var(--g)}
    .badge-U{background:rgba(245,158,11,.12);color:var(--y)}
    .badge-E{background:rgba(249,115,22,.12);color:var(--o)}
    .badge-C{background:rgba(239,68,68,.12);color:var(--r)}
    .temp-val{font-variant-numeric:tabular-nums}
    .delta{font-size:11px;margin-top:2px}
    .skeleton-row td{padding:14px}
    .skel{background:linear-gradient(90deg,var(--s) 25%,rgba(255,255,255,.04) 50%,var(--s) 75%);background-size:200% 100%;animation:sh 1.5s infinite;border-radius:4px;height:16px}
    @keyframes sh{0%{background-position:200% 0}100%{background-position:-200% 0}}
    .last-update{font-size:11px;color:var(--m)}
    .no-data{text-align:center;padding:60px;color:var(--m);font-size:14px}

    @media(max-width:768px){
      .hero-stats{gap:16px}.hs-n{font-size:22px}
      th:nth-child(4),th:nth-child(5),td:nth-child(4),td:nth-child(5){display:none}
      #map{height:220px}
    }
  </style>
</head>
<body>
<header class="hdr">
  <a href="/" class="logo">Weather<span>Arb</span></a>
  <nav class="nav">
    <a href="/">Home</a>
    <a href="/news/">News</a>
    <a href="/map.html">Map</a>
    <a href="/api.html">API</a>
    <a href="/alerts.html">Alerts</a>
    <div class="dot"></div>
  </nav>
</header>

<div class="hero">
  <div class="hero-left">
    <h1>Live Intelligence Dashboard</h1>
    <p>121 nodi europei · Z-Score su baseline NASA POWER 25 anni · Aggiornamento ogni ora</p>
  </div>
  <div class="hero-stats">
    <div class="hs"><div class="hs-n" id="stat-total">121</div><div class="hs-l">Città</div></div>
    <div class="hs"><div class="hs-n" id="stat-crit" style="color:var(--r)">—</div><div class="hs-l">Critical</div></div>
    <div class="hs"><div class="hs-n" id="stat-ext" style="color:var(--o)">—</div><div class="hs-l">Extreme</div></div>
    <div class="hs"><div class="hs-n" id="stat-avg" style="color:var(--bl)">—</div><div class="hs-l">Score Medio</div></div>
  </div>
</div>

<div class="controls">
  <input class="search" id="search" type="text" placeholder="🔍 Cerca città...">
  <div class="filter-group">
    <button class="filt on" data-lvl="ALL" onclick="setFilter(this,'ALL')">Tutti</button>
    <button class="filt crit" data-lvl="CRITICAL" onclick="setFilter(this,'CRITICAL')">● Critical</button>
    <button class="filt ext" data-lvl="EXTREME" onclick="setFilter(this,'EXTREME')">● Extreme</button>
    <button class="filt unu" data-lvl="UNUSUAL" onclick="setFilter(this,'UNUSUAL')">● Unusual</button>
    <button class="filt" data-lvl="NORMAL" onclick="setFilter(this,'NORMAL')">Normal</button>
  </div>
  <select class="sort-sel" id="sort-sel" onchange="sortTable()">
    <option value="score">Ordina: Score ↓</option>
    <option value="zscore">Ordina: Z-Score ↓</option>
    <option value="name">Ordina: Nome A-Z</option>
    <option value="temp">Ordina: Temperatura</option>
  </select>
</div>

<!-- MAP -->
<div class="map-wrap">
  <div id="map"></div>
</div>

<!-- TABLE -->
<div class="table-wrap">
  <div class="stitle">
    <span id="table-label">Caricamento segnali...</span>
    <div style="display:flex;gap:16px;align-items:center">
      <span class="last-update" id="last-update">—</span>
      <button class="refresh-btn" onclick="loadData()">↻ Refresh</button>
    </div>
  </div>
  <table>
    <thead>
      <tr>
        <th onclick="sortBy('name')" title="Ordina per nome">Città ↕</th>
        <th onclick="sortBy('country')" title="Ordina per paese">Paese</th>
        <th onclick="sortBy('zscore')" title="Ordina per Z-Score">Z-Score ↕</th>
        <th onclick="sortBy('score')" title="Ordina per Score">Score ↕</th>
        <th>Livello</th>
        <th onclick="sortBy('temp')" title="Ordina per temperatura">Temp ↕</th>
        <th>Evento</th>
      </tr>
    </thead>
    <tbody id="tbody">
      <!-- skeleton -->
      <tr class="skeleton-row"><td><div class="skel" style="width:120px"></div></td><td><div class="skel" style="width:60px"></div></td><td><div class="skel" style="width:60px"></div></td><td><div class="skel" style="width:100px"></div></td><td><div class="skel" style="width:70px"></div></td><td><div class="skel" style="width:50px"></div></td><td><div class="skel" style="width:90px"></div></td></tr>
      <tr class="skeleton-row"><td><div class="skel" style="width:140px"></div></td><td><div class="skel" style="width:50px"></div></td><td><div class="skel" style="width:55px"></div></td><td><div class="skel" style="width:100px"></div></td><td><div class="skel" style="width:60px"></div></td><td><div class="skel" style="width:45px"></div></td><td><div class="skel" style="width:80px"></div></td></tr>
      <tr class="skeleton-row"><td><div class="skel" style="width:100px"></div></td><td><div class="skel" style="width:70px"></div></td><td><div class="skel" style="width:65px"></div></td><td><div class="skel" style="width:100px"></div></td><td><div class="skel" style="width:75px"></div></td><td><div class="skel" style="width:50px"></div></td><td><div class="skel" style="width:95px"></div></td></tr>
    </tbody>
  </table>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const API = 'https://api.weatherarb.com';
const CC_FLAG = {it:'🇮🇹',de:'🇩🇪',fr:'🇫🇷',es:'🇪🇸',gb:'🇬🇧',se:'🇸🇪',nl:'🇳🇱',pl:'🇵🇱',at:'🇦🇹',ch:'🇨🇭',be:'🇧🇪',pt:'🇵🇹',dk:'🇩🇰',no:'🇳🇴'};
const LV = {NORMAL:{col:'#10b981',cls:'N'},UNUSUAL:{col:'#f59e0b',cls:'U'},EXTREME:{col:'#f97316',cls:'E'},CRITICAL:{col:'#ef4444',cls:'C'}};

let allData = [];
let currentFilter = 'ALL';
let currentSort = {key:'score', dir:-1};

// MAP
const map = L.map('map',{center:[50,10],zoom:4,zoomControl:true,attributionControl:false});
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',{maxZoom:18}).addTo(map);
const markers = [];

function clearMarkers(){markers.forEach(m=>map.removeLayer(m));markers.length=0;}

function addMarker(d){
  if(!d.lat||!d.lon) return;
  const lv = LV[d.anomaly_level]||LV.NORMAL;
  const r = 5 + (d.score||0)*0.7;
  const m = L.circleMarker([d.lat,d.lon],{
    radius:r, fillColor:lv.col, color:lv.col,
    weight:1, fillOpacity:(d.score||0)>4?0.85:0.4
  }).bindPopup(`<div class="wa-popup">
    <b>${d.location||'—'}</b>
    <div style="font-size:12px;color:${lv.col};margin-bottom:4px">Score ${(d.score||0).toFixed(1)}/10 · Z ${(d.z_score||0)>0?'+':''}${(d.z_score||0).toFixed(2)}</div>
    <small>${(d.vertical||'').replace(/_/g,' ')} · ${d.anomaly_level||''}</small>
    <a href="/${d.country_code||'it'}/${(d.location||'').toLowerCase().replace(/\s+/g,'-').replace(/[^a-z0-9-]/g,'')}/">Vedi analisi →</a>
  </div>`,{closeButton:false});
  m.addTo(map);
  markers.push(m);
}

// DATA
async function loadData(){
  try{
    const r = await fetch(`${API}/api/v1/europe/top?limit=200`);
    const d = await r.json();
    allData = (d.reports||d.data||[]);
    if(!allData.length){
      // retry dopo 20s se cache vuota
      setTimeout(loadData, 20000);
      document.getElementById('table-label').textContent = '⏳ Sincronizzazione nodi...';
      return;
    }
    renderAll();
    document.getElementById('last-update').textContent = 'Aggiornato: ' + new Date().toLocaleTimeString('it-IT',{hour:'2-digit',minute:'2-digit'});
  }catch(e){
    document.getElementById('table-label').textContent = 'Errore connessione — retry in 30s';
    setTimeout(loadData,30000);
  }
}

function renderAll(){
  updateStats();
  renderMap();
  renderTable();
}

function updateStats(){
  const crit = allData.filter(d=>(d.anomaly_level||'')=='CRITICAL').length;
  const ext  = allData.filter(d=>(d.anomaly_level||'')=='EXTREME').length;
  const avg  = allData.reduce((a,d)=>a+(d.score||0),0)/Math.max(allData.length,1);
  document.getElementById('stat-total').textContent = allData.length;
  document.getElementById('stat-crit').textContent = crit;
  document.getElementById('stat-ext').textContent = ext;
  document.getElementById('stat-avg').textContent = avg.toFixed(1);
}

function renderMap(){
  clearMarkers();
  allData.forEach(d=>addMarker(d));
}

function getFiltered(){
  let data = [...allData];
  const q = document.getElementById('search').value.toLowerCase().trim();
  if(q) data = data.filter(d=>(d.location||'').toLowerCase().includes(q)||(d.country||'').toLowerCase().includes(q));
  if(currentFilter!=='ALL') data = data.filter(d=>(d.anomaly_level||'NORMAL')===currentFilter);
  return data.sort((a,b)=>{
    const k = currentSort.key;
    let va,vb;
    if(k==='name'){va=(a.location||'');vb=(b.location||'');}
    else if(k==='zscore'){va=Math.abs(a.z_score||0);vb=Math.abs(b.z_score||0);}
    else if(k==='temp'){va=a.current_temp_c||0;vb=b.current_temp_c||0;}
    else if(k==='country'){va=a.country||'';vb=b.country||'';}
    else{va=a.score||0;vb=b.score||0;}
    if(typeof va==='string') return currentSort.dir*va.localeCompare(vb);
    return currentSort.dir*(vb-va);
  });
}

function renderTable(){
  const data = getFiltered();
  const tbody = document.getElementById('tbody');
  document.getElementById('table-label').textContent = `${data.length} segnali attivi`;

  if(!data.length){
    tbody.innerHTML = '<tr><td colspan="7" class="no-data">Nessun segnale trovato per i filtri selezionati</td></tr>';
    return;
  }

  tbody.innerHTML = data.map(d=>{
    const lv = LV[d.anomaly_level]||LV.NORMAL;
    const z = d.z_score||0;
    const sc = d.score||0;
    const cc = d.country_code||'it';
    const flag = CC_FLAG[cc]||'🌍';
    const slug = (d.location||'').toLowerCase().replace(/\s+/g,'-').replace(/[^a-z0-9-]/g,'');
    const sign = z>=0?'+':'';
    const t = d.current_temp_c;
    const tStr = t!=null ? `${t.toFixed(1)}°C` : '—';
    const base = d.baseline_temp||d.avg_temp_c;
    const delta = (t!=null&&base) ? (t-base) : null;
    const deltaStr = delta!=null ? `<div class="delta" style="color:${delta>=2?'var(--r)':delta>=1?'var(--y)':'var(--g)'}">
      ${delta>=0?'+':''}${delta.toFixed(1)}°</div>` : '';
    const vert = (d.vertical||d.event_type||'—').replace(/_/g,' ');

    return `<tr>
      <td><a href="/${cc}/${slug}/" class="city-link">${d.location||'—'}</a></td>
      <td><span class="country-tag">${flag} ${cc.toUpperCase()}</span></td>
      <td><span class="z-val" style="color:${lv.col}">${sign}${z.toFixed(2)}</span></td>
      <td>
        <div class="score-bar-wrap">
          <div class="score-bar"><div class="score-fill" style="width:${sc*10}%;background:${lv.col}"></div></div>
          <span class="score-num" style="color:${lv.col}">${sc.toFixed(1)}</span>
        </div>
      </td>
      <td><span class="badge badge-${lv.cls}">${d.anomaly_level||'NORMAL'}</span></td>
      <td><span class="temp-val">${tStr}</span>${deltaStr}</td>
      <td style="color:var(--m);font-size:12px">${vert}</td>
    </tr>`;
  }).join('');
}

function setFilter(btn, lvl){
  document.querySelectorAll('.filt').forEach(b=>b.classList.remove('on'));
  btn.classList.add('on');
  currentFilter = lvl;
  renderTable();
}

function sortBy(key){
  if(currentSort.key===key) currentSort.dir *= -1;
  else {currentSort.key=key; currentSort.dir=-1;}
  renderTable();
}

function sortTable(){
  const v = document.getElementById('sort-sel').value;
  currentSort = {key:v, dir:-1};
  renderTable();
}

document.getElementById('search').addEventListener('input', renderTable);

// Boot
loadData();
setInterval(loadData, 300000); // refresh ogni 5 min
</script>
</body>
</html>"""

from pathlib import Path
out = Path("data/website/data/index.html")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(content, encoding="utf-8")
print(f"✅ data/index.html generato ({len(content)} chars)")
print("\n📦 Esegui:")
print("   git add data/website/data/index.html")
print("   git commit -m 'feat: data dashboard v2 — tabella live + mappa + filtri'")
print("   git push origin main")
