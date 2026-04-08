"""
The Pulse — Product Mapper
Mappa eventi meteo a prodotti affiliate usando ChromaDB (vettoriale).
Fallback su dizionario statico se ChromaDB non disponibile.
"""

import csv
import logging
from pathlib import Path
from typing import List, Optional

from config import PRODUCTS_FILE, CHROMA_DIR, EVENT_PRODUCT_MAP

logger = logging.getLogger(__name__)


class ProductMapper:
    """
    Mappa semantica evento → prodotti usando ChromaDB.
    Se ChromaDB non è disponibile, usa fallback dizionario.
    """

    def __init__(self, use_chroma: bool = True):
        self.use_chroma = use_chroma
        self.collection = None
        self.products_df = self._load_csv()

        if use_chroma:
            self._init_chroma()

    def _load_csv(self) -> List[dict]:
        """Carica products_seed.csv."""
        products = []
        try:
            with open(PRODUCTS_FILE, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    products.append(row)
            logger.info(f"Loaded {len(products)} products from CSV")
        except FileNotFoundError:
            logger.warning(f"Products file not found: {PRODUCTS_FILE}")
        return products

    def _init_chroma(self):
        """Inizializza ChromaDB e popola la collection."""
        try:
            import chromadb
            from chromadb.utils import embedding_functions

            Path(CHROMA_DIR).mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=CHROMA_DIR)

            # Usa embedding function di default (sentence-transformers)
            # In produzione: sostituire con OpenAI embeddings per qualità superiore
            ef = embedding_functions.DefaultEmbeddingFunction()

            self.collection = client.get_or_create_collection(
                name="products",
                embedding_function=ef,
                metadata={"hnsw:space": "cosine"}
            )

            # Popola solo se vuota
            if self.collection.count() == 0:
                self._seed_chroma()
                logger.info(f"ChromaDB seeded with {len(self.products_df)} products")
            else:
                logger.info(f"ChromaDB loaded with {self.collection.count()} products")

        except ImportError:
            logger.warning("ChromaDB not available, using fallback mapping")
            self.use_chroma = False
        except Exception as e:
            logger.warning(f"ChromaDB init failed: {e}, using fallback")
            self.use_chroma = False

    def _seed_chroma(self):
        """Inserisce i prodotti in ChromaDB con embedding sulla descrizione semantica."""
        if not self.products_df or not self.collection:
            return

        docs, ids, metas = [], [], []
        for p in self.products_df:
            # Documento per embedding: combinazione nome + descrizione + eventi
            doc = (
                f"{p['nome']}. {p['descrizione_semantica']}. "
                f"Evento: {p['evento_primario']}. {p.get('evento_secondario', '')}"
            )
            docs.append(doc)
            ids.append(p["id"])
            metas.append({
                "categoria": p["categoria"],
                "evento_primario": p["evento_primario"],
                "urgency_tier": p["urgency_tier"],
                "prezzo_medio": float(p["prezzo_medio"]),
                "commissione_pct": float(p["commissione_pct"]),
                "amazon_tag": p["amazon_tag"],
            })

        self.collection.add(documents=docs, ids=ids, metadatas=metas)

    def get_products_for_event(
        self,
        event_type: str,
        event_description: str = "",
        n_results: int = 5,
    ) -> List[dict]:
        """
        Trova i prodotti più rilevanti per un tipo di evento.
        Usa ChromaDB se disponibile, altrimenti fallback dizionario.
        """
        if self.use_chroma and self.collection:
            return self._chroma_search(event_type, event_description, n_results)
        else:
            return self._fallback_search(event_type, n_results)

    def _chroma_search(
        self,
        event_type: str,
        event_description: str,
        n_results: int,
    ) -> List[dict]:
        """Ricerca semantica su ChromaDB."""
        try:
            query = f"Evento meteo: {event_type}. {event_description}"
            results = self.collection.query(
                query_texts=[query],
                n_results=min(n_results, self.collection.count()),
                include=["documents", "metadatas", "distances"],
            )

            products = []
            for i, meta in enumerate(results["metadatas"][0]):
                # Filtra risultati a bassa rilevanza (distanza coseno > 0.8)
                distance = results["distances"][0][i]
                if distance > 0.8:
                    continue

                products.append({
                    "id": results["ids"][0][i],
                    "categoria": meta["categoria"],
                    "amazon_tag": meta["amazon_tag"],
                    "urgency_tier": meta["urgency_tier"],
                    "prezzo_medio": meta["prezzo_medio"],
                    "commissione_pct": meta["commissione_pct"],
                    "relevance_score": round(1 - distance, 3),
                })

            # Ordina per urgency_tier poi relevance
            tier_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
            products.sort(key=lambda p: (
                tier_order.get(p["urgency_tier"], 4),
                -p["relevance_score"]
            ))

            return products[:n_results]

        except Exception as e:
            logger.warning(f"ChromaDB search failed: {e}, using fallback")
            return self._fallback_search(event_type, n_results)

    def _fallback_search(self, event_type: str, n_results: int) -> List[dict]:
        """Fallback: ricerca per corrispondenza esatta sul dizionario statico."""
        categories = EVENT_PRODUCT_MAP.get(event_type, [])
        products = []

        for p in self.products_df:
            if p["categoria"] in categories:
                products.append({
                    "id": p["id"],
                    "categoria": p["categoria"],
                    "amazon_tag": p["amazon_tag"],
                    "urgency_tier": p["urgency_tier"],
                    "prezzo_medio": float(p["prezzo_medio"]),
                    "commissione_pct": float(p["commissione_pct"]),
                    "relevance_score": 0.75,  # Score fisso per fallback
                })

        tier_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        products.sort(key=lambda p: tier_order.get(p["urgency_tier"], 4))
        return products[:n_results]

    def get_top_amazon_asins(self, event_type: str, n: int = 3) -> List[str]:
        """
        Ritorna i top ASIN/tag Amazon per un evento.
        Placeholder: in produzione usa PAAPI per ASIN reali.
        """
        products = self.get_products_for_event(event_type, n_results=n)
        return [p["amazon_tag"] for p in products]
