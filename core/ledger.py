"""
The Pulse — Weather-Product Ledger
Registra ogni "battito" del sistema per backtesting e predictive bidding.
Schema: evento → campagna → outcome → ROI reale

Flusso dati:
  Pulse-JSON → PulseLedger.record_pulse_event()
  Campagna lanciata → PulseLedger.record_campaign_start()
  Dati Taboola → PulseLedger.record_campaign_outcome()
  Query predittiva → PulseLedger.get_historical_roi()
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from config import LEDGER_DB

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────
# SCHEMA SQL
# ─────────────────────────────────────────────────

SCHEMA = """
-- Ogni valutazione del Pulse per una provincia
CREATE TABLE IF NOT EXISTS pulse_events (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp           TEXT NOT NULL,
    provincia           TEXT NOT NULL,
    regione             TEXT NOT NULL,
    cluster             TEXT NOT NULL,
    popolazione         INTEGER,

    -- Weather trigger
    event_type          TEXT NOT NULL,
    severity            REAL,
    anomaly_level       TEXT,
    z_score_primary     REAL,
    z_score_temp        REAL,
    z_score_rain        REAL,
    z_score_wind        REAL,
    delta_pct           TEXT,
    peak_expected_hours INTEGER,
    temp_current        REAL,
    temp_historical_avg REAL,
    rain_observed_mm    REAL,

    -- Scores
    arbitrage_score     REAL NOT NULL,
    confidence          REAL,
    actionable          INTEGER DEFAULT 0,   -- 0/1 boolean

    -- Action plan
    phase               TEXT,
    guardrail           TEXT,
    vertical            TEXT,
    budget_suggested    REAL,
    strategy            TEXT,

    -- Raw JSON per audit completo
    pulse_json          TEXT,

    -- Metadati
    engine_version      TEXT DEFAULT '0.1.0',
    data_sources        TEXT
);

-- Campagne lanciate a partire da un pulse_event
CREATE TABLE IF NOT EXISTS campaigns (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    pulse_event_id      INTEGER REFERENCES pulse_events(id),
    started_at          TEXT NOT NULL,

    -- Identificatori campagna
    platform            TEXT DEFAULT 'taboola',  -- taboola, outbrain, meta
    campaign_external_id TEXT,                   -- ID Taboola/Meta
    campaign_name       TEXT,

    -- Setup
    provincia           TEXT NOT NULL,
    event_type          TEXT NOT NULL,
    vertical            TEXT,
    product_category    TEXT,
    amazon_tag          TEXT,

    -- Budget
    budget_daily_eur    REAL,
    budget_total_eur    REAL,

    -- Copy info
    headline_variant    TEXT,   -- A/B/C label
    frame_emotivo       TEXT,   -- local_identity / urgency / solution
    landing_url         TEXT,

    -- Status
    status              TEXT DEFAULT 'active',  -- active, paused, completed
    ended_at            TEXT
);

-- Outcome giornaliero per ogni campagna (da API Taboola/Meta)
CREATE TABLE IF NOT EXISTS campaign_outcomes (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id         INTEGER REFERENCES campaigns(id),
    date                TEXT NOT NULL,

    -- Metriche Taboola real-time (proxy metrics)
    impressions         INTEGER DEFAULT 0,
    clicks              INTEGER DEFAULT 0,
    ctr                 REAL,                    -- Click-Through Rate
    cpc_eur             REAL,                    -- Cost Per Click
    spend_eur           REAL DEFAULT 0,

    -- Landing page metrics
    lp_clicks           INTEGER DEFAULT 0,       -- Click su CTA Amazon
    lp_ctr              REAL,                    -- Landing Page CTR
    time_on_page_sec    REAL,                    -- Proxy qualità copy
    bounce_rate         REAL,

    -- Affiliate (con ritardo 24h)
    affiliate_clicks    INTEGER DEFAULT 0,
    affiliate_conversions INTEGER DEFAULT 0,
    affiliate_revenue_eur REAL DEFAULT 0,
    commission_eur      REAL DEFAULT 0,

    -- Computed
    roi                 REAL,                   -- (commission - spend) / spend
    cplp_eur            REAL,                   -- Cost Per LP Click

    -- Thompson Bandit state
    bandit_alpha        INTEGER DEFAULT 1,
    bandit_beta         INTEGER DEFAULT 1,
    bandit_score        REAL
);

