#!/usr/bin/env python3
"""
WeatherArb — Sitemap completa + Fix ticker homepage
"""
import json
import re
from pathlib import Path
from datetime import datetime
from unicodedata import normalize

BASE = Path("data/website")
TODAY = datetime.utcnow().strftime("%Y-%m-%d")

COUNTRY_CODE = {
    "Italy": "it", "Germany": "de", "France": "fr", "Spain": "es",
    "United Kingdom": "gb", "Sweden": "se", "Netherlands": "nl",
    "Poland": "pl", "Austria": "at", "Switzerland": "ch",
    "Belgium": "be", "Portugal": "pt", "Denmark": "dk", "Norway": "no"
}

CITY_COUNTRY_FALLBACK = {
    "münchen": "de", "munchen": "de", "hamburg": "de", "berlin": "de",
    "frankfurt": "de", "stuttgart": "de", "köln": "de", "koln": "de",
    "düsseldorf": "de", "dusseldorf": "de", "nürnberg": "de", "nurnberg": "de",
    "madrid": "es", "barcelona": "es", "valencia": "es", "sevilla": "es", "bilbao": "es",
    "paris": "fr", "lyon": "fr", "marseille": "fr", "bordeaux": "fr", "nice": "fr",
    "london": "gb", "manchester": "gb", "birmingham": "gb", "edinburgh": "gb",
    "glasgow": "gb", "leeds": "gb", "bristol": "gb", "cardiff": "gb",
    "liverpool": "gb", "sheffield": "gb",
    "stockholm": "se", "göteborg": "se", "goteborg": "se", "malmö": "se", "malmo": "se",
    "uppsala": "se", "västerås": "se", "vasteras": "se", "örebro": "se", "orebro": "se",
    "linköping": "se", "linkoping": "se", "helsingborg": "se",
    "jönköping": "se", "jonkoping": "se", "umeå": "se", "umea": "se",
    "amsterdam": "nl", "rotterdam": "nl", "den haag": "nl", "den-haag": "nl",
    "utrecht": "nl", "eindhoven": "nl", "groningen": "nl",
    "warszawa": "pl", "kraków": "pl", "krakow": "pl", "wrocław": "pl", "wroclaw": "pl",
    "poznań": "pl", "poznan": "pl", "gdańsk": "pl", "gdansk": "pl", "łódź": "pl",
    "wien": "at", "graz": "at", "linz": "at", "salzburg": "at", "innsbruck": "at",
    "zürich": "ch", "zurich": "ch", "genève": "ch", "geneve": "ch",
    "basel": "ch", "bern": "ch", "lausanne": "ch",
    "bruxelles": "be", "antwerpen": "be", "gent": "be", "liège": "be", "liege": "be",
    "lisboa": "pt", "porto": "pt", "braga": "pt",
    "københavn": "dk", "kobenhavn": "dk", "kbenhavn": "dk", "aarhus": "dk", "odense": "dk",
    "oslo": "no", "bergen": "no", "trondheim": "no", "stavanger": "no",
}

def slugify(name: str) -> str:
    s = normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    return re.sub(r"[\s_]+", "-", s)

def get_cc(city: dict) -> str:
    cn = city.get("country", "")
    if cn and cn in COUNTRY_CODE:
        return COUNTRY_CODE[cn]
    return CITY_COUNTRY_FALLBACK.get(city.get("nome", "").lower(), "it")

def url(loc: str, priority: str, freq: str) -> str:
    return f"""  <url>
    <loc>https://weatherarb.com{loc}</loc>
    <lastmod>{TODAY}</lastmod>
    <changefreq>{freq}</changefreq>
    <priority>{priority}</priority>
  </url>"""

