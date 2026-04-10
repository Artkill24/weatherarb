"""
WeatherArb Auto-Publisher
Eseguito da GitHub Actions ogni 6h.
1. Fetch top anomalie dall'API Railway
2. Genera articoli Gemini per EXTREME/CRITICAL
3. Aggiorna latest_reports.json + sitemap
"""
import sys, os, requests, json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '.')

# Gemini
GEMINI_KEY = os.getenv('GEMINI_API_KEY','')
API_BASE = 'https://api.weatherarb.com'

def get_top_anomalies(limit=20):
    try:
        r = requests.get(f'{API_BASE}/api/v1/europe/top?limit={limit}', timeout=15)
        return r.json().get('data', [])
    except Exception as e:
        print(f"❌ API error: {e}")
        return []

def make_slug(nome, event, date):
    slug_name = nome.lower()
    for a,b in [('ü','u'),('ö','o'),('ä','a'),('à','a'),('è','e'),('ù','u'),(' ','-'),("'",'')]:
        slug_name = slug_name.replace(a,b)
    slug_event = event.lower().replace('_','-')
    return f"{date}-{slug_name}-{slug_event}"

def generate_article_gemini(item, provinces_data):
    if not GEMINI_KEY:
        return None
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_KEY)
        
        nome = item['province']
        z = item.get('z_score', 0)
        event = item.get('event_type', 'anomalia')
        temp = item.get('temperature_c', '—')
        level = item.get('anomaly_level', 'UNUSUAL')
        score = item.get('score', 0)
        
        prompt = f"""Sei un meteorologo esperto. Scrivi un articolo di analisi meteo professionale in italiano.

Città: {nome}
Evento: {event.replace('_',' ')}
Z-Score: {z:+.2f} (deviazione dalla baseline ERA5-Land)
Temperatura attuale: {temp}°C
Livello anomalia: {level}
Score: {score:.1f}/10

Struttura:
- Titolo breve (max 80 caratteri)
- Paragrafo introduttivo (2-3 frasi)
- Analisi tecnica (Z-Score, confronto storico)
- Impatto pratico
- Conclusione

Rispondi SOLO con JSON:
{{"title": "...", "content": "...", "excerpt": "..."}}"""

        resp = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        text = resp.text.strip()
        if text.startswith('```'):
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as e:
        print(f"  Gemini error: {e}")
        return None

def load_provinces():
    try:
        data = json.load(open('data/province_coords.json'))
        return {p['nome'].lower(): p for p in data['province']}
    except:
        return {}

def update_latest_reports(articles, max_items=15):
    path = Path('data/website/data/latest_reports.json')
    existing = []
    if path.exists():
        try:
            existing = json.load(open(path)).get('reports', [])
        except:
            pass
    
    # Aggiungi nuovi in cima
    all_reports = articles + [r for r in existing if r['slug'] not in {a['slug'] for a in articles}]
    all_reports = all_reports[:max_items]
    
    json.dump({
        'last_updated': datetime.utcnow().isoformat(),
        'reports': all_reports
    }, open(path, 'w'), ensure_ascii=False, indent=2)
    print(f"✅ latest_reports.json aggiornato: {len(all_reports)} articoli")

def create_article_html(item, article_data, slug):
    nome = item['province']
    z = item.get('z_score', 0)
    event = item.get('event_type', '').replace('_',' ')
    level = item.get('anomaly_level', 'UNUSUAL')
    score = item.get('score', 0)
    temp = item.get('temperature_c', '—')
    date_str = datetime.now().strftime('%d/%m/%Y')
    
    colors = {'CRITICAL':'#ef4444','EXTREME':'#f97316','UNUSUAL':'#d97706','NORMAL':'#2563eb'}
    color = colors.get(level, '#d97706')
    
    html = f'''<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{article_data["title"]} | WeatherArb</title>
<meta name="description" content="{article_data["excerpt"]}">
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
:root{{--ink:#0f1117;--paper:#f5f3ee;--storm:#1a3a5c;--electric:#2563eb;--mist:#e8e5de;--muted:#6b6560}}
*{{box-sizing:border-box;margin:0;padding:0}}body{{font-family:'DM Sans',sans-serif;background:var(--paper);color:var(--ink)}}
nav{{display:flex;align-items:center;justify-content:space-between;padding:20px 48px;border-bottom:1px solid var(--mist);background:rgba(245,243,238,.95);position:sticky;top:0;z-index:100}}
.logo{{font-family:'Instrument Serif',serif;font-size:20px;display:flex;align-items:center;gap:8px;text-decoration:none;color:var(--ink)}}
.logo-icon{{width:28px;height:28px;background:var(--storm);border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:14px}}
.hero-bar{{background:var(--storm);color:white;padding:16px 48px;display:flex;gap:24px;align-items:center;flex-wrap:wrap}}
.badge{{background:rgba(255,255,255,.12);border-radius:8px;padding:8px 14px;text-align:center}}
.badge strong{{display:block;font-family:'Instrument Serif',serif;font-size:20px}}
.badge span{{font-size:10px;opacity:.6;text-transform:uppercase;letter-spacing:1px}}
.container{{max-width:720px;margin:0 auto;padding:48px 24px}}
.tag{{font-size:11px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:{color};margin-bottom:16px}}
h1{{font-family:'Instrument Serif',serif;font-size:clamp(26px,4vw,38px);line-height:1.2;margin-bottom:12px}}
.byline{{font-size:13px;color:var(--muted);margin-bottom:32px;padding-bottom:24px;border-bottom:1px solid var(--mist)}}
.body-text p{{font-size:16px;line-height:1.8;margin-bottom:20px;color:var(--ink)}}
footer{{text-align:center;font-size:12px;color:var(--muted);padding:32px;border-top:1px solid var(--mist);margin-top:48px}}
</style>
</head>
<body>
<nav><a href="/" class="logo"><div class="logo-icon">⛈</div>WeatherArb</a><a href="/news/" style="font-size:12px;color:var(--muted);text-decoration:none">← Reports</a></nav>
<div class="hero-bar" style="background:{colors.get(level,'#1a3a5c')}">
  <div style="flex:1"><div style="font-size:11px;opacity:.6;margin-bottom:4px">📍 {nome}</div><div style="font-size:16px;font-weight:500">{event} · {level}</div></div>
  <div class="badge"><strong>{z:+.2f}</strong><span>Z-Score</span></div>
  <div class="badge"><strong>{score:.1f}/10</strong><span>Score</span></div>
  <div class="badge"><strong>{temp if isinstance(temp,str) else f"{temp:.1f}"}°C</strong><span>Temp</span></div>
</div>
<div class="container">
  <div class="tag">🇮🇹 {nome} · {event}</div>
  <h1>{article_data["title"]}</h1>
  <div class="byline">WeatherArb Intelligence · {date_str} · ERA5-Land ECMWF + NASA POWER</div>
  <div class="body-text">{"".join(f"<p>{p}</p>" for p in article_data["content"].split(chr(10)) if p.strip())}</div>
</div>
<footer>WeatherArb.com · Independent Weather Intelligence</footer>
</body>
</html>'''
    return html

