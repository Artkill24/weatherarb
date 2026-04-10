#!/usr/bin/env python3
"""
tools/generate_articles_expansion.py
Genera articoli Gemini per i nuovi paesi europei.
Chiamato da GitHub Actions ogni 6h.
Nessun riferimento affiliate.
"""

import json
import os
import sys
import argparse
import requests
from datetime import datetime
from pathlib import Path

# Import prompts (stessa dir)
sys.path.insert(0, str(Path(__file__).parent))
from gemini_prompts_expansion import GEMINI_PROMPTS

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
OWM_API_KEY = os.environ["OWM_API_KEY"]
API_BASE = os.getenv("WEATHERARB_API", "https://api.weatherarb.com")

GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

MIN_LEVEL_ORDER = {"NORMAL": 0, "UNUSUAL": 1, "EXTREME": 2, "CRITICAL": 3}

def get_pulse(city_slug: str) -> dict:
    try:
        r = requests.get(f"{API_BASE}/api/v1/pulse/{city_slug}", timeout=10)
        return r.json()
    except:
        return {}

def gemini_generate(prompt: str) -> str:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024}
    }
    r = requests.post(GEMINI_URL, json=payload, timeout=30)
    data = r.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]

def generate_for_country(country_code: str, cities: list, min_level: str = "EXTREME"):
    min_order = MIN_LEVEL_ORDER.get(min_level, 2)
    articles = []
    today = datetime.utcnow().strftime("%Y-%m-%d")

    for city_data in cities:
        slug = city_data["slug"]
        lang = city_data["lang"]
        city = city_data["city"]

        pulse = get_pulse(slug)
        if not pulse:
            print(f"  ⚠ No pulse for {city}")
            continue

        level = pulse.get("anomaly_level", "NORMAL")
        if MIN_LEVEL_ORDER.get(level, 0) < min_order:
            print(f"  – {city}: {level} (skip)")
            continue

        print(f"  ✍ Generating article for {city} ({level})")

        prompt_template = GEMINI_PROMPTS.get(lang, GEMINI_PROMPTS["en"])
        prompt = prompt_template.format(
            city=city,
            anomaly_level=level,
            z_score=pulse.get("z_score", 0),
            weather_type=pulse.get("weather_type", "Unknown"),
            temp=pulse.get("temperature", 0),
            temp_avg=pulse.get("temp_historical_avg", 0),
            humidity=pulse.get("humidity", 0),
        )

        try:
            content = gemini_generate(prompt)
        except Exception as e:
            print(f"  ✗ Gemini error for {city}: {e}")
            continue

        article_slug = f"{slug}-{today}"
        out_path = Path("news") / country_code.lower() / f"{article_slug}.html"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")

        articles.append({
            "slug": f"{country_code.lower()}/{article_slug}",
            "city": city,
            "country": country_code,
            "lang": lang,
            "anomaly_level": level,
            "z_score": pulse.get("z_score"),
            "date": datetime.utcnow().isoformat(),
            "title": f"Weather Anomaly: {city} — {level}"
        })

    return articles


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--countries", default="SE,GB,NL,PL,AT,CH,BE,PT,DK,NO")
    parser.add_argument("--min-level", default="EXTREME")
    args = parser.parse_args()

    with open("data/cities_expansion.json") as f:
        all_cities = json.load(f)

    # Carica latest_reports.json esistente
    reports_path = Path("data/latest_reports.json")
    existing = json.loads(reports_path.read_text()) if reports_path.exists() else []

    new_articles = []
    for country in args.countries.split(","):
        cities = all_cities.get(country, [])
        if not cities:
            print(f"⚠ No cities for {country}")
            continue
        print(f"\n🌍 {country} ({len(cities)} cities)")
        articles = generate_for_country(country, cities, args.min_level)
        new_articles.extend(articles)
        print(f"  → {len(articles)} articles generated")

    # Merge e salva (mantieni ultimi 200 articoli)
    merged = new_articles + existing
    merged = merged[:200]
    reports_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False))
    print(f"\n✅ Total new articles: {len(new_articles)}")
