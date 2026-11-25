import os
import re
import html
import asyncio
import hashlib
import datetime
import requests
import psycopg2
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.async_api import async_playwright

DATABASE_URL = os.environ["NEON_DATABASE_URL"].strip()
TELEGRAM_TOKEN = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
TELEGRAM_CHAT_ID = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()

HEADERS_HTTP = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

# 1. ELS 53 AJUNTAMENTS DE MALLORCA
MUNICIPIS_53 = [
    ("Alaró", "https://ajalaro.sedelectronica.es/board"),
    ("Alcúdia", "https://alcudia.sedelectronica.es/board"),
    ("Algaida", "https://ajalgaida.sedelectronica.es/board"),
    ("Andratx", "https://andratx.sedelectronica.es/board"),
    ("Ariany", "https://ajariany.sedelectronica.es/board"),
    ("Artà", "https://arta.sedelectronica.es/board"),
    ("Banyalbufar", "https://ajbanyalbufar.sedelectronica.es/board"),
    ("Binissalem", "https://ajbinissalem.sedelectronica.es/board"),
    ("Búger", "https://ajbuger.sedelectronica.es/board"),
    ("Bunyola", "https://ajbunyola.sedelectronica.es/board"),
    ("Calvià (Convoca)", "https://calvia.convoca.online/"),
    ("Campanet", "https://ajcampanet.sedelectronica.es/board"),
    ("Campos", "https://ajcampos.sedelectronica.es/board"),
    ("Capdepera", "https://capdepera.sedelectronica.es/board"),
    ("Consell", "https://ajconsell.sedelectronica.es/board"),
    ("Costitx", "https://ajcostitx.sedelectronica.es/board"),
    ("Deià", "https://ajdeia.sedelectronica.es/board"),
    ("Escorca", "https://ajescorca.sedelectronica.es/board"),
    ("Esporles", "https://ajesporles.sedelectronica.es/board"),
    ("Estellencs", "https://ajestellencs.sedelectronica.es/board"),
    ("Felanitx", "https://felanitx.sedelectronica.es/board"),
    ("Fornalutx", "https://ajfornalutx.sedelectronica.es/board"),
    ("Inca", "https://incaciutat.sedelectronica.es/board"),
    ("Lloret de Vistalegre", "https://ajlloretdevistalegre.sedelectronica.es/board"),
    ("Lloseta", "https://ajlloseta.sedelectronica.es/board"),
    ("Llubí", "https://ajllubi.sedelectronica.es/board"),
    ("Llucmajor (Convoca)", "https://llucmajor.convoca.online/"),
    ("Manacor", "https://manacor.sedelectronica.es/board"),
    ("Mancor de la Vall", "https://ajmancordelavall.sedelectronica.es/board"),
    ("Maria de la Salut", "https://ajmariadelasalut.sedelectronica.es/board"),
    ("Marratxí (Convoca)", "https://marratxi.convoca.online/"),
    ("Montuïri", "https://ajmontuiri.sedelectronica.es/board"),
    ("Muro", "https://ajmuro.sedelectronica.es/board"),
    ("Palma (Seu)", "https://seuelectronica.palma.es/"),
    ("Petra", "https://ajpetra.sedelectronica.es/board"),
    ("Sa Pobla", "https://sapobla.sedelectronica.es/board"),
    ("Pollença", "https://ajpollenca.sedelectronica.es/board"),
    ("Porreres", "https://porreres.sedelectronica.es/board"),
    ("Puigpunyent", "https://ajpuigpunyent.sedelectronica.es/board"),
    ("Ses Salines", "https://ajsessalines.sedelectronica.es/board"),
    ("Sant Joan", "https://ajsantjoan.sedelectronica.es/board"),
    ("Sant Llorenç des Cardassar", "https://santllorenc.sedelectronica.es/board"),
    ("Santa Eugènia", "https://ajsantaeugenia.sedelectronica.es/board"),
    ("Santa Margalida", "https://ajsantamargalida.sedelectronica.es/board"),
    ("Santa Maria del Camí", "https://ajsantamariadelcami.sedelectronica.es/board"),
    ("Santanyí", "https://ajsantanyi.sedelectronica.es/board"),
    ("Selva", "https://ajselva.sedelectronica.es/board"),
    ("Sencelles", "https://ajsencelles.sedelectronica.es/board"),
    ("Sineu", "https://ajsineu.sedelectronica.es/board"),
    ("Sóller", "https://ajsoller.sedelectronica.es/board"),
    ("Son Servera", "https://sonservera.sedelectronica.es/board"),
    ("Valldemossa", "https://ajvalldemossa.sedelectronica.es/board"),
    ("Vilafranca de Bonany", "https://ajvilafrancadebonany.sedelectronica.es/board"),
]