def main():
    print(f"🚀 WeatherArb Auto-Publisher — {datetime.utcnow().isoformat()}")
    
    provinces = load_provinces()
    top = get_top_anomalies(20)
    
    if not top:
        print("⚠️  Nessun dato dall'API — skip")
        return
    
    targets = [x for x in top if x.get('anomaly_level') in ('CRITICAL','EXTREME') and abs(x.get('z_score',0)) >= 1.5]
    print(f"📊 Anomalie trovate: {len(targets)}")
    
    today = datetime.now().strftime('%Y-%m-%d')
    existing_slugs = set(f.replace('.json','') for f in os.listdir('data/blog_posts/') if f.endswith('.json'))
    
    new_articles = []
    for item in targets[:6]:
        nome = item.get('province','')
        event = item.get('event_type','anomalia')
        slug = make_slug(nome, event, today)
        
        if slug in existing_slugs:
            print(f"⏭️  {nome} — già pubblicato oggi")
            continue
        
        print(f"📝 Generando articolo per {nome} (Z={item.get('z_score',0):+.2f})...")
        article_data = generate_article_gemini(item, provinces)
        
        if not article_data:
            # Fallback senza Gemini
            article_data = {
                'title': f"{event.replace('_',' ')} anomalo a {nome}: analisi WeatherArb del {datetime.now().strftime('%d/%m/%Y')}",
                'excerpt': f"Anomalia meteo a {nome}. Z-Score {item.get('z_score',0):+.2f}, livello {item.get('anomaly_level','UNUSUAL')}. Analisi tecnica.",
                'content': f"WeatherArb ha rilevato un'anomalia meteo significativa a {nome} con Z-Score {item.get('z_score',0):+.2f} rispetto alla baseline ERA5-Land."
            }
        
        # Salva JSON
        blog_data = {
            'slug': slug, 'title': article_data['title'],
            'excerpt': article_data['excerpt'], 'content': article_data['content'],
            'provincia': nome, 'evento': event, 'date': today,
            'z_score': item.get('z_score',0), 'score': item.get('score',0),
            'anomaly_level': item.get('anomaly_level','UNUSUAL'),
            'url': f'/news/{slug}/'
        }
        json.dump(blog_data, open(f'data/blog_posts/{slug}.json','w'), ensure_ascii=False, indent=2)
        
        # Crea HTML
        html = create_article_html(item, article_data, slug)
        Path(f'data/website/news/{slug}').mkdir(parents=True, exist_ok=True)
        open(f'data/website/news/{slug}/index.html','w').write(html)
        
        new_articles.append({
            'slug': slug, 'title': article_data['title'],
            'excerpt': article_data['excerpt'], 'provincia': nome,
            'evento': event, 'date': today,
            'z_score': item.get('z_score',0), 'score': item.get('score',0),
            'anomaly_level': item.get('anomaly_level','UNUSUAL'),
            'url': f'/news/{slug}/', 'is_live': True
        })
        print(f"  ✅ {slug}")
    
    # Aggiorna reports anche se nessun articolo nuovo (aggiorna timestamp)
    update_latest_reports(new_articles)
    
    # Sitemap base
    sitemap_urls = []
    for f in sorted(Path('data/website/news').iterdir()):
        if f.is_dir():
            sitemap_urls.append(f'https://weatherarb.com/news/{f.name}/')
    
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += '<url><loc>https://weatherarb.com/</loc><changefreq>hourly</changefreq><priority>1.0</priority></url>\n'
    sitemap += '<url><loc>https://weatherarb.com/data/</loc><changefreq>hourly</changefreq><priority>0.9</priority></url>\n'
    for url in sitemap_urls[-50:]:
        sitemap += f'<url><loc>{url}</loc><changefreq>daily</changefreq><priority>0.7</priority></url>\n'
    sitemap += '</urlset>'
    open('data/website/sitemap.xml','w').write(sitemap)
    
    print(f"\n✅ Auto-publisher completato. Nuovi articoli: {len(new_articles)}")

if __name__ == '__main__':
    main()
