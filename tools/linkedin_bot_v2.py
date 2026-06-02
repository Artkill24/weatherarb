import os, requests, json, sys
from datetime import datetime, timezone

LINKEDIN_TOKEN = os.getenv('LINKEDIN_ACCESS_TOKEN','')
LINKEDIN_URN = os.getenv('LINKEDIN_PERSON_URN','')
GROQ_KEY = os.getenv('GROQ_API_KEY','')
OR_KEY = os.getenv('OPENROUTER_API_KEY','')
API = 'https://artkill24-weatherarb-api.hf.space'

def get_wwai():
    r = requests.get(f"{API}/api/v1/wwai", timeout=10)
    return r.json()

def get_top(limit=10):
    r = requests.get(f"{API}/api/v1/europe/top?limit={limit}", timeout=10)
    return r.json()

def generate_text(prompt):
    # Prova Groq prima
    if GROQ_KEY:
        try:
            r = requests.post('https://api.groq.com/openai/v1/chat/completions',
                headers={'Authorization': f'Bearer {GROQ_KEY}', 'Content-Type': 'application/json'},
                json={'model': 'llama-3.3-70b-versatile',
                      'messages': [{'role': 'user', 'content': prompt}],
                      'max_tokens': 600, 'temperature': 0.8},
                timeout=20)
            return r.json()['choices'][0]['message']['content'].strip()
        except: pass
    # Fallback OpenRouter
    if OR_KEY:
        try:
            r = requests.post('https://openrouter.ai/api/v1/chat/completions',
                headers={'Authorization': f'Bearer {OR_KEY}', 'Content-Type': 'application/json',
                         'HTTP-Referer': 'https://weatherarb.com'},
                json={'model': 'moonshotai/kimi-k2.6:free',
                      'messages': [{'role': 'user', 'content': prompt}],
                      'max_tokens': 600},
                timeout=30)
            return r.json()['choices'][0]['message']['content'].strip()
        except: pass
    return None

def post_linkedin(text, url=None):
    if not LINKEDIN_TOKEN or not LINKEDIN_URN:
        print("❌ Missing LinkedIn credentials!")
        return False

    media = []
    if url:
        media = [{"status": "READY", "originalUrl": url,
                  "title": {"text": "WeatherArb — Global Weather Intelligence"},
                  "description": {"text": "Real-time anomaly data for 18,222+ cities"}}]

    payload = {
        "author": f"urn:li:person:{LINKEDIN_URN}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "ARTICLE" if url else "NONE",
                **({"media": media} if media else {})
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }

    r = requests.post("https://api.linkedin.com/v2/ugcPosts",
        headers={"Authorization": f"Bearer {LINKEDIN_TOKEN}",
                 "Content-Type": "application/json",
                 "X-Restli-Protocol-Version": "2.0.0"},
        json=payload, timeout=15)

    if r.status_code == 201:
        print(f"✅ Posted! ID: {r.headers.get('X-RestLi-Id','')}")
        return True
    else:
        print(f"❌ Error {r.status_code}: {r.text[:200]}")
        return False

def generate_post():
    wwai = get_wwai()
    top = get_top(10)

    score = wwai.get('wwai', 0)
    status = wwai.get('status', 'NORMAL')
    critical = wwai.get('breakdown', {}).get('critical_count', 0)
    severe = wwai.get('breakdown', {}).get('severe_count', 0)
    total = wwai.get('cities_monitored', 18222)
    date = datetime.now(timezone.utc).strftime('%B %d, %Y')
    dow = datetime.now(timezone.utc).strftime('%A')

    heat = wwai.get('top_heat', [])[:3]
    cold = wwai.get('top_cold', [])[:3]

    heat_str = ' · '.join([f"{c['city']} +{c['z']:.1f}σ" for c in heat]) or "None detected"
    cold_str = ' · '.join([f"{c['city']} {c['z']:.1f}σ" for c in cold]) or "None detected"

    # Emoji status
    if score >= 70: emoji, mood = "🔴", "EXTREME"
    elif score >= 50: emoji, mood = "🟠", "SEVERE"
    elif score >= 30: emoji, mood = "🟡", "ELEVATED"
    else: emoji, mood = "🟢", "NORMAL"

    # Top anomalie con link
    reports = top.get('reports', top.get('data', []))[:5]
    top_lines = []
    for r in reports:
        cc = r.get('country_code','').lower()
        slug = r.get('location','').lower().replace(' ','-').replace("'",'')
        z = r.get('z_score', 0)
        sign = '+' if z >= 0 else ''
        top_lines.append(f"  • {r.get('location')} ({cc.upper()}) {sign}{z:.1f}σ → weatherarb.com/{cc}/{slug}/")

    top_str = '\n'.join(top_lines)

    # Genera insight con AI
    prompt = f"""Write a 2-sentence professional weather intelligence insight for LinkedIn.
Today is {dow}. WWAI Score: {score}/100 ({mood}). 
Critical anomalies: {critical} cities. Top heat: {heat_str}. Top cold: {cold_str}.
Style: data-driven, professional, slightly urgent if score>50. No emojis in the insight text. Max 200 chars."""

    insight = generate_text(prompt) or f"Global weather patterns show {mood.lower()} anomaly levels with {critical} cities in critical deviation from 25-year NASA baselines."

    post = f"""{emoji} WeatherArb Global Intelligence — {date}

WWAI: {score:.0f}/100 — {mood}

{insight}

📊 Live Data:
  ├ {total:,} cities monitored globally
  ├ {critical} cities critical (|Z| ≥ 3σ)
  └ {severe} cities severe (|Z| ≥ 2σ)

🔥 Top Heat Anomalies:
{heat_str}

❄️ Top Cold Anomalies:
{cold_str}

📍 Most Active Signals:
{top_str}

Free API + live data → weatherarb.com/api

#WeatherIntelligence #ClimateData #WeatherArb #DataScience #EnergyTrading #API"""

    return post

if __name__ == '__main__':
    auto = '--auto' in sys.argv
    print("Fetching data...")
    text = generate_post()
    print("\n=== PREVIEW ===")
    print(text)
    print(f"\nCharacters: {len(text)}/3000")

    if auto:
        post_linkedin(text, "https://weatherarb.com/wwai/")
    else:
        confirm = input("\nPost to LinkedIn? (y/n): ")
        if confirm.lower() == 'y':
            post_linkedin(text, "https://weatherarb.com/wwai/")