# 2. ORGANISMES AUTONÒMICS, INSULARS, UNIVERSITATS I EMPRESES PÚBLIQUES
ENTITATS_PUBLIQUES = [
    ("IMAS (Ofertes)", "https://www.imasmallorca.net/ca/ofertes-de-feina"),
    ("IMAS (Seu Electrònica)", "https://seu.imasmallorca.net/"),
    ("Consell de Mallorca (Tauler)", "https://seu.conselldemallorca.net/tauler-d-anuncis"),
    ("Agència Defensa Territori (ADT)", "https://adt.conselldemallorca.net/"),
    ("Consorci Serra de Tramuntana", "https://www.serradetramuntana.net/"),
    ("CAIB Oposicions (Novetats)", "https://www.caib.es/sites/oposicions/ca/novetats/"),
    ("CAIB Oposicions (Borses)", "https://www.caib.es/sites/oposicions/ca/borses_temporals/"),
    ("IB-SALUT Treballa amb nosaltres", "https://www.ibsalut.es/ca/professionals/recursos-humans/treballa-amb-nosaltres"),
    ("IBAVI", "https://www.caib.es/sites/ibavi/"),
    ("ABAQUA", "https://www.abaqua.cat/"),
    ("IBANAT", "https://ibanat.caib.es/"),
    ("SFM Trens", "https://www.trensfm.com/"),
    ("Consorci Transports Mallorca (CTM)", "https://www.tib.org/"),
    ("Fundació BIT", "https://www.fundaciobit.org/"),
    ("IBETEC", "https://ibetec.caib.es/"),
    ("IBESTAT", "https://ibestat.es/"),
    ("SOIB Ofertes", "https://soib.es/ofertes-de-feina/"),
    ("PalmaActiva", "https://web.palmactiva.cat/"),
    ("EMAYA (Convoca)", "https://emaya.convoca.online/"),
    ("SMAP Palma", "https://smap.palma.es/"),
    ("UIB Investigació", "https://investigacio.uib.cat/Contractacio/Convocatories-vigents/"),
    ("UIB PTGAS (Administració)", "https://rrhh.uib.cat/arees/pas/convocatories/"),
    ("FUEIB Ofertes", "https://fueib.org/"),
    ("IMEDEA (CSIC-UIB)", "https://imedea.uib-csic.es/"),
    ("SOCIB", "https://www.socib.es/"),
    ("TRAGSA / TRAGSATEC", "https://www.tragsa.es/es/empleo/Paginas/default.aspx"),
    ("Autoritat Portuària Balears", "https://portsdebalears.com/convocatorias"),
    ("Mancomunitat Pla de Mallorca", "https://www.mancomunitatplademallorca.net/"),
    ("Mancomunitat des Raiguer", "https://www.mancomunitatdesraiguer.net/"),
    ("Mancomunitat del Migjorn", "https://www.mancomunitatdelmigjorn.org/"),
    ("Mancomunitat del Nord", "https://www.mancomunitatdelnord.org/"),
    ("GOB Mallorca", "https://www.gobmallorca.com/"),
    ("Fundació Marilles", "https://marilles.org/"),
    ("Fundació Deixalles", "https://www.deixalles.org/"),
]

# 3. REGLES ESTRUCTURALS DERIVADES DE L'AUDITORIA
NOMS_TERRITORI_I_ENS = [m[0].split(" (")[0].lower() for m in MUNICIPIS_53] + [
    "mallorca", "illes balears", "islas baleares", "caib", "imas", "1232767",
    "consell de mallorca", "ib-salut", "ibsalut", "ibavi", "abaqua", "ibanat",
    "sfm", "fundació bit", "ibestat", "fasd", "uib", "fueib", "tragsa", "tragsatec",
    "emaya", "smap", "aena", "autoritat portuària", "mancomunitat del pla",
    "mancomunitat des raiguer", "mancomunitat del migjorn", "mancomunitat del nord", "tramuntana"
]

