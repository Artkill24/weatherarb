import json, re, math
from pathlib import Path
from unicodedata import normalize

def sl(t):
    s = normalize('NFKD', t).encode('ascii','ignore').decode('ascii')
    return re.sub(r'[\s_]+','-', re.sub(r'[^\w\s-]','',s).strip().lower())

CC_MAP = {
    'Italy':'it','Germany':'de','France':'fr','Spain':'es','United Kingdom':'gb',
    'Sweden':'se','Netherlands':'nl','Poland':'pl','Austria':'at','Switzerland':'ch',
    'Belgium':'be','Portugal':'pt','Denmark':'dk','Norway':'no',
    'Greece':'gr','Croatia':'hr','Czech Republic':'cz','Hungary':'hu','Romania':'ro',
    'Finland':'fi','Slovenia':'si','Slovakia':'sk','Serbia':'rs'
}

LABEL = {
    'it':'Italia','de':'Deutschland','fr':'France','es':'España','gb':'United Kingdom',
    'se':'Sverige','nl':'Nederland','pl':'Polska','at':'Österreich','ch':'Schweiz',
    'be':'Belgique','pt':'Portugal','dk':'Danmark','no':'Norge',
    'gr':'Ελλάδα','hr':'Hrvatska','cz':'Česká republika','hu':'Magyarország',
    'ro':'România','fi':'Suomi','si':'Slovenija','sk':'Slovensko','rs':'Srbija'
}

