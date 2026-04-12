#!/usr/bin/env python3
"""
WeatherArb — Aggiunge sezione mappa alla homepage esistente
Inserisce Leaflet map con marker colorati live tra il ticker e il network grid
"""

from pathlib import Path

MAP_SECTION = '''
<!-- MAP -->
<div class="map-wrap">
  <div class="section-hdr">
    <div class="section-title">🗺 Mappa Anomalie Europa</div>
    <a href="/map.html" class="section-link">Fullscreen →</a>
  </div>
  <div id="map"></div>
</div>

<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>
  .map-wrap{max-width:1100px;margin:0 auto;padding:0 24px 40px}
  #map{height:420px;border-radius:12px;border:1px solid #141920;background:#0a0d12;z-index:1}
  .leaflet-container{background:#0a0d12!important}
  .wa-popup{background:#0a0d12;border:1px solid #1e2d3d;border-radius:8px;padding:10px 14px;color:#c8d6e5;font-family:-apple-system,sans-serif;min-width:160px}
  .wa-popup .city{font-weight:700;font-size:14px;margin-bottom:4px}
  .wa-popup .score{font-size:12px;margin-bottom:2px}
  .wa-popup .vert{font-size:11px;color:#4a5568;text-transform:uppercase;letter-spacing:.08em}
  .wa-popup a{display:inline-block;margin-top:8px;font-size:11px;color:#3b82f6;text-decoration:none}
  .leaflet-popup-content-wrapper,.leaflet-popup-tip{background:transparent!important;box-shadow:none!important;padding:0!important}
  .leaflet-popup-content{margin:0!important}
</style>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
(function(){
  const map = L.map('map', {
    center: [50, 12],
    zoom: 4,
    zoomControl: true,
    attributionControl: false
  });

  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 18
  }).addTo(map);

  function scoreColor(s) {
    if (s >= 8) return '#ef4444';
    if (s >= 6) return '#f97316';
    if (s >= 4) return '#f59e0b';
    return '#10b981';
  }

  function makeMarker(city, score, vertical, cc) {
    const col = scoreColor(score);
    const r = 5 + score * 0.8;
    const slug = (city || '').toLowerCase().replace(/\\s+/g, '-');
    return L.circleMarker([city.lat, city.lon], {
      radius: r,
      fillColor: col,
      color: col,
      weight: 1,
      fillOpacity: score > 4 ? 0.85 : 0.5
    }).bindPopup(`<div class="wa-popup">
      <div class="city">${city.name}</div>
      <div class="score" style="color:${col}">Score ${score.toFixed(1)}/10 · Z ${(city.z||0).toFixed(2)}</div>
      <div class="vert">${(vertical||'').replace('_',' ')}</div>
      <a href="/${cc}/${slug}/">Vedi analisi →</a>
    </div>`, {closeButton: false});
  }

  // Carica top signals dall'API
  async function loadMap() {
    try {
      const r = await fetch('https://api.weatherarb.com/api/v1/europe/top?limit=200');
      const d = await r.json();
      const cities = d.reports || d.cities || [];

      cities.forEach(c => {
        if (!c.lat || !c.lon) return;
        const sc = c.score || 0;
        const cc = c.country_code || 'it';
        const cityObj = { name: c.location || '—', lat: c.lat, lon: c.lon, z: c.z_score || 0 };
        makeMarker(cityObj, sc, c.vertical, cc).addTo(map);
      });

      // Se l'API non ha lat/lon, fallback su tutte le province con coordinate fisse
      if (cities.length === 0 || !cities[0].lat) loadFallback();

    } catch(e) { loadFallback(); }
  }

  // Fallback: mostra tutti i nodi da cities.json (senza score, solo posizione)
  async function loadFallback() {
    try {
      const r = await fetch('/api/v1/cities.json');
      const cities = await r.json();
      cities.forEach(c => {
        if (!c.lat || !c.lon) return;
        L.circleMarker([c.lat, c.lon], {
          radius: 5, fillColor: '#3b82f6', color: '#3b82f6',
          weight: 1, fillOpacity: 0.5
        }).bindPopup(`<div class="wa-popup"><div class="city">${c.name}</div><div class="vert">Monitoraggio Attivo</div><a href="/it/${c.id}/">Vedi →</a></div>`, {closeButton:false}).addTo(map);
      });
    } catch(e) {}
  }

  loadMap();
})();
</script>
'''

def patch_homepage():
    hp = Path("data/website/index.html")
    if not hp.exists():
        print("❌ data/website/index.html non trovato. Esegui dalla root di nano_pulse.")
        return

    content = hp.read_text(encoding="utf-8")

    # Inserisci la mappa DOPO il ticker e PRIMA del network europeo
    ANCHOR = '<!-- COUNTRIES -->'
    if ANCHOR not in content:
        # Fallback: cerca il div countries
        ANCHOR = '<div class="countries">'
    
    if ANCHOR not in content:
        print("❌ Anchor non trovato nella homepage. La mappa va aggiunta manualmente.")
        return

    new_content = content.replace(ANCHOR, MAP_SECTION + '\n' + ANCHOR)
    hp.write_text(new_content, encoding="utf-8")
    print("✅ Mappa aggiunta alla homepage")
    print("\n📦 Ora esegui:")
    print("   git add data/website/index.html")
    print("   git commit -m 'feat: mappa Leaflet live nella homepage'")
    print("   git pull --rebase && git push origin main")

if __name__ == "__main__":
    patch_homepage()
