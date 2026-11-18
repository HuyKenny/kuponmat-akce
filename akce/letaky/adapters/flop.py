"""Adaptér: Flop / Flop Top (flop-potraviny.cz).

PROČ TAKHLE: na `/akcni-letaky/` (WordPress + 3D flipbook) je věta „Letáky platné od 18. 11. do 24.11. 2026"
a dvě tlačítka s přímými odkazy na PDF v `wp-content/uploads/RRRR/MM/`: „Leták FLOP TOP" (`47-26-tisk-nahled-s.pdf`,
s klubovými cenami a přeškrtnutými původními cenami) a „Leták FLOP" (`Flop-A-47-26-tisk-nahled-s.pdf`, jen akční ceny).
Datum je tedy přímo na webu, nic se neodvozuje. Jde obyčejným requestem, bez prohlížeče.
Čtení jen odkazů na PDF z uploads téhle domény, jiné odkazy se nesledují.
Ověřeno 18. 11. 2026: dva leták 18.–24. 11. 2026, 16 stran, PDF 11 MB.
"""
from __future__ import annotations

import datetime as dt
import re

from km_letaky_model import Letak

NAZEV = "Flop"
SLUG = "flop"
WEB = "https://www.flop-potraviny.cz/"
STRANKA = "https://www.flop-potraviny.cz/akcni-letaky/"

_A = re.compile(r'<a\b[^>]*href="(https://www\.flop-potraviny\.cz/wp-content/uploads/[^"\s]+\.pdf)"[^>]*>(.*?)</a>', re.S | re.I)
_DATUM = re.compile(r"platn[ée]\s+od\s+(\d{1,2})\.\s*(\d{1,2})\.\s*(?:(\d{4})\s*)?do\s+(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", re.I)


def stahni(session) -> list[Letak]:
    r = session.get(STRANKA, timeout=90, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    text = re.sub(r"<[^>]+>", " ", r.text)
    m = _DATUM.search(re.sub(r"\s+", " ", text))
    if not m:
        print("  ! Flop: na stránce není datum platnosti, přeskakuji")
        return []
    d1, m1, y1, d2, m2, y2 = m.groups()
    y2 = int(y2)
    od, do = dt.date(int(y1) if y1 else y2, int(m1), int(d1)), dt.date(y2, int(m2), int(d2))
    letaky: list[Letak] = []
    videno = set()
    for pdf, popisek in _A.findall(r.text):
        if pdf in videno:
            continue
        videno.add(pdf)
        popisek = re.sub(r"<[^>]+>", " ", popisek)
        top = bool(re.search(r"\btop\b", popisek, re.I))
        letaky.append(Letak(
            obchod_slug=SLUG,
            obchod_nazev=NAZEV,
            externi_id=pdf.rsplit("/", 1)[-1].removesuffix(".pdf"),
            titul=f"{NAZEV} {'Top ' if top else ''}leták",
            od=od,
            do=do,
            zdroj_url=STRANKA,
            pdf_url=pdf,
            varianta="top" if top else None,
            oznaceni="Top leták" if top else None,
        ))
    return letaky
