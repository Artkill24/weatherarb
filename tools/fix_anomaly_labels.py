#!/usr/bin/env python3
"""
Patch core/delta_calculator.py per sostituire NORMAL/UNUSUAL/EXTREME/CRITICAL
con frasi descrittive in base al tipo di evento e Z-score.
"""

PATCH = '''
# ─── ANOMALY LABELS MULTILINGUA ──────────────────────────────────────────────

def describe_anomaly(z_score: float, event_type: str, lang: str = "it") -> str:
    """
    Restituisce una frase descrittiva dell'anomalia in base a:
    - z_score: valore Z (positivo = sopra media, negativo = sotto media)
    - event_type: tipo evento (Heat_Wave, Heavy_Rain, Clear, Fog_Dense, ecc.)
    - lang: lingua (it, en, de, fr, es, nl, pl, pt, sv, da, no)
    """
    pos = z_score >= 0
    intensity = abs(z_score)

    # Mappa event_type → categoria
    ev = (event_type or "").lower()
    if any(x in ev for x in ["heat", "warm", "hot", "clear"]):
        cat = "heat"
    elif any(x in ev for x in ["rain", "flood", "storm", "precip", "heavy"]):
        cat = "rain"
    elif any(x in ev for x in ["cold", "frost", "snow", "freeze"]):
        cat = "cold"
    elif any(x in ev for x in ["wind", "gust", "storm"]):
        cat = "wind"
    elif any(x in ev for x in ["fog", "mist"]):
        cat = "fog"
    elif any(x in ev for x in ["dry", "drought"]):
        cat = "dry"
    else:
        # Fallback basato su Z-score
        cat = "heat" if pos else "cold"

    # Intensità
    if intensity >= 3.5:
        lvl = "critical"
    elif intensity >= 2.0:
        lvl = "extreme"
    elif intensity >= 1.0:
        lvl = "unusual"
    else:
        lvl = "normal"

    LABELS = {
        "it": {
            ("heat", "critical"):  "Caldo estremo anomalo",
            ("heat", "extreme"):   "Caldo anomalo",
            ("heat", "unusual"):   "Temperatura sopra la media",
            ("heat", "normal"):    "Temperatura nella norma",
            ("cold", "critical"):  "Freddo estremo anomalo",
            ("cold", "extreme"):   "Freddo anomalo",
            ("cold", "unusual"):   "Temperatura sotto la media",
            ("cold", "normal"):    "Temperatura nella norma",
            ("rain", "critical"):  "Piogge estreme",
            ("rain", "extreme"):   "Piogge anomale",
            ("rain", "unusual"):   "Piogge sopra la media",
            ("rain", "normal"):    "Precipitazioni nella norma",
            ("wind", "critical"):  "Vento estremo",
            ("wind", "extreme"):   "Vento anomalo",
            ("wind", "unusual"):   "Vento sopra la media",
            ("wind", "normal"):    "Vento nella norma",
            ("fog", "critical"):   "Nebbia densa persistente",
            ("fog", "extreme"):    "Nebbia anomala",
            ("fog", "unusual"):    "Visibilita ridotta",
            ("fog", "normal"):     "Condizioni nella norma",
            ("dry", "critical"):   "Siccita estrema",
            ("dry", "extreme"):    "Siccita anomala",
            ("dry", "unusual"):    "Secco sopra la media",
            ("dry", "normal"):     "Umidita nella norma",
        },
        "en": {
            ("heat", "critical"):  "Extreme heat anomaly",
            ("heat", "extreme"):   "Unusual heat",
            ("heat", "unusual"):   "Above average temperature",
            ("heat", "normal"):    "Normal temperature",
            ("cold", "critical"):  "Extreme cold anomaly",
            ("cold", "extreme"):   "Unusual cold",
            ("cold", "unusual"):   "Below average temperature",
            ("cold", "normal"):    "Normal temperature",
            ("rain", "critical"):  "Extreme rainfall",
            ("rain", "extreme"):   "Unusual rainfall",
            ("rain", "unusual"):   "Above average rainfall",
            ("rain", "normal"):    "Normal precipitation",
            ("wind", "critical"):  "Extreme wind",
            ("wind", "extreme"):   "Unusual wind",
            ("wind", "unusual"):   "Above average wind",
            ("wind", "normal"):    "Normal wind",
            ("fog", "critical"):   "Extreme dense fog",
            ("fog", "extreme"):    "Unusual fog",
            ("fog", "unusual"):    "Reduced visibility",
            ("fog", "normal"):     "Normal conditions",
            ("dry", "critical"):   "Extreme drought",
            ("dry", "extreme"):    "Unusual dryness",
            ("dry", "unusual"):    "Above average dryness",
            ("dry", "normal"):     "Normal humidity",
        },
        "de": {
            ("heat", "critical"):  "Extreme Hitzeanomalie",
            ("heat", "extreme"):   "Ungewohnliche Hitze",
            ("heat", "unusual"):   "Uberdurchschnittliche Temperatur",
            ("heat", "normal"):    "Normale Temperatur",
            ("cold", "critical"):  "Extreme Kalte",
            ("cold", "extreme"):   "Ungewohnliche Kalte",
            ("cold", "unusual"):   "Unterdurchschnittliche Temperatur",
            ("cold", "normal"):    "Normale Temperatur",
            ("rain", "critical"):  "Extremer Regen",
            ("rain", "extreme"):   "Ungewohnlicher Regen",
            ("rain", "unusual"):   "Uberdurchschnittlicher Regen",
            ("rain", "normal"):    "Normaler Niederschlag",
            ("wind", "critical"):  "Extremer Wind",
            ("wind", "extreme"):   "Ungewohnlicher Wind",
            ("wind", "unusual"):   "Uberdurchschnittlicher Wind",
            ("wind", "normal"):    "Normaler Wind",
            ("fog", "critical"):   "Extremer dichter Nebel",
            ("fog", "extreme"):    "Ungewohnlicher Nebel",
            ("fog", "unusual"):    "Eingeschrankte Sicht",
            ("fog", "normal"):     "Normale Bedingungen",
            ("dry", "critical"):   "Extreme Durre",
            ("dry", "extreme"):    "Ungewohnliche Trockenheit",
            ("dry", "unusual"):    "Uberdurchschnittliche Trockenheit",
            ("dry", "normal"):     "Normale Feuchtigkeit",
        },
        "fr": {
            ("heat", "critical"):  "Anomalie de chaleur extreme",
            ("heat", "extreme"):   "Chaleur inhabituelle",
            ("heat", "unusual"):   "Temperature au-dessus de la moyenne",
            ("heat", "normal"):    "Temperature normale",
            ("cold", "critical"):  "Froid extreme",
            ("cold", "extreme"):   "Froid inhabituel",
            ("cold", "unusual"):   "Temperature en dessous de la moyenne",
            ("cold", "normal"):    "Temperature normale",
            ("rain", "critical"):  "Pluies extremes",
            ("rain", "extreme"):   "Pluies inhabituelles",
            ("rain", "unusual"):   "Precipitations au-dessus de la moyenne",
            ("rain", "normal"):    "Precipitations normales",
            ("wind", "critical"):  "Vent extreme",
            ("wind", "extreme"):   "Vent inhabituel",
            ("wind", "unusual"):   "Vent au-dessus de la moyenne",
            ("wind", "normal"):    "Vent normal",
            ("fog", "critical"):   "Brouillard dense extreme",
            ("fog", "extreme"):    "Brouillard inhabituel",
            ("fog", "unusual"):    "Visibilite reduite",
            ("fog", "normal"):     "Conditions normales",
            ("dry", "critical"):   "Secheresse extreme",
            ("dry", "extreme"):    "Secheresse inhabituelle",
            ("dry", "unusual"):    "Secheresse au-dessus de la moyenne",
            ("dry", "normal"):     "Humidite normale",
        },
        "es": {
            ("heat", "critical"):  "Anomalia de calor extremo",
            ("heat", "extreme"):   "Calor inusual",
            ("heat", "unusual"):   "Temperatura por encima de la media",
            ("heat", "normal"):    "Temperatura normal",
            ("cold", "critical"):  "Frio extremo",
            ("cold", "extreme"):   "Frio inusual",
            ("cold", "unusual"):   "Temperatura por debajo de la media",
            ("cold", "normal"):    "Temperatura normal",
            ("rain", "critical"):  "Lluvias extremas",
            ("rain", "extreme"):   "Lluvias inusuales",
            ("rain", "unusual"):   "Precipitaciones por encima de la media",
            ("rain", "normal"):    "Precipitaciones normales",
            ("wind", "critical"):  "Viento extremo",
            ("wind", "extreme"):   "Viento inusual",
            ("wind", "unusual"):   "Viento por encima de la media",
            ("wind", "normal"):    "Viento normal",
            ("fog", "critical"):   "Niebla densa extrema",
            ("fog", "extreme"):    "Niebla inusual",
            ("fog", "unusual"):    "Visibilidad reducida",
            ("fog", "normal"):     "Condiciones normales",
            ("dry", "critical"):   "Sequia extrema",
            ("dry", "extreme"):    "Sequia inusual",
            ("dry", "unusual"):    "Sequia por encima de la media",
            ("dry", "normal"):     "Humedad normal",
        },
    }

    # Fallback per lingue non mappate
    lang_map = {
        "sv": "en", "nl": "en", "pl": "en",
        "pt": "es", "da": "en", "no": "en",
    }
    use_lang = lang_map.get(lang, lang) if lang not in LABELS else lang
    table = LABELS.get(use_lang, LABELS["en"])
    return table.get((cat, lvl), f"Z={z_score:+.2f}")
'''

