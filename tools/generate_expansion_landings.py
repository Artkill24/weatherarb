#!/usr/bin/env python3
"""
Script da aggiungere a tools/ o usare in GitHub Actions
Genera le landing pages statiche per le nuove città europee
Output: /xx/{city_slug}/index.html
"""

import json
import os
from pathlib import Path

# Template HTML per landing page — identico alla struttura IT/DE/ES/FR
# Nessun riferimento affiliate
LANDING_TEMPLATE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{page_title}</title>
  <meta name="description" content="{meta_description}">
  <meta property="og:title" content="{page_title}">
  <meta property="og:description" content="{meta_description}">
  <link rel="canonical" href="https://weatherarb.com/{country_lower}/{city_slug}/">
  <link rel="stylesheet" href="/assets/style.css">
</head>
<body>
  <header>
    <a href="/" class="logo">⚡ WeatherArb</a>
    <nav>
      <a href="/data/">{nav_data}</a>
      <a href="/map.html">{nav_map}</a>
      <a href="/alerts.html">{nav_alerts}</a>
    </nav>
  </header>

  <main class="city-page">
    <div class="city-hero">
      <h1>{h1_title}</h1>
      <p class="city-subtitle">{subtitle}</p>
    </div>

    <div class="pulse-widget" id="pulse-{city_slug}">
      <div class="pulse-loading">{loading_text}</div>
    </div>

    <section class="city-info">
      <h2>{section_live}</h2>
      <div class="metrics-grid" id="metrics-{city_slug}">
        <!-- Popolato via JS da API -->
      </div>
    </section>

    <section class="city-context">
      <h2>{section_context}</h2>
      <p>{context_text}</p>
    </section>

    <section class="city-articles" id="articles-{city_slug}">
      <h2>{section_articles}</h2>
      <!-- Articoli dinamici da latest_reports.json -->
    </section>
  </main>

  <footer>
    <p>{footer_text}</p>
    <p><a href="/api.html">API</a> · <a href="/about.html">{footer_about}</a> · <a href="/alerts.html">{footer_alerts}</a></p>
  </footer>

  <script>
    const CITY_SLUG = "{city_slug}";
    const COUNTRY = "{country}";
    const API_BASE = "https://api.weatherarb.com";

    async function loadPulse() {{
      try {{
        const r = await fetch(`${{API_BASE}}/api/v1/pulse/${{CITY_SLUG}}`);
        const d = await r.json();
        document.getElementById(`pulse-${{CITY_SLUG}}`).innerHTML = renderPulse(d);
        document.getElementById(`metrics-${{CITY_SLUG}}`).innerHTML = renderMetrics(d);
      }} catch(e) {{
        document.getElementById(`pulse-${{CITY_SLUG}}`).innerHTML = '<p class="error">{error_text}</p>';
      }}
    }}

    function renderPulse(d) {{
      const level = d.anomaly_level || 'NORMAL';
      const score = d.z_score?.toFixed(2) || '–';
      const cls = level.toLowerCase();
      return `<div class="pulse-card ${{cls}}">
        <span class="pulse-level">${{level}}</span>
        <span class="pulse-score">Z: ${{score}}</span>
        <span class="pulse-temp">${{d.temperature?.toFixed(1) || '–'}}°C</span>
      </div>`;
    }}

    function renderMetrics(d) {{
      return `
        <div class="metric"><label>Z-Score</label><value>${{d.z_score?.toFixed(2) || '–'}}</value></div>
        <div class="metric"><label>Temp</label><value>${{d.temperature?.toFixed(1) || '–'}}°C</value></div>
        <div class="metric"><label>Humidity</label><value>${{d.humidity || '–'}}%</value></div>
        <div class="metric"><label>Level</label><value>${{d.anomaly_level || 'NORMAL'}}</value></div>
      `;
    }}

    // Carica articoli recenti per questa città
    async function loadArticles() {{
      try {{
        const r = await fetch('/data/latest_reports.json');
        const articles = await r.json();
        const cityArticles = articles.filter(a =>
          a.city?.toLowerCase() === CITY_SLUG.toLowerCase() ||
          a.country === COUNTRY
        ).slice(0, 3);
        if (cityArticles.length > 0) {{
          document.getElementById(`articles-${{CITY_SLUG}}`).querySelector('h2').insertAdjacentHTML(
            'afterend',
            cityArticles.map(a => `
              <article class="article-card">
                <h3><a href="/news/${{a.slug}}/">${{a.title}}</a></h3>
                <time>${{new Date(a.date).toLocaleDateString()}}</time>
              </article>
            `).join('')
          );
        }}
      }} catch(e) {{}}
    }}

    loadPulse();
    loadArticles();
    setInterval(loadPulse, 60000); // refresh ogni minuto
  </script>
