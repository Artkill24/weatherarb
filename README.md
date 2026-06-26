# 🌍 WeatherArb — Weather Anomaly Intelligence Platform

Piattaforma di rilevamento anomalie meteorologiche in tempo reale per **18.222+ città in 162+ paesi**, basata su Z-Score climatico confrontato con baseline storiche reali.

🔗 **Live**: [weatherarb.com](https://weatherarb.com)
📡 **API**: [weatherarb.com/pricing](https://weatherarb.com/pricing)

---

## Cos'è WeatherArb

WeatherArb calcola un indice proprietario **WWAI (World Weather Anomaly Index, 0-100)** per ogni città monitorata, confrontando i dati meteo attuali con baseline climatiche storiche per identificare deviazioni statisticamente significative (Z-Score).

**Use case principali:**
- 🌾 Agricoltura — stress idrico, rischio raccolto
- ⚡ Energia — domanda HDD/CDD anomala
- 🚚 Logistica — rischio meteo su rotte
- 🏦 Assicurazioni — climate risk scoring

---

## Architettura

```
NASA POWER (baseline climatica 20 anni, per città)
MET Norway / NOAA NWS / Open-Meteo / WeatherAPI (dati live)
         ↓
    [FastAPI Backend — HuggingFace Spaces]
    Z-Score Calculator + HDD/CDD Engine
         ↓
    [Supabase — Postgres]
    weather_cache (snapshot live)
    weather_history (serie storica oraria)
    city_baseline (climatologia NASA POWER per città)
         ↓
    [Cloudflare Workers — Frontend statico]
    19.000+ pagine SEO multilingua (IT/EN/DE/ES/FR/PT/AR)
         ↓
    Pulse-JSON via API pubblica
```

---

## Stack Tecnico

| Layer | Tecnologia |
|---|---|
| Backend API | FastAPI (Python), deploy su HuggingFace Spaces |
| Frontend | HTML statico + JS vanilla, Cloudflare Workers |
| Database | Supabase (PostgreSQL) |
| Dati meteo live | MET Norway, NOAA NWS, Open-Meteo, WeatherAPI |
| Baseline climatica | NASA POWER Climatology API (MERRA-2, 2001-2020) |
| AI / NLP | Groq (Llama 3) per articoli multilingua |
| Automazione | GitHub Actions (refresh orario, migrazioni batch) |
| Monetizzazione | Google AdSense |
| Email | Resend (newsletter, alert) |

---

## Setup Locale

### Backend (HuggingFace Spaces repo separato)

```bash
cd /path/to/hf-weatherarb
pip install -r requirements.txt
```

### Environment Variables (secrets su HF Spaces)

```bash
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=xxxxx
GROQ_API_KEY=xxxxx
WEATHER_API_KEY=xxxxx
RESEND_API_KEY=xxxxx
```

### Avvio locale

```bash
uvicorn main:app --reload --port 7860
```

API: `http://localhost:7860`
Docs: `http://localhost:7860/docs`

### Frontend (Cloudflare Workers)

```bash
cd data/website
npx wrangler deploy
```

---

## Endpoints Principali

| Endpoint | Metodo | Descrizione |
|---|---|---|
| `/health` | GET | Status sistema |
| `/api/v1/pulse/{slug}` | GET | Dati anomalia per città |
| `/api/v1/pulse/nearby` | GET | Città più vicina a lat/lon |
| `/api/v1/europe/top` | GET | Top anomalie per regione |
| `/api/v1/global-signals` | GET | Wildfires, eventi NASA EONET |
| `/api/v1/history/{slug}` | GET | Serie storica Z-Score (7gg) |
| `/api/v1/wwai` | GET | World Weather Anomaly Index globale |
| `/api/space-weather` | GET | Kp Index, solar flare (NOAA SWPC) |
| `/pulse/refresh` | POST | Refresh completo cache (18k città) |
| `/api/newsletter/subscribe` | POST | Iscrizione alert email |

### Esempio risposta `/api/v1/pulse/torino`

```json
{
  "province": "Torino",
  "comune": "Torino",
  "country_code": "it",
  "lat": 45.0703,
  "lon": 7.6869,
  "z_score": -1.5,
  "anomaly_level": "UNUSUAL",
  "event_type": "heavy_rain",
  "score": 5.0,
  "temperature_c": 17.7,
  "precipitation": 0,
  "humidity_pct": 94.6,
  "wind_kmh": 12.2
}
```

---

## Metodologia Z-Score

Lo Z-Score misura quante deviazioni standard la temperatura attuale si trova rispetto alla media storica per quel mese e quella città specifica:

```
Z = (temp_attuale - media_storica_NASA_POWER) / deviazione_standard
```

**Baseline**: climatologia NASA POWER (MERRA-2), 20 anni di dati (2001-2020), per ogni singola città — non una media globale generica.

| Z-Score | Livello |
|---|---|
| \|Z\| < 1 | NORMAL |
| 1 ≤ \|Z\| < 2 | UNUSUAL |
| 2 ≤ \|Z\| < 3 | EXTREME |
| \|Z\| ≥ 3 | CRITICAL |

---

## Roadmap

- [x] 18.222+ città in 162+ paesi
- [x] Baseline NASA POWER reale per città (migrazione in corso)
- [x] AdSense attivo
- [x] Pagine regione/paese con aggregazione live
- [x] Grafico storico Z-Score (7 giorni)
- [ ] API pubblica a pagamento (tier Pro)
- [ ] Widget embeddabile per siti terzi
- [ ] Climate Risk Index regionale a lungo termine
- [ ] App mobile

---

## Struttura File (Frontend — questo repo)

```
nano_pulse/data/website/
├── index.html                   # Homepage
├── {cc}/                        # Pagine indice paese (162 paesi)
│   ├── index.html
│   └── {slug}/                  # Pagine città (18.222+)
│       └── index.html
├── it/{regione}/                # Pagine regione italiane (20)
├── ar/ma/{slug}/                 # Pagine arabe Marocco (214)
├── sitemap-*.xml                 # Sitemap per lingua/area
├── ads.txt                       # Google AdSense authorized sellers
└── worker.js                     # Cloudflare Worker entry point
```

## Struttura File (Backend — repo separato hf-weatherarb)

```
hf-weatherarb/
├── main.py                       # FastAPI app, tutti gli endpoint
├── data/
│   └── province_coords.json      # 18.222 città con lat/lon/country
├── Dockerfile
└── requirements.txt
```

---

## Note

Progetto indie, costruito e mantenuto da un solo sviluppatore. Pre-revenue al momento, con traffico organico reale (~800 query/giorno su Google) e monetizzazione AdSense attiva.
