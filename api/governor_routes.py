"""
Emergency endpoints da aggiungere a api/main.py
Incolla queste route dopo gli endpoint esistenti.
"""

# ── Aggiungi a api/main.py ──────────────────────────────────────────

KILL_SWITCH_ROUTES = '''
from core.bid_manager import BidManager
bid_manager = BidManager()

@app.post("/emergency/kill")
def kill_switch_activate(reason: str = "Manual emergency stop"):
    """🛑 FERMA TUTTO — pausa tutte le campagne attive."""
    return bid_manager.activate_kill_switch(reason)

@app.post("/emergency/reset")
def kill_switch_reset(reason: str = "Manual reset after review"):
    """✅ Riattiva il sistema dopo verifica umana."""
    return bid_manager.deactivate_kill_switch(reason)

@app.get("/governor/status")
def governor_status():
    """Stato completo del Bid Manager."""
    return bid_manager.get_system_status()

@app.get("/governor/config")
def governor_config():
    """Configurazione safety limits attuale."""
    return {
        "daily_cap_eur": bid_manager.db.get_config("daily_cap_eur"),
        "cpc_max_eur": bid_manager.db.get_config("cpc_max_eur"),
        "max_campaigns": bid_manager.db.get_config("max_campaigns"),
        "kill_switch": bid_manager.db.is_kill_switch_active(),
    }

@app.post("/governor/config")
def update_governor_config(
    daily_cap_eur: float = None,
    cpc_max_eur: float = None,
    max_campaigns: int = None
):
    """Aggiorna safety limits a runtime senza riavviare."""
    updated = {}
    if daily_cap_eur is not None:
        bid_manager.db.set_config("daily_cap_eur", str(daily_cap_eur))
        updated["daily_cap_eur"] = daily_cap_eur
    if cpc_max_eur is not None:
        bid_manager.db.set_config("cpc_max_eur", str(cpc_max_eur))
        updated["cpc_max_eur"] = cpc_max_eur
    if max_campaigns is not None:
        bid_manager.db.set_config("max_campaigns", str(max_campaigns))
        updated["max_campaigns"] = max_campaigns
    return {"updated": updated, "timestamp": datetime.utcnow().isoformat()}

@app.post("/governor/evaluate/{provincia}")
def evaluate_budget(provincia: str):
    """Simula allocazione budget per una provincia senza spendere."""
    key = provincia.lower()
    if key not in _pulse_cache:
        raise HTTPException(status_code=404, detail=f"Nessun dato pulse per {provincia}")
    pulse = _pulse_cache[key]
    alloc = bid_manager.evaluate(pulse)
    return alloc.to_dict()

@app.get("/governor/allocations")
def get_allocations(hours: int = 24):
    """Storico allocazioni budget."""
    return bid_manager.get_allocation_history(hours)
'''