# ─── TRADUZIONI STATICHE ─────────────────────────────────────────────────────
T = {
    'it': {
        'lang': 'it',
        'nav_data': 'Dati', 'nav_news': 'Notizie', 'nav_api': 'API', 'nav_alerts': 'Alert',
        'meta_desc': 'Anomalie meteo in tempo reale per {city} ({country}). Z-Score, HDD/CDD, vento e umidità. Dati NASA POWER 25 anni. WeatherArb.',
        'title_suffix': 'Meteo Anomalie | WeatherArb Intelligence',
        'label_zscore': 'Z-Score', 'label_score': 'Score', 'label_temp': 'Temperatura',
        'label_humidity': 'Umidità', 'label_wind': 'Vento', 'label_hdd': 'HDD oggi',
        'label_cdd': 'CDD oggi', 'label_hdd_delta': 'Delta HDD', 'label_analysis': 'Analisi WeatherArb',
        'label_hdd_sub': 'gradi-giorno riscaldamento', 'label_cdd_sub': 'gradi-giorno raffrescamento',
        'label_delta_sub': 'vs storico', 'label_temp_sub': 'corrente', 'label_hum_sub': 'relativa',
        'label_wind_sub': 'km/h', 'label_score_sub': '0-10', 'label_zscore_sub': 'vs media 25 anni',
        'methodology_title': 'Metodologia',
        'methodology_text': 'WeatherArb calcola Z-Score, HDD e CDD su baseline NASA POWER 25 anni per {city} ({lat}°N, {lon}°E). Standard EN ISO 15927.',
        'sector_title': 'Settori Impattati',
        'sector_agr': 'Agricoltura', 'sector_log': 'Logistica', 'sector_ene': 'Energia',
        'sector_agr_ok': 'Condizioni agronomiche normali', 'sector_agr_warn': 'Rischio stress idrico elevato',
        'sector_log_ok': 'Condizioni ottimali per logistica', 'sector_log_warn': 'Condizioni avverse per trasporti',
        'sector_ene_ok': 'Domanda energetica nella norma', 'sector_ene_heat': 'Alta domanda riscaldamento',
        'sector_ene_cool': 'Alta domanda raffrescamento',
        'nl_title': 'Intelligence Alert per {city}',
        'nl_sub': 'Z-Score, HDD/CDD e anomalie per {city} nella tua inbox. Gratuito.',
        'nl_placeholder': 'La tua email', 'nl_btn': 'Iscriviti →',
        'nl_ok': 'Iscritto! Controlla email.', 'nl_exists': 'Sei già iscritto!', 'nl_err': 'Errore - riprova',
        'loading': 'Caricamento...', 'province': 'Provincia', 'node': 'Nodo dati',
    },
    'en': {
        'lang': 'en',
        'nav_data': 'Data', 'nav_news': 'News', 'nav_api': 'API', 'nav_alerts': 'Alerts',
        'meta_desc': 'Real-time weather anomalies for {city} ({country}). Z-Score, HDD/CDD, wind and humidity. NASA POWER 25-year baseline. WeatherArb.',
        'title_suffix': 'Weather Intelligence | WeatherArb',
        'label_zscore': 'Z-Score', 'label_score': 'Score', 'label_temp': 'Temperature',
        'label_humidity': 'Humidity', 'label_wind': 'Wind', 'label_hdd': 'HDD today',
        'label_cdd': 'CDD today', 'label_hdd_delta': 'HDD Delta', 'label_analysis': 'WeatherArb Analysis',
        'label_hdd_sub': 'heating degree days', 'label_cdd_sub': 'cooling degree days',
        'label_delta_sub': 'vs historical', 'label_temp_sub': 'current', 'label_hum_sub': 'relative',
        'label_wind_sub': 'km/h', 'label_score_sub': '0-10', 'label_zscore_sub': 'vs 25-year baseline',
        'methodology_title': 'Methodology',
        'methodology_text': 'WeatherArb calculates Z-Score, HDD and CDD against the NASA POWER 25-year baseline for {city} ({lat}°N, {lon}°E). EN ISO 15927 standard.',
        'sector_title': 'Impacted Sectors',
        'sector_agr': 'Agriculture', 'sector_log': 'Logistics', 'sector_ene': 'Energy',
        'sector_agr_ok': 'Normal agronomic conditions', 'sector_agr_warn': 'High water stress risk',
        'sector_log_ok': 'Optimal logistics conditions', 'sector_log_warn': 'Adverse transport conditions',
        'sector_ene_ok': 'Normal energy demand', 'sector_ene_heat': 'High heating demand',
        'sector_ene_cool': 'High cooling demand',
        'nl_title': 'Intelligence Alert for {city}',
        'nl_sub': 'Z-Score, HDD/CDD and weather anomalies for {city} in your inbox. Free.',
        'nl_placeholder': 'Your email', 'nl_btn': 'Subscribe →',
        'nl_ok': 'Subscribed! Check your email.', 'nl_exists': 'Already subscribed!', 'nl_err': 'Error - try again',
        'loading': 'Loading...', 'province': 'Province', 'node': 'Data node',
    },
    'de': {
        'lang': 'de',
        'nav_data': 'Daten', 'nav_news': 'Nachrichten', 'nav_api': 'API', 'nav_alerts': 'Warnungen',
        'meta_desc': 'Echtzeit-Wetteranomalien für {city} ({country}). Z-Score, HDD/CDD, Wind und Feuchtigkeit. NASA POWER 25 Jahre Baseline. WeatherArb.',
        'title_suffix': 'Wetter Intelligence | WeatherArb',
        'label_zscore': 'Z-Score', 'label_score': 'Score', 'label_temp': 'Temperatur',
        'label_humidity': 'Luftfeuchtigkeit', 'label_wind': 'Wind', 'label_hdd': 'HDD heute',
        'label_cdd': 'CDD heute', 'label_hdd_delta': 'HDD Delta', 'label_analysis': 'WeatherArb Analyse',
        'label_hdd_sub': 'Heizgradtage', 'label_cdd_sub': 'Kuehlgradtage',
        'label_delta_sub': 'vs. historisch', 'label_temp_sub': 'aktuell', 'label_hum_sub': 'relativ',
        'label_wind_sub': 'km/h', 'label_score_sub': '0-10', 'label_zscore_sub': 'vs. 25-Jahr-Baseline',
        'methodology_title': 'Methodik',
        'methodology_text': 'WeatherArb berechnet Z-Score, HDD und CDD gegen die NASA POWER 25-Jahres-Baseline fuer {city} ({lat}°N, {lon}°E). EN ISO 15927 Standard.',
        'sector_title': 'Betroffene Sektoren',
        'sector_agr': 'Landwirtschaft', 'sector_log': 'Logistik', 'sector_ene': 'Energie',
        'sector_agr_ok': 'Normale agronomische Bedingungen', 'sector_agr_warn': 'Hohes Trockenstress-Risiko',
        'sector_log_ok': 'Optimale Logistikbedingungen', 'sector_log_warn': 'Ungünstige Transportbedingungen',
        'sector_ene_ok': 'Normaler Energiebedarf', 'sector_ene_heat': 'Hoher Heizbedarf',
        'sector_ene_cool': 'Hoher Kuehlbedarf',
        'nl_title': 'Intelligence Alert fuer {city}',
        'nl_sub': 'Z-Score, HDD/CDD und Wetteranomalien fuer {city} in Ihrem Posteingang. Kostenlos.',
        'nl_placeholder': 'Ihre E-Mail', 'nl_btn': 'Abonnieren →',
        'nl_ok': 'Abonniert! Bitte pruefen Sie Ihre E-Mail.', 'nl_exists': 'Bereits abonniert!', 'nl_err': 'Fehler - erneut versuchen',
        'loading': 'Laden...', 'province': 'Provinz', 'node': 'Datenknoten',
    },
    'fr': {
        'lang': 'fr',
        'nav_data': 'Données', 'nav_news': 'Actualités', 'nav_api': 'API', 'nav_alerts': 'Alertes',
        'meta_desc': 'Anomalies météo en temps réel pour {city} ({country}). Z-Score, HDD/CDD, vent et humidité. Données NASA POWER 25 ans. WeatherArb.',
        'title_suffix': 'Météo Intelligence | WeatherArb',
        'label_zscore': 'Z-Score', 'label_score': 'Score', 'label_temp': 'Température',
        'label_humidity': 'Humidité', 'label_wind': 'Vent', 'label_hdd': 'HDD aujourd\'hui',
        'label_cdd': 'CDD aujourd\'hui', 'label_hdd_delta': 'Delta HDD', 'label_analysis': 'Analyse WeatherArb',
        'label_hdd_sub': 'degrés-jours chauffage', 'label_cdd_sub': 'degrés-jours climatisation',
        'label_delta_sub': 'vs historique', 'label_temp_sub': 'actuelle', 'label_hum_sub': 'relative',
        'label_wind_sub': 'km/h', 'label_score_sub': '0-10', 'label_zscore_sub': 'vs moyenne 25 ans',
        'methodology_title': 'Méthodologie',
        'methodology_text': 'WeatherArb calcule le Z-Score, HDD et CDD sur la baseline NASA POWER 25 ans pour {city} ({lat}°N, {lon}°E). Norme EN ISO 15927.',
        'sector_title': 'Secteurs Impactés',
        'sector_agr': 'Agriculture', 'sector_log': 'Logistique', 'sector_ene': 'Énergie',
        'sector_agr_ok': 'Conditions agronomiques normales', 'sector_agr_warn': 'Risque élevé de stress hydrique',
        'sector_log_ok': 'Conditions logistiques optimales', 'sector_log_warn': 'Conditions de transport défavorables',
        'sector_ene_ok': 'Demande énergétique normale', 'sector_ene_heat': 'Forte demande de chauffage',
        'sector_ene_cool': 'Forte demande de climatisation',
        'nl_title': 'Alerte Intelligence pour {city}',
        'nl_sub': 'Z-Score, HDD/CDD et anomalies météo pour {city} dans votre boîte mail. Gratuit.',
        'nl_placeholder': 'Votre email', 'nl_btn': 'S\'abonner →',
        'nl_ok': 'Abonné! Vérifiez votre email.', 'nl_exists': 'Déjà abonné!', 'nl_err': 'Erreur - réessayez',
        'loading': 'Chargement...', 'province': 'Province', 'node': 'Noeud de données',
    },
    'es': {
        'lang': 'es',
        'nav_data': 'Datos', 'nav_news': 'Noticias', 'nav_api': 'API', 'nav_alerts': 'Alertas',
        'meta_desc': 'Anomalías meteorológicas en tiempo real para {city} ({country}). Z-Score, HDD/CDD, viento y humedad. Datos NASA POWER 25 años. WeatherArb.',
        'title_suffix': 'Inteligencia Meteorológica | WeatherArb',
        'label_zscore': 'Z-Score', 'label_score': 'Score', 'label_temp': 'Temperatura',
        'label_humidity': 'Humedad', 'label_wind': 'Viento', 'label_hdd': 'HDD hoy',
        'label_cdd': 'CDD hoy', 'label_hdd_delta': 'Delta HDD', 'label_analysis': 'Análisis WeatherArb',
        'label_hdd_sub': 'grados-día calefacción', 'label_cdd_sub': 'grados-día refrigeración',
        'label_delta_sub': 'vs histórico', 'label_temp_sub': 'actual', 'label_hum_sub': 'relativa',
        'label_wind_sub': 'km/h', 'label_score_sub': '0-10', 'label_zscore_sub': 'vs media 25 años',
        'methodology_title': 'Metodología',
        'methodology_text': 'WeatherArb calcula Z-Score, HDD y CDD contra la baseline NASA POWER 25 años para {city} ({lat}°N, {lon}°E). Norma EN ISO 15927.',
        'sector_title': 'Sectores Impactados',
        'sector_agr': 'Agricultura', 'sector_log': 'Logística', 'sector_ene': 'Energía',
        'sector_agr_ok': 'Condiciones agronómicas normales', 'sector_agr_warn': 'Alto riesgo de estrés hídrico',
        'sector_log_ok': 'Condiciones óptimas para logística', 'sector_log_warn': 'Condiciones adversas para transporte',
        'sector_ene_ok': 'Demanda energética normal', 'sector_ene_heat': 'Alta demanda de calefacción',
        'sector_ene_cool': 'Alta demanda de refrigeración',
        'nl_title': 'Alerta Intelligence para {city}',
        'nl_sub': 'Z-Score, HDD/CDD y anomalías meteorológicas para {city} en tu bandeja de entrada. Gratis.',
        'nl_placeholder': 'Tu email', 'nl_btn': 'Suscribirse →',
        'nl_ok': 'Suscrito! Comprueba tu email.', 'nl_exists': 'Ya suscrito!', 'nl_err': 'Error - inténtalo de nuevo',
        'loading': 'Cargando...', 'province': 'Provincia', 'node': 'Nodo de datos',
    },
}

