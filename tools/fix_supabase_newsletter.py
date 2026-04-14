"""
Patch api/main.py per usare Supabase come database newsletter
"""
import re

SUPABASE_URL = "https://mlawljowkvgeyydrwirk.supabase.co"
TABLE = "newsletter_subscribers"

new_endpoints = f'''
# ─── NEWSLETTER su Supabase ──────────────────────────────────────────────────
import urllib.request as _ur
import json as _json

_SB_URL = os.getenv("SUPABASE_URL", "{SUPABASE_URL}")
_SB_KEY = os.getenv("SUPABASE_ANON_KEY", "")
_SB_TABLE = "{TABLE}"

def _sb_headers():
    return {{
        "apikey": _SB_KEY,
        "Authorization": f"Bearer {{_SB_KEY}}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }}

def _sb_request(method, path, data=None):
    url = f"{{_SB_URL}}/rest/v1/{{path}}"
    payload = _json.dumps(data).encode() if data else None
    req = _ur.Request(url, data=payload, headers=_sb_headers(), method=method)
    try:
        with _ur.urlopen(req, timeout=10) as r:
            body = r.read()
            return r.status, _json.loads(body) if body else {{}}
    except _ur.HTTPError as e:
        body = e.read()
        return e.code, _json.loads(body) if body else {{}}
    except Exception as ex:
        logger.error(f"Supabase error: {{ex}}")
        return 500, {{}}

def _resend_welcome(email: str, city: str, cc: str):
    key = os.getenv("RESEND_API_KEY", "")
    if not key:
        return
    city_label = city or "Europa"
    html = (
        "<!DOCTYPE html><html><body style=\\"background:#040608;color:#c8d6e5;"
        "font-family:-apple-system,sans-serif;max-width:600px;margin:0 auto;padding:40px 24px\\">"
        "<h1 style=\\"font-size:28px;font-weight:800;color:#fff\\">Weather"
        "<span style=\\"color:#3b82f6\\">Arb</span></h1>"
        "<p style=\\"color:#4a5568;font-size:11px;text-transform:uppercase;letter-spacing:.15em\\">Intelligence Agency</p>"
        f"<p style=\\"font-size:15px;line-height:1.6;margin-top:24px\\">Iscritto agli alert per <strong>{{city_label}}</strong>.</p>"
        "<p style=\\"font-size:13px;color:#4a5568;margin-top:32px\\">WeatherArb · weatherarb.com</p>"
        "</body></html>"
    )
    payload = _json.dumps({{
        "from": "WeatherArb Intelligence <alerts@weatherarb.com>",
        "to": [email],
        "subject": f"Alert WeatherArb per {{city_label}}",
        "html": html
    }}).encode()
    req = _ur.Request("https://api.resend.com/emails", data=payload,
        headers={{"Authorization": f"Bearer {{key}}", "Content-Type": "application/json"}})
    try:
        with _ur.urlopen(req, timeout=10): pass
    except Exception as e:
        logger.warning(f"Resend error: {{e}}")

@app.post("/api/newsletter/subscribe")
def newsletter_subscribe(email: str, city: str = "", country_code: str = "it"):
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Email non valida")
    email = email.strip().lower()
    status, resp = _sb_request("POST", _SB_TABLE,
        {{"email": email, "city": city, "country_code": country_code}})
    if status == 201:
        logger.info(f"New subscriber: {{email}} ({{city}})")
        _resend_welcome(email, city, country_code)
        return {{"status": "subscribed", "message": f"Benvenuto! Alert per {{city or 'Europa'}}"}}
    elif status == 409:
        return {{"status": "already_subscribed", "message": "Sei gia iscritto!"}}
    else:
        logger.error(f"Supabase subscribe error {{status}}: {{resp}}")
        raise HTTPException(status_code=500, detail="Errore interno")

@app.get("/api/newsletter/count")
def newsletter_count():
    status, resp = _sb_request("GET", f"{{_SB_TABLE}}?select=count")
    if status == 200 and isinstance(resp, list):
        return {{"count": resp[0].get("count", 0) if resp else 0}}
    # fallback: conta manualmente
    status2, resp2 = _sb_request("GET", f"{{_SB_TABLE}}?select=email")
    if status2 == 200:
        return {{"count": len(resp2) if isinstance(resp2, list) else 0}}
    return {{"count": 0}}

@app.post("/api/newsletter/unsubscribe")
def newsletter_unsubscribe(email: str):
    status, _ = _sb_request("DELETE", f"{{_SB_TABLE}}?email=eq.{{email.strip().lower()}}")
    return {{"status": "unsubscribed" if status == 204 else "not_found"}}

@app.get("/api/newsletter/list")
def newsletter_list(secret: str = ""):
    if secret != os.getenv("ADMIN_SECRET", "weatherarb2026"):
        raise HTTPException(status_code=403, detail="Forbidden")
    status, resp = _sb_request("GET", f"{{_SB_TABLE}}?select=email,city,country_code,created_at&order=created_at.desc")
    if status == 200 and isinstance(resp, list):
        return {{"count": len(resp), "subscribers": resp}}
    return {{"count": 0, "subscribers": []}}
'''

content = open("api/main.py").read()

# Rimuovi tutti i vecchi endpoint newsletter
content = re.sub(
    r'# ─+ NEWSLETTER.*?(?=\n@app\.get\("/"\)|\n@app\.get\("/pulse|\nif __name__|# ─{3,}(?!.*NEWSLETTER))',
    '',
    content, flags=re.DOTALL
)

# Rimuovi endpoint rimasti
for pattern in [
    r'@app\.(post|get)\("/api/newsletter/[^"]+"\)\ndef newsletter_\w+.*?(?=\n@app|\nif __name__|$)',
    r'def _get_subs_conn.*?(?=\n@app|\ndef [a-z]|\nif __name__|$)',
    r'def _resend_welcome.*?(?=\n@app|\ndef [a-z]|\nif __name__|$)',
    r'def _sb_request.*?(?=\n@app|\ndef [a-z]|\nif __name__|$)',
    r'_SUBS_DB.*?\n',
    r'_SB_URL.*?\n',
    r'_SB_KEY.*?\n',
    r'_SB_TABLE.*?\n',
]:
    content = re.sub(pattern, '', content, flags=re.DOTALL)

# Inserisci prima di if __name__
if 'if __name__ == "__main__":' in content:
    content = content.replace(
        'if __name__ == "__main__":',
        new_endpoints + '\nif __name__ == "__main__":'
    )
else:
    content += new_endpoints

open("api/main.py", "w").write(content)
print("✅ api/main.py aggiornato con Supabase newsletter")
print("\nAggiungi su Railway Variables:")
print(f"  SUPABASE_URL = {SUPABASE_URL}")
print(f"  SUPABASE_ANON_KEY = <la tua anon key>")
