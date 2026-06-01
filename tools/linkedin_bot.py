import os, requests, json
from datetime import datetime, timezone

LINKEDIN_TOKEN = os.getenv('LINKEDIN_ACCESS_TOKEN','')
LINKEDIN_PERSON_URN = os.getenv('LINKEDIN_PERSON_URN','')
API = 'https://artkill24-weatherarb-api.hf.space'

def get_wwai():
    r = requests.get(f"{API}/api/v1/wwai", timeout=10)
    return r.json()

def get_top_anomalies():
    r = requests.get(f"{API}/api/v1/europe/top?limit=5", timeout=10)
    return r.json()

def post_linkedin(text):
    if not LINKEDIN_TOKEN or not LINKEDIN_PERSON_URN:
        print("Missing LinkedIn credentials!")
        return False
    
    payload = {
        "author": f"urn:li:person:{LINKEDIN_PERSON_URN}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "ARTICLE",
                "media": [{
                    "status": "READY",
                    "originalUrl": "https://weatherarb.com/wwai/",
                    "title": {"text": "WeatherArb — World Weather Anomaly Index"},
                    "description": {"text": "Real-time global climate intelligence for 18,222+ cities"}
                }]
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    
    r = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers={
            "Authorization": f"Bearer {LINKEDIN_TOKEN}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        },
        json=payload, timeout=15)
    
    if r.status_code == 201:
        print(f"✓ Posted to LinkedIn!")
        return True
    else:
        print(f"✗ LinkedIn error: {r.status_code} — {r.text}")
        return False

def generate_post():
    wwai = get_wwai()
    top = get_top_anomalies()
    
    score = wwai.get('wwai', 0)
    status = wwai.get('status', 'NORMAL')
    critical = wwai.get('breakdown', {}).get('critical_count', 0)
    total = wwai.get('cities_monitored', 0)
    
    heat = wwai.get('top_heat', [])[:3]
    cold = wwai.get('top_cold', [])[:3]
    
    date = datetime.now(timezone.utc).strftime('%B %d, %Y')
    
    heat_str = ' · '.join([f"{c['city']} +{c['z']:.1f}σ" for c in heat]) if heat else "None"
    cold_str = ' · '.join([f"{c['city']} {c['z']:.1f}σ" for c in cold]) if cold else "None"
    
    emoji = "🔴" if score >= 70 else "🟠" if score >= 50 else "🟡" if score >= 30 else "🟢"
    
    text = f"""🌍 WeatherArb Global Report — {date}

{emoji} World Weather Anomaly Index (WWAI): {score:.1f}/100 — {status}

📊 {total:,} cities monitored globally
⚠️ {critical} cities in critical anomaly (|Z| ≥ 3σ)

🔥 Top Heat Anomalies:
{heat_str}

❄️ Top Cold Anomalies:
{cold_str}

The WWAI tracks real-time weather deviations vs NASA POWER 25-year baseline across 18,222+ cities worldwide.

Free API available → weatherarb.com/api

#WeatherIntelligence #ClimateData #WeatherArb #DataScience #API"""
    
    return text

if __name__ == '__main__':
    import sys
    auto = '--auto' in sys.argv
    if auto:
        text = generate_post()
        print(text)
        post_linkedin(text)
        exit()
    text = generate_post()
    print("=== PREVIEW ===")
    print(text)
    print(f"\nCharacters: {len(text)}/3000")
    
    confirm = input("\nPost to LinkedIn? (y/n): ")
    if confirm.lower() == 'y':
        post_linkedin(text)