# Lingua per country code
CC_LANG = {
    'it':'it', 'de':'de', 'fr':'fr', 'es':'es', 'gb':'en',
    'se':'en', 'nl':'en', 'pl':'en', 'at':'de', 'ch':'de',
    'be':'fr', 'pt':'en', 'dk':'en', 'no':'en',
    'gr':'en', 'hr':'en', 'cz':'en', 'hu':'en', 'ro':'en',
    'fi':'en', 'si':'en', 'sk':'en', 'rs':'en'
}

API = 'https://api.weatherarb.com'

with open('data/province_coords.json') as f:
    raw = json.load(f)
provinces = raw['province'] if 'province' in raw else raw

ok = 0
for c in provinces:
    name = c.get('nome','')
    country = c.get('country','Italy')
    cc = CC_MAP.get(country, 'it')
    lat = c.get('lat', 45.0)
    lon = c.get('lon', 10.0)
    slug = sl(name)
    country_label = LABEL.get(cc, cc.upper())

    lang_key = CC_LANG.get(cc, 'en')
    t = T.get(lang_key, T['en'])

    d = Path('data/website') / cc / slug
    d.mkdir(parents=True, exist_ok=True)
    p = d / 'index.html'

    meta_desc = t['meta_desc'].format(city=name, country=country_label)
    title = f"{name} {t['title_suffix']}"
    method = t['methodology_text'].format(city=name, lat=round(lat,2), lon=round(lon,2))
    nl_title = t['nl_title'].format(city=name)
    nl_sub = t['nl_sub'].format(city=name)
    city_safe = name.replace('"','').replace("'","")

    css = (
        '*{box-sizing:border-box;margin:0;padding:0}'
        'body{background:#040608;color:#c8d6e5;font-family:-apple-system,sans-serif;min-height:100vh}'
        '.hdr{border-bottom:1px solid #141920;padding:14px 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:10;background:rgba(4,6,8,.95);backdrop-filter:blur(12px)}'
        '.logo{font-size:13px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:#c8d6e5;text-decoration:none}.logo span{color:#3b82f6}'
        '.nav a{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:#4a5568;text-decoration:none;margin-left:16px}'
        '.hero{max-width:1100px;margin:0 auto;padding:48px 24px 32px}'
        '.bc{font-size:11px;text-transform:uppercase;letter-spacing:.15em;color:#4a5568;margin-bottom:12px}.bc a{color:#4a5568;text-decoration:none}'
        'h1{font-size:clamp(32px,5vw,56px);font-weight:800;letter-spacing:-.02em;line-height:1;color:#fff;margin-bottom:8px}'
        '.cmeta{font-size:12px;color:#4a5568;letter-spacing:.08em;text-transform:uppercase}.cmeta span{color:#3b82f6}'
        '.main{max-width:1100px;margin:0 auto;padding:0 24px 80px}'
        '.panel{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:1px;background:#141920;border:1px solid #141920;border-radius:12px;overflow:hidden;margin-bottom:24px}'
        '.pcell{background:#0a0d12;padding:16px 18px}'
        '.plabel{font-size:10px;text-transform:uppercase;letter-spacing:.15em;color:#4a5568;margin-bottom:6px}'
        '.pval{font-size:19px;font-weight:700;line-height:1.2}'
        '.psub{font-size:10px;color:#4a5568;margin-top:4px}'
        '.energy-row{grid-column:1/-1;background:#0a0d12;border-top:1px solid #141920;padding:16px 18px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px}'
        '.energy-label{font-size:10px;text-transform:uppercase;letter-spacing:.12em;color:#4a5568;margin-bottom:4px}'
        '.energy-val{font-size:17px;font-weight:700}'
        '.energy-sub{font-size:10px;color:#4a5568;margin-top:2px}'
        '.analysis-bar{grid-column:1/-1;background:#0a0d12;padding:14px 18px;border-top:1px solid #141920}'
        '.alabel{font-size:10px;text-transform:uppercase;letter-spacing:.15em;color:#4a5568;margin-bottom:4px}'
        '.aval{font-size:15px;font-weight:700;color:#3b82f6}'
        '.mbox{background:#0a0d12;border:1px solid #141920;border-radius:12px;padding:24px;margin-bottom:24px}'
        '.stitle{font-size:11px;text-transform:uppercase;letter-spacing:.2em;color:#4a5568;margin-bottom:16px;padding-bottom:10px;border-bottom:1px solid #141920}'
        '.sectors{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:24px}'
        '.sector{background:#0a0d12;border:1px solid #141920;border-radius:10px;padding:16px}'
        '.sector-icon{font-size:18px;margin-bottom:6px}'
        '.sector-name{font-size:12px;font-weight:700;color:#fff;margin-bottom:4px;text-transform:uppercase;letter-spacing:.08em}'
        '.sector-status{font-size:11px;color:#4a5568;line-height:1.4}'
        '.nl-box{background:linear-gradient(135deg,rgba(59,130,246,.08),rgba(16,185,129,.05));border:1px solid rgba(59,130,246,.2);border-radius:12px;padding:24px;margin-bottom:24px}'
        '.nl-title{font-size:15px;font-weight:700;color:#fff;margin-bottom:8px}'
        '.nl-sub{font-size:13px;color:#c8d6e5;line-height:1.6;margin-bottom:14px}'
        '.nl-row{display:flex;gap:8px;flex-wrap:wrap}'
        '.nl-input{flex:1;min-width:180px;background:rgba(255,255,255,.05);border:1px solid #1e2d3d;border-radius:8px;padding:10px 14px;color:#c8d6e5;font-size:13px;outline:none}'
        '.nl-btn{background:#3b82f6;color:#fff;border:none;border-radius:8px;padding:10px 20px;font-size:13px;font-weight:700;cursor:pointer}'
        '.nl-msg{display:none;font-size:13px;margin-top:10px;padding:8px;border-radius:6px}'
        '.ftr{border-top:1px solid #141920;padding:24px;text-align:center;font-size:11px;color:#4a5568}'
        '.ftr a{color:#4a5568;text-decoration:none}'
    )

    nl_ok = t['nl_ok']
    nl_exists = t['nl_exists']
    nl_err = t['nl_err']

    nl_js = (
        'function nlsub(){'
        f'var e=document.getElementById("nle").value.trim();'
        f'var m=document.getElementById("nlm");'
        f'if(!e||e.indexOf("@")<0){{m.style.display="block";m.style.background="rgba(239,68,68,.1)";m.style.color="#ef4444";m.textContent="{nl_err}";return;}}'
        f'fetch("{API}/api/newsletter/subscribe?email="+encodeURIComponent(e)+"&city={city_safe}&country_code={cc}",{{method:"POST"}})'
        f'.then(function(r){{return r.json();}})'
        f'.then(function(d){{'
        f'document.getElementById("nl-row").style.display="none";'
        f'm.style.display="block";m.style.background="rgba(16,185,129,.1)";m.style.color="#10b981";'
        f'm.textContent=d.status==="already_subscribed"?"{nl_exists}":"{nl_ok}";'
        f'}}).catch(function(){{m.style.display="block";m.style.background="rgba(239,68,68,.1)";m.style.color="#ef4444";m.textContent="{nl_err}";}});}}'
    )

    pulse_js = (
        f'function updateSectors(sc,hdd,cdd,wind,hum){{'
        f'var agr=document.getElementById("sector-agr");'
        f'var log=document.getElementById("sector-log");'
        f'var ene=document.getElementById("sector-ene");'
        f'if(agr){{agr.textContent=(hum>80||hum<30)?"{t["sector_agr_warn"]}":"{t["sector_agr_ok"]}";  }}'
        f'if(log){{log.textContent=(wind>50||sc>7)?"{t["sector_log_warn"]}":"{t["sector_log_ok"]}";  }}'
        f'if(ene){{ene.textContent=(hdd>5)?"{t["sector_ene_heat"]}":(cdd>5)?"{t["sector_ene_cool"]}":"{t["sector_ene_ok"]}"; }}'
        f'}}'
        f'async function loadPulse(){{'
        f'try{{'
        f'var r=await fetch("{API}/api/v1/pulse/{slug}");'
        f'var d=await r.json();'
        f'var w=d.weather||{{}};'
        f'var z=w.z_score||0;var sc=d.signal?d.signal.score:0;'
        f'var t2=w.temperature_c;var hum=w.humidity_pct;var wind=w.wind_kmh;'
        f'var hdd=w.hdd;var cdd=w.cdd;var hdd_delta=w.hdd_delta;'
        f'var lbl=w.anomaly_label||w.anomaly_level||"";'
        f'var col=sc>=7?"#ef4444":sc>=5?"#f97316":sc>=3?"#f59e0b":"#10b981";'
        f'var pz=document.getElementById("pz");'
        f'var psc=document.getElementById("psc");'
        f'var pt=document.getElementById("pt");'
        f'var phum=document.getElementById("phum");'
        f'var pwind=document.getElementById("pwind");'
        f'var phdd=document.getElementById("phdd");'
        f'var pcdd=document.getElementById("pcdd");'
        f'var phdd_delta=document.getElementById("phdd_delta");'
        f'var plbl=document.getElementById("plbl");'
        f'if(pz){{pz.textContent=(z>=0?"+":"")+z.toFixed(2)+"s";pz.style.color=col;}}'
        f'if(psc){{psc.textContent=sc.toFixed(1)+"/10";psc.style.color=col;}}'
        f'if(pt&&t2!=null){{pt.textContent=t2.toFixed(1)+"C";}}'
        f'if(phum&&hum!=null){{phum.textContent=hum+"%";}}'
        f'if(pwind&&wind!=null){{pwind.textContent=wind+" kmh";}}'
        f'if(phdd&&hdd!=null){{phdd.textContent=hdd.toFixed(1)+" GG";}}'
        f'if(pcdd&&cdd!=null){{pcdd.textContent=cdd.toFixed(1)+" GG";}}'
        f'if(phdd_delta&&hdd_delta!=null){{'
        f'phdd_delta.textContent=(hdd_delta>=0?"+":"")+hdd_delta.toFixed(1)+" GG";'
        f'phdd_delta.style.color=hdd_delta>2?"#ef4444":hdd_delta<-2?"#10b981":"#f59e0b";}}'
        f'if(plbl&&lbl){{plbl.textContent=lbl;plbl.style.color=col;}}'
        f'updateSectors(sc,hdd||0,cdd||0,wind||0,hum||50);'
        f'}}catch(e){{console.warn("pulse unavailable");}}}}'
        f'loadPulse();setInterval(loadPulse,3600000);'
    )

    html = (
        f'<!DOCTYPE html><html lang="{t["lang"]}">'
        f'<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{title}</title>'
        f'<meta name="description" content="{meta_desc}">'
        f'<link rel="canonical" href="https://weatherarb.com/{cc}/{slug}/">'
        f'<style>{css}</style></head>'
        f'<body>'
        f'<header class="hdr">'
        f'<a href="/" class="logo">Weather<span>Arb</span></a>'
        f'<nav class="nav">'
        f'<a href="/data/">{t["nav_data"]}</a>'
        f'<a href="/news/">{t["nav_news"]}</a>'
        f'<a href="/api.html">{t["nav_api"]}</a>'
        f'<a href="/alerts.html">{t["nav_alerts"]}</a>'
        f'</nav></header>'
        f'<div class="hero">'
        f'<div class="bc"><a href="/">WeatherArb</a> / <a href="/{cc}/">{country_label}</a> / {name}</div>'
        f'<h1>{name}</h1>'
        f'<p class="cmeta">{country_label} &middot; <span>{round(lat,2)}&deg;N {round(lon,2)}&deg;E</span> &middot; NASA POWER 25y</p>'
        f'</div>'
        f'<main class="main">'
        f'<div class="panel">'
        f'<div class="pcell"><div class="plabel">{t["label_zscore"]}</div><div class="pval" id="pz" style="color:#10b981">...</div><div class="psub">{t["label_zscore_sub"]}</div></div>'
        f'<div class="pcell"><div class="plabel">{t["label_score"]}</div><div class="pval" id="psc">...</div><div class="psub">{t["label_score_sub"]}</div></div>'
        f'<div class="pcell"><div class="plabel">{t["label_temp"]}</div><div class="pval" id="pt">...</div><div class="psub">{t["label_temp_sub"]}</div></div>'
        f'<div class="pcell"><div class="plabel">{t["label_humidity"]}</div><div class="pval" id="phum">...</div><div class="psub">{t["label_hum_sub"]}</div></div>'
        f'<div class="pcell"><div class="plabel">{t["label_wind"]}</div><div class="pval" id="pwind">...</div><div class="psub">{t["label_wind_sub"]}</div></div>'
        f'<div class="energy-row">'
        f'<div><div class="energy-label">{t["label_hdd"]}</div><div class="energy-val" id="phdd">...</div><div class="energy-sub">{t["label_hdd_sub"]}</div></div>'
        f'<div><div class="energy-label">{t["label_cdd"]}</div><div class="energy-val" id="pcdd">...</div><div class="energy-sub">{t["label_cdd_sub"]}</div></div>'
        f'<div><div class="energy-label">{t["label_hdd_delta"]}</div><div class="energy-val" id="phdd_delta">...</div><div class="energy-sub">{t["label_delta_sub"]}</div></div>'
        f'</div>'
        f'<div class="analysis-bar"><div class="alabel">{t["label_analysis"]}</div><div class="aval" id="plbl">{t["loading"]}</div></div>'
        f'</div>'
        f'<div class="stitle">{t["sector_title"]}</div>'
        f'<div class="sectors">'
        f'<div class="sector"><div class="sector-icon">🌾</div><div class="sector-name">{t["sector_agr"]}</div><div class="sector-status" id="sector-agr">{t["loading"]}</div></div>'
        f'<div class="sector"><div class="sector-icon">🚛</div><div class="sector-name">{t["sector_log"]}</div><div class="sector-status" id="sector-log">{t["loading"]}</div></div>'
        f'<div class="sector"><div class="sector-icon">⚡</div><div class="sector-name">{t["sector_ene"]}</div><div class="sector-status" id="sector-ene">{t["loading"]}</div></div>'
        f'</div>'
        f'<div class="mbox"><div class="stitle">{t["methodology_title"]}</div>'
        f'<p style="font-size:13px;color:#4a5568;line-height:1.6">{method}</p></div>'
        f'<div class="nl-box">'
        f'<div class="nl-title">{nl_title}</div>'
        f'<div class="nl-sub">{nl_sub}</div>'
        f'<div class="nl-row" id="nl-row">'
        f'<input id="nle" class="nl-input" type="email" placeholder="{t["nl_placeholder"]}" onkeydown="if(event.key===\'Enter\')nlsub()">'
        f'<button class="nl-btn" onclick="nlsub()">{t["nl_btn"]}</button>'
        f'</div>'
        f'<div id="nlm" class="nl-msg"></div>'
        f'</div>'
        f'</main>'
        f'<footer class="ftr">'
        f'<a href="/">WeatherArb</a> &middot; <a href="/about.html">{t["methodology_title"]}</a> &middot; <a href="/pricing/">API Pro</a>'
        f'</footer>'
        f'<script>{nl_js}{pulse_js}</script>'
        f'</body></html>'
    )

    p.write_text(html, encoding='utf-8')
    ok += 1

print(f'Generati: {ok} landing multilingua')
