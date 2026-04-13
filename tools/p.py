import json,re
from pathlib import Path
from unicodedata import normalize
def sl(t):
 s=normalize("NFKD",t).encode("ascii","ignore").decode("ascii")
 return re.sub(r"[\s_]+","-",re.sub(r"[^\w\s-]","",s).strip().lower())
CC={"Italy":"it","Germany":"de","France":"fr","Spain":"es","United Kingdom":"gb","Sweden":"se","Netherlands":"nl","Poland":"pl","Austria":"at","Switzerland":"ch","Belgium":"be","Portugal":"pt","Denmark":"dk","Norway":"no"}
raw=json.loads(Path("data/province_coords.json").read_text())
provinces=raw["province"] if "province" in raw else raw
ok=sk=0
for c in provinces:
 name=c.get("nome","");cn=c.get("country","Italy")
 cc={"Italy":"it","Germany":"de","France":"fr","Spain":"es","United Kingdom":"gb","Sweden":"se","Netherlands":"nl","Poland":"pl","Austria":"at","Switzerland":"ch","Belgium":"be","Portugal":"pt","Denmark":"dk","Norway":"no"}.get(cn,"it")
 slug=sl(name);p=Path("data/website")/cc/slug/"index.html"
 if not p.exists():sk+=1;continue
 html=p.read_text(encoding="utf-8")
 if "nl-box" in html:sk+=1;continue
 if "</main>" in html:html=html.replace("</main>",w+"</main>",1)
 elif "</body>" in html:html=html.replace("</body>",w+"</body>",1)
 p.write_text(html,encoding="utf-8");ok+=1
print(f"Patched:{ok} Skipped:{sk}")
