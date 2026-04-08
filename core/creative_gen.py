"""The Architect — Creative Generator (Sprint 2)"""
import json, logging, os, re, time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

CLUSTER_PERSONAS = {
    "NE_Industrial": {"tono": "Concreto, diretto, da uomo a uomo.", "vocabolario": ["capannone", "lavoro", "durata"], "evita": ["lusso", "lifestyle"]},
    "Metro_Hub": {"tono": "Efficiente, diretto, zero sentimentalismo.", "vocabolario": ["pratico", "veloce", "consegna rapida"], "evita": ["caldo", "tradizione"]},
    "Po_Valley": {"tono": "Caldo, comunitario, parla come un vicino.", "vocabolario": ["nella Bassa", "pratico", "chi conosce"], "evita": ["metropolitano", "innovativo"]},
    "Alpine_Extreme": {"tono": "Asciutto, tecnico, qualità prima del prezzo.", "vocabolario": ["durevole", "qualità", "vale l'investimento"], "evita": ["offerta", "sconto"]},
    "Coastal_NE": {"tono": "Ironico, consapevole, non allarmista.", "vocabolario": ["umidità", "chi ci abita", "laguna"], "evita": ["emergenza", "pericolo"]},
    "NW_Industrial": {"tono": "Essenziale, niente fronzoli.", "vocabolario": ["affidabile", "robusto", "funziona"], "evita": ["esclusivo", "rivoluzionario"]},
}
_DEFAULT_PERSONA = CLUSTER_PERSONAS["Po_Valley"]

GLOBAL_FORBIDDEN = ["emergenza","paura","catastrofe","ultima occasione","affrettati","scorte esaurite","ACQUISTA ORA"]

@dataclass
class CreativeRequest:
    provincia: str; regione: str; cluster: str; evento: str
    z_score: float; anomaly_level: str; fase: str
    prodotto_nome: str; prodotto_categoria: str; amazon_tag: str; prezzo_medio: float
    frame_emotivo: str = "local_identity"
    peak_ore: Optional[int] = None
    historical_roi: Optional[float] = None

@dataclass
class CreativeVariant:
    label: str; headline: str; subheadline: str; body_preview: str; frame_emotivo: str
    fear_score: float = 0.0; urgency_score: float = 0.0
    def __post_init__(self): self.char_count = len(self.headline)

@dataclass
class CreativeOutput:
    request: CreativeRequest
    variants: List[CreativeVariant] = field(default_factory=list)
    approved_variants: List[CreativeVariant] = field(default_factory=list)
    blocked_variants: List[CreativeVariant] = field(default_factory=list)
    generation_time_ms: float = 0.0
    model_used: str = ""
    error: Optional[str] = None
    def best_variant(self): return self.approved_variants[0] if self.approved_variants else None

def score_copy(text):
    t = text.lower()
    fear = sum(1 for w in ["affoga","distrugge","rovina","pericolo","danno","grave"] if w in t)
    urgency = sum(1 for w in ["adesso","subito","immediato","ultima","scade","oggi"] if w in t)
    forbidden = sum(1 for w in GLOBAL_FORBIDDEN if w.lower() in t)
    return round(min(fear*0.2 + forbidden*0.4, 1.0), 2), round(min(urgency*0.15 + forbidden*0.4, 1.0), 2)

def is_copy_approved(v, fase):
    text = f"{v.headline} {v.subheadline}".lower()
    for w in GLOBAL_FORBIDDEN:
        if w.lower() in text: return False, f"Parola vietata: {w}"
    if v.fear_score > 0.6: return False, f"Fear score: {v.fear_score}"
    max_u = 0.4 if fase == "PRE_EVENT_PREP" else 0.7
    if v.urgency_score > max_u: return False, f"Urgency: {v.urgency_score}"
    if len(v.headline) > 65: return False, f"Headline lunga: {len(v.headline)}"
    return True, "OK"

def build_prompt(req):
    persona = CLUSTER_PERSONAS.get(req.cluster, _DEFAULT_PERSONA)
    ledger_ctx = f"\nLedger: ROI storico {req.historical_roi:.1f}x con frame '{req.frame_emotivo}'." if req.historical_roi else ""
    peak_ctx = f"Picco previsto in {req.peak_ore} ore." if req.peak_ore else ""
    # Determina lingua in base al cluster
    lang_map = {
        "DE_Metro": "German", "DE_Industrial": "German",
        "DE_Alpine": "German", "DE_Coastal": "German",
    }
    lang = lang_map.get(req.cluster, "Italian")
    lang_instruction = f"Write EXCLUSIVELY in {lang}. Never mix languages." if lang != "Italian" else "Scrivi in italiano."

    return f"""Sei un esperto di Native Advertising locale. {lang_instruction}
EVENTO: {req.provincia} ({req.regione}) | {req.evento} | {req.anomaly_level} | Z={req.z_score:+.2f} | {peak_ctx}
PRODOTTO: {req.prodotto_nome} | €{req.prezzo_medio:.0f}
TONO ({req.cluster}): {persona['tono']}
VOCABOLARIO: {', '.join(persona['vocabolario'])}
EVITA: {', '.join(persona['evita'])}
FRAME: {req.frame_emotivo}{ledger_ctx}
REGOLE: headline max 60 caratteri. Vietato: {', '.join(GLOBAL_FORBIDDEN[:5])}.
Genera 3 varianti JSON:
{{"variants":[{{"label":"A","frame":"local_identity","headline":"...","subheadline":"...","body_preview":"..."}},{{"label":"B","frame":"solution","headline":"...","subheadline":"...","body_preview":"..."}},{{"label":"C","frame":"urgency","headline":"...","subheadline":"...","body_preview":"..."}}]}}"""

