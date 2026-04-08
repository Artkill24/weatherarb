"""
WeatherArb — Scheduler automatico
Gira ogni ora: refresh pulse → genera articoli → aggiorna sito
"""

import time
import logging
import sys
import os
import json
import glob
import re
import shutil
from datetime import datetime

sys.path.insert(0, '.')
logging.basicConfig(level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

from google import genai
from core.ingestor import load_provinces, build_historical_baseline, OWMFetcher, build_weather_snapshot
from core.delta_calculator import build_pulse_json
from core.content_generator import generate_article, update_sitemap, update_rss
from core.telegram_alerts import send_alert, send_daily_summary

GEMINI_KEY = os.getenv('GEMINI_API_KEY', '')
OWM_KEY = os.getenv('OWM_API_KEY', '')
SCORE_THRESHOLD = 6.5   # Genera articolo sopra questa soglia
ALERT_THRESHOLD = 7.0   # Invia Telegram sopra questa soglia


def run_cycle():
    """Ciclo completo: pulse → articoli → site update."""
    logger.info("=== CICLO AVVIATO ===")
    
    gemini = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None
    fetcher = OWMFetcher(api_key=OWM_KEY, use_mock=(not OWM_KEY))
    provinces = load_provinces()
    
    new_articles = []
    alerts_sent = []
    
    for prov in provinces:
        try:
            snapshot = build_weather_snapshot(prov, fetcher)
            baseline = build_historical_baseline(prov)
            pulse = build_pulse_json(prov, snapshot, baseline)
            
            score = pulse['arbitrage_score']['score']
            provincia = prov['nome']
            
            # Alert Telegram
            if score >= ALERT_THRESHOLD:
                sent = send_alert(pulse)
                if sent:
                    alerts_sent.append(provincia)
                    logger.info(f"🔔 Alert: {provincia} score={score:.1f}")
            
            # Genera articolo
            if score >= SCORE_THRESHOLD:
                # Evita duplicati — controlla se articolo oggi esiste già
                today = datetime.now().strftime('%Y-%m-%d')
                slug_check = f"data/blog_posts/{today}-*{provincia.lower().replace(' ','-')}*"
                if not glob.glob(slug_check):
                    article = generate_article(pulse, gemini_client=gemini)
                    new_articles.append(article)
                    logger.info(f"📝 Articolo: {provincia} score={score:.1f}")
                    
        except Exception as e:
            logger.warning(f"Errore {prov['nome']}: {e}")
        
        time.sleep(0.5)  # Rate limit OWM
    
    # Aggiorna sitemap + RSS
    if new_articles:
        all_articles = []
        for f in sorted(glob.glob('data/blog_posts/*.json'), reverse=True)[:50]:
            with open(f) as fp:
                all_articles.append(json.load(fp))
        
        update_sitemap(all_articles)
        update_rss(all_articles)
        _update_homepage(all_articles[:3])
        logger.info(f"✅ {len(new_articles)} nuovi articoli, sito aggiornato")
    
    logger.info(f"=== CICLO COMPLETATO | Articoli: {len(new_articles)} | Alert: {len(alerts_sent)} ===")
    return new_articles, alerts_sent


def _update_homepage(articles):
    """Aggiorna le card Intelligence Reports nella homepage."""
    if not articles:
        return
    
    widget = """  <div class="regions-section" style="background:white;padding:60px 48px;max-width:100%">
    <div style="max-width:1200px;margin:0 auto">
      <div class="section-label">Latest Intelligence Reports</div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:20px">"""

    for art in articles:
        flag = "🇩🇪" if "München" in art.get('provincia','') else "🇮🇹"
        color = "#ef4444" if art.get('anomaly_level') == 'CRITICAL' else "#f97316"
        preview = art['body'][:130].replace('\n',' ').replace('"',"'").strip()
        widget += f"""
        <a href="/news/{art['slug']}/" style="text-decoration:none;color:inherit;background:var(--paper);border-radius:16px;padding:24px;border:1px solid var(--mist);display:block">
          <div style="font-size:11px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:{color};margin-bottom:12px">{flag} {art.get('anomaly_level','UNUSUAL')} · {art.get('evento','').replace('_',' ')}</div>
          <div style="font-family:'Instrument Serif',serif;font-size:18px;line-height:1.3;margin-bottom:12px;color:#0f1117">{art['title'][:75]}{'...' if len(art['title'])>75 else ''}</div>
          <div style="font-size:13px;color:#6b7280;margin-bottom:16px;line-height:1.6">{preview}...</div>
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span style="font-size:12px;color:#2563eb;font-weight:500">Leggi report →</span>
            <span style="font-size:11px;color:#9ca3af">{art['timestamp'][:10]}</span>
          </div>
        </a>"""

    widget += "\n      </div>\n    </div>\n  </div>"

    try:
        homepage = open('data/website/index.html').read()
        homepage = re.sub(
            r'<!-- INTELLIGENCE REPORTS -->.*?<!-- END INTELLIGENCE REPORTS -->',
            '<!-- INTELLIGENCE REPORTS -->\n' + widget + '\n<!-- END INTELLIGENCE REPORTS -->',
            homepage, flags=re.DOTALL
        )
        open('data/website/index.html', 'w').write(homepage)
        
        # Zippa e copia automaticamente
        import subprocess
        subprocess.run(['zip', '-r', 'website_auto.zip', 'data/website/'], 
                      capture_output=True)
        shutil.copy('website_auto.zip', '/mnt/c/Users/Saad/Downloads/website_auto.zip')
        logger.info("📦 website_auto.zip pronto in Downloads")
    except Exception as e:
        logger.warning(f"Homepage update failed: {e}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true', help='Esegui una volta sola')
    parser.add_argument('--interval', type=int, default=3600, help='Intervallo in secondi (default: 3600)')
    args = parser.parse_args()

    if args.once:
        run_cycle()
    else:
        logger.info(f"Scheduler avviato — ciclo ogni {args.interval}s")
        while True:
            run_cycle()
            logger.info(f"Prossimo ciclo tra {args.interval//60} minuti...")
            time.sleep(args.interval)
