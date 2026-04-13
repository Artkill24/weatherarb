import json, re
from pathlib import Path
from unicodedata import normalize

def sl(t):
    s = normalize('NFKD', t).encode('ascii','ignore').decode('ascii')
    return re.sub(r'[\s_]+','-', re.sub(r'[^\w\s-]','',s).strip().lower())

CC = {'Italy':'it','Germany':'de','France':'fr','Spain':'es','United Kingdom':'gb','Sweden':'se','Netherlands':'nl','Poland':'pl','Austria':'at','Switzerland':'ch','Belgium':'be','Portugal':'pt','Denmark':'dk','Norway':'no'}
FB = {'munchen':'de','hamburg':'de','berlin':'de','frankfurt':'de','koln':'de','madrid':'es','barcelona':'es','valencia':'es','paris':'fr','lyon':'fr','london':'gb','manchester':'gb','birmingham':'gb','edinburgh':'gb','glasgow':'gb','stockholm':'se','goteborg':'se','amsterdam':'nl','rotterdam':'nl','warszawa':'pl','krakow':'pl','wien':'at','graz':'at','zurich':'ch','bern':'ch','bruxelles':'be','lisboa':'pt','porto':'pt','kobenhavn':'dk','oslo':'no','bergen':'no'}

raw = json.loads(Path('data/province_coords.json').read_text())
provinces = raw['province'] if 'province' in raw else raw

ok = sk = 0
for c in provinces:
    name = c.get('nome','')
    cn = c.get('country','Italy')
    cc = CC.get(cn, FB.get(sl(name),'it'))
    slug = sl(name)
    p = Path(f'data/website/{cc}/{slug}/index.html')
    if not p.exists(): sk+=1; continue
    html = p.read_text(encoding='utf-8')
    if 'nl-box' in html: sk+=1; continue
    w = '<div style="background:linear-gradient(135deg,rgba(59,130,246,.08),rgba(16,185,129,.05));border:1px solid rgba(59,130,246,.2);border-radius:12px;padding:24px;margin:24px 0" id="nl-box"><div style="font-size:15px;font-weight:700;color:#fff;margin-bottom:8px">Intelligence Briefing per ' + name + '</div><p style="font-size:13px;color:#c8d6e5;line-height:1.6;margin:0 0 14px">Alert anomalie meteo per ' + name + ' nella tua inbox. Gratuito.</p><div style="display:flex;gap:8px;flex-wrap:wrap" id="nl-f"><input id="nl-e" type="email" placeholder="La tua email" style="flex:1;min-width:180px;background:rgba(255,255,255,.05);border:1px solid #1e2d3d;border-radius:8px;padding:10px 14px;color:#c8d6e5;font-size:13px;outline:none"><button onclick="nls()" style="background:#3b82f6;color:#fff;border:none;border-radius:8px;padding:10px 20px;font-size:13px;font-weight:700;cursor:pointer">Iscriviti</button></div><div id="nl-m" style="display:none;font-size:13px;margin-top:10px;padding:10px;border-radius:8px"></div></div><script>async function nls(){var e=document.getElementById("nl-e").value.trim(),m=document.getElementById("nl-m");if(!e||!e.includes("@")){m.style.display="block";m.style.background="rgba(239,68,68,.1)";m.style.color="#ef4444";m.textContent="Email non valida";return;}try{var r=await fetch("https://api.weatherarb.com/api/newsletter/subscribe?email="+encodeURIComponent(e)+"&city=' + name + '&country_code=' + cc + '",{method:"POST"});var d=await r.json();document.getElementById("nl-f").style.display="none";m.style.display="block";m.style.background="rgba(16,185,129,.1)";m.style.color="#10b981";m.textContent=d.status==="already_subscribed"?"Sei gia iscritto!":"Iscritto!";}catch(x){m.style.display="block";m.style.background="rgba(239,68,68,.1)";m.style.color="#ef4444";m.textContent="Errore";}}</script>'
    if '</main>' in html: html = html.replace('</main>', w+'</main>', 1)
    elif '</body>' in html: html = html.replace('</body>', w+'</body>', 1)
    else: html += w
    p.write_text(html, encoding='utf-8')
    ok += 1

print(f'Patched: {ok}, Skipped: {sk}')
