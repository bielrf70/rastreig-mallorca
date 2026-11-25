import os
import re
import html
import hashlib
import datetime
import requests
import psycopg2
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

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

# 2. ORGANISMES AUTONÒMICS, INSULARS, UNIVERSITATS, EMPRESES PÚBLIQUES I TERCER SECTOR
ENTITATS_PUBLIQUES = [
    ("IMAS (Seu Electrònica)", "https://seu.imasmallorca.net/"),
    ("Consell de Mallorca (Seu)", "https://seu.conselldemallorca.net/"),
    ("Agència Defensa Territori (ADT)", "https://adt.conselldemallorca.net/"),
    ("Consorci Serra de Tramuntana", "https://www.serradetramuntana.net/"),
    ("CAIB Oposicions", "https://www.caib.es/sites/oposicions/"),
    ("IB-SALUT Recursos Humans", "https://www.ibsalut.es/ca/professionals/recursos-humans"),
    ("IBAVI", "https://www.caib.es/sites/ibavi/"),
    ("ABAQUA", "https://www.abaqua.cat/"),
    ("IBANAT", "https://ibanat.caib.es/"),
    ("SFM Trens", "https://www.trensfm.com/"),
    ("Consorci Transports Mallorca (CTM)", "https://www.tib.org/"),
    ("Fundació BIT", "https://www.fundaciobit.org/"),
    ("IBETEC", "https://ibetec.caib.es/"),
    ("IBESTAT", "https://ibestat.es/"),
    ("SOIB Ofertes", "https://soib.es/"),
    ("PalmaActiva", "https://web.palmactiva.cat/"),
    ("EMAYA Palma", "https://www.emaya.es/"),
    ("SMAP Palma", "https://smap.palma.es/"),
    ("UIB Investigació Convocatòries", "https://investigacio.uib.cat/Contractacio/Convocatories-vigents/"),
    ("FUEIB Ofertes", "https://fueib.org/"),
    ("IMEDEA (CSIC-UIB)", "https://imedea.uib-csic.es/"),
    ("SOCIB", "https://www.socib.es/"),
    ("TRAGSA / TRAGSATEC Ocupació", "https://www.tragsa.es/es/empleo/Paginas/default.aspx"),
    ("Autoritat Portuària Balears", "https://www.portsdebalears.com/"),
    ("Mancomunitat Pla de Mallorca", "https://www.mancomunitatplademallorca.net/"),
    ("Mancomunitat des Raiguer", "https://www.mancomunitatdesraiguer.net/"),
    ("Mancomunitat del Migjorn", "https://www.mancomunitatdelmigjorn.org/"),
    ("Mancomunitat del Nord", "https://www.mancomunitatdelnord.org/"),
    ("GOB Mallorca", "https://www.gobmallorca.com/"),
    ("Fundació Marilles", "https://marilles.org/"),
    ("Fundació Deixalles", "https://www.deixalles.org/"),
]

# 3. FILTRES DE DOBLE CLAU: (1) ÉS UNA OFERTA D'OCUPACIÓ + (2) ENCAIXA AMB EL TEU PERFIL
NOMS_TERRITORI_I_ENS = [m[0].split(" (")[0].lower() for m in MUNICIPIS_53] + [
    "mallorca", "illes balears", "islas baleares", "caib", "imas", "1232767",
    "consell de mallorca", "ib-salut", "ibsalut", "ibavi", "abaqua", "ibanat",
    "sfm", "fundació bit", "ibestat", "fasd", "uib", "fueib", "tragsa", "tragsatec",
    "emaya", "smap", "aena", "autoritat portuària", "mancomunitat del pla",
    "mancomunitat des raiguer", "mancomunitat del migjorn", "mancomunitat del nord", "tramuntana"
]

# Clau 1: Ha d'indicar explícitament que és un procés selectiu, borsí, oposició o oferta de feina
OCUPACIO = [
    r"bors[íia]", r"borsa de treball", r"bolsa de trabajo", r"bolsa de empleo",
    r"oposic", r"concurs[- ]oposic", r"procés selectiu", r"proceso selectivo",
    r"procediment selectiu", r"procedimiento selectivo", r"oferta de treball",
    r"oferta d'ocupació", r"oferta de empleo", r"contractació de personal",
    r"contratación de personal", r"provisió d'un lloc", r"provisión de un puesto",
    r"cobertura de \d+ pla", r"cobertura d'una pla", r"nova convocatòria",
    r"anunci de la convocatòria", r"bases i convocatòria", r"bases de la convocatòria"
]

