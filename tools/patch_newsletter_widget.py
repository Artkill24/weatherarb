#!/usr/bin/env python3
import json, re
from pathlib import Path
from unicodedata import normalize

def slugify(t):
    s = normalize("NFKD", t).encode("ascii","ignore").decode("ascii")
    return re.sub(r"[\s_]+","-", re.sub(r"[^\w\s-]","",s).strip().lower())

COUNTRY_CODE = {
    "Italy":"it","Germany":"de","France":"fr","Spain":"es",
    "United Kingdom":"gb","Sweden":"se","Netherlands":"nl",
    "Poland":"pl","Austria":"at","Switzerland":"ch",
    "Belgium":"be","Portugal":"pt","Denmark":"dk","Norway":"no"
}
FALLBACK = {
    "münchen":"de","hamburg":"de","berlin":"de","frankfurt":"de","köln":"de",
    "düsseldorf":"de","stuttgart":"de","nürnberg":"de",
    "madrid":"es","barcelona":"es","valencia":"es","sevilla":"es","bilbao":"es",
    "paris":"fr","lyon":"fr","marseille":"fr","bordeaux":"fr","nice":"fr",
    "london":"gb","manchester":"gb","birmingham":"gb","edinburgh":"gb",
    "glasgow":"gb","leeds":"gb","bristol":"gb","cardiff":"gb","liverpool":"gb","sheffield":"gb",
    "stockholm":"se","göteborg":"se","malmö":"se","uppsala":"se","västerås":"se",
    "örebro":"se","linköping":"se","helsingborg":"se","jönköping":"se","umeå":"se",
    "amsterdam":"nl","rotterdam":"nl","den-haag":"nl","utrecht":"nl","eindhoven":"nl","groningen":"nl",
    "warszawa":"pl","kraków":"pl","wrocław":"pl","gdańsk":"pl","poznań":"pl","łódź":"pl",
    "wien":"at","graz":"at","linz":"at","salzburg":"at","innsbruck":"at",
    "zürich":"ch","genève":"ch","basel":"ch","bern":"ch","lausanne":"ch",
    "bruxelles":"be","antwerpen":"be","gent":"be","liège":"be",
    "lisboa":"pt","porto":"pt","braga":"pt",
    "københavn":"dk","aarhus":"dk","odense":"dk",
    "oslo":"no","bergen":"no","trondheim":"no","stavanger":"no",
}

WIDGET_TPL = """
<div style="background:linear-gradient(135deg,rgba(59,130,246,.08),rgba(16,185,129,.05));border:1px solid rgba(59,130,246,.2);border-radius:12px;padding:24px;margin:24px 0" id="nl-box">
  <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:12px">
    <span style="font-size:24px;line-height:1">&#128236;</span>
    <div>
      <div style="font-size:15px;font-weight:700;color:#fff">Intelligence Briefing per CITYNAME</div>
      <div style="font-size:12px;color:#4a5568;margin-top:2px">Alert anomalie + briefing settimanale &middot; Gratuito</div>
    </div>
  </div>
  <p style="font-size:13px;color:#c8d6e5;line-height:1.6;margin:0 0 14px">Ricevi l'analisi Z-Score per CITYNAME nella tua inbox. Basato su NASA POWER 25 anni.</p>
  <div id="nl-form" style="display:flex;gap:8px;flex-wrap:wrap">
    <input id="nl-email" type="email" placeholder="La tua email"
      style="flex:1;min-width:180px;background:rgba(255,255,255,.05);border:1px solid #1e2d3d;border-radius:8px;padding:10px 14px;color:#c8d6e5;font-size:13px;outline:none">
    <button onclick="nlSub()"
      style="background:#3b82f6;color:#fff;border:none;border-radius:8px;padding:10px 20px;font-size:13px;font-weight:700;cursor:pointer">
      Iscriviti &rarr;
    </button>
  </div>
  <div id="nl-msg" style="display:none;font-size:13px;margin-top:10px;padding:10px 14px;border-radius:8px"></div>
  <p style="font-size:10px;color:#4a5568;margin-top:8px">Nessuno spam. Cancellazione con un click.</p>
</div>
<script>
async function nlSub() {
  var e = document.getElementById('nl-email').value.trim();
  var m = document.getElementById('nl-msg');
  if (!e || !e.includes('@')) {
    m.style.display='block'; m.style.background='rgba(239,68,68,.1)';
    m.style.color='#ef4444'; m.textContent='Email non valida'; return;
  }
  try {
    var r = await fetch('https://api.weatherarb.com/api/newsletter/subscribe?email='+encodeURIComponent(e)+'&city=CITYNAME&country_code=CCCODE', {method:'POST'});
    var d = await r.json();
    document.getElementById('nl-form').style.display='none';
    m.style.display='block'; m.style.background='rgba(16,185,129,.1)'; m.style.color='#10b981';
    m.textContent = d.status==='already_subscribed' ? 'Sei gia iscritto!' : 'Iscritto! Controlla la tua email.';
  } catch(err) {
    m.style.display='block'; m.style.background='rgba(239,68,68,.1)';
    m.style.color='#ef4444'; m.textContent='Errore - riprova';
  }
}
document.getElementById('nl-email').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') nlSub();
});
</script>
"""

with open("data/province_coords.json") as f:
    raw = json.load(f)
provinces = raw["province"] if "province" in raw else raw

patched = 0
skipped = 0

for city in provinces:
    name = city.get("nome", "")
    cn = city.get("country", "Italy")
    cc = COUNTRY_CODE.get(cn, FALLBACK.get(name.lower(), "it"))
    slug = slugify(name)
    path = Path(f"data/website/{cc}/{slug}/index.html")

    if not path.exists():
        skipped += 1
        continue

    content = path.read_text(encoding="utf-8")
    if "nl-box" in content:
        skipped += 1
        continue

    widget = WIDGET_TPL.replace("CITYNAME", name).replace("CCCODE", cc)

    if "</main>" in content:
        content = content.replace("</main>", widget + "\n</main>", 1)
    elif "</body>" in content:
        content = content.replace("</body>", widget + "\n</body>", 1)
    else:
        content += widget

    path.write_text(content, encoding="utf-8")
    patched += 1
    print(f"  ✅ /{cc}/{slug}/")

print(f"\n✅ Widget aggiunto a {patched} landing ({skipped} saltate)")
print("\nOra esegui:")
print("  git add -A")
print("  git commit -m 'feat: newsletter widget in tutte le landing'")
print("  git pull --rebase && git push origin main")