# Perfils compatibles amb Geografia, Ciències Socials, Territori i Administració General A1/A2/C1
LLISTA_BLANCA_PERFIL = [
    r"ge[òo]graf", r"geografia", r"geografía",
    r"soci[òo]leg", r"sociologia", r"sociología",
    r"\bsig\b", r"\bgis\b", r"cartograf", r"territori", r"ordenació\s+territorial",
    r"urbanism", r"medi\s+ambient", r"medio\s+ambiente", r"sostenibilitat", r"canvi\s+climàtic",
    r"mobilitat", r"movilidad", r"habitatge", r"vivienda",
    r"turisme", r"turismo", r"desenvolupament\s+local", r"desarrollo\s+local", r"\badl\b",
    r"demograf", r"estadístic", r"enquest", r"projectes\s+europeus", r"fons\s+europeus",
    r"polítiques\s+públiques", r"investigador", r"recerca",
    r"(?<!auxiliar\s)(?<!aux\.\s)(?<!aux\s)administrati(?:u|va|vo|us|ves|vos)",
    r"administració\s+general", r"administración\s+general", r"\btag\b",
    r"tècnic(?:/a|-a|a)?\s+de\s+gestió", r"técnico(?:/a|-a|a)?\s+de\s+gestión",
    r"gestió\s+administrativa", r"titulat(?:/da|-da|da)?\s+superior", r"titulat(?:/da|-da|da)?\s+mitj"
]

INDICADOR_OBERTURA = [
    r"bases\s+(?:i\s+convocatòria|de\s+la\s+convocatòria|reguladores)",
    r"convocatòria\s+(?:pública|de\s+procés|del\s+procediment|per\s+a\s+la\s+constitució|d['’]una\s+borsa)",
    r"anunci\s+de\s+la\s+convocatòria", r"nova\s+convocatòria", r"obertura\s+(?:del\s+)?termini",
    r"bors[íia]", r"borsa\s+de\s+treball", r"bolsa\s+de\s+trabajo", r"bolsa\s+de\s+empleo",
    r"oposic", r"concurs[- ]oposic", r"procés\s+selectiu", r"proceso\s+selectivo",
    r"procediment\s+selectiu", r"procedimiento\s+selectivo", r"provisió", r"provisión",
    r"cobertura\s+de\s+(?:\d+|una)\s+pla", r"oferta\s+de\s+treball", r"contractació\s+de\s+personal"
]

# Fases ja tancades o tràmits intermedis detectats a l'auditoria (Gestiona, Convoca, UIB, BOIB)
FASES_TANCADES = [
    r"provisional\s+listing", r"final\s+official\s+list", r"relació\s+provisional", r"relación\s+provisional",
    r"relació\s+definitiva", r"relación\s+definitiva", r"llista\s+provisional", r"lista\s+provisional",
    r"llista\s+definitiva", r"lista\s+definitiva", r"llista\s+d['’]admesos", r"admesos\s+i\s+exclosos",
    r"resultat", r"resultado", r"qualificacions", r"calificaciones", r"baremació", r"aprovats", r"aprobados",
    r"data\s+(?:del\s+)?\d", r"data\s+del\s+(?:primer|segon|tercer)", r"fecha\s+del",
    r"citació", r"citación", r"revisió\s+examen", r"revisió\s+exercici",
    r"tribunal\s+(?:qualificador|de\s+selecció)", r"constitució\s+del\s+tribunal",
    r"comissió\s+avaluadora", r"composició\s+del\s+tribunal",
    r"acta\s+(?:núm|de\s+la\s+sessió|sessió|valoració)", r"valoració\s+de\s+mèrits",
    r"proposta\s+de\s+(?:candidats|nomenament|contractació)", r"constitució\s+(?:de\s+la\s+)?borsa",
    r"nomenament", r"nombramiento", r"adjudicaci", r"adjudicación",
    r"recurs\s+d['’]alçada", r"recurso\s+de\s+alzada", r"desestimació",
    r"finalitzaci", r"finalizaci", r"comissió\s+de\s+serveis", r"promoció\s+interna",
    r"^\s*annex\b", r"^\s*anexo\b",
    r"oferta\s+d['’]ocupació\s+pública", r"oferta\s+de\s+empleo\s+público", r"\boop\b", r"\boep\b",
    r"plantilla\s+orgànica", r"relació\s+de\s+llocs\s+de\s+treball", r"\brlt\b", r"\brpt\b",
    r"licit", r"contracte\s+de\s+servei", r"plecs", r"subvenc", r"premi", r"seminari", r"jornada",
    r"memòria", r"expropiaci", r"cuentas\s+anuales", r"comptes\s+anuals", r"estadístiques", r"estadísticas",
    r"eivissa", r"ibiza", r"formentera", r"menorca", r"maó", r"ciutadella"
]

