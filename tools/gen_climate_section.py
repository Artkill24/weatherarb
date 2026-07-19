#!/usr/bin/env python3
"""
Genera la sezione "Clima in cambiamento" (statica, indicizzabile) e la
inserisce nelle pagine citta' che hanno dati NASA daily.

    python3 tools/gen_climate_section.py --dry milano   # anteprima
    python3 tools/gen_climate_section.py                # scrive tutto
"""
import glob, hashlib, json, os, sys

DAILY, SITE = "data/nasa_daily", "data/website"
MARK = "climate-trend-section"

cities, cells = {}, {}
for f in glob.glob(f"{DAILY}/*.json"):
    d = json.load(open(f))
    cities[d["slug"]] = d
    h = hashlib.md5(json.dumps(d["daily_norms"], sort_keys=True).encode()).hexdigest()
    cells.setdefault(h, []).append(d["slug"])
cell_of = {s: sorted(v) for v in cells.values() for s in v}
print(f"{len(cities)} citta' -> {len(cells)} celle di griglia distinte\n")

T = {
 "it": dict(h="Clima in Cambiamento", warm="Temperatura media annua",
   since="dal", hot="Giorni sopra 30&deg;C", per_year="all'anno",
   rec="Record assoluto", src="Rianalisi NASA POWER (MERRA-2)",
   meth="Metodologia", decade="decennio",
   note="I dati provengono dalla rianalisi NASA POWER (MERRA-2), con risoluzione di griglia di circa 50 km: si riferiscono all'area e non alla singola stazione urbana.",
   shared="Nella griglia NASA quest'area comprende anche"),
 "en": dict(h="A Changing Climate", warm="Mean annual temperature",
   since="since", hot="Days above 30&deg;C", per_year="per year",
   rec="All-time record", src="NASA POWER reanalysis (MERRA-2)",
   meth="Methodology", decade="decade",
   note="Data comes from the NASA POWER reanalysis (MERRA-2) at roughly 50 km grid resolution: figures describe the surrounding area rather than a single urban station.",
   shared="In the NASA grid this area also covers"),
}
NAMES = {"monza-e-brianza":"Monza e Brianza","forlì-cesena":"Forlì-Cesena","verbano-cusio-ossola":"Verbano-Cusio-Ossola"}
LANG = {"it":"it","de":"en","fr":"en","es":"en","pt":"en"}

def esc(s): return s.replace("&","&amp;").replace("<","&lt;")

def section(d, lang, name):
    t = T[lang]; w, hd, rc, pe = d["warming"], d["hot_days"], d["records"], d["period"]
    warm = w["annual_total"]; a, b = hd["first_decade_avg"], hd["last_decade_avg"]
    y0, y1 = pe["start"], pe["end"]
    peers = [p for p in cell_of[d["slug"]] if p != d["slug"]]

    cards = [(f"+{warm}&deg;C", f"{t['warm']} {t['since']} {y0}")] if warm else []
    if b is not None and b >= 1:
        cards.append((f"{a} &rarr; {b}", f"{t['hot']} {t['per_year']}"))
    if rc["hottest"]:
        cards.append((f"{rc['hottest']['c']}&deg;C", f"{t['rec']} ({rc['hottest']['date'][:4]})"))

    body = (f"{'Nell&rsquo;area di' if lang=='it' else 'In the'} {esc(name)}"
            f"{'' if lang=='it' else ' area'}, "
            + (f"{'la temperatura media annua &egrave; salita di' if lang=='it' else 'the mean annual temperature has risen'} "
               f"{'' if lang=='it' else 'by '}{warm}&deg;C {t['since']} {y0}. " if warm else ""))
    if b is not None and b >= 1:
        body += (f"{'I giorni con massima oltre i 30&deg;C sono passati da una media di' if lang=='it' else 'Days with highs above 30&deg;C went from an average of'} "
                 f"{a} {'nel decennio' if lang=='it' else 'in'} {y0}&ndash;{y0+9} "
                 f"{'a' if lang=='it' else 'to'} {b} {'nel' if lang=='it' else 'in'} {y1-9}&ndash;{y1}. ")
    if rc["hottest"]:
        body += (f"{'Il valore pi&ugrave; alto registrato &egrave; stato' if lang=='it' else 'The highest recorded value was'} "
                 f"{rc['hottest']['c']}&deg;C ({rc['hottest']['date']}). ")

    note = t["note"]
    if peers:
        note += f" {t['shared']}: {', '.join(NAMES.get(p, p.replace('-',' ').title()) for p in peers)}."

    cs = "".join(
      f'<div style="flex:1;min-width:150px;background:#0d1117;border-radius:10px;padding:14px">'
      f'<div style="font-size:24px;font-weight:800;color:#c8d6e5">{v}</div>'
      f'<div style="font-size:11px;color:#4a5568;margin-top:4px">{l}</div></div>' for v, l in cards)

    return f'''
<div id="{MARK}" style="background:#0a0d12;border:1px solid #141920;border-radius:14px;padding:24px;margin-bottom:16px">
  <h2 style="font-size:15px;font-weight:700;color:#fff;margin-bottom:4px">{t["h"]} &mdash; {esc(name)}</h2>
  <div style="font-size:11px;color:#4a5568;margin-bottom:14px">{t["src"]} &middot; {y0}&ndash;{y1}</div>
  <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px">{cs}</div>
  <p style="font-size:13px;color:#4a5568;line-height:1.7">{body}</p>
  <p style="font-size:11px;color:#2d3748;line-height:1.6;margin-top:12px;border-top:1px solid #141920;padding-top:10px">
    <strong style="color:#4a5568">{t["meth"]}:</strong> {note}</p>
</div>'''

_TR = str.maketrans({'ł':'l','ø':'o','æ':'ae','ß':'ss'})
def _ascii(s):
    import unicodedata
    return unicodedata.normalize('NFKD', s.lower().translate(_TR)).encode('ascii','ignore').decode()

def pages(slug):
    out = glob.glob(f"{SITE}/*/{slug}/index.html") + glob.glob(f"{SITE}/*/*/{slug}/index.html")
    if not out:
        a = _ascii(slug)
        out = glob.glob(f"{SITE}/*/{a}/index.html") + glob.glob(f"{SITE}/*/*/{a}/index.html")
    return out

dry = "--dry" in sys.argv
only = sys.argv[-1] if dry and not sys.argv[-1].startswith("--") else None
done = skip = 0

for slug, d in sorted(cities.items()):
    if only and slug != only: continue
    ps = pages(slug)
    if not ps:
        print(f"  {slug}: nessuna pagina trovata"); skip += 1; continue
    for p in ps:
        cc = p.split("/")[2]
        lang = LANG.get(cc, "en")
        name = NAMES.get(slug, slug.replace("-", " ").title())
        html = open(p, encoding="utf-8").read()
        if MARK in html: skip += 1; continue
        blk = section(d, lang, name)
        if dry:
            print(f"--- {p} [{lang}] ---\n{blk}\n"); continue
        if "</main>" in html: html = html.replace("</main>", blk + "\n</main>", 1)
        elif "<footer" in html: html = html.replace("<footer", blk + "\n<footer", 1)
        else: skip += 1; continue
        open(p, "w", encoding="utf-8").write(html)
        done += 1

print(f"\n>>> inserite: {done}   saltate: {skip}")