# Clau 2: Ha d'encaixar amb Geografia, Ciències Socials, Territori, SIG o Administració general (A1/A2/C1)
PERFILS = [
    r"ge[òo]graf", r"geografia", r"soci[òo]leg", r"sociologia", r"\bsig\b", r"\bgis\b",
    r"cartograf", r"territori", r"urbanism", r"habitatge", r"vivienda",
    r"mobilitat", r"movilidad", r"demograf", r"estadístic", r"enquest",
    r"recerca", r"investigaci", r"polítiques públiques", r"políticas públicas",
    r"projectes europeus", r"fons europeus", r"medi ambient", r"medio ambiente",
    r"administratiu", r"administrativo", r"administració general", r"administración general",
    r"gestió", r"gestión", r"tècnic", r"técnico", r"titulat superior", r"titulat mitjà",
    r"\ba1\b", r"\ba2\b", r"\bc1\b", r"\btag\b", r"anunci de la convocatòria"
]

# Titulacions específiques alienes al Grau en Geografia / Administració general
TITULACIONS_EXCLOSES = [
    r"grau en dret", r"grado en derecho", r"llicenciatura en dret", r"licenciatura en derecho",
    r"tècnic/a superior jurídic", r"tècnic superior jurídic", r"técnico superior jurídico",
    r"assessor/a jurídic", r"asesor jurídico", r"lletrat", r"letrado", r"advocat",
    r"sanitari", r"sanitario", r"metge", r"médico", r"infermer", r"enfermer",
    r"auxiliar d'infermeria", r"tcae", r"celador", r"fisioterapeuta", r"farmacèutic",
    r"veterinari", r"psic[òo]leg", r"psicología", r"treballador/a social", r"treballador social",
    r"trabajador social", r"treballador/a familiar", r"educador/a social", r"educació infantil",
    r"educación infantil", r"mestre", r"maestro", r"professor", r"profesor", r"docent", r"\bpdi\b",
    r"arquitect", r"enginyer", r"ingenier", r"aparellador", r"delineant",
    r"economista", r"interventor", r"tresorer", r"tesorero", r"comptabilitat",
    r"informàtic", r"informático", r"programador", r"desenvolupador",
    r"policia local", r"policía local", r"bomber", r"bombero", r"socorrista",
    r"oficial 1", r"manteniment", r"mantenimiento", r"electricista", r"lampista",
    r"fuster", r"jardiner", r"netej", r"conserge", r"subaltern", r"ordenança", r"peó", r"operari", r"brigada"
]

# Exclusions de tràmits intermedis, licitacions, notícies, memòries i altres illes
EXCLOURES = [
    r"\bc2\b", r"licit", r"contracte de servei", r"contrato de servicio", r"plecs", r"pliegos",
    r"pressupost base", r"perfil del contractant", r"adjudicaci", r"adjudicación",
    r"llista provisional", r"lista provisional", r"llista definitiva", r"lista definitiva",
    r"relació provisional", r"relación provisional", r"provisional listing",
    r"relació definitiva", r"relación definitiva", r"resultat provisional", r"resultado provisional",
    r"resultat definitiu", r"resultado definitivo", r"aprovats", r"aprobados",
    r"qualificacions", r"calificaciones", r"acta sessió", r"acta de la sessió", r"valoració de mèrits",
    r"citació", r"citación", r"revisió examen", r"revisió exercici", r"finalització procés",
    r"finalización proceso", r"comissió de serveis", r"comisión de servicios",
    r"nomenament", r"nombramiento", r"promoció interna", r"promoción interna",
    r"memòria", r"memoria", r"expropiaci", r"expropiación", r"cuentas anuales", r"comptes anuals",
    r"auditoría", r"estadístiques", r"estadísticas", r"seminari", r"jornada", r"premi",
    r"subvenc", r"xec formació", r"formació", r"estudiants", r"notícies", r"noticias",
    r"sessió ordinària", r"sessió extraordinària", r"del ple\b", r"del pleno\b",
    r"colònies felines", r"taules salarials", r"permisos i llicències", r"protecció de dades",
    r"eivissa", r"ibiza", r"formentera", r"menorca", r"maó", r"ciutadella"
]