# Titulacions alienes o llocs C2/oficis
TITULACIONS_EXCLOSES = [
    r"auxiliar\s+administrati", r"auxiliar\s+administrativo", r"aux\.?\s*adm", r"\bc2\b",
    r"dret", r"derecho", r"jurídic", r"jurídico", r"lletrat", r"letrado", r"advoca",
    r"sanitari", r"sanitario", r"metge", r"médico", r"infermer", r"enfermer",
    r"tcae", r"celador", r"fisioterapeuta", r"farmacèutic", r"veterinari",
    r"psic[òo]leg", r"psicología",
    r"treballador(?:/a|-a|a)?\s+(?:social|familiar)", r"trabajador(?:/a|-a|a)?\s+(?:social|familiar)",
    r"atenció\s+domiciliària", r"gerocultor", r"cuidador", r"sociosanit",
    r"educador(?:/a|-a|a)?\s+social", r"educació\s+infantil", r"educación\s+infantil",
    r"mestre", r"maestro", r"professor", r"profesor", r"docent", r"\bpdi\b",
    r"arquitect", r"enginyer", r"ingenier", r"aparellador", r"delineant", r"top[òo]graf",
    r"economista", r"interventor", r"tresorer", r"tesorero", r"comptabilitat", r"contabilidad",
    r"informàtic", r"informático", r"programador", r"desenvolupador", r"sistemes\s+informàtics", r"\btic\b",
    r"policia\s+local", r"policía\s+local", r"bomber", r"bombero", r"socorrista",
    r"oficial\s+\d", r"xòfer", r"chofer", r"conductor", r"manteniment", r"mantenimiento",
    r"electricista", r"lampista", r"fuster", r"jardiner", r"netej", r"limpieza",
    r"conserge", r"subaltern", r"ordenança", r"peó", r"peón", r"operari", r"operario", r"brigada", r"cuina"
]

PATRO_UBICACIO = re.compile(r"\b(" + "|".join(re.escape(x) for x in NOMS_TERRITORI_I_ENS) + r")\b", re.I)
PATRO_PERFIL_BLANC = re.compile(r"(" + "|".join(LLISTA_BLANCA_PERFIL) + r")", re.I)
PATRO_OBERTURA = re.compile(r"(" + "|".join(INDICADOR_OBERTURA) + r")", re.I)
PATRO_TANCADA = re.compile(r"(" + "|".join(FASES_TANCADES) + r")", re.I)
PATRO_TITULACIO_EXCLOSA = re.compile(r"(" + "|".join(TITULACIONS_EXCLOSES) + r")", re.I)
PATRO_IMAS = re.compile(r"\b(imas|1232767)\b", re.I)


