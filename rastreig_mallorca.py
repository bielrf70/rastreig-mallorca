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
    ("UIB Personal / Recerca", "https://www.uib.cat/"),
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

# 3. FILTRES AFINATS DE TERRITORI, PERFILS I EXCLUSIONS
NOMS_TERRITORI_I_ENS = [m[0].split(" (")[0].lower() for m in MUNICIPIS_53] + [
    "mallorca", "illes balears", "islas baleares", "caib", "imas", "1232767",
    "consell de mallorca", "ib-salut", "ibsalut", "ibavi", "abaqua", "ibanat",
    "sfm", "fundació bit", "ibestat", "fasd", "uib", "fueib", "tragsa", "tragsatec",
    "emaya", "smap", "aena", "autoritat portuària", "mancomunitat del pla",
    "mancomunitat des raiguer", "mancomunitat del migjorn", "mancomunitat del nord", "tramuntana"
]

PERFILS = [
    r"geograf", r"sociolog", r"\bsig\b", r"\bgis\b", r"cartograf",
    r"urbanism", r"habitatge", r"vivienda", r"mobilitat", r"movilidad",
    r"demograf", r"estadístic", r"enquest", r"investigador",
    r"polítiques públiques", r"políticas públicas", r"projectes europeus", r"fons europeus",
    r"administratiu", r"administrativo", r"tècnic", r"técnico",
    r"titulat superior", r"titulat mitjà", r"\ba1\b", r"\ba2\b", r"\bc1\b",
    r"borsí", r"borsa de treball", r"bolsa de trabajo", r"bolsa de empleo",
    r"convocatòria", r"convocatoria", r"oposic", r"procés selectiu", r"proceso selectivo",
    r"procediment selectiu", r"procedimiento selectivo", r"crida pública"
]

EXCLOURES = [
    r"\bc2\b", r"auxiliar d'infermeria", r"auxiliar de enfermería", r"tcae", r"celador",
    r"subaltern", r"ordenança", r"conserge", r"peó", r"operari", r"brigada",
    r"policia local", r"policía local", r"bomber", r"bombero", r"socorrista",
    r"llista provisional", r"lista provisional", r"llista definitiva", r"lista definitiva",
    r"resultat definitiu", r"resultado definitivo", r"aprovats", r"aprobados",
    r"qualificacions", r"calificaciones", r"nomenament", r"nombramiento",
    r"adjudicació", r"adjudicación", r"promoció interna", r"promoción interna",
    r"eivissa", r"ibiza", r"formentera", r"menorca", r"maó", r"ciutadella",
    r"les meves dades", r"protecció de dades", r"sessió ordinària", r"sessió extraordinària",
    r"del ple\b", r"del pleno\b", r"colònies felines", r"subvencions", r"subvenciones",
    r"jornada informativa", r"taules salarials", r"permisos i llicències"
]

PATRO_UBICACIO = re.compile(r"\b(" + "|".join(re.escape(x) for x in NOMS_TERRITORI_I_ENS) + r")\b", re.I)
PATRO_PERFIL = re.compile(r"(" + "|".join(PERFILS) + r")", re.I)
PATRO_EXCLOURE = re.compile(r"(" + "|".join(EXCLOURES) + r")", re.I)


def envia_telegram(missatge_html: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram no configurat.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    resp = requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": missatge_html[:4000],
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }, timeout=15)
    print("Resposta Telegram:", resp.status_code, resp.text[:200])


def es_rellevant(text: str, es_local_mallorca: bool = False) -> bool:
    t = text.lower()
    if PATRO_EXCLOURE.search(t):
        return False
    if es_local_mallorca:
        return bool(PATRO_PERFIL.search(t) or "1232767" in t or "imas" in t)
    return bool(PATRO_UBICACIO.search(t) and PATRO_PERFIL.search(t))


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
                                    novetats.append((id_boe, nom_dep, titol, url_html))

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

            for a_tag in soup_ed.find_all("a", href=True):
                text = a_tag.get_text(" ", strip=True)
                if len(text) < 15:
                    continue
                if es_rellevant(text, es_local_mallorca=True):
                    link = urljoin("https://www.caib.es", a_tag["href"])
                    h = hashlib.md5(f"{num_edicio}:{text}".encode()).hexdigest()[:10]
                    codi = f"BOIB-{any_actual}-{num_edicio}-{h}"
                    if desa_convocatoria(cur, codi, "BOIB", "CAIB / Ens Locals IB", text, "PUBLICAT_BOIB", link):
                        novetats.append((f"BOIB {num_edicio}", "BOIB", text[:240], link))

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
        candidats = []
        for a in soup.find_all("a", href=True):
            text = a.get_text(" ", strip=True)
            if len(text) >= 15 and es_rellevant(text, es_local_mallorca=True):
                enllac = urljoin(url, a["href"])
                if not enllac.startswith("mailto:"):
                    candidats.append((text, enllac))
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
                h = hashlib.md5(f"{nom}:{text}:{enllac}".encode()).hexdigest()[:12]
                codi = f"{tipus_font}-{h}"
                if desa_convocatoria(cur, codi, tipus_font, nom, text, "DETECTADA_PORTAL", enllac):
                    novetats.append((codi, nom, text[:240], enllac))
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
    print(f"Total novetats detectades: {len(totes)}")

    if totes:
        linies = [f"📌 <b>Rastreig Integral Mallorca · {avui.strftime('%d/%m/%Y')}</b>\n"]
        for codi, entitat, titol, url in totes[:25]:
            alerta = "🚨 <b>ALERTA IMAS C1!</b> " if ("imas" in (entitat + titol).lower() or "1232767" in titol) else ""
            entitat_segura = html.escape(entitat)
            titol_segur = html.escape(titol)
            url_segura = html.escape(url, quote=True)
            linies.append(f"{alerta}<b>{entitat_segura}</b> (<code>{codi}</code>)\n{titol_segur}\n<a href=\"{url_segura}\">Veure fitxa</a>\n")
        envia_telegram("\n".join(linies))

    conn.close()


if __name__ == "__main__":
    main()
