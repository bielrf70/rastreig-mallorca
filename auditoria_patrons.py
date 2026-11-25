import re
import asyncio
import requests
from bs4 import BeautifulSoup
from collections import Counter
from playwright.async_api import async_playwright

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

MOSTRES_ESTATIQUES = [
    ("BOIB_PORTADA", "https://www.caib.es/eboibfront/ca/2026/"),
    ("CAIB_NOVETATS", "https://www.caib.es/sites/oposicions/ca/novetats/"),
    ("IMAS_OFERTES", "https://www.imasmallorca.net/ca/ofertes-de-feina"),
    ("FUNDACIO_BIT", "https://www.fundaciobit.org/"),
    ("UIB_INVESTIGACIO", "https://investigacio.uib.cat/Contractacio/Convocatories-vigents/"),
]

MOSTRES_JS = [
    ("GESTIONA_POLLENCA", "https://ajpollenca.sedelectronica.es/board"),
    ("GESTIONA_CAMPOS", "https://ajcampos.sedelectronica.es/board"),
    ("GESTIONA_BINISSALEM", "https://ajbinissalem.sedelectronica.es/board"),
    ("CONVOCA_CALVIA", "https://calvia.convoca.online/"),
    ("CONVOCA_MARRATXI", "https://marratxi.convoca.online/"),
]


def analitza_blocs(nom: str, html_text: str):
    soup = BeautifulSoup(html_text, "html.parser")
    for tag in soup(["nav", "header", "footer", "script", "style"]):
        tag.decompose()

    families_gestiona = Counter()
    prefixos_titol = Counter()
    exemples = []

    for el in soup.find_all(["tr", "li", "article", "div"]):
        enllacos = el.find_all("a", href=True)
        if not (1 <= len(enllacos) <= 3):
            continue
        txt = re.sub(r"\s+", " ", el.get_text(" ", strip=True))
        if not (30 <= len(txt) <= 450):
            continue

        # Detecta famílies procedimentals de Gestiona (p. ex. "1234/2026 Seleccions de Personal...")
        m_gest = re.search(r"\b\d{1,5}/202\d\s+([A-ZÀ-Ú][^0-9]{10,70}?)\s+(?:Anuncis|Ocupació pública)", txt)
        if m_gest:
            families_gestiona[m_gest.group(1).strip()] += 1

        # Detecta les 4 primeres paraules (fórmula administrativa d'inici)
        paraules = [p for p in re.sub(r"[^a-zA-ZÀ-ÿ\s]", "", txt).split() if len(p) > 2]
        if len(paraules) >= 3:
            prefixos_titol[" ".join(paraules[:3]).lower()] += 1

        if len(exemples) < 6 and re.search(r"(bors|oposic|convocat|bases|procés|plaça|selecc)", txt, re.I):
            exemples.append(f"  [{el.name} class={el.get('class')}] {txt[:220]}")

    print(f"\n=== {nom} ===")
    if families_gestiona:
        print("Families procedimentals detectades:", dict(families_gestiona.most_common(5)))
    print("Formules d'inici mes frequents:", dict(prefixos_titol.most_common(6)))
    print("Exemples estructurals:")
    for ex in exemples:
        print(ex)


async def executa_auditoria():
    for nom, url in MOSTRES_ESTATIQUES:
        try:
            r = requests.get(url, headers=HEADERS, timeout=12)
            if r.status_code == 200:
                analitza_blocs(nom, r.text)
        except Exception as e:
            print(f"Error {nom}: {e}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=HEADERS["User-Agent"])
        for nom, url in MOSTRES_JS:
            page = await context.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(2500)
                analitza_blocs(nom, await page.content())
            except Exception as e:
                print(f"Error JS {nom}: {e}")
            finally:
                await page.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(executa_auditoria())
