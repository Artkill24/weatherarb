"""
Auto-publish: scarica dati dal backend Railway e genera pagine statiche.
Viene eseguito da GitHub Actions ogni 6 ore.
"""
import requests, json, os, sys
from pathlib import Path
from datetime import datetime

API = "https://api.weatherarb.com"

def main():
    print("=== WeatherArb Auto-Publisher ===")
    
    # 1. Scarica top signals da Railway
    try:
        r = requests.get(f"{API}/api/v1/europe/top?limit=10", timeout=30)
        signals = r.json().get("data", [])
        print(f"✅ {len(signals)} segnali scaricati")
    except Exception as e:
        print(f"❌ API non raggiungibile: {e}")
        signals = []

    # 2. Scarica latest reports
    try:
        r = requests.get(f"{API}/pulse/reports/latest?limit=10", timeout=30)
        reports = r.json().get("reports", [])
        print(f"✅ {len(reports)} report scaricati")
    except:
        reports = []

    # 3. Aggiorna latest_reports.json per la homepage
    output = Path("data/website/data")
    output.mkdir(parents=True, exist_ok=True)
    
    json.dump({
        "last_updated": datetime.utcnow().isoformat(),
        "reports": reports
    }, open(output / "latest_reports.json", "w"), ensure_ascii=False, indent=2)
    print("✅ latest_reports.json aggiornato")

    # 4. Aggiorna sitemap
    urls = [
        "https://weatherarb.com/",
        "https://weatherarb.com/it/",
        "https://weatherarb.com/open.html",
        "https://weatherarb.com/about.html",
        "https://weatherarb.com/news/",
    ]
    for r in reports:
        urls.append(f"https://weatherarb.com/news/{r['slug']}/")

    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for url in urls:
        sitemap += f"  <url><loc>{url}</loc><changefreq>daily</changefreq></url>\n"
    sitemap += "</urlset>"
    
    open("data/website/sitemap.xml", "w").write(sitemap)
    print(f"✅ Sitemap aggiornata: {len(urls)} URL")

    print("=== Deploy ready ===")

if __name__ == "__main__":
    main()
