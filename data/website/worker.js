const VALID_IT = new Set(["abano-terme", "abbiategrasso", "abruzzo", "acerra", "acilia", "acireale", "acquaviva-delle-fonti", "acqui-terme", "adelfia", "adrano", "adria", "afragola", "aglie", "agna", "agrate-brianza", "agrigento", "agropoli", "aicurzio", "alatri", "alba", "albano-laziale", "albignasego", "alcamo", "alessandria", "alghero", "alme", "alpignano", "altamura", "altavilla-milicia", "alzano-lombardo", "ambivere", "amelia", "anacapri", "ancona", "andria", "angri", "anzio", "aosta", "aprilia", "arcore", "ardea", "arezzo", "argelato", "argentera", "ariccia", "arona", "artena", "arzano", "arzignano", "ascoli-piceno", "asola", "aspra", "assago", "assemini", "assisi", "asti", "atri", "augusta", "avellino", "aversa", "avezzano", "avigliana", "avola", "azzano", "bacoli", "bagheria", "bagnatica", "bagno-a-ripoli", "baldissero-torinese", "baone", "barano-d-ischia", "barberino-di-mugello", "barberino-tavarnelle", "barcellona-pozzo-di-gotto", "bari", "baricella", "barletta", "barletta-andria-trani", "basilicata", "bassano-del-grappa", "battipaglia", "beinasco", "bellegra", "bellinzago-lombardo", "belluno", "bellusco", "belmonte-mezzagno", "benevento", "bentivoglio", "bergamo", "bernareggio", "biella", "binasco", "binetto", "bisceglie", "bitetto", "bitonto", "bitritto", "bollate", "bologna", "bolognetta", "bolzano", "bonate-sopra", "bonate-sotto", "borgaro-torinese", "borgo-san-dalmazzo", "borgo-san-lorenzo", "borgomanero", "bosco-marengo", "bovegno", "boves", "bovezzo", "bovisio-masciago", "bra", "bracciano", "brandizzo", "breno", "brescia", "bressanone", "brindisi", "brugherio", "bruino", "brusaporto", "bubbiano", "buccinasco", "budrio", "burago-di-molgora", "burcei", "busca", "busnago", "busto-arsizio", "busto-garolfo", "cabras", "caccamo", "cagliari", "caivano", "calabria", "calderara-di-reno", "calenzano", "calimera", "caltabellotta", "caltagirone", "caltanissetta", "calusco-d-adda", "caluso", "calvignasco", "calvizzano", "cambiago", "cambiano", "campania", "camparada", "campi-bisenzio", "campobasso", "campofelice-di-roccella", "canegrate", "canelli", "canicatti", "cantu", "capannori", "capo-di-ponte", "caponago", "capoterra", "capranica-prenestina", "capri", "capriate-san-gervasio", "capurso", "carate-brianza", "carbonera", "carbonia", "carignano", "carini", "carmagnola", "carnate", "carpi", "carpineto-romano", "carrara", "carugate", "carvico", "casale-monferrato", "casalecchio-di-reno", "casalmaggiore", "casalnuovo-di-napoli", "casalserugo", "casamassima", "casamicciola-terme", "casandrino", "casavatore", "cascina", "caserta", "casoria", "cassina-de-pecchi", "cassino", "castagnole-delle-lanze", "castel-di-sangro", "castel-gandolfo", "castel-guelfo-di-bologna", "castel-maggiore", "castel-san-giovanni", "castelbuono", "castelfranco-emilia", "castelfranco-veneto", "castellammare-di-stabia", "castellamonte", "castellana-grotte", "castellaneta", "castellanza", "castelmagno", "castelnuovo-di-garfagnana", "castiglione-della-pescaia", "castiglione-delle-stiviere", "castiglione-torinese", "castrovillari", "catania", "catanzaro", "cattolica", "cava-de-tirreni", "cavallermaggiore", "cave", "cavernago", "cecina", "cefalu", "cellamare", "cellatica", "centallo", "cento", "cerignola", "cernusco-sul-naviglio", "cerro-maggiore", "cerveteri", "cesano-boscone", "cesano-maderno", "cesate", "cesena", "cesenatico", "ceva", "chatillon", "chiaravalle", "chiavari", "chieri", "chieti", "chioggia", "chivasso", "ciampino", "cigliano", "cinisello-balsamo", "cinto-euganeo", "cirie", "cison-di-valmarino", "cisterna-di-latina", "citta-di-castello", "cittadella", "civitanova-marche", "civitavecchia", "col-san-martino", "colle-di-val-d-elsa", "collebeato", "collegno", "collesano", "collio", "cologno-monzese", "colonna", "comiso", "como", "concesio", "concorezzo", "conegliano", "conversano", "copertino", "corato", "corbetta", "corigliano-calabro", "corigliano-rossano", "correggio", "correzzola", "corsico", "cortona", "cosenza", "costa-di-mezzate", "costigliole-d-asti", "courmayeur", "crema", "cremona", "crescentino", "crevalcore", "crotone", "cuggiono", "cuneo", "cuorgne", "curno", "cusago", "dalmine", "darfo-boario-terme", "decimomannu", "decimoputzu", "demonte", "desenzano-del-garda", "desio", "dicomano", "dolianova", "domodossola", "donori", "dronero", "due-carrare", "eboli", "edolo", "elmas", "emilia-romagna", "empoli", "enna", "ercolano", "este", "fabriano", "faenza", "falconara-marittima", "fano", "farra-di-soligo", "fasano", "favara", "felizzano", "fermo", "ferrara", "ficarazzi", "fidenza", "fiesole", "figline-e-incisa-valdarno", "filago", "firenze", "fiumicino", "foggia", "foglizzo", "foligno", "follina", "follonica", "fondi", "forio", "forli", "forli-cesena", "formia", "formigine", "forte-dei-marmi", "fossano", "francavilla-al-mare", "francavilla-fontana", "frascati", "friuli-venezia-giulia", "front", "frosinone", "frugarolo", "gaeta", "gaggiano", "gallarate", "galliera", "gallipoli", "garbagnate-milanese", "gardone-val-trompia", "garessio", "gassino-torinese", "gela", "genazzano", "genoa", "genova", "genzano-di-roma", "giarre", "ginosa", "giovinazzo", "giugliano-in-campania", "giulianova", "godrano", "gorgonzola", "gorizia", "gorle", "granarolo-dell-emilia", "grassobbio", "gratteri", "gravina-in-puglia", "greve-in-chianti", "grosseto", "grottaferrata", "grottaglie", "grugliasco", "grumo-appula", "guastalla", "gubbio", "guidonia-montecelio", "gussago", "iesi", "iglesias", "imola", "imperia", "impruneta", "inveruno", "inzago", "irma", "iseo", "isernia", "isnello", "isola-d-asti", "isola-di-capo-rizzuto", "ivrea", "jesi", "l-aquila", "la-spezia", "lacchiarella", "lacco-ameno", "ladispoli", "lainate", "lamezia-terme", "lanciano", "langhirano", "lanuvio", "laquila", "lariano", "lascari", "lastra-a-signa", "laterza", "latina", "lazio", "lecce", "lecco", "legnago", "legnano", "legnaro", "leini", "lentini", "licata", "liguria", "limbiate", "limone-piemonte", "liscate", "lissone", "livorno", "livorno-ferraris", "locate-di-triulzi", "lodi", "lodi-vecchio", "lodrino", "lombardia", "londa", "lozzo-atestino", "lucca", "lucera", "lugo", "luino", "lumezzane", "macerata", "maddaloni", "magenta", "maglie", "malalbergo", "manduria", "manfredonia", "mantova", "mapello", "maracalagonis", "marano-di-napoli", "marche", "marcheno", "marcianise", "marengo", "marigliano", "marina-di-carrara", "marineo", "marino", "marone", "marradi", "marsala", "martina-franca", "mascalucia", "masera-di-padova", "massa", "massa-carrara", "massa-marittima", "massafra", "matera", "mazara-del-vallo", "medicina", "medolago", "melfi", "melito-di-napoli", "melzo", "mentana", "merano", "merate", "mesagne", "messina", "mestre", "mezzago", "mezzojuso", "miane", "milan", "milano", "milazzo", "minerbio", "minervino-murge", "mira", "mirandola", "misilmeri", "misterbianco", "modena", "modica", "modugno", "mogliano-veneto", "molfetta", "molinella", "molise", "mombercelli", "monastir", "moncalieri", "mondovi", "monfalcone", "monopoli", "monreale", "monselice", "monserrato", "monsummano-terme", "montagnana", "montalto-di-castro", "montanaro", "monte-compatri", "monte-di-procida", "monte-porzio-catone", "montebelluna", "montecatini-terme", "montecompatri", "montelupo-fiorentino", "montepulciano", "monterotondo", "montesilvano", "monticelli-brusati", "monza", "monza-e-brianza", "monza-e-della-brianza", "morgano", "moriago-della-battaglia", "motta-visconti", "muggio", "mugnano-di-napoli", "muravera", "naples", "napoli", "nardo", "narni", "nave", "nerviano", "nettuno", "nicastro", "nichelino", "nicosia", "nizza-monferrato", "nocera-inferiore", "noci", "nogara", "noicattaro", "nola", "none", "noto", "nova-milanese", "novara", "nuoro", "nuraminis", "oderzo", "olbia", "olevano-romano", "ome", "opera", "orio-al-serio", "oristano", "ornago", "orosei", "ortona", "orvieto", "orzinuovi", "osimo", "osio-sopra", "osio-sotto", "ostia", "ostuni", "ovada", "ozieri", "paderno-dugnano", "padova", "paese", "pagani", "paladina", "palazzuolo-sul-senio", "palermo", "palestrina", "palo-del-colle", "paola", "parabiago", "parma", "partanna", "partinico", "paterno", "patti", "pavia", "pavullo-nel-frignano", "pecetto-torinese", "pedrengo", "pelago", "pernumia", "perugia", "pesaro", "pesaro-e-urbino", "pescara", "peschiera-borromeo", "pescia", "pessano-con-bornago", "pezzaze", "piacenza", "piazza-armerina", "piemonte", "pietraporzio", "pieve-di-cento", "pieve-di-soligo", "pinerolo", "pineto", "pino-torinese", "pioltello", "piombino", "piove-di-sacco", "pisa", "pisogne", "pistoia", "poggibonsi", "poggiorsini", "pollina", "polverara", "pomezia", "pomigliano-darco", "pontassieve", "ponte-san-nicolo", "ponte-san-pietro", "pontedera", "ponteranica", "ponzano-veneto", "pordenone", "portici", "porto-san-giorgio", "porto-tolle", "porto-torres", "potenza", "pozzuoli", "pradleves", "prato", "preganziol", "provaglio-d-iseo", "puglia", "pula", "qualiano", "quargnento", "quarto", "quartu-sant-elena", "quartu-santelena", "quattordio", "quinto-di-treviso", "racconigi", "ragusa", "rapallo", "ravenna", "refrontolo", "reggello", "reggio-calabria", "reggio-di-calabria", "reggio-emilia", "rende", "rescaldina", "rho", "riccione", "riccione-marina", "rieti", "rignano-sull-arno", "rimini", "riva-del-garda", "rivalta-di-torino", "rivarolo-canavese", "rivoli", "robassomero", "robecco-sul-naviglio", "rocca-di-papa", "rocca-priora", "rocchetta-tanaro", "rodano", "rodengo-saiano", "roma", "romano-di-lombardia", "rome", "roncade", "roncaglia", "roncello", "rondissone", "rosate", "roseto-degli-abruzzi", "rossano", "rovereto", "rovigo", "rovolon", "rozzano", "rufina", "russi", "rutigliano", "ruvo-di-puglia", "sale-marasino", "salerno", "salsomaggiore-terme", "saluzzo", "samatzai", "sambuco", "sammichele-di-bari", "san-benedetto-del-tronto", "san-benigno-canavese", "san-bonifacio", "san-casciano-in-val-di-pesa", "san-cesareo", "san-dona-di-piave", "san-donato-milanese", "san-giorgio-a-cremano", "san-giorgio-canavese", "san-giorgio-su-legnano", "san-giovanni-a-teduccio", "san-giovanni-in-persiceto", "san-giuliano-milanese", "san-giuliano-terme", "san-giuseppe-vesuviano", "san-godenzo", "san-lazzaro-di-savena", "san-marzano-oliveto", "san-mauro-torinese", "san-miniato", "san-pietro-in-casale", "san-remo", "san-salvo", "san-sebastiano-da-po", "san-severo", "san-sperate", "san-vito-romano", "sannicandro-di-bari", "sannicandro-garganico", "sanremo", "sant-agata-bolognese", "sant-agata-sul-santerno", "sant-angelo-d-ischia", "sant-angelo-di-piove-di-sacco", "sant-angelo-in-vado", "sant-antimo", "santa-flavia", "santa-maria-capua-vetere", "santantimo", "santarcangelo-di-romagna", "santena", "santeufemia-lamezia", "saonara", "sardegna", "sarezzo", "sarno", "saronno", "sarroch", "sassari", "sasso-marconi", "sassuolo", "savigliano", "savona", "scafati", "scandicci", "scanzorosciate", "scarperia-e-san-piero", "schio", "sciacca", "scillato", "sclafani-bagni", "secondigliano", "segni", "segrate", "selargius", "senigallia", "seregno", "serra-san-bruno", "serrara-fontana", "sesto-calende", "sesto-fiorentino", "sesto-san-giovanni", "sestu", "settala", "settimo-san-pietro", "settimo-torinese", "sezzadio", "sicilia", "siena", "signa", "silea", "siniscola", "sinnai", "siracusa", "soazza", "solaro", "solero", "solza", "somma-vesuviana", "sondrio", "sora", "sorisole", "sotto-il-monte-giovanni-xxiii", "spinazzola", "spirano", "spoleto", "stezzano", "sud-sardegna", "suisio", "sulbiate", "sulmona", "sulzano", "susegana", "taranto", "tavernole-sul-mella", "teolo", "teramo", "terlizzi", "termini-imerese", "termoli", "terni", "terracina", "terralba", "thiene", "tivoli", "tolentino", "torino", "torrazza-piemonte", "torre-annunziata", "torre-del-greco", "tortoli", "tortona", "toscana", "trabia", "tradate", "trani", "trapani", "trentino-alto-adige", "trento", "treviglio", "treviso", "trezzano-sul-naviglio", "tribano", "trieste", "triggiano", "trofarello", "tropea", "turi", "turin", "udine", "umbria", "usmate-velate", "uta", "vaglia", "valdagno", "valdobbiadene", "valenza", "valenzano", "valle-d-aosta", "valperga", "varedo", "varese", "vasto", "velletri", "venaria-reale", "veneto", "venezia", "venice", "ventimiglia", "verbania", "verbano-cusio-ossola", "vercelli", "vernante", "vernate", "verolengo", "verona", "viareggio", "vibo-valentia", "vicchio", "vicenza", "vigevano", "vignola", "villa-carcina", "villa-d-alme", "villa-san-pietro", "villabate", "villacidro", "villafranca-di-verona", "villanova-mondovi", "villaricca", "villasanta", "villasor", "villaspeciosa", "villorba", "vimercate", "vimodrone", "vinadio", "vinovo", "viterbo", "vittoria", "vittorio-veneto", "vo", "voghera", "volpiano", "zagarolo", "zanica", "zibido-san-giacomo", "zone"]);
const COMUNI_PROVINCES = {"torino":"Torino","milano":"Milano","roma":"Roma","napoli":"Napoli","bologna":"Bologna","firenze":"Firenze","venezia":"Venezia","genova":"Genova","palermo":"Palermo","bari":"Bari"};