def envia_telegram_blocs(blocs_html: list[str]):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram no configurat.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    missatge_actual = ""

    for bloc in blocs_html:
        if len(missatge_actual) + len(bloc) + 2 > 3800:
            requests.post(url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": missatge_actual,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }, timeout=15)
            missatge_actual = bloc
        else:
            missatge_actual = f"{missatge_actual}\n\n{bloc}" if missatge_actual else bloc

    if missatge_actual:
        resp = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": missatge_actual,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }, timeout=15)
        print("Resposta Telegram:", resp.status_code, resp.text[:160])


def valida_oferta(text: str, es_contenidor_rrhh: bool = False, requerir_ubicacio: bool = False) -> bool:
    t = text.strip()
    if len(t) < 20:
        return False
    if PATRO_TANCADA.search(t) or PATRO_TITULACIO_EXCLOSA.search(t):
        return False
    if PATRO_IMAS.search(t):
        return True
    if requerir_ubicacio and not PATRO_UBICACIO.search(t):
        return False

    # Si ja som dins d'un tauler oficial de RRHH (Gestiona Seleccions, Convoca, BOIB Sec II, CAIB Oposicions),
    # basta que sigui una obertura real i no estigui exclosa (així no perdem títols genèrics com "Anunci de la convocatòria")
    if es_contenidor_rrhh:
        return bool(PATRO_OBERTURA.search(t))

    # Si és una web generalista (SOIB, BOE, portals generals), exigim obertura + perfil blanc explícit
    return bool(PATRO_OBERTURA.search(t) and PATRO_PERFIL_BLANC.search(t))


def desa_convocatoria(cur, codi, font, entitat, titol, estat, url):
    cur.execute("""
        INSERT INTO convocatories
        (codi_expedient, font, entitat, titol, estat_proces, data_publicacio, url_bases, url_candidatura)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (codi_expedient) DO NOTHING
        RETURNING id;
    """, (codi, font, entitat, titol[:450], estat, datetime.date.today(), url, url))
    return cur.fetchone() is not None


def desa_log(cur, font, identificador, estat, obs=""):
    cur.execute("""
        INSERT INTO log_cobertura (data_execucio, font, identificador_edicio, estat, observacions)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (data_execucio, font, identificador_edicio)
        DO UPDATE SET estat = EXCLUDED.estat, observacions = EXCLUDED.observacions;
    """, (datetime.date.today(), font, identificador, estat, obs[:300]))


def extreu_candidats_estructurals(soup: BeautifulSoup, base_url: str, mode: str = "GENERAL"):
    for tag in soup(["nav", "header", "footer", "script", "style"]):
        tag.decompose()

    candidats = []
    vists = set()

    # MODE 1: Seu Electrònica Gestiona (*.sedelectronica.es/board)
    if mode == "GESTIONA":
        for tr in soup.find_all("tr"):
            enllacos = tr.find_all("a", href=True)
            if not enllacos:
                continue
            txt = re.sub(r"\s+", " ", tr.get_text(" ", strip=True))
            # Filtre estructural exacte detectat a l'auditoria
            if "seleccions de personal i provisions de llocs de treball" not in txt.lower():
                continue
            if valida_oferta(txt, es_contenidor_rrhh=True):
                enllac = urljoin(base_url, enllacos[0]["href"])
                clau = f"{txt[:150]}|{enllac}"
                if clau not in vists:
                    vists.add(clau)
                    candidats.append((txt, enllac))
        return candidats

    # MODE 2: Plataforma Convoca (*.convoca.online)
    if mode == "CONVOCA":
        articles = soup.select("article.applicant__article") or soup.find_all("article")
        for art in articles:
            enllacos = art.find_all("a", href=True)
            if not enllacos:
                continue
            txt = re.sub(r"\s+", " ", art.get_text(" ", strip=True))
            # A Convoca, les fases 3+ (Tribunal, Acta, Resultat) no són convocatòries noves
            if re.search(r"\b(?:[3-9]|[1-9]\d)\.\s", txt):
                continue
            if valida_oferta(txt, es_contenidor_rrhh=True):
                enllac = urljoin(base_url, enllacos[0]["href"])
                clau = f"{txt[:150]}|{enllac}"
                if clau not in vists:
                    vists.add(clau)
                    candidats.append((txt, enllac))
        return candidats

    # MODE 3: Fundació BIT (només targetes amb NOVA CONVOCATÒRIA)
    if "fundaciobit.org" in base_url:
        for a in soup.find_all("a", href=True):
            txt = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
            if "nova convocatòria" in txt.lower() and valida_oferta(txt, es_contenidor_rrhh=True):
                enllac = urljoin(base_url, a["href"])
                if enllac not in vists:
                    vists.add(enllac)
                    candidats.append((txt, enllac))
        return candidats

    # MODE 4: BOIB Secció II / CAIB Oposicions / UIB / Resta d'entitats
    es_rrhh = mode in ("BOIB_SEC2", "RRHH_DIRECTE")
    for bloc in soup.find_all(["tr", "li", "article", "div"]):
        enllacos = bloc.find_all("a", href=True)
        if not (1 <= len(enllacos) <= 3):
            continue
        txt = re.sub(r"\s+", " ", bloc.get_text(" ", strip=True))
        if 25 <= len(txt) <= 550 and valida_oferta(txt, es_contenidor_rrhh=es_rrhh):
            enllac = urljoin(base_url, enllacos[0]["href"])
            if enllac.startswith(("mailto:", "javascript:")):
                continue
            clau = f"{txt[:150]}|{enllac}"
            if clau not in vists:
                vists.add(clau)
                candidats.append((txt, enllac))

    for a in soup.find_all("a", href=True):
        txt = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
        if len(txt) < 22:
            continue
        enllac = urljoin(base_url, a["href"])
        if enllac.startswith(("mailto:", "javascript:")) or enllac.endswith("#"):
            continue
        clau = f"{txt[:150]}|{enllac}"
        if clau not in vists and valida_oferta(txt, es_contenidor_rrhh=es_rrhh):
            vists.add(clau)
            candidats.append((txt, enllac))

    return candidats


def extreu_fitxa_detall(item: tuple):
    codi, entitat, titol, url = item
    text_complet = titol
    resum_extra = ""
    es_pdf = url.lower().endswith(".pdf") or "/preview-document/" in url.lower()

    if not es_pdf and url.startswith("http"):
        try:
            r = requests.get(url, headers=HEADERS_HTTP, timeout=8)
            ctype = r.headers.get("Content-Type", "").lower()
            if "application/pdf" in ctype:
                es_pdf = True
            elif r.status_code == 200 and "text/html" in ctype:
                soup = BeautifulSoup(r.text, "html.parser")
                for tag in soup(["script", "style", "nav", "header", "footer"]):
                    tag.decompose()
                contenidor = soup.find("main") or soup.find("article") or soup.body
                if contenidor:
                    cos_net = re.sub(r"\s+", " ", contenidor.get_text(" ", strip=True))
                    text_complet = f"{titol} {cos_net[:2500]}"

                    # Segon filtre damunt les bases completes (p. ex. si a Fundació BIT demana Grau en Dret)
                    if PATRO_TANCADA.search(cos_net[:2500]) or PATRO_TITULACIO_EXCLOSA.search(cos_net[:2500]):
                        return None

                    if len(titol) < 100 or "anunci de la convocatòria" in titol.lower():
                        paragrafs = [
                            re.sub(r"\s+", " ", p.get_text(" ", strip=True))
                            for p in contenidor.find_all(["p", "dd", "li"])
                        ]
                        utils = [
                            p for p in paragrafs
                            if 45 <= len(p) <= 350 and "cookie" not in p.lower() and "política" not in p.lower()
                        ]
                        if utils:
                            resum_extra = utils[0][:260]
        except Exception:
            pass

    grup_match = re.search(
        r"\b(subgrup\s*[ABC]1|grup\s*[ABC]1|[ABC]1|A2|titulat\s+superior|titulat\s+mitjà|grau\s+universitari|batxillerat)\b",
        text_complet, re.I
    )
    grup = grup_match.group(1).upper() if grup_match else ""

    tipus = ""
    if re.search(r"bors[íia]|bolsa", text_complet, re.I):
        tipus = "Borsí"
    elif re.search(r"concurs[- ]oposic", text_complet, re.I):
        tipus = "Concurs-oposició"
    elif re.search(r"oposic", text_complet, re.I):
        tipus = "Oposició"
    elif re.search(r"inter[íi]|temporal", text_complet, re.I):
        tipus = "Interí / Temporal"

    termini_match = re.search(
        r"(termini[^\.]{5,90}|fins al \d{1,2}[/-]\d{1,2}[/-]\d{2,4}|plazo[^\.]{5,90}|\d{1,2}\s+dies\s+(?:hàbils|naturals))",
        text_complet, re.I
    )
    termini = termini_match.group(1).strip().capitalize() if termini_match else ""

    return {
        "codi": codi,
        "entitat": entitat,
        "titol": titol,
        "url": url,
        "grup": grup,
        "tipus": tipus,
        "termini": termini,
        "resum_extra": resum_extra,
        "es_pdf": es_pdf,
    }


def consulta_boe(conn, data_str: str):
    url = f"https://www.boe.es/datosabiertos/api/boe/sumario/{data_str}"
    r = requests.get(url, headers={"Accept": "application/json"}, timeout=20)
    novetats = []

    with conn.cursor() as cur:
        if r.status_code != 200:
            desa_log(cur, "BOE", f"BOE-{data_str}", "NO_DISPONIBLE", f"HTTP {r.status_code}")
            conn.commit()
            return novetats

        dades = r.json()
        diaris = dades.get("data", {}).get("sumario", {}).get("diario", [])
        if isinstance(diaris, dict):
            diaris = [diaris]

        for diari in diaris:
            seccions = diari.get("seccion", [])
            if isinstance(seccions, dict):
                seccions = [seccions]
            for sec in seccions:
                if sec.get("@codigo") not in ("2B", "5A", "5B"):
                    continue
                departaments = sec.get("departamento", [])
                if isinstance(departaments, dict):
                    departaments = [departaments]
                for dep in departaments:
                    nom_dep = dep.get("@nombre", "AGE/Local")
                    epigrafs = dep.get("epigrafe", [])
                    if isinstance(epigrafs, dict):
                        epigrafs = [epigrafs]
                    for epi in epigrafs:
                        items = epi.get("item", [])
                        if isinstance(items, dict):
                            items = [items]
                        for item in items:
                            id_boe = item.get("identificador")
                            titol = item.get("titulo", "")
                            url_html = item.get("url_html", "")
                            if valida_oferta(f"{nom_dep} {titol}", es_contenidor_rrhh=False, requerir_ubicacio=True):
                                if desa_convocatoria(cur, id_boe, "BOE", nom_dep, titol, "OBERTA", url_html):
                                    novetats.append((id_boe, f"BOE · {nom_dep}", titol, url_html))

        desa_log(cur, "BOE", f"BOE-{data_str}", "REVISAT", f"Noves: {len(novetats)}")
        conn.commit()
    return novetats


def consulta_boib(conn, any_actual: int):
    url_portada = f"https://www.caib.es/eboibfront/ca/{any_actual}/"
    novetats = []
    with conn.cursor() as cur:
        try:
            r = requests.get(url_portada, headers=HEADERS_HTTP, timeout=20)
            if r.status_code != 200:
                desa_log(cur, "BOIB", f"BOIB-{any_actual}", "ERROR", f"HTTP {r.status_code}")
                conn.commit()
                return novetats

            soup = BeautifulSoup(r.text, "html.parser")
            enllacos = [
                a["href"] for a in soup.find_all("a", href=True)
                if re.search(rf"/eboibfront/ca/{any_actual}/\d+/?$", a["href"])
            ]
            if not enllacos:
                desa_log(cur, "BOIB", f"BOIB-{any_actual}", "NO_DISPONIBLE", "Sense edicions")
                conn.commit()
                return novetats

            url_edicio = urljoin("https://www.caib.es", enllacos[0])
            num_edicio = url_edicio.rstrip("/").split("/")[-1]
            r_ed = requests.get(url_edicio, headers=HEADERS_HTTP, timeout=20)
            soup_ed = BeautifulSoup(r_ed.text, "html.parser")

            seccions_objectiu = []
            for a_sec in soup_ed.find_all("a", href=True):
                href = a_sec["href"]
                if re.search(rf"/eboibfront/ca/{any_actual}/{num_edicio}/(seccio-ii|seccio-v)", href, re.I):
                    full_sec = urljoin("https://www.caib.es", href)
                    mode_sec = "BOIB_SEC2" if "seccio-ii" in href.lower() else "GENERAL"
                    if (full_sec, mode_sec) not in seccions_objectiu:
                        seccions_objectiu.append((full_sec, mode_sec))

            for url_sec, mode_sec in seccions_objectiu[:12]:
                r_s = requests.get(url_sec, headers=HEADERS_HTTP, timeout=15)
                soup_s = BeautifulSoup(r_s.text, "html.parser")
                candidats = extreu_candidats_estructurals(soup_s, url_sec, mode=mode_sec)
                for text, link in candidats:
                    h = hashlib.md5(f"{num_edicio}:{text[:180]}".encode()).hexdigest()[:10]
                    codi = f"BOIB-{num_edicio}-{h}"
                    if desa_convocatoria(cur, codi, "BOIB", f"BOIB núm. {num_edicio}", text, "PUBLICAT_BOIB", link):
                        novetats.append((codi, f"BOIB núm. {num_edicio}", text[:380], link))

            desa_log(cur, "BOIB", f"BOIB-{any_actual}-{num_edicio}", "REVISAT", f"Noves: {len(novetats)}")
        except Exception as e:
            desa_log(cur, "BOIB", f"BOIB-{any_actual}", "ERROR", str(e)[:120])
        conn.commit()
    return novetats


def detecta_mode_portal(url: str) -> str:
    if "sedelectronica.es" in url:
        return "GESTIONA"
    if "convoca.online" in url:
        return "CONVOCA"
    if any(k in url for k in ("oposicions", "ofertes-de-feina", "treballa-amb-nosaltres", "Convocatories", "convocatorias", "pas/convocatories")):
        return "RRHH_DIRECTE"
    return "GENERAL"


def descarrega_portal_http(nom: str, url: str):
    mode = detecta_mode_portal(url)
    if mode == "CONVOCA":
        return nom, url, "JS_REQUIRED", "", []
    try:
        r = requests.get(url, headers=HEADERS_HTTP, timeout=10)
        if r.status_code != 200:
            return nom, url, "ERROR", f"HTTP {r.status_code}", []
        soup = BeautifulSoup(r.text, "html.parser")
        if mode == "GESTIONA" and len(soup.find_all("tr")) < 2:
            return nom, url, "JS_REQUIRED", "", []
        return nom, url, "REVISAT", "", extreu_candidats_estructurals(soup, url, mode=mode)
    except Exception as e:
        return nom, url, "ERROR", str(e)[:120], []


async def renderitza_portals_js(pendents: list[tuple]):
    resultats = []
    if not pendents:
        return resultats

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # ignore_https_errors=True evita l'error de certificat SSL de Marratxí
        context = await browser.new_context(
            user_agent=HEADERS_HTTP["User-Agent"],
            ignore_https_errors=True
        )
        await context.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2}", lambda route: route.abort())
        sem = asyncio.Semaphore(5)

        async def llegeix_una(nom: str, url: str):
            async with sem:
                page = await context.new_page()
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    await page.wait_for_timeout(2400)
                    soup = BeautifulSoup(await page.content(), "html.parser")
                    mode = detecta_mode_portal(url)
                    candidats = extreu_candidats_estructurals(soup, url, mode=mode)
                    return nom, "REVISAT", "", candidats
                except Exception as e:
                    return nom, "ERROR", str(e)[:120], []
                finally:
                    await page.close()

        tasques = [llegeix_una(nom, url) for nom, url in pendents]
        resultats = await asyncio.gather(*tasques)
        await browser.close()
    return resultats


