"""
The Media Buyer — Bid Manager (Sprint 3)
Gestisce l'allocazione budget, i safety limits e il Kill Switch globale.
NON tocca mai le API Taboola senza passare per tutti i gate di sicurezza.

Architettura:
  Pulse-JSON → BidManager.evaluate() → BudgetAllocation
  BudgetAllocation → TaboolaPublisher.launch() [Sprint 3b]
  Watchdog → review_performance() → pause/scale/kill
"""

import json
import logging
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from config import LEDGER_DB, SCORE_THRESHOLD_ACTIONABLE, SCORE_THRESHOLD_AGGRESSIVE

logger = logging.getLogger(__name__)

GOVERNOR_DB = str(Path(LEDGER_DB).parent / "governor.db")


# ─────────────────────────────────────────────────
# SAFETY LIMITS (tutti modificabili via API, mai via codice in produzione)
# ─────────────────────────────────────────────────

@dataclass
class SafetyConfig:
    # Limiti globali
    daily_cap_global_eur: float = 50.0      # Hard limit giornaliero su tutto il sistema
    max_active_campaigns: int = 20           # Max campagne simultanee
    
    # Limiti per campagna
    cpc_max_eur: float = 0.15               # CPC massimo per click
    campaign_budget_min_eur: float = 5.0    # Budget minimo per campagna
    campaign_budget_max_eur: float = 50.0   # Budget massimo per campagna
    
    # Burn rate watchdog
    burn_rate_window_hours: int = 2          # Finestra di controllo
    burn_rate_max_pct: float = 0.40         # Max 40% del daily in 2h → pausa
    
    # Performance watchdog
    lpctr_min_threshold: float = 0.05       # Min 5% LP CTR dopo 100 click
    ctr_min_threshold: float = 0.005        # Min 0.5% CTR su Taboola
    min_clicks_before_review: int = 100     # Click minimi prima di valutare LPCTR
    
    # Kill switch
    kill_switch_active: bool = False        # Stato globale kill switch
    kill_switch_reason: str = ""


SAFETY = SafetyConfig()


# ─────────────────────────────────────────────────
# BUDGET ALLOCATION
# ─────────────────────────────────────────────────

@dataclass
class BudgetAllocation:
    """Allocazione budget per una singola provincia/evento."""
    provincia: str
    cluster: str
    event_type: str
    arbitrage_score: float
    confidence: float
    
    # Budget calcolato
    daily_budget_eur: float = 0.0
    cpc_target_eur: float = 0.0
    strategy: str = "HOLD"
    
    # Approvazione
    approved: bool = False
    block_reason: str = ""
    
    # Metadata
    pulse_event_id: Optional[int] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict:
        return {
            "provincia": self.provincia,
            "cluster": self.cluster,
            "event_type": self.event_type,
            "arbitrage_score": self.arbitrage_score,
            "daily_budget_eur": self.daily_budget_eur,
            "cpc_target_eur": self.cpc_target_eur,
            "strategy": self.strategy,
            "approved": self.approved,
            "block_reason": self.block_reason,
        }


@dataclass  
class SystemBudgetState:
    """Stato aggregato del sistema in un momento dato."""
    total_spent_today_eur: float = 0.0
    total_budget_allocated_eur: float = 0.0
    active_campaigns: int = 0
    paused_campaigns: int = 0
    kill_switch_active: bool = False
    remaining_daily_budget_eur: float = 0.0
    burn_rate_2h_pct: float = 0.0


# ─────────────────────────────────────────────────
# GOVERNOR DATABASE
# ─────────────────────────────────────────────────