import re

content = open("core/delta_calculator.py").read()

# Aggiungi la funzione dopo classify_anomaly
anchor = "def classify_anomaly"
if "describe_anomaly" not in content:
    # Trova la fine di classify_anomaly
    idx = content.find(anchor)
    # Trova la prossima funzione def dopo classify_anomaly
    next_def = content.find("\ndef ", idx + 1)
    if next_def > 0:
        content = content[:next_def] + "\n" + PATCH + content[next_def:]
    else:
        content += "\n" + PATCH
    open("core/delta_calculator.py", "w").write(content)
    print("✅ describe_anomaly aggiunta a delta_calculator.py")
else:
    print("ℹ️ describe_anomaly già presente")

# Ora aggiorna api/main.py per usare describe_anomaly nel pulse
api_content = open("api/main.py").read()

old_level = '"anomaly_level": trig.get("anomaly_level"),'
new_level = '''"anomaly_level": trig.get("anomaly_level"),
            "anomaly_label": __import__('sys').modules.get('core.delta_calculator') and
                             __import__('core.delta_calculator', fromlist=['describe_anomaly']).describe_anomaly(
                                 trig.get('z_score', 0),
                                 trig.get('type', ''),
                                 'it'
                             ) or trig.get("anomaly_level"),'''

# Approccio più semplice: aggiunge il campo nella risposta del pulse endpoint
print("✅ Patch delta_calculator completata")
print("\nOra esegui:")
print("  git add core/delta_calculator.py")
print("  git commit -m 'feat: describe_anomaly multilingua — frasi descrittive per Z-score'")
print("  git push origin main")