</body>
</html>"""

# Stringhe UI per ogni lingua
UI_STRINGS = {
    "sv": {
        "nav_data": "Live Data", "nav_map": "Karta", "nav_alerts": "Aviseringar",
        "loading_text": "Laddar väderdata...",
        "section_live": "Live Väderdata",
        "section_context": "Om WeatherArb",
        "section_articles": "Senaste Rapporter",
        "context_text": "WeatherArb övervakar väderanomalier i realtid i 10 svenska städer med Z-Score-analys baserad på 25 års historiska data (NASA POWER + ERA5-Land ECMWF).",
        "footer_text": "Data uppdateras varje timme · WeatherArb European Weather Intelligence",
        "footer_about": "Metodik", "footer_alerts": "Prenumerera",
        "error_text": "Kunde inte ladda data. Försök igen."
    },
    "en": {
        "nav_data": "Live Data", "nav_map": "Map", "nav_alerts": "Alerts",
        "loading_text": "Loading weather data...",
        "section_live": "Live Weather Data",
        "section_context": "About WeatherArb",
        "section_articles": "Latest Reports",
        "context_text": "WeatherArb monitors weather anomalies in real time across 10 UK cities using Z-Score analysis based on 25 years of historical data (NASA POWER + ERA5-Land ECMWF).",
        "footer_text": "Data updated hourly · WeatherArb European Weather Intelligence",
        "footer_about": "Methodology", "footer_alerts": "Subscribe",
        "error_text": "Could not load data. Please try again."
    },
    "nl": {
        "nav_data": "Live Data", "nav_map": "Kaart", "nav_alerts": "Meldingen",
        "loading_text": "Weergegevens laden...",
        "section_live": "Live Weerdata",
        "section_context": "Over WeatherArb",
        "section_articles": "Laatste Rapporten",
        "context_text": "WeatherArb monitort weeranomalieën in realtime in 6 Nederlandse en Belgische steden met Z-Score-analyse op basis van 25 jaar historische data.",
        "footer_text": "Data elk uur bijgewerkt · WeatherArb European Weather Intelligence",
        "footer_about": "Methodologie", "footer_alerts": "Abonneren",
        "error_text": "Kon geen gegevens laden. Probeer opnieuw."
    },
    "pl": {
        "nav_data": "Dane Live", "nav_map": "Mapa", "nav_alerts": "Alerty",
        "loading_text": "Ładowanie danych pogodowych...",
        "section_live": "Dane Pogodowe Live",
        "section_context": "O WeatherArb",
        "section_articles": "Najnowsze Raporty",
        "context_text": "WeatherArb monitoruje anomalie pogodowe w czasie rzeczywistym w 6 polskich miastach, używając analizy Z-Score opartej na 25 latach danych historycznych.",
        "footer_text": "Dane aktualizowane co godzinę · WeatherArb European Weather Intelligence",
        "footer_about": "Metodologia", "footer_alerts": "Subskrybuj",
        "error_text": "Nie można załadować danych. Spróbuj ponownie."
    },
    "pt": {
        "nav_data": "Dados Live", "nav_map": "Mapa", "nav_alerts": "Alertas",
        "loading_text": "A carregar dados meteorológicos...",
        "section_live": "Dados Meteorológicos em Direto",
        "section_context": "Sobre WeatherArb",
        "section_articles": "Últimos Relatórios",
        "context_text": "WeatherArb monitoriza anomalias meteorológicas em tempo real em 3 cidades portuguesas, usando análise Z-Score baseada em 25 anos de dados históricos.",
        "footer_text": "Dados atualizados de hora em hora · WeatherArb European Weather Intelligence",
        "footer_about": "Metodologia", "footer_alerts": "Subscrever",
        "error_text": "Não foi possível carregar os dados. Tente novamente."
    },
    "da": {
        "nav_data": "Live Data", "nav_map": "Kort", "nav_alerts": "Advarsler",
        "loading_text": "Indlæser vejrdata...",
        "section_live": "Live Vejrdata",
        "section_context": "Om WeatherArb",
        "section_articles": "Seneste Rapporter",
        "context_text": "WeatherArb overvåger vejranomalier i realtid i 3 danske byer ved hjælp af Z-Score-analyse baseret på 25 års historiske data.",
        "footer_text": "Data opdateres hver time · WeatherArb European Weather Intelligence",
        "footer_about": "Metodologi", "footer_alerts": "Abonner",
        "error_text": "Kunne ikke indlæse data. Prøv igen."
    },
    "no": {
        "nav_data": "Live Data", "nav_map": "Kart", "nav_alerts": "Varsler",
        "loading_text": "Laster værddata...",
        "section_live": "Live Værdata",
        "section_context": "Om WeatherArb",
        "section_articles": "Siste Rapporter",
        "context_text": "WeatherArb overvåker værvarsler i sanntid i 4 norske byer ved hjelp av Z-Score-analyse basert på 25 års historiske data.",
        "footer_text": "Data oppdateres hver time · WeatherArb European Weather Intelligence",
        "footer_about": "Metodologi", "footer_alerts": "Abonner",
        "error_text": "Kunne ikke laste data. Prøv igjen."
    },
    "de": {  # Per AT e CH
        "nav_data": "Live Daten", "nav_map": "Karte", "nav_alerts": "Warnungen",
        "loading_text": "Wetterdaten werden geladen...",
        "section_live": "Live Wetterdaten",
        "section_context": "Über WeatherArb",
        "section_articles": "Aktuelle Berichte",
        "context_text": "WeatherArb überwacht Wetteranomalien in Echtzeit in deutschen, österreichischen und Schweizer Städten mittels Z-Score-Analyse auf Basis von 25 Jahren historischer Daten.",
        "footer_text": "Daten stündlich aktualisiert · WeatherArb European Weather Intelligence",
        "footer_about": "Methodik", "footer_alerts": "Abonnieren",
        "error_text": "Daten konnten nicht geladen werden. Bitte erneut versuchen."
    },
    "fr": {  # Per BE e CH francofono
        "nav_data": "Données Live", "nav_map": "Carte", "nav_alerts": "Alertes",
        "loading_text": "Chargement des données météo...",
        "section_live": "Données Météo en Direct",
        "section_context": "À propos de WeatherArb",
        "section_articles": "Derniers Rapports",
        "context_text": "WeatherArb surveille les anomalies météorologiques en temps réel dans les villes françaises, belges et suisses grâce à l'analyse Z-Score basée sur 25 ans de données historiques.",
        "footer_text": "Données mises à jour toutes les heures · WeatherArb European Weather Intelligence",
        "footer_about": "Méthodologie", "footer_alerts": "S'abonner",
        "error_text": "Impossible de charger les données. Veuillez réessayer."
    },
}

# Titoli H1 e meta description per paese/lingua
CITY_TITLES = {
    "sv": {
        "h1": "Väderanomalier i {city} — Live Z-Score",
        "title": "Väder {city} — Anomaliövervakning | WeatherArb",
        "desc": "Realtidsövervakning av väderanomalier i {city}. Z-Score-analys baserad på 25 år av historiska klimatdata.",
        "subtitle": "Live klimatövervakning · Z-Score · NASA POWER + ERA5"
    },
    "en": {
        "h1": "Weather Anomalies in {city} — Live Z-Score",
        "title": "Weather {city} — Anomaly Monitoring | WeatherArb",
        "desc": "Real-time weather anomaly monitoring in {city}. Z-Score analysis based on 25 years of historical climate data.",
        "subtitle": "Live climate monitoring · Z-Score · NASA POWER + ERA5"
    },
    "nl": {
        "h1": "Weeranomalieën in {city} — Live Z-Score",
        "title": "Weer {city} — Anomaliemonitoring | WeatherArb",
        "desc": "Realtime monitoring van weeranomalieën in {city}. Z-Score-analyse op basis van 25 jaar historische klimaatdata.",
        "subtitle": "Live klimaatmonitoring · Z-Score · NASA POWER + ERA5"
    },
    "pl": {
        "h1": "Anomalie Pogodowe w {city} — Live Z-Score",
        "title": "Pogoda {city} — Monitoring Anomalii | WeatherArb",
        "desc": "Monitoring anomalii pogodowych w czasie rzeczywistym w {city}. Analiza Z-Score oparta na 25 latach historycznych danych klimatycznych.",
        "subtitle": "Monitoring klimatu na żywo · Z-Score · NASA POWER + ERA5"
    },
    "pt": {
        "h1": "Anomalias Meteorológicas em {city} — Z-Score Live",
        "title": "Tempo {city} — Monitorização de Anomalias | WeatherArb",
        "desc": "Monitorização em tempo real de anomalias meteorológicas em {city}. Análise Z-Score baseada em 25 anos de dados climáticos históricos.",
        "subtitle": "Monitorização climática live · Z-Score · NASA POWER + ERA5"
    },
    "da": {
        "h1": "Vejranomalier i {city} — Live Z-Score",
        "title": "Vejr {city} — Anomalovervågning | WeatherArb",
        "desc": "Realtidsovervågning af vejranomalier i {city}. Z-Score-analyse baseret på 25 års historiske klimadata.",
        "subtitle": "Live klimaovervågning · Z-Score · NASA POWER + ERA5"
    },
    "no": {
        "h1": "Væranomalier i {city} — Live Z-Score",
        "title": "Vær {city} — Anomalovervåking | WeatherArb",
        "desc": "Sanntidsovervåking av væranomalier i {city}. Z-Score-analyse basert på 25 år med historiske klimadata.",
        "subtitle": "Live klimaovervåking · Z-Score · NASA POWER + ERA5"
    },
    "de": {
        "h1": "Wetteranomalien in {city} — Live Z-Score",
        "title": "Wetter {city} — Anomalie-Monitoring | WeatherArb",
        "desc": "Echtzeit-Überwachung von Wetteranomalien in {city}. Z-Score-Analyse basierend auf 25 Jahren historischer Klimadaten.",
        "subtitle": "Live Klimaüberwachung · Z-Score · NASA POWER + ERA5"
    },
    "fr": {
        "h1": "Anomalies Météo à {city} — Z-Score Live",
        "title": "Météo {city} — Surveillance des Anomalies | WeatherArb",
        "desc": "Surveillance en temps réel des anomalies météorologiques à {city}. Analyse Z-Score basée sur 25 ans de données climatiques historiques.",
        "subtitle": "Surveillance climatique live · Z-Score · NASA POWER + ERA5"
    },
}

def generate_landing(city_data: dict, output_dir: str = "expansion_landings"):
    city = city_data["city"]
    slug = city_data["slug"]
    lang = city_data["lang"]
    country = city_data["country"].lower()

    ui = UI_STRINGS.get(lang, UI_STRINGS["en"])
    titles = CITY_TITLES.get(lang, CITY_TITLES["en"])

    html = LANDING_TEMPLATE.format(
        lang=lang,
        page_title=titles["title"].format(city=city),
        meta_description=titles["desc"].format(city=city),
        h1_title=titles["h1"].format(city=city),
        subtitle=titles["subtitle"],
        city_slug=slug,
        country=country.upper(),
        country_lower=country,
        **ui
    )

    out_path = Path(output_dir) / country / slug / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return str(out_path)


if __name__ == "__main__":
    with open("cities_expansion.json") as f:
        cities = json.load(f)

    generated = []
    for country_code, city_list in cities.items():
        for city_data in city_list:
            path = generate_landing(city_data)
            generated.append(path)
            print(f"  ✓ {path}")

    print(f"\n✅ Generate {len(generated)} landing pages")
