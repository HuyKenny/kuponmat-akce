"""Adaptér: Billa (billa.cz).

PROČ TAKHLE: Billa hostuje letáky na Publitas (stejně jako Albert). Seznam je na
`billa.cz/akcni-letaky` a **jde obyčejným requestem, bez prohlížeče** (Nuxt SSR).
Karty ukazují na dvojí typ adres:

    /letaky-billa?tab=letaky-billa/velky-letak[-nasledujici]   (týdenní „velký leták")
    /akcni-letaky/{slug}                                       (katalogy, leták BILLA klub, speciály)

Každá podstránka má v HTML přímý odkaz na PDF
`view.publitas.com/64069/{id}/pdfs/{uuid}.pdf?response-content-disposition=…filename=…`,
a **název souboru nese titulek i datum od–do** („BILLA.cz - Velký leták
14. 10. - 20. 10. 2026.pdf"). Datum tedy pochází od Billy, nic se neodvozuje.
(Totéž datum je na kartě v seznamu: „Platí od středy 14. 10. do úterý 20. 10. 2026".)

PDF (view.publitas.com) jde stáhnout curlem; robots.txt na view.publitas.com je 404
(žádná omezení), billa.cz/robots.txt je jen odkaz na sitemapu.

Přeskakuje se:
 - cokoli, z čeho nejde vyčíst datum (např. „Gusto magazín – Podzim 2026"),
 - regionální „Speciál: {město}" (leták jen pro pár prodejen; na celostátním webu
   by mátl). Zapnout jde `VCETNE_REGIONALNICH = True`.

Ověřeno 12. 10. 2026: velký leták 7.–13. 10. + následující 14.–20. 10., katalogy
Itálie a Podzimní nápoje (30. 9.–20. 10.), leták BILLA klub (7.–20. 10.).
"""
from __future__ import annotations

import datetime as dt
import html
import re
from urllib.parse import unquote

from km_letaky_model import Letak, odstran_diakritiku

NAZEV = "Billa"
SLUG = "billa"
WEB = "https://www.billa.cz/"
ZDROJ = "https://www.billa.cz/akcni-letaky"

VCETNE_REGIONALNICH = False

ODKAZ = re.compile(r'href="(/letaky-billa\?tab=letaky-billa/[a-z0-9-]+|/akcni-letaky/[a-z0-9-]+)"')
PDF = re.compile(r'https://view\.publitas\.com/\d+/(\d+)/pdfs/[0-9a-f-]+\.pdf\?[^"\'<> \\]+')
# „… 14. 10. - 20. 10. 2026" nebo „… 30. 9. 2026 - 20. 10. 2026"
DATA = re.compile(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})?\s*-\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})")


def _soubor(pdf_url: str) -> str:
    m = re.search(r"filename%2A%3DUTF-8%27%27([^&]+)", pdf_url.replace("&amp;", "&"))
    if not m:
        return ""
    return unquote(unquote(m.group(1)))     # dvakrát zakódováno


def stahni(session) -> list[Letak]:
    r = session.get(ZDROJ, timeout=90)
    r.raise_for_status()
    odkazy = list(dict.fromkeys(ODKAZ.findall(r.text)))
    if not odkazy:
        raise RuntimeError("Billa: na stránce nejsou odkazy na letáky — nejspíš redesign")

    letaky: list[Letak] = []
    videne: set[str] = set()
    # 18. 11. 2026: velký leták má na své stránce záložky „…-aktualni" / „…-nasledujici" a aktuální týden bývá
    # pod „následující" (web Billy se zpožďuje) → odkazy nalezené na podstránkách se procházejí taky.
    i = 0
    while i < len(odkazy):
        cesta = odkazy[i]
        i += 1
        if "/special-" in cesta and not VCETNE_REGIONALNICH:
            continue
        url = "https://www.billa.cz" + html.unescape(cesta)
        d = session.get(url, timeout=90)
        if d.status_code != 200:
            print(f"  ! Billa: {cesta} vrací {d.status_code}, přeskakuji")
            continue
        for nove in ODKAZ.findall(d.text):
            if nove not in odkazy and "velky-letak" in nove:
                odkazy.append(nove)
        m = PDF.search(d.text)
        if not m:
            print(f"  – Billa: {cesta} nemá PDF, přeskakuji")
            continue
        pdf = html.unescape(m.group(0))
        doc_id = m.group(1)
        if doc_id in videne:
            continue
        videne.add(doc_id)

        soubor = _soubor(pdf)
        md = DATA.search(soubor)
        if not md:
            print(f"  – Billa: {cesta} — z názvu PDF nejde vyčíst platnost, přeskakuji")
            continue
        d1, m1, r1, d2, m2, r2 = md.groups()
        try:
            do = dt.date(int(r2), int(m2), int(d2))
            od = dt.date(int(r1 or r2), int(m1), int(d1))
        except ValueError as e:
            print(f"  ! Billa: nesmyslné datum v názvu PDF ({e}), přeskakuji")
            continue
        if do < od:                        # přes Silvestr, rok začátku v názvu chybí
            od = od.replace(year=od.year - 1)

        titul = re.sub(r"^BILLA\.cz\s*-\s*", "", soubor[:md.start()]).strip(" -")
        titul = re.sub(r"\.pdf$", "", titul)
        titul = re.sub(r"^BILLA\s+", "", titul, flags=re.I)      # „Billa klub" → „klub" nechceme, viz níže
        if titul.lower() == "klub":
            titul = "leták BILLA klub"
        velky = "/velky-letak" in cesta
        slug_str = cesta.rstrip("/").split("/")[-1]
        letaky.append(Letak(
            obchod_slug=SLUG,
            obchod_nazev=NAZEV,
            externi_id=doc_id,
            titul=f"{NAZEV} {titul}".strip(),
            od=od,
            do=do,
            zdroj_url=url,
            pdf_url=pdf,
            varianta=None if velky else odstran_diakritiku(titul or slug_str),
            oznaceni=None if velky else (titul or None),
        ))
    return letaky