GOVERNOR_SCHEMA = """
CREATE TABLE IF NOT EXISTS budget_allocations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at      TEXT NOT NULL,
    provincia       TEXT NOT NULL,
    cluster         TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    arbitrage_score REAL,
    daily_budget_eur REAL,
    cpc_target_eur  REAL,
    strategy        TEXT,
    approved        INTEGER DEFAULT 0,
    block_reason    TEXT,
    pulse_event_id  INTEGER
);

CREATE TABLE IF NOT EXISTS campaign_spend (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,
    campaign_id     TEXT NOT NULL,
    provincia       TEXT NOT NULL,
    spend_eur       REAL DEFAULT 0,
    clicks          INTEGER DEFAULT 0,
    lp_clicks       INTEGER DEFAULT 0,
    impressions     INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS kill_switch_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,
    action      TEXT NOT NULL,   -- ACTIVATE / DEACTIVATE
    reason      TEXT,
    triggered_by TEXT            -- 'manual' / 'watchdog' / 'burn_rate'
);

CREATE TABLE IF NOT EXISTS system_config (
    key     TEXT PRIMARY KEY,
    value   TEXT NOT NULL,
    updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_spend_date ON campaign_spend(timestamp, provincia);
CREATE INDEX IF NOT EXISTS idx_alloc_date ON budget_allocations(created_at, approved);
"""