ETIQUETES_MENU_GENERIQUES = {
    "convocatòries", "convocatorias", "borsa de treball", "oposicions",
    "treballa amb nosaltres", "ocupació", "personal investigador",
    "fons europeus", "estadísticas", "estadístiques", "recursos humans"
}

PATRO_UBICACIO = re.compile(r"\b(" + "|".join(re.escape(x) for x in NOMS_TERRITORI_I_ENS) + r")\b", re.I)
PATRO_OCUPACIO = re.compile(r"(" + "|".join(OCUPACIO) + r")", re.I)
PATRO_PERFIL = re.compile(r"(" + "|".join(PERFILS) + r")", re.I)
PATRO_TITULACIO_EXCLOSA = re.compile(r"(" + "|".join(TITULACIONS_EXCLOSES) + r")", re.I)
PATRO_EXCLOURE = re.compile(r"(" + "|".join(EXCLOURES) + r")", re.I)
PATRO_IMAS = re.compile(r"\b(imas|1232767)\b", re.I)


def envia_telegram_blocs(blocs_html: list[str]):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram no configurat.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    missatge_actual = ""

    for bloc in blocs_html:
        if len(missatge_actual) + len(bloc) + 2 > 3800:
            resp = requests.post(url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": missatge_actual,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }, timeout=15)
            print("Resposta Telegram (bloc):", resp.status_code)
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
        print("Resposta Telegram (final):", resp.status_code, resp.text[:160])


def es_rellevant(text: str, es_local_mallorca: bool = False) -> bool:
    t = text.strip().lower()
    if t in ETIQUETES_MENU_GENERIQUES:
        return False
    if PATRO_EXCLOURE.search(t) or PATRO_TITULACIO_EXCLOSA.search(t):
        return False
    if PATRO_IMAS.search(t):
        return True

    compleix_ocupacio_i_perfil = bool(PATRO_OCUPACIO.search(t) and PATRO_PERFIL.search(t))
    if es_local_mallorca:
        return compleix_ocupacio_i_perfil
    return bool(PATRO_UBICACIO.search(t) and compleix_ocupacio_i_perfil)


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

                    # Segona passada de filtratge damunt el cos complet de l'oferta
                    if PATRO_EXCLOURE.search(cos_net[:2500]) or PATRO_TITULACIO_EXCLOSA.search(cos_net[:2500]):
                        return None

                    if len(titol) < 85 or "anunci de la convocatòria" in titol.lower():
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
        r"\b(subgrup\s*[ABC][12]|grup\s*[ABC][12]|[ABC][12]|titulat\s+superior|titulat\s+mitjà|grau\s+universitari|batxillerat)\b",
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
        r"(termini[^\.]{5,85}|fins al \d{1,2}[/-]\d{1,2}[/-]\d{2,4}|plazo[^\.]{5,85}|\d{1,2}\s+dies\s+(?:hàbils|naturals))",
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
                            if es_rellevant(f"{nom_dep} {titol}", es_local_mallorca=False):
                                estat = "OBERTA" if ("convocatoria" in titol.lower() or "plazo" in titol.lower()) else "ANUNCI"
                                if desa_convocatoria(cur, id_boe, "BOE", nom_dep, titol, estat, url_html):
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
                desa_log(cur, "BOIB", f"BOIB-{any_actual}", "NO_DISPONIBLE", "Sense edicions detectades")
                conn.commit()
                return novetats

            url_edicio = urljoin("https://www.caib.es", enllacos[0])
            num_edicio = url_edicio.rstrip("/").split("/")[-1]
            r_ed = requests.get(url_edicio, headers=HEADERS_HTTP, timeout=20)
            soup_ed = BeautifulSoup(r_ed.text, "html.parser")

            pagines_seccio = []
            for a_sec in soup_ed.find_all("a", href=True):
                href = a_sec["href"]
                if re.search(r"seccio-ii-|oposicions-i-concursos|seccio-v-", href, re.I):
                    full_sec = urljoin("https://www.caib.es", href)
                    if full_sec not in pagines_seccio:
                        pagines_seccio.append(full_sec)

            if not pagines_seccio:
                pagines_seccio = [url_edicio]

            for url_sec in pagines_seccio[:4]:
                r_s = requests.get(url_sec, headers=HEADERS_HTTP, timeout=15)
                soup_s = BeautifulSoup(r_s.text, "html.parser")
                for tag in soup_s(["nav", "header", "footer"]):
                    tag.decompose()
                for a_tag in soup_s.find_all("a", href=True):
                    text = re.sub(r"\s+", " ", a_tag.get_text(" ", strip=True))
                    if len(text) < 25:
                        continue
                    parent = a_tag.find_parent(["li", "article", "div"])
                    if parent and len(parent.find_all("a")) <= 3:
                        p_text = re.sub(r"\s+", " ", parent.get_text(" ", strip=True))
                        if len(text) < len(p_text) <= 450:
                            text = p_text

                    if es_rellevant(text, es_local_mallorca=True):
                        link = urljoin("https://www.caib.es", a_tag["href"])
                        h = hashlib.md5(f"{num_edicio}:{text[:180]}".encode()).hexdigest()[:10]
                        codi = f"BOIB-{num_edicio}-{h}"
                        if desa_convocatoria(cur, codi, "BOIB", f"BOIB núm. {num_edicio}", text, "PUBLICAT_BOIB", link):
                            novetats.append((codi, f"BOIB núm. {num_edicio}", text[:340], link))

            desa_log(cur, "BOIB", f"BOIB-{any_actual}-{num_edicio}", "REVISAT", f"Noves: {len(novetats)}")
        except Exception as e:
            desa_log(cur, "BOIB", f"BOIB-{any_actual}", "ERROR", str(e)[:120])
        conn.commit()
    return novetats


def descarrega_portal(nom: str, url: str):
    try:
        r = requests.get(url, headers=HEADERS_HTTP, timeout=10)
        if r.status_code != 200:
            return nom, "ERROR", f"HTTP {r.status_code}", []
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["nav", "header", "footer"]):
            tag.decompose()

        candidats = []
        vists = set()

        for a in soup.find_all("a", href=True):
            link_text = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
            if len(link_text) < 15:
                continue
            enllac = urljoin(url, a["href"])
            if enllac.startswith(("mailto:", "javascript:")) or enllac.endswith("#"):
                continue

            text_complet = link_text
            parent = a.find_parent(["tr", "li", "article"])
            if parent and len(parent.find_all("a")) <= 3:
                p_text = re.sub(r"\s+", " ", parent.get_text(" ", strip=True))
                if len(link_text) + 10 < len(p_text) <= 420:
                    text_complet = p_text

            clau = f"{text_complet[:140]}|{enllac}"
            if clau in vists:
                continue
            vists.add(clau)

            if es_rellevant(text_complet, es_local_mallorca=True):
                candidats.append((text_complet, enllac))

        return nom, "REVISAT", "", candidats
    except Exception as e:
        return nom, "ERROR", str(e)[:120], []


