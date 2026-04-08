# ⚡ Nano-Arbitrage Engine — The Pulse
## Sprint 1: Weather Signal → Actionable JSON

Sistema di rilevamento anomalie meteo per affiliate marketing geo-localizzato.
Copre **47 province del Nord Italia** (bacino Padano + Alpi + Liguria + Emilia-Romagna).

---

## Architettura Sprint 1

```
Copernicus ERA5-Land (baseline storica)
         +
OpenWeatherMap API (previsione 72h)
         ↓
    [The Ingestor]
    WeatherSnapshot × Provincia
         ↓
  [Delta Calculator]
  Z-Score + Arbitrage Score
         ↓
  [Product Mapper]
  ChromaDB semantic search
         ↓
    Pulse-JSON pronto per The Architect
```

---

## Setup

### 1. Ambiente Python

```bash
cd nano_pulse
python -m venv venv
source venv/bin/activate          # Linux/Mac
# venv\Scripts\activate           # Windows
pip install -r requirements.txt
```

### 2. API Keys

**OpenWeatherMap** (gratuito fino a 1.000 calls/giorno):
- Registrati su https://openweathermap.org/api
- Ottieni la API key dalla dashboard

**Copernicus CDS** (gratuito, richiede accettazione ToS):
- Registrati su https://cds.climate.copernicus.eu
- Crea il file `~/.cdsapirc`:
```
url: https://cds.climate.copernicus.eu/api/v2
key: UID:API-KEY
```

### 3. Environment Variables

```bash
export OWM_API_KEY="la_tua_api_key_owm"
export CDS_API_KEY="la_tua_api_key_copernicus"
```

> ⚠️ **Senza API key**: il sistema gira in modalità MOCK con dati simulati realistici.
> Perfetto per validare l'architettura prima di attivare le API.

---

## Avvio

### Backend FastAPI

```bash
# Dalla root del progetto
uvicorn api.main:app --reload --port 8000
```

API disponibile su: http://localhost:8000
Docs interattive: http://localhost:8000/docs

### Dashboard Streamlit

```bash
# In un secondo terminale
streamlit run dashboard/app.py
```

Dashboard su: http://localhost:8501

---

## Endpoints Principali

| Endpoint | Metodo | Descrizione |
|---|---|---|
| `/` | GET | Status sistema |
| `/pulse/{provincia}` | GET | Pulse-JSON per una provincia |
| `/pulse/refresh` | POST | Refresh globale in background |
| `/pulse/heatmap/scores` | GET | Tutti gli score per la heatmap |
| `/pulse/heatmap/opportunities` | GET | Solo province azionabili |
| `/province` | GET | Lista province disponibili |

### Esempio risposta `/pulse/vicenza`

```json
{
  "timestamp": "2026-04-03T22:00:00Z",
  "location": {
    "provincia": "Vicenza",
    "regione": "Veneto",
    "codice_istat": "024",
    "cluster": "NE_Industrial",
    "popolazione": 859000
  },
  "weather_trigger": {
    "type": "Heavy_Rain",
    "severity": 0.75,
    "anomaly_level": "EXTREME",
    "z_score": 2.34,
    "delta_historical": "+85.2%",
    "peak_expected_in": "42h"
  },
  "arbitrage_score": {
    "score": 8.2,
    "confidence": 0.91,
    "historical_roi_estimate": 3.4,
    "actionable": true,
    "aggressive_scale": true
  },
  "action_plan": {
    "phase": "PRE_EVENT_PREP",
    "guardrail": "APPROVED",
    "recommended_vertical": "Home_Maintenance",
    "top_product_categories": ["Deumidificatori", "Impermeabili", "Stivali"],
    "budget_recommendation": {
      "daily_eur": 50.0,
      "strategy": "AGGRESSIVE_SCALE_THOMPSON_BANDIT"
    }
  }
}
```

---

## Logica del Guardrail Etico

Il sistema implementa **Temporal Decoupling**:

| Timing | Fase | Azione |
|---|---|---|
| 72h - 24h pre-evento | PRE_EVENT_PREP | Campagne educative |
| 24h - 6h pre-evento | PRE_EVENT_LAUNCH | Campagne prodotto |
| < 6h pre-evento | BLACKOUT | Solo contenuto informativo |
| Durante evento attivo | BLACKOUT | Zero spend pubblicitario |
| 24h - 7g post-evento | POST_EVENT_RECOVERY | Vertical recovery |

Le categorie "Pompe idrauliche" e "Generatori" sono **hardcoded-bloccate** durante anomalie CRITICAL (Z > 3.0) per prevenire gouging pricing.

---

## Roadmap Sprint 2

- [ ] Integrazione CDS API reale per baseline ERA5-Land (vs cluster simulati)
- [ ] LangGraph orchestration per The Architect (landing page generator)
- [ ] Taboola API integration per The Media Buyer
- [ ] Weather-Product Ledger su PostgreSQL + TimescaleDB
- [ ] Thompson Sampling bandit per ottimizzazione creative
- [ ] Backtesting 24 mesi con Volume di Opportunità Mensile

---

## Struttura File

```
nano_pulse/
├── config.py                    # Soglie, API keys, costanti
├── requirements.txt
├── core/
│   ├── ingestor.py              # OWM fetcher + ERA5 baseline
│   ├── delta_calculator.py      # Z-Score + Arbitrage Score
│   └── product_mapper.py        # ChromaDB semantic search
├── api/
│   └── main.py                  # FastAPI endpoints
├── dashboard/
│   └── app.py                   # Streamlit heatmap
└── data/
    ├── province_coords.json      # 47 province Nord Italia
    ├── products_seed.csv         # 30 prodotti affiliate evergreen
    ├── chroma_db/               # Vector DB (auto-generato)
    └── era5_cache/              # Cache NetCDF (auto-generato)
```
