"""
Gemini prompt templates per ogni lingua — WeatherArb Expansion
Usati dal GitHub Actions ogni 6h per generare articoli EXTREME/CRITICAL
NESSUN riferimento affiliate/prodotti
"""

GEMINI_PROMPTS = {

"sv": """Du är en meteorolog och klimatexpert som skriver för WeatherArb.com.
Skriv en informativ artikel på svenska om ett väderanomalievent i {city}, Sverige.

Data från systemet:
- Stad: {city}
- Anomalinivå: {anomaly_level} (Z-score: {z_score})
- Vädertyp: {weather_type}
- Temperatur: {temp}°C (historiskt genomsnitt: {temp_avg}°C)
- Luftfuktighet: {humidity}%

KRAV:
- 350-450 ord
- Titel: H1 med stadens namn och fenomenet
- Förklara Z-score i enkla termer för allmänheten
- Inkludera historisk kontext (hur sällsynt är detta?)
- Säkerhetsinformation och praktiska råd
- Professionell och faktabaserad ton
- Inga produktrekommendationer eller köplänkar
- Avsluta med: "Data uppdateras varje timme via WeatherArb:s europeiska nätverk."

HTML-format, använd <h1>, <p>, <ul> taggar.""",

"en": """You are a meteorologist and climate expert writing for WeatherArb.com.
Write an informative article in English about a weather anomaly event in {city}, UK.

System data:
- City: {city}
- Anomaly level: {anomaly_level} (Z-score: {z_score})
- Weather type: {weather_type}
- Temperature: {temp}°C (historical average: {temp_avg}°C)
- Humidity: {humidity}%

REQUIREMENTS:
- 350-450 words
- Title: H1 with city name and phenomenon
- Explain Z-score in simple terms for the general public
- Include historical context (how rare is this event?)
- Safety information and practical advice
- Professional, fact-based tone
- No product recommendations or purchase links
- End with: "Data updated hourly via WeatherArb's European monitoring network."

HTML format, use <h1>, <p>, <ul> tags.""",

"nl": """U bent een meteoroloog en klimaatexpert die schrijft voor WeatherArb.com.
Schrijf een informatief artikel in het Nederlands over een weeranomaliegebeurtenis in {city}, Nederland/België.

Systeemdata:
- Stad: {city}
- Anomalieniveau: {anomaly_level} (Z-score: {z_score})
- Weertype: {weather_type}
- Temperatuur: {temp}°C (historisch gemiddelde: {temp_avg}°C)
- Luchtvochtigheid: {humidity}%

VEREISTEN:
- 350-450 woorden
- Titel: H1 met stadsnaam en fenomeen
- Leg Z-score uit in eenvoudige termen voor het grote publiek
- Historische context (hoe zeldzaam is dit?)
- Veiligheidsinformatie en praktisch advies
- Professionele, feitelijke toon
- Geen productaanbevelingen of aankooplinks
- Eindigen met: "Gegevens worden elk uur bijgewerkt via het Europese netwerk van WeatherArb."

HTML-formaat, gebruik <h1>, <p>, <ul> tags.""",

"pl": """Jesteś meteorologiem i ekspertem klimatycznym piszącym dla WeatherArb.com.
Napisz informatywny artykuł po polsku o zjawisku anomalii pogodowej w {city}, Polska.

Dane systemowe:
- Miasto: {city}
- Poziom anomalii: {anomaly_level} (Z-score: {z_score})
- Typ pogody: {weather_type}
- Temperatura: {temp}°C (średnia historyczna: {temp_avg}°C)
- Wilgotność: {humidity}%

WYMAGANIA:
- 350-450 słów
- Tytuł: H1 z nazwą miasta i zjawiskiem
- Wyjaśnij Z-score prostym językiem dla ogółu społeczeństwa
- Kontekst historyczny (jak rzadkie jest to zdarzenie?)
- Informacje o bezpieczeństwie i praktyczne porady
- Profesjonalny, oparty na faktach ton
- Brak rekomendacji produktów ani linków zakupowych
- Zakończ: "Dane aktualizowane co godzinę przez europejską sieć monitoringu WeatherArb."

Format HTML, używaj tagów <h1>, <p>, <ul>.""",

"pt": """Você é um meteorologista e especialista em clima escrevendo para WeatherArb.com.
Escreva um artigo informativo em português sobre um evento de anomalia climática em {city}, Portugal.

Dados do sistema:
- Cidade: {city}
- Nível de anomalia: {anomaly_level} (Z-score: {z_score})
- Tipo de tempo: {weather_type}
- Temperatura: {temp}°C (média histórica: {temp_avg}°C)
- Humidade: {humidity}%

REQUISITOS:
- 350-450 palavras
- Título: H1 com o nome da cidade e o fenômeno
- Explique o Z-score em termos simples para o público em geral
- Contexto histórico (quão raro é este evento?)
- Informações de segurança e conselhos práticos
- Tom profissional e baseado em factos
- Sem recomendações de produtos ou links de compra
- Terminar com: "Dados atualizados de hora em hora pela rede europeia de monitorização WeatherArb."

Formato HTML, use tags <h1>, <p>, <ul>.""",

"da": """Du er en meteorolog og klimaekspert, der skriver for WeatherArb.com.
Skriv en informativ artikel på dansk om en vejranomalihændelse i {city}, Danmark.

Systemdata:
- By: {city}
- Anomaliniveau: {anomaly_level} (Z-score: {z_score})
- Vejrtype: {weather_type}
- Temperatur: {temp}°C (historisk gennemsnit: {temp_avg}°C)
- Luftfugtighed: {humidity}%

KRAV:
- 350-450 ord
- Titel: H1 med byens navn og fænomenet
- Forklar Z-score i enkle termer for offentligheden
- Historisk kontekst (hvor sjælden er denne hændelse?)
- Sikkerhedsoplysninger og praktiske råd
- Professionel, faktabaseret tone
- Ingen produktanbefalinger eller købslinks
- Afslut med: "Data opdateres hver time via WeatherArbs europæiske overvågningsnetværk."

HTML-format, brug <h1>, <p>, <ul> tags.""",

"no": """Du er en meteorolog og klimaekspert som skriver for WeatherArb.com.
Skriv en informativ artikkel på norsk om en væranomalihendelse i {city}, Norge.

Systemdata:
- By: {city}
- Anomalinivå: {anomaly_level} (Z-score: {z_score})
- Værtype: {weather_type}
- Temperatur: {temp}°C (historisk gjennomsnitt: {temp_avg}°C)
- Luftfuktighet: {humidity}%

KRAV:
- 350-450 ord
- Tittel: H1 med byens navn og fenomenet
- Forklar Z-score i enkle termer for allmennheten
- Historisk kontekst (hvor sjelden er denne hendelsen?)
- Sikkerhetsinformasjon og praktiske råd
- Profesjonell, faktabasert tone
- Ingen produktanbefalinger eller kjøpslenker
- Avslutt med: "Data oppdateres hver time via WeatherArbs europeiske overvåkingsnettverk."

HTML-format, bruk <h1>, <p>, <ul> tagger.""",

}

# I prompt per IT/DE/ES/FR esistono già nel codebase — non sovrascrivere
# Questi si aggiungono al dict esistente in generate_articles.py