class GovernorDB:
    def __init__(self, db_path: str = GOVERNOR_DB):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init(self):
        with self._conn() as conn:
            conn.executescript(GOVERNOR_SCHEMA)
            # Init config defaults
            defaults = {
                "kill_switch": "false",
                "daily_cap_eur": str(SAFETY.daily_cap_global_eur),
                "cpc_max_eur": str(SAFETY.cpc_max_eur),
                "max_campaigns": str(SAFETY.max_active_campaigns),
            }
            for k, v in defaults.items():
                conn.execute(
                    "INSERT OR IGNORE INTO system_config (key, value, updated_at) VALUES (?, ?, ?)",
                    (k, v, datetime.utcnow().isoformat())
                )

    def get_config(self, key: str, default=None):
        with self._conn() as conn:
            row = conn.execute(
                "SELECT value FROM system_config WHERE key=?", (key,)
            ).fetchone()
            return row["value"] if row else default

    def set_config(self, key: str, value: str):
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO system_config (key, value, updated_at) VALUES (?, ?, ?)",
                (key, value, datetime.utcnow().isoformat())
            )

    def is_kill_switch_active(self) -> bool:
        return self.get_config("kill_switch", "false").lower() == "true"

    def activate_kill_switch(self, reason: str, triggered_by: str = "manual"):
        self.set_config("kill_switch", "true")
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO kill_switch_log (timestamp, action, reason, triggered_by) VALUES (?,?,?,?)",
                (datetime.utcnow().isoformat(), "ACTIVATE", reason, triggered_by)
            )
        logger.critical(f"🛑 KILL SWITCH ATTIVATO: {reason} (da: {triggered_by})")

    def deactivate_kill_switch(self, reason: str = "Manual reset"):
        self.set_config("kill_switch", "false")
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO kill_switch_log (timestamp, action, reason, triggered_by) VALUES (?,?,?,?)",
                (datetime.utcnow().isoformat(), "DEACTIVATE", reason, "manual")
            )
        logger.info(f"✅ Kill switch disattivato: {reason}")

    def get_spent_today(self) -> float:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(spend_eur), 0) as total FROM campaign_spend WHERE timestamp LIKE ?",
                (f"{today}%",)
            ).fetchone()
            return row["total"] if row else 0.0

    def get_active_campaigns_count(self) -> int:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as n FROM campaign_spend WHERE status='active'"
            ).fetchone()
            return row["n"] if row else 0

    def get_burn_rate(self, window_hours: int = 2) -> float:
        """Percentuale del daily cap consumata nelle ultime N ore."""
        since = (datetime.utcnow() - timedelta(hours=window_hours)).isoformat()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(spend_eur), 0) as spent FROM campaign_spend WHERE timestamp >= ?",
                (since,)
            ).fetchone()
            spent = row["spent"] if row else 0.0
        daily_cap = float(self.get_config("daily_cap_eur", str(SAFETY.daily_cap_global_eur)))
        return spent / daily_cap if daily_cap > 0 else 0.0

    def record_spend(self, campaign_id: str, provincia: str,
                     spend_eur: float, clicks: int, lp_clicks: int, impressions: int):
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO campaign_spend
                   (timestamp, campaign_id, provincia, spend_eur, clicks, lp_clicks, impressions)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (datetime.utcnow().isoformat(), campaign_id, provincia,
                 spend_eur, clicks, lp_clicks, impressions)
            )

    def save_allocation(self, alloc: BudgetAllocation) -> int:
        with self._conn() as conn:
            cursor = conn.execute(
                """INSERT INTO budget_allocations
                   (created_at, provincia, cluster, event_type, arbitrage_score,
                    daily_budget_eur, cpc_target_eur, strategy, approved, block_reason, pulse_event_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (alloc.created_at, alloc.provincia, alloc.cluster, alloc.event_type,
                 alloc.arbitrage_score, alloc.daily_budget_eur, alloc.cpc_target_eur,
                 alloc.strategy, 1 if alloc.approved else 0,
                 alloc.block_reason, alloc.pulse_event_id)
            )
            return cursor.lastrowid


# ─────────────────────────────────────────────────
# BID MANAGER CORE
# ─────────────────────────────────────────────────

class BidManager:
    """
    The Governor — controlla ogni euro prima che esca.
    
    Gate di sicurezza in ordine:
    1. Kill Switch globale
    2. Daily cap raggiunto
    3. Max campagne attive
    4. Burn rate anomalo
    5. Score minimo
    6. Calcolo budget proporzionale
    """

    def __init__(self, safety: SafetyConfig = None, db_path: str = GOVERNOR_DB):
        self.safety = safety or SAFETY
        self.db = GovernorDB(db_path)

    def evaluate(self, pulse_json: Dict,
                  pulse_event_id: Optional[int] = None) -> BudgetAllocation:
        """
        Valuta un Pulse-JSON e ritorna un'allocazione budget.
        È il punto di ingresso principale del Bid Manager.
        """
        loc = pulse_json.get("location", {})
        arb = pulse_json.get("arbitrage_score", {})
        action = pulse_json.get("action_plan", {})
        trig = pulse_json.get("weather_trigger", {})

        alloc = BudgetAllocation(
            provincia=loc.get("provincia", ""),
            cluster=loc.get("cluster", ""),
            event_type=trig.get("type", ""),
            arbitrage_score=arb.get("score", 0),
            confidence=arb.get("confidence", 0),
            pulse_event_id=pulse_event_id,
        )

        # ── Gate 1: Kill Switch ──────────────────
        if self.db.is_kill_switch_active():
            return self._block(alloc, "KILL_SWITCH_ACTIVE")

        # ── Gate 2: Guardrail dall'Architect ────
        if action.get("guardrail") == "HARD_BLOCK":
            return self._block(alloc, f"ARCHITECT_HARD_BLOCK:{trig.get('type')}")

        # ── Gate 3: Fase campagna ────────────────
        phase = action.get("phase", "NO_ACTION")
        if phase in ["NO_ACTION", "BLACKOUT"]:
            return self._block(alloc, f"PHASE_{phase}")

        # ── Gate 4: Score minimo ─────────────────
        score = arb.get("score", 0)
        if score < SCORE_THRESHOLD_ACTIONABLE:
            return self._block(alloc, f"SCORE_TOO_LOW:{score:.1f}<{SCORE_THRESHOLD_ACTIONABLE}")

        # ── Gate 5: Daily cap ────────────────────
        daily_cap = float(self.db.get_config("daily_cap_eur", str(self.safety.daily_cap_global_eur)))
        spent_today = self.db.get_spent_today()
        remaining = daily_cap - spent_today

        if remaining <= self.safety.campaign_budget_min_eur:
            return self._block(alloc, f"DAILY_CAP_REACHED:{spent_today:.1f}/{daily_cap:.1f}€")

        # ── Gate 6: Max campagne ─────────────────
        active = self.db.get_active_campaigns_count()
        max_campaigns = int(self.db.get_config("max_campaigns", str(self.safety.max_active_campaigns)))
        if active >= max_campaigns:
            return self._block(alloc, f"MAX_CAMPAIGNS_REACHED:{active}/{max_campaigns}")

        # ── Gate 7: Burn rate ────────────────────
        burn_rate = self.db.get_burn_rate(self.safety.burn_rate_window_hours)
        if burn_rate > self.safety.burn_rate_max_pct:
            self.db.activate_kill_switch(
                reason=f"Burn rate anomalo: {burn_rate*100:.0f}% in {self.safety.burn_rate_window_hours}h",
                triggered_by="watchdog"
            )
            return self._block(alloc, f"BURN_RATE_EXCEEDED:{burn_rate*100:.0f}%")

        # ── Calcolo budget ───────────────────────
        alloc = self._calculate_budget(alloc, score, remaining, phase)
        alloc.approved = True

        # Salva nel DB
        self.db.save_allocation(alloc)

        logger.info(
            f"✅ Budget approvato: {alloc.provincia} | "
            f"€{alloc.daily_budget_eur:.1f}/g | CPC €{alloc.cpc_target_eur:.3f} | "
            f"Score {score:.1f}"
        )
        return alloc

    def _calculate_budget(self, alloc: BudgetAllocation, score: float,
                           remaining_eur: float, phase: str) -> BudgetAllocation:
        """
        Calcola budget e CPC proporzionali allo score.
        
        Tabella di allocazione:
        Score 6.0-6.9 → 5€  | CPC 0.08€ | TEST
        Score 7.0-7.9 → 10€ | CPC 0.10€ | MODERATE  
        Score 8.0-8.9 → 20€ | CPC 0.12€ | AGGRESSIVE
        Score 9.0+    → 35€ | CPC 0.14€ | MAX_SCALE
        """
        if score >= 9.0:
            base_budget = 35.0
            cpc = 0.14
            strategy = "MAX_SCALE"
        elif score >= SCORE_THRESHOLD_AGGRESSIVE:  # 8.0
            base_budget = 20.0
            cpc = 0.12
            strategy = "AGGRESSIVE"
        elif score >= 7.0:
            base_budget = 10.0
            cpc = 0.10
            strategy = "MODERATE"
        else:
            base_budget = 5.0
            cpc = 0.08
            strategy = "TEST"

        # Recovery phase: budget ridotto del 30% (meno competizione ma meno urgenza)
        if phase == "POST_EVENT_RECOVERY":
            base_budget *= 0.7
            strategy = f"RECOVERY_{strategy}"

        # Non superare il remaining cap
        budget = min(base_budget, remaining_eur, self.safety.campaign_budget_max_eur)
        budget = max(budget, self.safety.campaign_budget_min_eur)

        # CPC non supera il limite di safety
        cpc = min(cpc, float(self.db.get_config("cpc_max_eur", str(self.safety.cpc_max_eur))))

        alloc.daily_budget_eur = round(budget, 2)
        alloc.cpc_target_eur = round(cpc, 3)
        alloc.strategy = strategy
        return alloc

    def _block(self, alloc: BudgetAllocation, reason: str) -> BudgetAllocation:
        alloc.approved = False
        alloc.block_reason = reason
        alloc.daily_budget_eur = 0.0
        alloc.strategy = "BLOCKED"
        logger.debug(f"❌ Budget bloccato: {alloc.provincia} → {reason}")
        self.db.save_allocation(alloc)
        return alloc

    # ─────────────────────────────────────────────
    # WATCHDOG
    # ─────────────────────────────────────────────

    def review_campaign(self, campaign_id: str, provincia: str,
                         clicks: int, lp_clicks: int,
                         spend_eur: float) -> Dict:
        """
        Watchdog: valuta performance proxy in real-time.
        Chiamato ogni 30 minuti per campagna attiva.
        """
        result = {"campaign_id": campaign_id, "action": "CONTINUE", "reason": ""}

        # Kill switch check (può essere attivato da fuori nel frattempo)
        if self.db.is_kill_switch_active():
            result["action"] = "PAUSE"
            result["reason"] = "KILL_SWITCH_ACTIVE"
            return result

        # Burn rate check
        burn_rate = self.db.get_burn_rate(self.safety.burn_rate_window_hours)
        if burn_rate > self.safety.burn_rate_max_pct:
            self.db.activate_kill_switch(
                f"Burn rate {burn_rate*100:.0f}% in {self.safety.burn_rate_window_hours}h",
                triggered_by="watchdog"
            )
            result["action"] = "PAUSE_ALL"
            result["reason"] = f"BURN_RATE:{burn_rate*100:.0f}%"
            return result

        # LPCTR check (solo dopo N click significativi)
        if clicks >= self.safety.min_clicks_before_review:
            lpctr = lp_clicks / clicks if clicks > 0 else 0
            if lpctr < self.safety.lpctr_min_threshold:
                result["action"] = "PAUSE"
                result["reason"] = f"LOW_LPCTR:{lpctr*100:.1f}%<{self.safety.lpctr_min_threshold*100:.0f}%"
                logger.warning(
                    f"Campagna {campaign_id} pausata: LPCTR {lpctr*100:.1f}% "
                    f"dopo {clicks} click su {provincia}"
                )
                return result

        result["reason"] = f"OK | clicks={clicks} lpctr={lp_clicks/max(clicks,1)*100:.1f}% burn={burn_rate*100:.0f}%"
        return result

    # ─────────────────────────────────────────────
    # GLOBAL KILL SWITCH (endpoint FastAPI)
    # ─────────────────────────────────────────────

    def activate_kill_switch(self, reason: str = "Manual") -> Dict:
        """Ferma TUTTO. Chiamato da /emergency/kill endpoint."""
        self.db.activate_kill_switch(reason, triggered_by="manual")
        return {
            "status": "KILL_SWITCH_ACTIVATED",
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Tutte le campagne verranno pausate al prossimo ciclo Watchdog (max 30s)"
        }

    def deactivate_kill_switch(self, reason: str = "Manual reset") -> Dict:
        """Reset manuale dopo verifica umana."""
        self.db.deactivate_kill_switch(reason)
        return {
            "status": "KILL_SWITCH_DEACTIVATED",
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        }

    # ─────────────────────────────────────────────
    # SYSTEM STATUS
    # ─────────────────────────────────────────────

    def get_system_status(self) -> Dict:
        """Status completo del sistema — per dashboard e health check."""
        spent = self.db.get_spent_today()
        daily_cap = float(self.db.get_config("daily_cap_eur", str(self.safety.daily_cap_global_eur)))
        burn_rate = self.db.get_burn_rate(2)
        active = self.db.get_active_campaigns_count()
        kill_switch = self.db.is_kill_switch_active()

        return {
            "kill_switch": kill_switch,
            "daily_cap_eur": daily_cap,
            "spent_today_eur": round(spent, 2),
            "remaining_eur": round(max(daily_cap - spent, 0), 2),
            "spent_pct": round(spent / daily_cap * 100, 1) if daily_cap > 0 else 0,
            "burn_rate_2h_pct": round(burn_rate * 100, 1),
            "burn_rate_warning": burn_rate > self.safety.burn_rate_max_pct * 0.7,
            "active_campaigns": active,
            "max_campaigns": int(self.db.get_config("max_campaigns", str(self.safety.max_active_campaigns))),
            "cpc_max_eur": float(self.db.get_config("cpc_max_eur", str(self.safety.cpc_max_eur))),
            "status": "🛑 KILL SWITCH ATTIVO" if kill_switch else "✅ OPERATIVO",
        }

    def get_allocation_history(self, hours: int = 24) -> List[Dict]:
        """Storico allocazioni per audit."""
        since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        with self.db._conn() as conn:
            rows = conn.execute("""
                SELECT created_at, provincia, arbitrage_score, daily_budget_eur,
                       strategy, approved, block_reason
                FROM budget_allocations
                WHERE created_at >= ?
                ORDER BY created_at DESC
            """, (since,)).fetchall()
            return [dict(r) for r in rows]