# ─── SITEMAP ────────────────────────────────────────────────────────────────
def build_sitemap():
    with open("data/province_coords.json") as f:
        raw = json.load(f)
    provinces = raw["province"] if "province" in raw else raw

    urls = []

    # Pagine statiche principali
    static = [
        ("/", "1.0", "hourly"),
        ("/data/", "0.9", "hourly"),
        ("/news/", "0.9", "daily"),
        ("/map.html", "0.8", "daily"),
        ("/api.html", "0.7", "weekly"),
        ("/alerts.html", "0.7", "weekly"),
        ("/about.html", "0.6", "weekly"),
    ]
    for loc, pri, freq in static:
        urls.append(url(loc, pri, freq))

    # Hub nazionali
    seen_cc = set()
    for p in provinces:
        cc = get_cc(p)
        if cc not in seen_cc:
            urls.append(url(f"/{cc}/", "0.8", "daily"))
            seen_cc.add(cc)

    # Landing 121 città
    for p in provinces:
        cc = get_cc(p)
        slug = slugify(p["nome"])
        urls.append(url(f"/{cc}/{slug}/", "0.8", "hourly"))

    # Articoli news esistenti
    news_dir = BASE / "news"
    if news_dir.exists():
        for d in sorted(news_dir.iterdir()):
            if d.is_dir() and (d / "index.html").exists():
                urls.append(url(f"/news/{d.name}/", "0.7", "weekly"))

    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>"""

    out = BASE / "sitemap.xml"
    out.write_text(sitemap, encoding="utf-8")
    print(f"✅ sitemap.xml — {len(urls)} URL")
    return len(urls)


# ─── TICKER FIX ─────────────────────────────────────────────────────────────
def fix_ticker():
    hp = BASE / "index.html"
    if not hp.exists():
        print("❌ index.html non trovato")
        return

    content = hp.read_text(encoding="utf-8")

    # Il vecchio JS cerca d.reports che a volte è vuoto al primo load
    # Nuovo JS: retry automatico + fallback su cities.json se API vuota
    old_ticker = """async function loadTicker(){
  try{
    const r=await fetch(API+'/api/v1/europe/top?limit=12');
    const d=await r.json();
    const items=(d.reports||d.cities||[]).slice(0,12);
    if(!items.length)return;
    const t=document.getElementById('ticker');
    t.innerHTML=items.map(c=>{
      const sc=c.score||0,z=c.z_score||0,lvl=lv(sc),col=LV[lvl];
      const slug=(c.location||'').toLowerCase().replace(/\\s+/g,'-');
      const cc=c.country_code||'it';
      return `<a href="/${cc}/${slug}/" class="tc">
        <div class="tc-left"><div class="tc-city">${c.location||'—'}</div><div class="tc-country">${c.country||cc.toUpperCase()}</div></div>
        <div class="tc-right"><div class="tc-score" style="color:${col}">${sc.toFixed(1)}</div><div class="tc-vert">${(c.vertical||'').replace('_',' ')}</div></div>
      </a>`;
    }).join('');
    const anom=items.filter(c=>(c.score||0)>=5).length;
    document.getElementById('live-anom').textContent=anom;
  }catch(e){
    document.getElementById('ticker').innerHTML='<p style="color:var(--muted);font-size:13px;padding:20px">Connessione API in corso...</p>';
  }
}"""

    new_ticker = """async function loadTicker(attempt){
  attempt=attempt||1;
  try{
    const r=await fetch(API+'/api/v1/europe/top?limit=12');
    const d=await r.json();
    const items=(d.reports||d.data||[]).filter(c=>c.location||c.province).slice(0,12);
    if(!items.length && attempt<3){
      // Cache vuota: aspetta e riprova (Railway si sta scaldando)
      setTimeout(()=>loadTicker(attempt+1), 15000);
      document.getElementById('ticker').innerHTML='<p style="color:var(--muted);font-size:13px;padding:20px">⏳ Sincronizzazione nodi in corso...</p>';
      return;
    }
    const t=document.getElementById('ticker');
    if(!items.length){
      t.innerHTML='<p style="color:var(--muted);font-size:13px;padding:20px">Nessuna anomalia rilevata al momento.</p>';
      return;
    }
    t.innerHTML=items.map(c=>{
      const sc=c.score||0,z=c.z_score||0,lvl=lv(sc),col=LV[lvl];
      const name=c.location||c.province||'—';
      const slug=name.toLowerCase().replace(/\\s+/g,'-').replace(/[^a-z0-9-]/g,'');
      const cc=c.country_code||'it';
      const vert=(c.vertical||c.event_type||'').replace(/_/g,' ');
      const sign=z>=0?'+':'';
      return `<a href="/${cc}/${slug}/" class="tc">
        <div class="tc-left">
          <div class="tc-city">${name}</div>
          <div class="tc-country">${c.country||cc.toUpperCase()} · Z${sign}${(z).toFixed(1)}</div>
        </div>
        <div class="tc-right">
          <div class="tc-score" style="color:${col}">${sc.toFixed(1)}</div>
          <div class="tc-vert">${vert||'—'}</div>
        </div>
      </a>`;
    }).join('');
    const anom=items.filter(c=>(c.score||0)>=5).length;
    document.getElementById('live-anom').textContent=anom;
  }catch(e){
    if(attempt<3){setTimeout(()=>loadTicker(attempt+1),20000);}
    else{document.getElementById('ticker').innerHTML='<p style="color:var(--muted);font-size:13px;padding:20px">Sistema in avvio...</p>';}
  }
}"""

    if old_ticker in content:
        content = content.replace(old_ticker, new_ticker)
        hp.write_text(content, encoding="utf-8")
        print("✅ Ticker JS aggiornato — retry automatico + fix chiavi API")
    else:
        print("⚠️  Pattern ticker non trovato esattamente — aggiorna manualmente il JS")
        print("    Cerca 'async function loadTicker' in data/website/index.html")


# ─── ROBOTS.TXT ─────────────────────────────────────────────────────────────
def update_robots():
    robots = """User-agent: *
Allow: /

Sitemap: https://weatherarb.com/sitemap.xml
"""
    (BASE / "robots.txt").write_text(robots, encoding="utf-8")
    print("✅ robots.txt aggiornato con sitemap URL")


# ─── MAIN ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("WeatherArb — Sitemap + Ticker + Robots\n")
    n = build_sitemap()
    fix_ticker()
    update_robots()
    print(f"""
╔═══════════════════════════════════════════════╗
║  Completato                                   ║
║  {n} URL in sitemap.xml                      ║
║  Ticker con retry automatico                  ║
║  robots.txt con sitemap                       ║
╚═══════════════════════════════════════════════╝

📦 Ora esegui:
   git add data/website/sitemap.xml data/website/index.html data/website/robots.txt
   git commit -m "feat: sitemap 121 città + ticker fix + robots"
   git pull --rebase && git push origin main

🔍 Poi vai su Google Search Console:
   → Sitemaps → Aggiungi: https://weatherarb.com/sitemap.xml
""")