-- Pattern storici aggregati (il vero "Librone degli Ordini")
-- Aggiornato ogni volta che una campagna si conclude
CREATE TABLE IF NOT EXISTS historical_patterns (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    updated_at          TEXT NOT NULL,

    -- Chiave del pattern (combinazione che identifica il "tipo di evento")
    cluster             TEXT NOT NULL,
    event_type          TEXT NOT NULL,
    month               INTEGER NOT NULL,         -- 1-12
    anomaly_level       TEXT NOT NULL,            -- UNUSUAL / EXTREME / CRITICAL
    vertical            TEXT NOT NULL,
    frame_emotivo       TEXT,

    -- Metriche aggregate (medie pesate su n_campaigns)
    n_campaigns         INTEGER DEFAULT 0,
    avg_roi             REAL,
    avg_ctr             REAL,
    avg_cplp_eur        REAL,
    avg_conversion_rate REAL,
    avg_spend_eur       REAL,
    avg_commission_eur  REAL,

    -- Saturation data
    avg_saturation_hours REAL,    -- Ore prima che il CTR cali del 35%
    avg_audience_size   INTEGER,

    -- Confidence del pattern
    pattern_confidence  REAL,     -- n_campaigns / (n_campaigns + 10) — formula Laplace

    UNIQUE(cluster, event_type, month, anomaly_level, vertical, frame_emotivo)
);

-- Guardrail log: ogni decisione di blocco viene tracciata
CREATE TABLE IF NOT EXISTS guardrail_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,
    provincia       TEXT NOT NULL,
    event_type      TEXT,
    anomaly_level   TEXT,
    product_blocked TEXT,
    decision        TEXT,   -- HARD_BLOCK / SOFT_BLOCK / APPROVED
    reason          TEXT
);