class GeminiCreativeGenerator:
    MODEL = "gemini-2.5-flash"

    def __init__(self, api_key=""):
        self.api_key = api_key or GEMINI_API_KEY
        self.client = None
        self._init_client()

    def _init_client(self):
        if not self.api_key or self.api_key == "YOUR_GEMINI_KEY":
            logger.warning("Gemini API key non configurata — uso fallback templates")
            return
        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
            logger.info(f"Gemini client inizializzato ({self.MODEL})")
        except ImportError:
            logger.warning("Installa: pip install google-genai")
        except Exception as e:
            logger.warning(f"Gemini init fallito: {e}")

    def generate(self, req):
        start = time.time()
        output = CreativeOutput(request=req, model_used=self.MODEL)
        prompt = build_prompt(req)
        raw = self._call_gemini(prompt) if self.client else self._fallback(req)
        for rv in raw:
            fear, urgency = score_copy(f"{rv.get('headline','')} {rv.get('subheadline','')}")
            v = CreativeVariant(label=rv.get("label","?"), headline=rv.get("headline",""),
                subheadline=rv.get("subheadline",""), body_preview=rv.get("body_preview",""),
                frame_emotivo=rv.get("frame", req.frame_emotivo), fear_score=fear, urgency_score=urgency)
            ok, reason = is_copy_approved(v, req.fase)
            (output.approved_variants if ok else output.blocked_variants).append(v)
            if not ok: logger.info(f"Variante {v.label} bloccata: {reason}")
        output.variants = output.approved_variants + output.blocked_variants
        output.generation_time_ms = round((time.time()-start)*1000, 1)
        return output

    def _call_gemini(self, prompt):
        try:
            response = self.client.models.generate_content(model=self.MODEL, contents=prompt)
            text = re.sub(r"```json\s*|\s*```", "", response.text.strip()).strip()
            return json.loads(text).get("variants", [])
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return []

    def _fallback(self, req):
        p, prod = req.provincia, req.prodotto_nome
        return [
            {"label":"A","frame":"local_identity","headline":f"{p}: cosa fare prima che arrivi la pioggia","subheadline":f"I residenti del {req.regione} conoscono il problema. Ecco la soluzione.","body_preview":f"Chi vive in {p} sa che certe piogge non avvisano."},
            {"label":"B","frame":"solution","headline":f"Umidità in casa a {p}? Questo risolve.","subheadline":f"{prod} — scelto da chi non vuole sorprese.","body_preview":f"Con le previsioni di pioggia, il {prod} è la scelta pratica."},
            {"label":"C","frame":"urgency","headline":f"Pioggia intensa su {p}: guida pratica","subheadline":f"Cosa fare nelle prossime {req.peak_ore or 48} ore.","body_preview":f"Le previsioni per {p} indicano precipitazioni sopra la media."},
        ]

def pulse_to_creative_request(pulse_json, product, historical_roi=None, frame_emotivo="local_identity"):
    loc = pulse_json.get("location", {}); trig = pulse_json.get("weather_trigger", {})
    peak_str = trig.get("peak_expected_in", "N/A")
    peak_ore = None
    try: peak_ore = int(peak_str.replace("h","")) if peak_str != "N/A" else None
    except: pass
    return CreativeRequest(
        provincia=loc.get("provincia",""), regione=loc.get("regione",""),
        cluster=loc.get("cluster","Po_Valley"), evento=trig.get("type",""),
        z_score=trig.get("z_score",0), anomaly_level=trig.get("anomaly_level",""),
        fase=pulse_json.get("action_plan",{}).get("phase",""),
        prodotto_nome=product.get("nome", product.get("categoria","")),
        prodotto_categoria=product.get("categoria",""), amazon_tag=product.get("amazon_tag",""),
        prezzo_medio=float(product.get("prezzo_medio",0)),
        frame_emotivo=frame_emotivo, peak_ore=peak_ore, historical_roi=historical_roi)
