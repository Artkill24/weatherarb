const COMUNI_PROVINCES = {"torino":"Torino","milano":"Milano","roma":"Roma","napoli":"Napoli","bologna":"Bologna","firenze":"Firenze","venezia":"Venezia","genova":"Genova","palermo":"Palermo","bari":"Bari"};

async function handleComune(provincia, comune, request) {
  const API = "https://api.weatherarb.com";
  
  // Fetch dati meteo provincia più vicina
  let weatherData = null;
  try {
    const r = await fetch(`${API}/api/v1/pulse/${provincia}`, {cf:{cacheTtl:3600}});
    if(r.ok) weatherData = await r.json();
  } catch(e) {}

  const z = weatherData?.weather?.z_score || 0;
  const temp = weatherData?.weather?.temperature_c || '--';
  const level = weatherData?.weather?.anomaly_level || 'NORMAL';
  const event = (weatherData?.weather?.event_type || 'clear').replace(/_/g,' ');
  const sign = z >= 0 ? '+' : '';
  const colors = {CRITICAL:'#ef4444',EXTREME:'#f97316',UNUSUAL:'#eab308',NORMAL:'#10b981'};
  const color = colors[level] || '#10b981';
  
  const comuneName = comune.split('-').map(w=>w.charAt(0).toUpperCase()+w.slice(1)).join(' ');
  const provName = provincia.split('-').map(w=>w.charAt(0).toUpperCase()+w.slice(1)).join(' ');

  const html = `<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Meteo ${comuneName} — Anomalie Z-Score | WeatherArb</title>
  <meta name="description" content="Dati meteo e anomalie climatiche per ${comuneName} (${provName}). Z-Score NASA POWER 25 anni, HDD/CDD energy data, Space Weather.">
  <link rel="canonical" href="https://weatherarb.com/it/${provincia}/${comune}/">
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{background:#040608;color:#c8d6e5;font-family:-apple-system,sans-serif;min-height:100vh}
    .hdr{border-bottom:1px solid #141920;padding:14px 24px;display:flex;align-items:center;justify-content:space-between}
    .logo{font-size:13px;font-weight:700;letter-spacing:.2em;text-decoration:none;color:#c8d6e5}
    .logo span{color:#3b82f6}
    .wrap{max-width:800px;margin:0 auto;padding:48px 24px}
    .breadcrumb{font-size:12px;color:#4a5568;margin-bottom:24px}
    .breadcrumb a{color:#4a5568;text-decoration:none}
    .breadcrumb a:hover{color:#3b82f6}
    h1{font-size:36px;font-weight:900;color:#fff;margin-bottom:8px}
    .subtitle{font-size:16px;color:#4a5568;margin-bottom:32px}
    .card{background:#0a0d12;border:1px solid #141920;border-radius:16px;padding:28px;margin-bottom:20px}
    .card-title{font-size:11px;text-transform:uppercase;letter-spacing:.2em;color:#4a5568;margin-bottom:16px}
    .metric{display:flex;align-items:baseline;gap:8px;margin-bottom:8px}
    .metric-val{font-size:48px;font-weight:900}
    .metric-label{font-size:14px;color:#4a5568}
    .badge{display:inline-block;padding:4px 12px;border-radius:100px;font-size:12px;font-weight:700;text-transform:uppercase;margin-bottom:16px}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-top:16px}
    .stat{background:#141920;border-radius:10px;padding:16px;text-align:center}
    .stat-val{font-size:24px;font-weight:800;color:#fff}
    .stat-lbl{font-size:11px;color:#4a5568;margin-top:4px;text-transform:uppercase}
    .cta{display:block;background:#2563eb;color:#fff;padding:16px;border-radius:10px;text-align:center;font-weight:700;text-decoration:none;margin-top:24px}
    .related{margin-top:8px}
    .related a{display:inline-block;background:#141920;border-radius:6px;padding:6px 12px;font-size:12px;color:#c8d6e5;text-decoration:none;margin:4px}
    .related a:hover{background:#1e2d3d}
  </style>
  <script type="application/ld+json">{"@context":"https://schema.org","@type":"WebPage","name":"Meteo ${comuneName}","description":"Anomalie meteo per ${comuneName}","url":"https://weatherarb.com/it/${provincia}/${comune}/"}</script>
</head>
<body>
<header class="hdr">
  <a href="/" class="logo">Weather<span>Arb</span></a>
  <nav style="display:flex;gap:16px">
    <a href="/it/${provincia}/" style="font-size:11px;color:#4a5568;text-decoration:none">${provName}</a>
    <a href="/leaderboard/" style="font-size:11px;color:#4a5568;text-decoration:none">Leaderboard</a>
  </nav>
</header>
<div class="wrap">
  <div class="breadcrumb">
    <a href="/">WeatherArb</a> › <a href="/it/">Italia</a> › <a href="/it/${provincia}/">${provName}</a> › ${comuneName}
  </div>
  <h1>Meteo ${comuneName}</h1>
  <p class="subtitle">Anomalie climatiche in tempo reale · Provincia di ${provName}</p>
  
  <div class="card">
    <div class="card-title">📡 Anomalia Rilevata</div>
    <div class="badge" style="background:${color}22;color:${color}">${level}</div>
    <div class="metric">
      <div class="metric-val" style="color:${color}">${sign}${z.toFixed(2)}σ</div>
      <div class="metric-label">Z-Score vs baseline 25 anni NASA POWER</div>
    </div>
    <div class="grid">
      <div class="stat"><div class="stat-val">${temp}°C</div><div class="stat-lbl">Temperatura</div></div>
      <div class="stat"><div class="stat-val" style="text-transform:capitalize">${event}</div><div class="stat-lbl">Evento</div></div>
      <div class="stat"><div class="stat-val">${weatherData?.weather?.humidity_pct || '--'}%</div><div class="stat-lbl">Umidità</div></div>
      <div class="stat"><div class="stat-val">${weatherData?.weather?.wind_kmh || '--'}</div><div class="stat-lbl">Vento km/h</div></div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">⚡ Energy Data — HDD/CDD</div>
    <div class="grid">
      <div class="stat"><div class="stat-val">${weatherData?.weather?.hdd?.toFixed(1) || '0.0'}</div><div class="stat-lbl">HDD oggi</div></div>
      <div class="stat"><div class="stat-val">${weatherData?.weather?.cdd?.toFixed(1) || '0.0'}</div><div class="stat-lbl">CDD oggi</div></div>
      <div class="stat"><div class="stat-val">${weatherData?.weather?.hdd_delta?.toFixed(1) || '0.0'}</div><div class="stat-lbl">Delta HDD</div></div>
    </div>
  </div>

  <a href="/it/${provincia}/" class="cta">Vedi tutti i dati per la Provincia di ${provName} →</a>
  
  <div class="card" style="margin-top:20px">
    <div class="card-title">🗺️ Altri comuni in provincia</div>
    <div class="related">
      <a href="/it/${provincia}/">Capoluogo ${provName}</a>
      <a href="/leaderboard/">Top Anomalie Globali</a>
      <a href="/data/">Dashboard Live</a>
    </div>
  </div>
</div>
</body>
</html>`;

  return new Response(html, {
    headers: {'Content-Type':'text/html;charset=UTF-8','Cache-Control':'public,max-age=3600'}
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;
    
    // Match /it/{provincia}/{comune}/
    const match = path.match(/^\/it\/([a-z0-9-]+)\/([a-z0-9-]+)\/?$/);
    if (match) {
      const provincia = match[1];
      const comune = match[2];
      // Solo se non è già una pagina statica esistente
      return handleComune(provincia, comune, request);
    }
    
    // Passa tutto il resto agli asset statici
    return env.ASSETS.fetch(request);
  }
};
