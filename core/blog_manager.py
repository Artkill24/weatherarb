import json
from pathlib import Path
from datetime import datetime

def update_latest_reports(max_items=6):
    posts_dir = Path("data/blog_posts")
    output_path = Path("data/website/data/latest_reports.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    articles = []
    if posts_dir.exists():
        for fp in posts_dir.glob("*.json"):
            try:
                articles.append(json.load(open(fp, encoding="utf-8")))
            except: pass

    articles.sort(key=lambda x: x.get('timestamp',''), reverse=True)

    latest = []
    for art in articles[:max_items]:
        # Calcola se "LIVE" (ultimi 12h)
        ts = art.get('timestamp','')
        is_live = False
        try:
            from datetime import timezone
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(ts.replace('Z','+00:00'))).total_seconds()
            is_live = age < 43200
        except: pass

        latest.append({
            "title": art.get('title',''),
            "slug": art.get('slug',''),
            "date": ts[:10],
            "provincia": art.get('provincia',''),
            "regione": art.get('regione',''),
            "evento": art.get('evento',''),
            "z_score": art.get('z_score', 0),
            "score": art.get('score', 0),
            "anomaly_level": art.get('anomaly_level','UNUSUAL'),
            "excerpt": art.get('meta_description','')[:150],
            "url": f"/news/{art.get('slug')}/",
            "is_live": is_live,
        })

    json.dump({"last_updated": datetime.utcnow().isoformat(), "reports": latest},
              open(output_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    return len(latest)

if __name__ == "__main__":
    n = update_latest_reports()
    print(f"✅ Feed aggiornato: {n} report")