async function handleComune(provincia, comune, request) {
  const API = "https://artkill24-weatherarb-api.hf.space";
  
  // Fetch dati meteo provincia più vicina
  let weatherData = null;
  try {
    const r = await fetch(`${API}/api/v1/pulse/${provincia}`, {cf:{cacheTtl:3600}});
    if(r.ok) weatherData = await r.json();
  } catch(e) {}

  const z = weatherData?.weather?.z_score || 0;
  const temp = weatherData?.weather?.temperature_c || '--';
  const level = weatherData?.weather?.anomaly_level || 'NORMAL';
  const event = (weatherData?.weather?.event_type || 'clear').replace(/_/g,' ');
  const sign = z >= 0 ? '+' : '';
  const colors = {CRITICAL:'#ef4444',EXTREME:'#f97316',UNUSUAL:'#eab308',NORMAL:'#10b981'};
  const color = colors[level] || '#10b981';
  
  const comuneName = comune.split('-').map(w=>w.charAt(0).toUpperCase()+w.slice(1)).join(' ');
  const provName = provincia.split('-').map(w=>w.charAt(0).toUpperCase()+w.slice(1)).join(' ');

  const html = `<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Meteo ${comuneName} — Anomalie Z-Score | WeatherArb</title>
  <meta name="description" content="Dati meteo e anomalie climatiche per ${comuneName} (${provName}). Z-Score NASA POWER 25 anni, HDD/CDD energy data, Space Weather.">
  <link rel="canonical" href="https://weatherarb.com/it/${provincia}/${comune}/">
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{background:#040608;color:#c8d6e5;font-family:-apple-system,sans-serif;min-height:100vh}
    .hdr{border-bottom:1px solid #141920;padding:14px 24px;display:flex;align-items:center;justify-content:space-between}
    .logo{font-size:13px;font-weight:700;letter-spacing:.2em;text-decoration:none;color:#c8d6e5}
    .logo span{color:#3b82f6}
    .wrap{max-width:800px;margin:0 auto;padding:48px 24px}
    .breadcrumb{font-size:12px;color:#4a5568;margin-bottom:24px}
    .breadcrumb a{color:#4a5568;text-decoration:none}
    .breadcrumb a:hover{color:#3b82f6}
    h1{font-size:36px;font-weight:900;color:#fff;margin-bottom:8px}
    .subtitle{font-size:16px;color:#4a5568;margin-bottom:32px}
    .card{background:#0a0d12;border:1px solid #141920;border-radius:16px;padding:28px;margin-bottom:20px}
    .card-title{font-size:11px;text-transform:uppercase;letter-spacing:.2em;color:#4a5568;margin-bottom:16px}
    .metric{display:flex;align-items:baseline;gap:8px;margin-bottom:8px}
    .metric-val{font-size:48px;font-weight:900}
    .metric-label{font-size:14px;color:#4a5568}
    .badge{display:inline-block;padding:4px 12px;border-radius:100px;font-size:12px;font-weight:700;text-transform:uppercase;margin-bottom:16px}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-top:16px}
    .stat{background:#141920;border-radius:10px;padding:16px;text-align:center}
    .stat-val{font-size:24px;font-weight:800;color:#fff}
    .stat-lbl{font-size:11px;color:#4a5568;margin-top:4px;text-transform:uppercase}
    .cta{display:block;background:#2563eb;color:#fff;padding:16px;border-radius:10px;text-align:center;font-weight:700;text-decoration:none;margin-top:24px}
    .related{margin-top:8px}
    .related a{display:inline-block;background:#141920;border-radius:6px;padding:6px 12px;font-size:12px;color:#c8d6e5;text-decoration:none;margin:4px}
    .related a:hover{background:#1e2d3d}
  </style>
  <script type="application/ld+json">{"@context":"https://schema.org","@type":"WebPage","name":"Meteo ${comuneName}","description":"Anomalie meteo per ${comuneName}","url":"https://weatherarb.com/it/${provincia}/${comune}/"}</script>
</head>
<body>
<header class="hdr">
  <a href="/" class="logo">Weather<span>Arb</span></a>
  <nav style="display:flex;gap:16px">
    <a href="/it/${provincia}/" style="font-size:11px;color:#4a5568;text-decoration:none">${provName}</a>
    <a href="/leaderboard/" style="font-size:11px;color:#4a5568;text-decoration:none">Leaderboard</a>
  </nav>
</header>
<div class="wrap">
  <div class="breadcrumb">
    <a href="/">WeatherArb</a> › <a href="/it/">Italia</a> › <a href="/it/${provincia}/">${provName}</a> › ${comuneName}
  </div>
  <h1>Meteo ${comuneName}</h1>
  <p class="subtitle">Anomalie climatiche in tempo reale · Provincia di ${provName}</p>
  
  <div class="card">
    <div class="card-title">📡 Anomalia Rilevata</div>
    <div class="badge" style="background:${color}22;color:${color}">${level}</div>
    <div class="metric">
      <div class="metric-val" style="color:${color}">${sign}${z.toFixed(2)}σ</div>
      <div class="metric-label">Z-Score vs baseline 25 anni NASA POWER</div>
    </div>
    <div class="grid">
      <div class="stat"><div class="stat-val">${temp}°C</div><div class="stat-lbl">Temperatura</div></div>
      <div class="stat"><div class="stat-val" style="text-transform:capitalize">${event}</div><div class="stat-lbl">Evento</div></div>
      <div class="stat"><div class="stat-val">${weatherData?.weather?.humidity_pct || '--'}%</div><div class="stat-lbl">Umidità</div></div>
      <div class="stat"><div class="stat-val">${weatherData?.weather?.wind_kmh || '--'}</div><div class="stat-lbl">Vento km/h</div></div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">⚡ Energy Data — HDD/CDD</div>
    <div class="grid">
      <div class="stat"><div class="stat-val">${weatherData?.weather?.hdd?.toFixed(1) || '0.0'}</div><div class="stat-lbl">HDD oggi</div></div>
      <div class="stat"><div class="stat-val">${weatherData?.weather?.cdd?.toFixed(1) || '0.0'}</div><div class="stat-lbl">CDD oggi</div></div>
      <div class="stat"><div class="stat-val">${weatherData?.weather?.hdd_delta?.toFixed(1) || '0.0'}</div><div class="stat-lbl">Delta HDD</div></div>
    </div>
  </div>

  <a href="/it/${provincia}/" class="cta">Vedi tutti i dati per la Provincia di ${provName} →</a>
  
  <div class="card" style="margin-top:20px">
    <div class="card-title">🗺️ Altri comuni in provincia</div>
    <div class="related">
      <a href="/it/${provincia}/">Capoluogo ${provName}</a>
      <a href="/leaderboard/">Top Anomalie Globali</a>
      <a href="/data/">Dashboard Live</a>
    </div>
  </div>
</div>
</body>
</html>`;

  return new Response(html, {
    headers: {'Content-Type':'text/html;charset=UTF-8','Cache-Control':'public,max-age=3600'}
  });
}

