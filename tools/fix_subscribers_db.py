"""
Patch api/main.py per salvare iscritti su SQLite invece di CSV
"""

patch = '''
# ─── NEWSLETTER con SQLite (persistente) ─────────────────────────────────────
import sqlite3 as _sqlite3
from pathlib import Path as _Path

_SUBS_DB = "data/subscribers.db"

def _get_subs_conn():
    conn = _sqlite3.connect(_SUBS_DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS subscribers (
        email TEXT PRIMARY KEY,
        city TEXT DEFAULT '',
        country_code TEXT DEFAULT 'it',
        created_at TEXT DEFAULT (datetime('now'))
    )""")
    conn.commit()
    return conn

def _resend_welcome(email: str, city: str, cc: str):
    import urllib.request as _ur, json as _j
    key = os.getenv("RESEND_API_KEY","")
    if not key: return
    city_label = city or "Europa"
    html = (
        "<!DOCTYPE html><html><body style='background:#040608;color:#c8d6e5;"
        "font-family:-apple-system,sans-serif;max-width:600px;margin:0 auto;padding:40px 24px'>"
        "<h1 style='font-size:28px;font-weight:800;color:#fff;margin-bottom:6px'>"
        "Weather<span style='color:#3b82f6'>Arb</span></h1>"
        "<p style='color:#4a5568;font-size:11px;text-transform:uppercase;letter-spacing:.15em;margin-bottom:32px'>"
        "Intelligence Agency</p>"
        "<div style='background:#0a0d12;border:1px solid #141920;border-radius:12px;padding:28px'>"
        "<h2 style='font-size:18px;font-weight:700;margin-bottom:12px'>Iscrizione confermata per " + "'+city_label+'" + "</h2>"
        "<p style='font-size:14px;line-height:1.6;color:#c8d6e5'>"
        "Riceverai alert quando lo Z-Score supera la soglia critica e il briefing settimanale ogni luned&#236;.</p>"
        "</div>"
        "<p style='font-size:11px;color:#4a5568;text-align:center;margin-top:24px'>"
        "WeatherArb &middot; <a href='https://weatherarb.com' style='color:#4a5568'>weatherarb.com</a></p>"
        "</body></html>"
    )
    payload = _j.dumps({
        "from": "WeatherArb Intelligence <alerts@weatherarb.com>",
        "to": [email],
        "subject": f"Iscritto agli alert WeatherArb per {city_label}",
        "html": html.replace("'+city_label+'", city_label)
    }).encode()
    req = _ur.Request("https://api.resend.com/emails", data=payload,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with _ur.urlopen(req, timeout=10): pass
    except Exception as e:
        logger.warning(f"Resend error: {e}")

@app.post("/api/newsletter/subscribe")
def newsletter_subscribe(email: str, city: str = "", country_code: str = "it"):
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Email non valida")
    email = email.strip().lower()
    try:
        conn = _get_subs_conn()
        conn.execute(
            "INSERT INTO subscribers (email, city, country_code) VALUES (?,?,?)",
            (email, city, country_code)
        )
        conn.commit()
        conn.close()
        logger.info(f"New subscriber: {email} ({city})")
        _resend_welcome(email, city, country_code)
        return {"status": "subscribed", "message": f"Benvenuto! Alert per {city or 'Europa'}"}
    except _sqlite3.IntegrityError:
        return {"status": "already_subscribed", "message": "Sei gia iscritto!"}
    except Exception as e:
        logger.error(f"Subscribe error: {e}")
        raise HTTPException(status_code=500, detail="Errore interno")

@app.get("/api/newsletter/count")
def newsletter_count():
    try:
        conn = _get_subs_conn()
        count = conn.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0]
        conn.close()
        return {"count": count}
    except Exception:
        return {"count": 0}

@app.post("/api/newsletter/unsubscribe")
def newsletter_unsubscribe(email: str):
    try:
        conn = _get_subs_conn()
        cur = conn.execute("DELETE FROM subscribers WHERE email=?", (email.strip().lower(),))
        conn.commit()
        conn.close()
        return {"status": "unsubscribed" if cur.rowcount > 0 else "not_found"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.get("/api/newsletter/list")
def newsletter_list(secret: str = ""):
    if secret != os.getenv("ADMIN_SECRET", "weatherarb2026"):
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        conn = _get_subs_conn()
        rows = conn.execute("SELECT email, city, country_code, created_at FROM subscribers ORDER BY created_at DESC").fetchall()
        conn.close()
        return {"count": len(rows), "subscribers": [
            {"email": r[0], "city": r[1], "cc": r[2], "date": r[3]} for r in rows
        ]}
    except Exception as e:
        return {"count": 0, "error": str(e)}
'''

import re

content = open("api/main.py").read()

# Rimuovi vecchi endpoint newsletter
content = re.sub(
    r'# ─+ NEWSLETTER.*?(?=\n@app|\nif __name__|$)',
    '',
    content,
    flags=re.DOTALL
)

# Rimuovi vecchi endpoint singoli se presenti
for old_ep in [
    r'@app\.post\("/api/newsletter/subscribe"\).*?(?=\n@app|\nif __name__|$)',
    r'@app\.get\("/api/newsletter/count"\).*?(?=\n@app|\nif __name__|$)',
    r'@app\.post\("/api/newsletter/unsubscribe"\).*?(?=\n@app|\nif __name__|$)',
    r'@app\.get\("/api/newsletter/list"\).*?(?=\n@app|\nif __name__|$)',
]:
    content = re.sub(old_ep, '', content, flags=re.DOTALL)

# Inserisci prima dell'ultimo @app.get o alla fine
if 'if __name__ == "__main__":' in content:
    content = content.replace('if __name__ == "__main__":', patch + '\nif __name__ == "__main__":')
else:
    content += patch

open("api/main.py", "w").write(content)
print("✅ Newsletter endpoints aggiornati con SQLite + Resend")
