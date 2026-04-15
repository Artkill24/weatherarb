#!/usr/bin/env python3
"""
Aggiunge ~150 nuovi nodi a province_coords.json
Italia completa + espansione EU (GR, HR, CZ, HU, RO + extra DE/FR/ES/GB/SE/NL/PL ecc.)
"""
import json

new_nodes = [
    # ─── ITALIA MANCANTI ───
    {"nome":"Prato","regione":"Toscana","country":"Italy","lat":43.8777,"lon":11.0967,"cluster":"Central"},
    {"nome":"Fermo","regione":"Marche","country":"Italy","lat":43.1608,"lon":13.7152,"cluster":"Central"},
    {"nome":"Lamezia Terme","regione":"Calabria","country":"Italy","lat":38.9706,"lon":16.3172,"cluster":"South"},
    {"nome":"Marsala","regione":"Sicilia","country":"Italy","lat":37.7989,"lon":12.4333,"cluster":"Sicily"},
    {"nome":"Gela","regione":"Sicilia","country":"Italy","lat":37.0675,"lon":14.2506,"cluster":"Sicily"},
    {"nome":"Acireale","regione":"Sicilia","country":"Italy","lat":37.6119,"lon":15.1650,"cluster":"Sicily"},
    {"nome":"Bagheria","regione":"Sicilia","country":"Italy","lat":38.0833,"lon":13.5119,"cluster":"Sicily"},
    {"nome":"Olbia","regione":"Sardegna","country":"Italy","lat":40.9208,"lon":9.4978,"cluster":"Sardinia"},
    {"nome":"Sud Sardegna","regione":"Sardegna","country":"Italy","lat":39.3122,"lon":8.9661,"cluster":"Sardinia"},
    {"nome":"Spoleto","regione":"Umbria","country":"Italy","lat":42.7340,"lon":12.7381,"cluster":"Central"},
    {"nome":"Lanciano","regione":"Abruzzo","country":"Italy","lat":42.2289,"lon":14.3908,"cluster":"South"},
    {"nome":"Vasto","regione":"Abruzzo","country":"Italy","lat":42.1121,"lon":14.7086,"cluster":"South"},
    {"nome":"Torre del Greco","regione":"Campania","country":"Italy","lat":40.7886,"lon":14.3694,"cluster":"South"},
    {"nome":"Giugliano in Campania","regione":"Campania","country":"Italy","lat":40.9272,"lon":14.1956,"cluster":"South"},
    {"nome":"Altamura","regione":"Puglia","country":"Italy","lat":40.8267,"lon":16.5536,"cluster":"South"},
    {"nome":"Melfi","regione":"Basilicata","country":"Italy","lat":40.9942,"lon":15.6512,"cluster":"South"},
    # ─── GERMANIA EXTRA ───
    {"nome":"Leipzig","regione":"Sachsen","country":"Germany","lat":51.3397,"lon":12.3731,"cluster":"DE_East"},
    {"nome":"Dresden","regione":"Sachsen","country":"Germany","lat":51.0504,"lon":13.7373,"cluster":"DE_East"},
    {"nome":"Dortmund","regione":"Nordrhein-Westfalen","country":"Germany","lat":51.5136,"lon":7.4653,"cluster":"DE_West"},
    {"nome":"Essen","regione":"Nordrhein-Westfalen","country":"Germany","lat":51.4566,"lon":7.0116,"cluster":"DE_West"},
    {"nome":"Bremen","regione":"Bremen","country":"Germany","lat":53.0793,"lon":8.8017,"cluster":"DE_North"},
    {"nome":"Hannover","regione":"Niedersachsen","country":"Germany","lat":52.3759,"lon":9.7320,"cluster":"DE_North"},
    {"nome":"Duisburg","regione":"Nordrhein-Westfalen","country":"Germany","lat":51.4344,"lon":6.7623,"cluster":"DE_West"},
    {"nome":"Bochum","regione":"Nordrhein-Westfalen","country":"Germany","lat":51.4818,"lon":7.2162,"cluster":"DE_West"},
    {"nome":"Wuppertal","regione":"Nordrhein-Westfalen","country":"Germany","lat":51.2562,"lon":7.1508,"cluster":"DE_West"},
    {"nome":"Bielefeld","regione":"Nordrhein-Westfalen","country":"Germany","lat":52.0302,"lon":8.5325,"cluster":"DE_West"},
    {"nome":"Mannheim","regione":"Baden-Württemberg","country":"Germany","lat":49.4875,"lon":8.4660,"cluster":"DE_South"},
    {"nome":"Augsburg","regione":"Bayern","country":"Germany","lat":48.3717,"lon":10.8983,"cluster":"DE_South"},
    {"nome":"Wiesbaden","regione":"Hessen","country":"Germany","lat":50.0782,"lon":8.2398,"cluster":"DE_Central"},
    {"nome":"Munster","regione":"Nordrhein-Westfalen","country":"Germany","lat":51.9607,"lon":7.6261,"cluster":"DE_West"},
    {"nome":"Chemnitz","regione":"Sachsen","country":"Germany","lat":50.8278,"lon":12.9214,"cluster":"DE_East"},
    {"nome":"Freiburg im Breisgau","regione":"Baden-Württemberg","country":"Germany","lat":47.9990,"lon":7.8421,"cluster":"DE_South"},
    {"nome":"Kiel","regione":"Schleswig-Holstein","country":"Germany","lat":54.3233,"lon":10.1394,"cluster":"DE_North"},
    {"nome":"Rostock","regione":"Mecklenburg-Vorpommern","country":"Germany","lat":54.0887,"lon":12.1403,"cluster":"DE_North"},
    {"nome":"Erfurt","regione":"Thuringen","country":"Germany","lat":50.9787,"lon":11.0328,"cluster":"DE_Central"},
    {"nome":"Kassel","regione":"Hessen","country":"Germany","lat":51.3127,"lon":9.4797,"cluster":"DE_Central"},
    {"nome":"Mainz","regione":"Rheinland-Pfalz","country":"Germany","lat":49.9929,"lon":8.2473,"cluster":"DE_Central"},
    {"nome":"Saarbrucken","regione":"Saarland","country":"Germany","lat":49.2354,"lon":6.9969,"cluster":"DE_West"},
    {"nome":"Heidelberg","regione":"Baden-Württemberg","country":"Germany","lat":49.3988,"lon":8.6724,"cluster":"DE_South"},
    # ─── FRANCIA EXTRA ───
    {"nome":"Toulouse","regione":"Occitanie","country":"France","lat":43.6047,"lon":1.4442,"cluster":"FR_South"},
    {"nome":"Strasbourg","regione":"Grand Est","country":"France","lat":48.5734,"lon":7.7521,"cluster":"FR_East"},
    {"nome":"Nantes","regione":"Pays de la Loire","country":"France","lat":47.2184,"lon":-1.5536,"cluster":"FR_West"},
    {"nome":"Montpellier","regione":"Occitanie","country":"France","lat":43.6108,"lon":3.8767,"cluster":"FR_South"},
    {"nome":"Rennes","regione":"Bretagne","country":"France","lat":48.1147,"lon":-1.6794,"cluster":"FR_West"},
    {"nome":"Grenoble","regione":"Auvergne-Rhone-Alpes","country":"France","lat":45.1885,"lon":5.7245,"cluster":"FR_Alps"},
    {"nome":"Dijon","regione":"Bourgogne-Franche-Comte","country":"France","lat":47.3220,"lon":5.0415,"cluster":"FR_Central"},
    {"nome":"Nimes","regione":"Occitanie","country":"France","lat":43.8367,"lon":4.3601,"cluster":"FR_South"},
    {"nome":"Le Havre","regione":"Normandie","country":"France","lat":49.4938,"lon":0.1077,"cluster":"FR_North"},
    {"nome":"Reims","regione":"Grand Est","country":"France","lat":49.2583,"lon":4.0317,"cluster":"FR_North"},
    {"nome":"Toulon","regione":"Provence-Alpes","country":"France","lat":43.1242,"lon":5.9280,"cluster":"FR_South"},
    {"nome":"Lille","regione":"Hauts-de-France","country":"France","lat":50.6292,"lon":3.0573,"cluster":"FR_North"},
    {"nome":"Brest","regione":"Bretagne","country":"France","lat":48.3905,"lon":-4.4860,"cluster":"FR_West"},
    {"nome":"Clermont-Ferrand","regione":"Auvergne-Rhone-Alpes","country":"France","lat":45.7797,"lon":3.0863,"cluster":"FR_Central"},
    # ─── SPAGNA EXTRA ───
    {"nome":"Zaragoza","regione":"Aragon","country":"Spain","lat":41.6561,"lon":-0.8773,"cluster":"ES_Central"},
    {"nome":"Malaga","regione":"Andalucia","country":"Spain","lat":36.7213,"lon":-4.4213,"cluster":"ES_South"},
    {"nome":"Murcia","regione":"Region de Murcia","country":"Spain","lat":37.9922,"lon":-1.1307,"cluster":"ES_East"},
    {"nome":"Palma","regione":"Islas Baleares","country":"Spain","lat":39.5696,"lon":2.6502,"cluster":"ES_Islands"},
    {"nome":"Valladolid","regione":"Castilla y Leon","country":"Spain","lat":41.6523,"lon":-4.7245,"cluster":"ES_Central"},
    {"nome":"Cordoba","regione":"Andalucia","country":"Spain","lat":37.8882,"lon":-4.7794,"cluster":"ES_South"},
    {"nome":"Alicante","regione":"Comunitat Valenciana","country":"Spain","lat":38.3452,"lon":-0.4810,"cluster":"ES_East"},
    {"nome":"Vigo","regione":"Galicia","country":"Spain","lat":42.2314,"lon":-8.7124,"cluster":"ES_North"},
    {"nome":"Granada","regione":"Andalucia","country":"Spain","lat":37.1765,"lon":-3.5981,"cluster":"ES_South"},
    {"nome":"Oviedo","regione":"Asturias","country":"Spain","lat":43.3614,"lon":-5.8593,"cluster":"ES_North"},
    {"nome":"Pamplona","regione":"Navarra","country":"Spain","lat":42.8125,"lon":-1.6458,"cluster":"ES_North"},
    {"nome":"Santander","regione":"Cantabria","country":"Spain","lat":43.4623,"lon":-3.8099,"cluster":"ES_North"},
    # ─── UK EXTRA ───
    {"nome":"Nottingham","regione":"East Midlands","country":"United Kingdom","lat":52.9548,"lon":-1.1581,"cluster":"GB_Midlands"},
    {"nome":"Leicester","regione":"East Midlands","country":"United Kingdom","lat":52.6369,"lon":-1.1398,"cluster":"GB_Midlands"},
    {"nome":"Southampton","regione":"South East","country":"United Kingdom","lat":50.9097,"lon":-1.4044,"cluster":"GB_South"},
    {"nome":"Newcastle upon Tyne","regione":"North East","country":"United Kingdom","lat":54.9783,"lon":-1.6178,"cluster":"GB_North"},
    {"nome":"Coventry","regione":"West Midlands","country":"United Kingdom","lat":52.4068,"lon":-1.5197,"cluster":"GB_Midlands"},
    {"nome":"Bradford","regione":"Yorkshire","country":"United Kingdom","lat":53.7960,"lon":-1.7594,"cluster":"GB_North"},
    {"nome":"Portsmouth","regione":"South East","country":"United Kingdom","lat":50.8198,"lon":-1.0880,"cluster":"GB_South"},
    {"nome":"Plymouth","regione":"South West","country":"United Kingdom","lat":50.3755,"lon":-4.1427,"cluster":"GB_South"},
    {"nome":"Aberdeen","regione":"Scotland","country":"United Kingdom","lat":57.1497,"lon":-2.0943,"cluster":"GB_Scotland"},
    {"nome":"Swansea","regione":"Wales","country":"United Kingdom","lat":51.6214,"lon":-3.9436,"cluster":"GB_Wales"},
    # ─── NUOVI PAESI ───
    # Grecia
    {"nome":"Atene","regione":"Attica","country":"Greece","lat":37.9838,"lon":23.7275,"cluster":"GR_Central"},
    {"nome":"Salonicco","regione":"Macedonia","country":"Greece","lat":40.6401,"lon":22.9444,"cluster":"GR_North"},
    {"nome":"Patrasso","regione":"Peloponneso","country":"Greece","lat":38.2444,"lon":21.7344,"cluster":"GR_South"},
    {"nome":"Heraklion","regione":"Creta","country":"Greece","lat":35.3387,"lon":25.1442,"cluster":"GR_Island"},
    {"nome":"Larissa","regione":"Tessaglia","country":"Greece","lat":39.6390,"lon":22.4191,"cluster":"GR_Central"},
    # Croazia
    {"nome":"Zagabria","regione":"Grad Zagreb","country":"Croatia","lat":45.8150,"lon":15.9819,"cluster":"HR_Central"},
    {"nome":"Spalato","regione":"Dalmazia","country":"Croatia","lat":43.5081,"lon":16.4402,"cluster":"HR_Coast"},
    {"nome":"Rijeka","regione":"Primorje-Gorski Kotar","country":"Croatia","lat":45.3271,"lon":14.4422,"cluster":"HR_Coast"},
    {"nome":"Osijek","regione":"Slavonia","country":"Croatia","lat":45.5550,"lon":18.6955,"cluster":"HR_East"},
    {"nome":"Zadar","regione":"Dalmazia","country":"Croatia","lat":44.1194,"lon":15.2314,"cluster":"HR_Coast"},
    # Repubblica Ceca
    {"nome":"Praga","regione":"Hlavni mesto Praha","country":"Czech Republic","lat":50.0755,"lon":14.4378,"cluster":"CZ_Central"},
    {"nome":"Brno","regione":"Jihomoravsky kraj","country":"Czech Republic","lat":49.1951,"lon":16.6068,"cluster":"CZ_South"},
    {"nome":"Ostrava","regione":"Moravskoslezsky kraj","country":"Czech Republic","lat":49.8209,"lon":18.2625,"cluster":"CZ_East"},
    {"nome":"Plzen","regione":"Plzensky kraj","country":"Czech Republic","lat":49.7384,"lon":13.3736,"cluster":"CZ_West"},
    # Ungheria
    {"nome":"Budapest","regione":"Budapest","country":"Hungary","lat":47.4979,"lon":19.0402,"cluster":"HU_Central"},
    {"nome":"Debrecen","regione":"Hajdu-Bihar","country":"Hungary","lat":47.5316,"lon":21.6273,"cluster":"HU_East"},
    {"nome":"Miskolc","regione":"Borsod-Abauj-Zemplen","country":"Hungary","lat":48.1035,"lon":20.7784,"cluster":"HU_North"},
    {"nome":"Pecs","regione":"Baranya","country":"Hungary","lat":46.0727,"lon":18.2323,"cluster":"HU_South"},
    {"nome":"Gyor","regione":"Gyor-Moson-Sopron","country":"Hungary","lat":47.6875,"lon":17.6504,"cluster":"HU_West"},
    # Romania
    {"nome":"Bucarest","regione":"Bucuresti","country":"Romania","lat":44.4268,"lon":26.1025,"cluster":"RO_Central"},
    {"nome":"Cluj-Napoca","regione":"Cluj","country":"Romania","lat":46.7712,"lon":23.6236,"cluster":"RO_West"},
    {"nome":"Timisoara","regione":"Timis","country":"Romania","lat":45.7489,"lon":21.2087,"cluster":"RO_West"},
    {"nome":"Iasi","regione":"Iasi","country":"Romania","lat":47.1585,"lon":27.6014,"cluster":"RO_East"},
    {"nome":"Constanta","regione":"Constanta","country":"Romania","lat":44.1733,"lon":28.6383,"cluster":"RO_Coast"},
    {"nome":"Brasov","regione":"Brasov","country":"Romania","lat":45.6427,"lon":25.5887,"cluster":"RO_Central"},
    # Polonia extra
    {"nome":"Lodz","regione":"Lodzkie","country":"Poland","lat":51.7592,"lon":19.4560,"cluster":"PL_Central"},
    {"nome":"Wroclaw","regione":"Dolnoslaskie","country":"Poland","lat":51.1079,"lon":17.0385,"cluster":"PL_South"},
    {"nome":"Poznan","regione":"Wielkopolskie","country":"Poland","lat":52.4064,"lon":16.9252,"cluster":"PL_West"},
    {"nome":"Gdansk","regione":"Pomorskie","country":"Poland","lat":54.3520,"lon":18.6466,"cluster":"PL_North"},
    {"nome":"Szczecin","regione":"Zachodniopomorskie","country":"Poland","lat":53.4285,"lon":14.5528,"cluster":"PL_North"},
    {"nome":"Lublin","regione":"Lubelskie","country":"Poland","lat":51.2465,"lon":22.5684,"cluster":"PL_East"},
    {"nome":"Katowice","regione":"Slaskie","country":"Poland","lat":50.2649,"lon":19.0238,"cluster":"PL_South"},
    # Svezia extra
    {"nome":"Gothenburg","regione":"Vastra Gotaland","country":"Sweden","lat":57.7089,"lon":11.9746,"cluster":"SE_West"},
    {"nome":"Malmo","regione":"Skane","country":"Sweden","lat":55.6050,"lon":13.0038,"cluster":"SE_South"},
    {"nome":"Vasteras","regione":"Vastmanland","country":"Sweden","lat":59.6099,"lon":16.5448,"cluster":"SE_Central"},
    {"nome":"Orebro","regione":"Orebro","country":"Sweden","lat":59.2741,"lon":15.2066,"cluster":"SE_Central"},
    {"nome":"Linkoping","regione":"Ostergotland","country":"Sweden","lat":58.4108,"lon":15.6214,"cluster":"SE_Central"},
    {"nome":"Helsingborg","regione":"Skane","country":"Sweden","lat":56.0465,"lon":12.6945,"cluster":"SE_South"},
    {"nome":"Jonkoping","regione":"Jonkoping","country":"Sweden","lat":57.7826,"lon":14.1618,"cluster":"SE_Central"},
    # Olanda extra
    {"nome":"Eindhoven","regione":"Noord-Brabant","country":"Netherlands","lat":51.4416,"lon":5.4697,"cluster":"NL_South"},
    {"nome":"Tilburg","regione":"Noord-Brabant","country":"Netherlands","lat":51.5555,"lon":5.0913,"cluster":"NL_South"},
    {"nome":"Groningen","regione":"Groningen","country":"Netherlands","lat":53.2194,"lon":6.5665,"cluster":"NL_North"},
    {"nome":"Breda","regione":"Noord-Brabant","country":"Netherlands","lat":51.5719,"lon":4.7683,"cluster":"NL_South"},
    {"nome":"Nijmegen","regione":"Gelderland","country":"Netherlands","lat":51.8426,"lon":5.8546,"cluster":"NL_Central"},
    {"nome":"Arnhem","regione":"Gelderland","country":"Netherlands","lat":51.9851,"lon":5.8987,"cluster":"NL_Central"},
    # Belgio extra
    {"nome":"Charleroi","regione":"Hainaut","country":"Belgium","lat":50.4108,"lon":4.4446,"cluster":"BE_South"},
    {"nome":"Namur","regione":"Namur","country":"Belgium","lat":50.4674,"lon":4.8720,"cluster":"BE_Central"},
    {"nome":"Bruges","regione":"West-Vlaanderen","country":"Belgium","lat":51.2093,"lon":3.2247,"cluster":"BE_West"},
    # Danimarca extra
    {"nome":"Aalborg","regione":"Nordjylland","country":"Denmark","lat":57.0488,"lon":9.9217,"cluster":"DK_North"},
    {"nome":"Esbjerg","regione":"Syddanmark","country":"Denmark","lat":55.4760,"lon":8.4593,"cluster":"DK_West"},
    # Norvegia extra
    {"nome":"Tromsoe","regione":"Troms","country":"Norway","lat":69.6492,"lon":18.9553,"cluster":"NO_North"},
    {"nome":"Fredrikstad","regione":"Viken","country":"Norway","lat":59.2181,"lon":10.9298,"cluster":"NO_South"},
    {"nome":"Kristiansand","regione":"Agder","country":"Norway","lat":58.1467,"lon":7.9956,"cluster":"NO_South"},
    # Svizzera extra
    {"nome":"Lugano","regione":"Ticino","country":"Switzerland","lat":46.0037,"lon":8.9511,"cluster":"CH_South"},
    {"nome":"Winterthur","regione":"Zurich","country":"Switzerland","lat":47.5006,"lon":8.7241,"cluster":"CH_North"},
    {"nome":"Lucerna","regione":"Luzern","country":"Switzerland","lat":47.0502,"lon":8.3093,"cluster":"CH_Central"},
    # Austria extra
    {"nome":"Klagenfurt","regione":"Karnten","country":"Austria","lat":46.6249,"lon":14.3050,"cluster":"AT_South"},
    {"nome":"Sankt Polten","regione":"Niederosterreich","country":"Austria","lat":48.2047,"lon":15.6256,"cluster":"AT_Central"},
    # Portogallo extra
    {"nome":"Setubal","regione":"Setubal","country":"Portugal","lat":38.5243,"lon":-8.8926,"cluster":"PT_Central"},
    {"nome":"Coimbra","regione":"Centro","country":"Portugal","lat":40.2033,"lon":-8.4103,"cluster":"PT_Central"},
    {"nome":"Faro","regione":"Algarve","country":"Portugal","lat":37.0194,"lon":-7.9322,"cluster":"PT_South"},
    {"nome":"Funchal","regione":"Madeira","country":"Portugal","lat":32.6669,"lon":-16.9241,"cluster":"PT_Island"},
    # Finlandia
    {"nome":"Helsinki","regione":"Uusimaa","country":"Finland","lat":60.1699,"lon":24.9384,"cluster":"FI_South"},
    {"nome":"Tampere","regione":"Pirkanmaa","country":"Finland","lat":61.4978,"lon":23.7610,"cluster":"FI_Central"},
    {"nome":"Turku","regione":"Varsinais-Suomi","country":"Finland","lat":60.4518,"lon":22.2666,"cluster":"FI_South"},
    {"nome":"Oulu","regione":"Pohjois-Pohjanmaa","country":"Finland","lat":65.0121,"lon":25.4651,"cluster":"FI_North"},
    # Slovenia
    {"nome":"Ljubljana","regione":"Osrednjeslovenska","country":"Slovenia","lat":46.0569,"lon":14.5058,"cluster":"SI_Central"},
    {"nome":"Maribor","regione":"Podravska","country":"Slovenia","lat":46.5547,"lon":15.6459,"cluster":"SI_East"},
    # Slovacchia
    {"nome":"Bratislava","regione":"Bratislavsky kraj","country":"Slovakia","lat":48.1486,"lon":17.1077,"cluster":"SK_Central"},
    {"nome":"Kosice","regione":"Kosicky kraj","country":"Slovakia","lat":48.7164,"lon":21.2611,"cluster":"SK_East"},
    # Serbia
    {"nome":"Belgrado","regione":"Grad Beograd","country":"Serbia","lat":44.8176,"lon":20.4569,"cluster":"RS_Central"},
    {"nome":"Novi Sad","regione":"Vojvodina","country":"Serbia","lat":45.2671,"lon":19.8335,"cluster":"RS_North"},
]

with open('data/province_coords.json') as f:
    raw = json.load(f)
provinces = raw['province'] if 'province' in raw else raw

existing = {p['nome'] for p in provinces}
added = 0
for n in new_nodes:
    if n['nome'] not in existing:
        provinces.append(n)
        added += 1

if 'province' in raw:
    raw['province'] = provinces
    data = raw
else:
    data = provinces

with open('data/province_coords.json','w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

from collections import Counter
countries = Counter(p.get('country','?') for p in provinces)
print(f"Aggiunti: {added} nuovi nodi")
print(f"Totale: {len(provinces)} nodi")
print("\nPer paese:")
for c, n in sorted(countries.items(), key=lambda x: -x[1]):
    print(f"  {c}: {n}")