// Slug redirect map per 404 comuni
async function trySlugRedirect(pathname, env) {
    // Es: /eu/viacha/ → cerca in tutti i cc
    const parts = pathname.split('/').filter(Boolean)
    if (parts.length === 2) {
        const [cc, slug] = parts
        // Lista cc validi
        const VALID_CC = ['bo','ar','br','cl','co','pe','ve','mx','us','ca','gb','de','fr','it','es','pt','pl','ro','gr','tr','ma','eg','ng','za','in','pk','bd','cn','jp','kr','id','ph','vn','th','au']
        if (!VALID_CC.includes(cc)) {
            // Prova a trovare lo slug in altri cc
            for (const trycc of VALID_CC) {
                try {
                    const r = await env.ASSETS.fetch(new Request(`https://fake/${trycc}/${slug}/`))
                    if (r.status === 200) {
                        return Response.redirect(`https://weatherarb.com/${trycc}/${slug}/`, 301)
                    }
                } catch(e) {}
            }
        }
    }
    return null
}

export default {
  async fetch(request, env) {
    // 301: /de/de/x/ -> /de/x/ (duplicati annidati rimossi)
    {
      const u = new URL(request.url);
      const m = u.pathname.match(/^\/(de|ru|tr|id)\/\1\/(.*)$/);
      if (m) return Response.redirect(`${u.origin}/${m[1]}/${m[2]}${u.search}`, 301);
    }
    // 301: /de/de/x/ -> /de/x/ (duplicati annidati rimossi)
    {
      const u = new URL(request.url);
      const m = u.pathname.match(/^\/(de|ru|tr|id)\/\1\/(.*)$/);
      if (m) return Response.redirect(`${u.origin}/${m[1]}/${m[2]}${u.search}`, 301);
    }
    const url = new URL(request.url);
    const path = url.pathname;
    
    // Match /it/{provincia}/{comune}/
    const match = path.match(/^\/it\/([a-z0-9-]+)\/([a-z0-9-]+)\/?$/);
    if (match) {
      const provincia = match[1];
      const comune = match[2];
      // 1. se esiste la pagina statica flat -> 301 (consolida i duplicati)
      const flat = await env.ASSETS.fetch(new Request(`https://a/it/${comune}/`));
      if (flat.status === 200) {
        return Response.redirect(`https://weatherarb.com/it/${comune}/`, 301);
      }
      // 2. provincia/regione non valida -> 404 (chiude lo spazio URL infinito)
      if (!VALID_IT.has(provincia)) {
        return new Response('Not Found', { status: 404 });
      }
      return handleComune(provincia, comune, request);
    }
    
    // Passa tutto il resto agli asset statici
    return env.ASSETS.fetch(request);
  }
};
