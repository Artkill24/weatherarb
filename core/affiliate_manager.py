"""
WeatherArb — Affiliate Manager
Gestisce link Awin (primary) e Amazon (fallback).
Cookie window: Awin 30gg vs Amazon 24h — vantaggio enorme per pre-event.
"""

import os
import logging
import requests
from urllib.parse import quote

logger = logging.getLogger(__name__)

AWIN_PUBLISHER_ID = os.getenv("AWIN_PUBLISHER_ID", "")
AMAZON_TAG_IT = "weatherarb0f-21"
AMAZON_TAG_DE = "weatherarb-21"
AMAZON_TAG_ES = "weatherarb04-21"
AMAZON_TAG_FR = "weatherarb08-21"

# Merchant Awin Italia — aggiungi i tuoi dopo registrazione
AWIN_MERCHANTS = {
    "IT": {
        "leroymerlin": {"id": "12543", "search": "https://www.leroymerlin.it/ricerca?q={}"},
        "mediaworld":  {"id": "15321", "search": "https://www.mediaworld.it/search?query={}"},
        "decathlon":   {"id": "11422", "search": "https://www.decathlon.it/search?Ntt={}"},
        "unieuro":     {"id": "14521", "search": "https://www.unieuro.it/online/search?q={}"},
    },
    "DE": {
        "mediamarkt":  {"id": "14300", "search": "https://www.mediamarkt.de/de/search.html?query={}"},
        "obi":         {"id": "13200", "search": "https://www.obi.de/suche/{}"},
    }
}

# Mapping evento → query di ricerca per merchant
EVENT_QUERIES = {
    "Heavy_Rain":     {"leroymerlin": "deumidificatore portatile", "mediaworld": "deumidificatore"},
    "Flooding_Risk":  {"leroymerlin": "pompa immersione", "mediaworld": "pompa idraulica"},
    "Heat_Wave":      {"mediaworld": "ventilatore silenzioso", "unieuro": "ventilatore tower"},
    "Snowfall":       {"leroymerlin": "catene neve auto", "decathlon": "catene neve"},
    "Ice_Risk":       {"leroymerlin": "antigelo spray", "decathlon": "antigelo"},
    "Storm":          {"mediaworld": "torcia led emergenza", "unieuro": "power bank"},
    "Pollen_High":    {"mediaworld": "purificatore aria hepa", "unieuro": "purificatore aria"},
    "Cold_Snap":      {"mediaworld": "termoventilatore", "unieuro": "stufa elettrica"},
}

# ASIN Amazon come fallback per ogni evento
AMAZON_FALLBACK = {
    "Heavy_Rain":    "B07HGFBXT8",  # De'Longhi Tasciugo
    "Flooding_Risk": "B07HGFBXT8",
    "Heat_Wave":     "B01891LZBY",  # Rowenta Silence Extreme
    "Snowfall":      "B000UNKGGU",  # König catene neve
    "Ice_Risk":      "B000UNKGGU",
    "Storm":         "B01891LZBY",
    "Pollen_High":   "B01891LZBY",
    "Cold_Snap":     "B01891LZBY",
}


class AffiliateManager:
    """
    Gestore ibrido Awin + Amazon.
    Priorità: Awin (30gg cookie) → Amazon (24h cookie)
    """

    def __init__(self, publisher_id: str = ""):
        self.publisher_id = publisher_id or AWIN_PUBLISHER_ID

    def get_best_link(self, evento: str, provincia: str,
                       country: str = "IT") -> dict:
        """
        Ritorna il miglior link affiliato per evento + provincia.
        Tenta Awin prima, fallback Amazon.
        """
        # Prova Awin
        awin_result = self._try_awin(evento, provincia, country)
        if awin_result:
            return awin_result

        # Fallback Amazon
        return self._amazon_fallback(evento, provincia, country)

    def _try_awin(self, evento: str, provincia: str, country: str) -> dict:
        """Tenta di costruire link Awin per il merchant più rilevante."""
        if not self.publisher_id:
            logger.debug("Awin publisher ID non configurato — skip")
            return {}

        queries = EVENT_QUERIES.get(evento, {})
        merchants = AWIN_MERCHANTS.get(country, {})

        for merchant_name, query in queries.items():
            if merchant_name not in merchants:
                continue

            merchant = merchants[merchant_name]
            search_url = merchant["search"].format(quote(query))

            # Genera deep link Awin verso la pagina di ricerca del merchant
            subid = f"{provincia.lower()}_{evento.lower()}"
            awin_link = (
                f"https://www.awin1.com/cread.php"
                f"?awinmid={merchant['id']}"
                f"&awinaffid={self.publisher_id}"
                f"&clickref={subid}"
                f"&ued={quote(search_url, safe='')}"
            )

            return {
                "network": "awin",
                "merchant": merchant_name,
                "url": awin_link,
                "destination": search_url,
                "cookie_days": 30,
                "commission_type": "fixed_pct",
                "subid": subid,
            }

        return {}

    def _amazon_fallback(self, evento: str, provincia: str,
                          country: str) -> dict:
        """Fallback Amazon con ASIN predefinito."""
        tag_map = {"IT": AMAZON_TAG_IT, "DE": AMAZON_TAG_DE,
                   "ES": AMAZON_TAG_ES, "FR": AMAZON_TAG_FR}
        tag = tag_map.get(country, AMAZON_TAG_IT)
        asin = AMAZON_FALLBACK.get(evento, "B01891LZBY")

        from datetime import date
        subid = f"{provincia.lower()}_{evento.lower()}_{date.today().strftime('%Y%m%d')}"

        url = (f"https://www.amazon.it/dp/{asin}"
               f"?tag={tag}&ascsubtag={subid}&linkCode=ogi")

        return {
            "network": "amazon",
            "merchant": "amazon",
            "url": url,
            "asin": asin,
            "cookie_days": 1,
            "commission_type": "pct_of_sale",
            "subid": subid,
        }

    def build_awin_link(self, merchant_name: str, destination_url: str,
                         provincia: str, evento: str,
                         country: str = "IT") -> str:
        """Costruisce link Awin da URL prodotto specifico."""
        merchants = AWIN_MERCHANTS.get(country, {})
        if merchant_name not in merchants:
            return destination_url

        merchant = merchants[merchant_name]
        subid = f"{provincia.lower()}_{evento.lower()}"

        return (
            f"https://www.awin1.com/cread.php"
            f"?awinmid={merchant['id']}"
            f"&awinaffid={self.publisher_id}"
            f"&clickref={subid}"
            f"&ued={quote(destination_url, safe='')}"
        )


# Istanza globale
affiliate_manager = AffiliateManager()
