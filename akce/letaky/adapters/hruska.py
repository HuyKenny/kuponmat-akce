"""Adaptér: Hruška (mojehruska.cz).

PROČ TAKHLE: oficiální web je `mojehruska.cz` (WordPress, `hruska.cz` neexistuje).
Na `/` je nadpis „Aktuální leták 7.10.2026 - 13.10.2026" a tlačítko „Otevřít v PDF"
s přímým odkazem na `media.mojehruska.cz/RRRR/M/{číslo}_{rok}-web.pdf`. Na `/katalog/`
je stejná struktura pro dvouměsíční katalog („Aktuální katalog 15. 9. - 9. 11. 2026",
rok je jen u konce). Datum platnosti je tedy přímo na webu, nic se neodvozuje.
Jde obyčejným requestem, bez prohlížeče.

robots.txt: `User-agent: *` / `Disallow:` (nic nezakazuje).
Ověřeno 12. 10. 2026: leták 7.–13. 10. 2026, PDF 10 MB.
"""
from __future__ import annotations

import datetime as dt
import re

from km_letaky_model import Letak

NAZEV = "Hruška"
SLUG = "hruska"
WEB = "https://mojehruska.cz/"

STRANKY = [
    ("https://mojehruska.cz/", "leták", None),
    ("https://mojehruska.cz/katalog/", "katalog", "katalog"),
]

_NADPIS = re.compile(
    r"Aktuální\s+(?:leták|katalog)\s*(?:<br\s*/?>|\s)*"
    r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})?\s*[-–]\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", re.I)
_PDF = re.compile(r'href="(https://media\.mojehruska\.cz/[^"\s]+\.pdf)"')


def stahni(session) -> list[Letak]:
    letaky: list[Letak] = []
    for url, druh, varianta in STRANKY:
        r = session.get(url, timeout=90)
        r.raise_for_status()
        m, p = _NADPIS.search(r.text), _PDF.search(r.text)
        if not (m and p):
            print(f"  ! Hruška: {url} bez nadpisu s datem nebo bez PDF, přeskakuji")
            continue
        d1, m1, y1, d2, m2, y2 = m.groups()
        y2 = int(y2)
        y1 = int(y1) if y1 else y2
        od, do = dt.date(y1, int(m1), int(d1)), dt.date(y2, int(m2), int(d2))
        if od > do:                      # katalog přes Nový rok: „15. 12. - 9. 1. 2027"
            od = od.replace(year=y1 - 1)
        pdf = p.group(1)
        letaky.append(Letak(
            obchod_slug=SLUG,
            obchod_nazev=NAZEV,
            externi_id=pdf.rsplit("/", 1)[-1].removesuffix(".pdf"),
            titul=f"{NAZEV} {druh}",
            od=od,
            do=do,
            zdroj_url=url,
            pdf_url=pdf,
            varianta=varianta,
            oznaceni="katalog" if varianta else None,
        ))
    return letaky