-- Indici per query veloci
CREATE INDEX IF NOT EXISTS idx_pulse_provincia ON pulse_events(provincia, timestamp);
CREATE INDEX IF NOT EXISTS idx_pulse_score ON pulse_events(arbitrage_score DESC);
CREATE INDEX IF NOT EXISTS idx_pulse_event ON pulse_events(event_type, anomaly_level);
CREATE INDEX IF NOT EXISTS idx_campaigns_provincia ON campaigns(provincia, event_type);
CREATE INDEX IF NOT EXISTS idx_patterns_key ON historical_patterns(cluster, event_type, month, anomaly_level);
CREATE INDEX IF NOT EXISTS idx_outcomes_campaign ON campaign_outcomes(campaign_id, date);
"""


# ─────────────────────────────────────────────────
# LEDGER CLASS
# ─────────────────────────────────────────────────

class PulseLedger:
    """
    Interfaccia al Weather-Product Ledger.
    Thread-safe tramite connessioni per-thread.
    """

    def __init__(self, db_path: str = LEDGER_DB):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info(f"Ledger initialized at {db_path}")

    @contextmanager
    def _conn(self):
        """Context manager per connessione SQLite."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")   # Write-Ahead Logging per concorrenza
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_db(self):
        """Crea le tabelle se non esistono."""
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    # ─────────────────────────────────────────────
    # WRITE OPERATIONS
    # ─────────────────────────────────────────────

    def record_pulse_event(self, pulse_json: Dict) -> int:
        """
        Registra un Pulse-JSON nel Ledger.
        Ritorna l'ID del record creato.
        """
        loc = pulse_json.get("location", {})
        trig = pulse_json.get("weather_trigger", {})
        arb = pulse_json.get("arbitrage_score", {})
        action = pulse_json.get("action_plan", {})
        deltas = {d["variable"]: d["z_score"] for d in pulse_json.get("delta_breakdown", [])}

        with self._conn() as conn:
            cursor = conn.execute("""
                INSERT INTO pulse_events (
                    timestamp, provincia, regione, cluster, popolazione,
                    event_type, severity, anomaly_level,
                    z_score_primary, z_score_temp, z_score_rain, z_score_wind,
                    delta_pct, peak_expected_hours,
                    temp_current, temp_historical_avg,
                    arbitrage_score, confidence, actionable,
                    phase, guardrail, vertical, budget_suggested, strategy,
                    pulse_json, engine_version, data_sources
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?,
                    ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?
                )
            """, (
                pulse_json.get("timestamp", datetime.utcnow().isoformat()),
                loc.get("provincia", ""),
                loc.get("regione", ""),
                loc.get("cluster", ""),
                loc.get("popolazione", 0),

                trig.get("type", ""),
                trig.get("severity", 0),
                trig.get("anomaly_level", ""),

                trig.get("z_score", 0),
                deltas.get("temperature", None),
                deltas.get("precipitation", None),
                deltas.get("wind", None),

                str(trig.get("delta_historical", "")),
                self._parse_lead_time(trig.get("peak_expected_in")),

                trig.get("current_temp_c"),
                trig.get("historical_avg_temp_c"),

                arb.get("score", 0),
                arb.get("confidence", 0),
                1 if arb.get("actionable") else 0,

                action.get("phase", ""),
                action.get("guardrail", ""),
                action.get("recommended_vertical", ""),
                action.get("budget_recommendation", {}).get("daily_eur", 0),
                action.get("budget_recommendation", {}).get("strategy", ""),

                json.dumps(pulse_json, ensure_ascii=False),
                pulse_json.get("meta", {}).get("engine_version", "0.1.0"),
                json.dumps(pulse_json.get("meta", {}).get("data_sources", [])),
            ))

            event_id = cursor.lastrowid

        logger.debug(f"Recorded pulse event {event_id} for {loc.get('provincia')} "
                     f"score={arb.get('score')}")
        return event_id

    def record_guardrail_decision(self, provincia: str, event_type: str,
                                   anomaly_level: str, product: str,
                                   decision: str, reason: str = ""):
        """Log ogni decisione del guardrail per audit."""
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO guardrail_log
                (timestamp, provincia, event_type, anomaly_level, product_blocked, decision, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.utcnow().isoformat(),
                provincia, event_type, anomaly_level, product, decision, reason
            ))

    def record_campaign_outcome(self, campaign_id: int, date: str,
                                 metrics: Dict) -> int:
        """Registra i dati giornalieri di una campagna."""
        roi = None
        if metrics.get("commission_eur") and metrics.get("spend_eur", 0) > 0:
            roi = (metrics["commission_eur"] - metrics["spend_eur"]) / metrics["spend_eur"]

        cplp = None
        if metrics.get("lp_clicks", 0) > 0 and metrics.get("spend_eur", 0) > 0:
            cplp = metrics["spend_eur"] / metrics["lp_clicks"]

        with self._conn() as conn:
            cursor = conn.execute("""
                INSERT INTO campaign_outcomes (
                    campaign_id, date,
                    impressions, clicks, ctr, cpc_eur, spend_eur,
                    lp_clicks, lp_ctr, time_on_page_sec, bounce_rate,
                    affiliate_clicks, affiliate_conversions,
                    affiliate_revenue_eur, commission_eur,
                    roi, cplp_eur,
                    bandit_alpha, bandit_beta
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                campaign_id, date,
                metrics.get("impressions", 0),
                metrics.get("clicks", 0),
                metrics.get("ctr"),
                metrics.get("cpc_eur"),
                metrics.get("spend_eur", 0),
                metrics.get("lp_clicks", 0),
                metrics.get("lp_ctr"),
                metrics.get("time_on_page_sec"),
                metrics.get("bounce_rate"),
                metrics.get("affiliate_clicks", 0),
                metrics.get("affiliate_conversions", 0),
                metrics.get("affiliate_revenue_eur", 0),
                metrics.get("commission_eur", 0),
                roi,
                cplp,
                metrics.get("bandit_alpha", 1),
                metrics.get("bandit_beta", 1),
            ))
            return cursor.lastrowid

    def update_historical_pattern(self, cluster: str, event_type: str,
                                   month: int, anomaly_level: str,
                                   vertical: str, frame_emotivo: str,
                                   roi: float, ctr: float, cplp: float,
                                   conversion_rate: float):
        """
        Aggiorna il pattern storico con i dati di una campagna conclusa.
        Usa media mobile ponderata per aggiornamento incrementale.
        """
        with self._conn() as conn:
            # Cerca pattern esistente
            row = conn.execute("""
                SELECT * FROM historical_patterns
                WHERE cluster=? AND event_type=? AND month=?
                  AND anomaly_level=? AND vertical=? AND frame_emotivo=?
            """, (cluster, event_type, month, anomaly_level, vertical, frame_emotivo)).fetchone()

            if row:
                n = row["n_campaigns"]
                # Media mobile: (vecchia_media * n + nuovo_valore) / (n + 1)
                new_roi = (row["avg_roi"] * n + roi) / (n + 1) if row["avg_roi"] else roi
                new_ctr = (row["avg_ctr"] * n + ctr) / (n + 1) if row["avg_ctr"] else ctr
                new_cplp = (row["avg_cplp_eur"] * n + cplp) / (n + 1) if row["avg_cplp_eur"] else cplp
                new_cr = (row["avg_conversion_rate"] * n + conversion_rate) / (n + 1) if row["avg_conversion_rate"] else conversion_rate
                new_n = n + 1
                confidence = new_n / (new_n + 10)  # Laplace smoothing

                conn.execute("""
                    UPDATE historical_patterns SET
                        updated_at=?, n_campaigns=?,
                        avg_roi=?, avg_ctr=?, avg_cplp_eur=?,
                        avg_conversion_rate=?, pattern_confidence=?
                    WHERE id=?
                """, (
                    datetime.utcnow().isoformat(), new_n,
                    new_roi, new_ctr, new_cplp, new_cr, confidence,
                    row["id"]
                ))
            else:
                # Primo record per questo pattern
                conn.execute("""
                    INSERT INTO historical_patterns (
                        updated_at, cluster, event_type, month, anomaly_level,
                        vertical, frame_emotivo, n_campaigns,
                        avg_roi, avg_ctr, avg_cplp_eur, avg_conversion_rate,
                        pattern_confidence
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
                """, (
                    datetime.utcnow().isoformat(),
                    cluster, event_type, month, anomaly_level,
                    vertical, frame_emotivo,
                    roi, ctr, cplp, conversion_rate,
                    1 / 11  # Prior con 1 campagna
                ))

    # ─────────────────────────────────────────────
    # READ OPERATIONS
    # ─────────────────────────────────────────────

    def get_historical_roi(self, cluster: str, event_type: str,
                            month: int, anomaly_level: str,
                            vertical: str) -> Optional[Dict]:
        """
        Query principale del Predictive Bidding.
        Ritorna ROI storico medio per configurare il bid iniziale.
        """
        with self._conn() as conn:
            row = conn.execute("""
                SELECT avg_roi, avg_ctr, avg_cplp_eur, avg_conversion_rate,
                       n_campaigns, pattern_confidence, frame_emotivo
                FROM historical_patterns
                WHERE cluster=? AND event_type=? AND month=?
                  AND anomaly_level=? AND vertical=?
                ORDER BY pattern_confidence DESC, avg_roi DESC
                LIMIT 1
            """, (cluster, event_type, month, anomaly_level, vertical)).fetchone()

            if row:
                return {
                    "avg_roi": row["avg_roi"],
                    "avg_ctr": row["avg_ctr"],
                    "avg_cplp_eur": row["avg_cplp_eur"],
                    "avg_conversion_rate": row["avg_conversion_rate"],
                    "n_campaigns": row["n_campaigns"],
                    "confidence": row["pattern_confidence"],
                    "best_frame": row["frame_emotivo"],
                }
        return None

    def get_province_history(self, provincia: str,
                              limit: int = 30) -> List[Dict]:
        """Storico eventi per una provincia — per drilldown dashboard."""
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT timestamp, event_type, anomaly_level, z_score_primary,
                       arbitrage_score, confidence, phase, guardrail,
                       temp_current, temp_historical_avg
                FROM pulse_events
                WHERE provincia=?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (provincia, limit)).fetchall()
            return [dict(r) for r in rows]

    def get_opportunity_volume(self, days: int = 30) -> Dict:
        """
        Volume di opportunità degli ultimi N giorni.
        KPI principale per validare il sistema.
        """
        with self._conn() as conn:
            total = conn.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN actionable=1 THEN 1 ELSE 0 END) as actionable,
                       AVG(arbitrage_score) as avg_score,
                       MAX(arbitrage_score) as max_score
                FROM pulse_events
                WHERE timestamp >= datetime('now', ?)
            """, (f"-{days} days",)).fetchone()

            by_event = conn.execute("""
                SELECT event_type, COUNT(*) as count,
                       AVG(arbitrage_score) as avg_score,
                       SUM(CASE WHEN actionable=1 THEN 1 ELSE 0 END) as actionable_count
                FROM pulse_events
                WHERE timestamp >= datetime('now', ?) AND actionable=1
                GROUP BY event_type
                ORDER BY count DESC
            """, (f"-{days} days",)).fetchall()

            top_province = conn.execute("""
                SELECT provincia, COUNT(*) as events,
                       AVG(arbitrage_score) as avg_score,
                       SUM(CASE WHEN actionable=1 THEN 1 ELSE 0 END) as opportunities
                FROM pulse_events
                WHERE timestamp >= datetime('now', ?)
                GROUP BY provincia
                ORDER BY opportunities DESC, avg_score DESC
                LIMIT 10
            """, (f"-{days} days",)).fetchall()

            return {
                "period_days": days,
                "total_evaluations": total["total"] if total else 0,
                "actionable_opportunities": total["actionable"] if total else 0,
                "avg_score": round(total["avg_score"], 2) if total and total["avg_score"] else 0,
                "max_score_seen": round(total["max_score"], 2) if total and total["max_score"] else 0,
                "by_event_type": [dict(r) for r in by_event],
                "top_province": [dict(r) for r in top_province],
            }

    def get_guardrail_stats(self) -> Dict:
        """Stats sui blocchi del guardrail — audit di sicurezza."""
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT decision, COUNT(*) as count, product_blocked
                FROM guardrail_log
                GROUP BY decision, product_blocked
                ORDER BY count DESC
            """).fetchall()
            return {"guardrail_decisions": [dict(r) for r in rows]}

    # ─────────────────────────────────────────────
    # UTILS
    # ─────────────────────────────────────────────

    def _parse_lead_time(self, value) -> Optional[int]:
        """Converte '42h' in 42."""
        if not value or value == "N/A":
            return None
        try:
            return int(str(value).replace("h", "").strip())
        except (ValueError, AttributeError):
            return None

    def get_db_stats(self) -> Dict:
        """Stats generali del database."""
        with self._conn() as conn:
            stats = {}
            for table in ["pulse_events", "campaigns", "campaign_outcomes",
                          "historical_patterns", "guardrail_log"]:
                count = conn.execute(
                    f"SELECT COUNT(*) as n FROM {table}"
                ).fetchone()["n"]
                stats[table] = count
            return stats