def rastreja_portals(conn, llista_fonts, tipus_font):
    novetats = []
    resultats_finals = []
    pendents_js = []

    with ThreadPoolExecutor(max_workers=12) as executor:
        futurs = [executor.submit(descarrega_portal_http, nom, url) for nom, url in llista_fonts]
        for futur in as_completed(futurs):
            nom, url, estat, error_msg, candidats = futur.result()
            if estat == "JS_REQUIRED":
                pendents_js.append((nom, url))
            else:
                resultats_finals.append((nom, estat, error_msg, candidats))

    if pendents_js:
        resultats_js = asyncio.run(renderitza_portals_js(pendents_js))
        resultats_finals.extend(resultats_js)

    with conn.cursor() as cur:
        for nom, estat, error_msg, candidats in resultats_finals:
            if estat == "ERROR":
                desa_log(cur, tipus_font, nom, "ERROR", error_msg)
                continue
            trobades_font = 0
            for text, enllac in candidats:
                h = hashlib.md5(f"{nom}:{text[:180]}:{enllac}".encode()).hexdigest()[:12]
                codi = f"{tipus_font}-{h}"
                if desa_convocatoria(cur, codi, tipus_font, nom, text, "DETECTADA_PORTAL", enllac):
                    novetats.append((codi, nom, text[:380], enllac))
                    trobades_font += 1
            desa_log(cur, tipus_font, nom, "REVISAT", f"Noves: {trobades_font}")
        conn.commit()
    return novetats


