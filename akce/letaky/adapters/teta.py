"""Adaptér: Teta drogerie (tetadrogerie.cz).

PROČ TAKHLE: `tetadrogerie.cz/letak` (SSR Nuxt, jde obyčejným requestem) vypisuje
aktuální letáky jako bloky `c-block-leaflet` s názvem a **platností od–do přímo
na webu** („platnost 8. 10. 2026 - 19. 10. 2026"), takže se nic neodvozuje.
Odkaz vede na `letak.tetadrogerie.cz/{slug}/` (eCPaper) a ta stránka má v HTML
odkaz na kompletní PDF na `liveecpaperdmp.blob.core.windows.net/.../*.pdf`.
PDF je úplné (21 stran) — obrázky stran z HTML by byly jen 20 a chyběla by jedna
(„cenový tresk"), proto se bere PDF a ne jednotlivé JPEG.

Vydávají se dva letáky: běžný („Teta leták č. 21", 21 stran) a klubový
(„Teta klubový leták č. 21", 1 strana, stejná platnost) — klubový dostane
`varianta=klub`, jinak by měly stejný slug.

robots.txt: tetadrogerie.cz zakazuje jen košík, účet, /api/ a /_nuxt/;
letak.tetadrogerie.cz má `Allow: /`.
Ověřeno 12. 10. 2026: leták č. 21, 8. 10. – 19. 10. 2026, PDF 13 MB / 21 stran.
"""
from __future__ import annotations

import html
import re

from km_letaky_model import Letak, datum_cz

NAZEV = "Teta"
SLUG = "teta"
WEB = "https://www.tetadrogerie.cz/"
ZDROJ = "https://www.tetadrogerie.cz/letak"

_ODKAZ = re.compile(r'<a href="\s*(https://letak\.tetadrogerie\.cz/[^"\s]+)"')
_TITUL = re.compile(r'c-block-leaflet__title[^>]*>([^<]*)<')
_PLATNOST = re.compile(r'platnost\s*(?:<[^>]*>\s*)*(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})\s*[-–]\s*(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})')
_PDF = re.compile(r'https://liveecpaperdmp\.blob\.core\.windows\.net/[^"\'\s<>\\)]+\.pdf')


def stahni(session) -> list[Letak]:
    r = session.get(ZDROJ, timeout=90)
    r.raise_for_status()
    # Bloky letáků jsou ohraničené začátkem `c-block-leaflet"`.
    bloky = re.split(r'<div class="c-block-leaflet"', r.text)[1:]
    if not bloky:
        raise RuntimeError("Teta: na stránce nejsou bloky letáků (c-block-leaflet) — oprav adaptér")

    letaky: list[Letak] = []
    for blok in bloky:
        blok = blok[:3000]
        mo, mt, mp = _ODKAZ.search(blok), _TITUL.search(blok), _PLATNOST.search(blok)
        if not (mo and mt and mp):
            print("  ! Teta: blok letáku bez odkazu/názvu/platnosti, přeskakuji")
            continue
        url = mo.group(1).rstrip("/") + "/"
        nazev = html.unescape(mt.group(1)).strip()
        od, do = datum_cz(mp.group(1)), datum_cz(mp.group(2))

        det = session.get(url, timeout=90)
        pdfs = sorted(set(_PDF.findall(det.text)))
        if det.status_code != 200 or not pdfs:
            print(f"  ! Teta: {url} nemá odkaz na PDF (HTTP {det.status_code}), přeskakuji")
            continue
        if len(pdfs) > 1:
            print(f"  ! Teta: {url} má {len(pdfs)} PDF, beru první")

        slug = url.rstrip("/").rsplit("/", 1)[-1]
        klub = "klub" in slug or "klub" in nazev.lower()
        letaky.append(Letak(
            obchod_slug=SLUG,
            obchod_nazev=NAZEV,
            externi_id=slug,
            titul=nazev,
            od=od,
            do=do,
            zdroj_url=url,
            pdf_url=pdfs[0],
            varianta="klub" if klub else None,
            oznaceni="klubový leták" if klub else None,
        ))
    return letaky