def rastreja_portals(conn, llista_fonts, tipus_font):
    novetats = []
    resultats_http = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futurs = [executor.submit(descarrega_portal, nom, url) for nom, url in llista_fonts]
        for futur in as_completed(futurs):
            resultats_http.append(futur.result())

    with conn.cursor() as cur:
        for nom, estat, error_msg, candidats in resultats_http:
            if estat == "ERROR":
                desa_log(cur, tipus_font, nom, "ERROR", error_msg)
                continue
            trobades_font = 0
            for text, enllac in candidats:
                h = hashlib.md5(f"{nom}:{text[:180]}:{enllac}".encode()).hexdigest()[:12]
                codi = f"{tipus_font}-{h}"
                if desa_convocatoria(cur, codi, tipus_font, nom, text, "DETECTADA_PORTAL", enllac):
                    novetats.append((codi, nom, text[:340], enllac))
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
            futurs = [executor.submit(extreu_fitxa_detall, item) for item in totes[:30]]
            for futur in as_completed(futurs):
                resultat = futur.result()
                if resultat is not None:
                    fitxes.append(resultat)

        print(f"Total novetats netes enviades: {len(fitxes)}")
        if fitxes:
            blocs = [f"📌 <b>Rastreig Integral Mallorca · {avui.strftime('%d/%m/%Y')}</b> ({len(fitxes)} ofertes filtrades)"]
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