def main():
    avui = datetime.date.today()
    data_str = avui.strftime("%Y%m%d")
    conn = psycopg2.connect(DATABASE_URL)

    novetats_boe = consulta_boe(conn, data_str)
    novetats_boib = consulta_boib(conn, avui.year)
    novetats_entitats = rastreja_portals(conn, ENTITATS_PUBLIQUES, "ENTITAT_PUBLICA")
    novetats_municipis = rastreja_portals(conn, MUNICIPIS_53, "AJUNTAMENT")

    totes = novetats_boe + novetats_boib + novetats_entitats + novetats_municipis

    if totes:
        fitxes = []
        with ThreadPoolExecutor(max_workers=6) as executor:
            futurs = [executor.submit(extreu_fitxa_detall, item) for item in totes[:40]]
            for futur in as_completed(futurs):
                resultat = futur.result()
                if resultat is not None:
                    fitxes.append(resultat)

        print(f"Total novetats netes enviades: {len(fitxes)}")
        if fitxes:
            blocs = [f"📌 <b>Rastreig Integral Mallorca · {avui.strftime('%d/%m/%Y')}</b> ({len(fitxes)} ofertes compatibles)"]
            for f in fitxes:
                alerta = "🚨 <b>ALERTA IMAS C1!</b> " if PATRO_IMAS.search(f["entitat"] + " " + f["titol"]) else ""
                etiquetes = []
                if f["tipus"]:
                    etiquetes.append(f"📋 <b>{html.escape(f['tipus'])}</b>")
                if f["grup"]:
                    etiquetes.append(f"🎓 <b>Grup {html.escape(f['grup'])}</b>")
                if f["es_pdf"]:
                    etiquetes.append("📄 <i>PDF directe</i>")

                linia_meta = (" · ".join(etiquetes) + "\n") if etiquetes else ""
                linia_resum = f"<i>{html.escape(f['resum_extra'])}</i>\n" if f["resum_extra"] else ""
                linia_termini = f"⏳ <b>Termini:</b> {html.escape(f['termini'])}\n" if f["termini"] else ""

                targeta = (
                    f"{alerta}🏛️ <b>{html.escape(f['entitat'])}</b>\n"
                    f"{linia_meta}"
                    f"{html.escape(f['titol'])}\n"
                    f"{linia_resum}"
                    f"{linia_termini}"
                    f"🔗 <a href=\"{html.escape(f['url'], quote=True)}\">Obrir convocatòria</a>"
                )
                blocs.append(targeta)

            envia_telegram_blocs(blocs)
    else:
        print("Total novetats detectades: 0")

    conn.close()


if __name__ == "__main__":
    main()
