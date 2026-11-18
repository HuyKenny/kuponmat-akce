"""Adaptér: Travel Free (travel-free.cz, obchody na hranicích).

Stránka `/cz/akcni-nabidka` obsahuje kartu „Leták s akční nabídkou" s datem „13.11. – 26.11.2026"
a odkazem `/data/special_offer/<id>-special-offer-cz-RRRR-MM-DD-RRRR-MM-DD.pdf` (platnost je i v názvu souboru).
Jde obyčejným requestem.

POZOR: `robots.txt` Travel Free má `Disallow: /*.pdf$` — roboti nemají PDF stahovat. Adaptér to respektuje:
dokud je pravidlo v robots.txt, vrací []. Zapnout jde `RESPEKTOVAT_ROBOTS = False` (rozhodnutí majitele).
Ověřeno 18. 11. 2026: leták 13.–26. 11. 2026, 12 stran.
"""
from __future__ import annotations

import datetime as dt
import re

from km_letaky_model import Letak

NAZEV = "Travel Free"
SLUG = "travelfree"
WEB = "https://www.travel-free.cz/"
ZDROJ = "https://www.travel-free.cz/cz/akcni-nabidka"

RESPEKTOVAT_ROBOTS = True
PDF = re.compile(r'/data/special_offer/(\d+)-special-offer-cz-(\d{4})-(\d{2})-(\d{2})-(\d{4})-(\d{2})-(\d{2})\.pdf')


def _robots_zakazuje_pdf(session) -> bool:
    try:
        r = session.get("https://www.travel-free.cz/robots.txt", timeout=60)
    except Exception:
        return True
    return r.status_code == 200 and bool(re.search(r"^\s*Disallow:\s*/\*\.pdf\$", r.text, re.M))


def stahni(session) -> list[Letak]:
    if RESPEKTOVAT_ROBOTS and _robots_zakazuje_pdf(session):
        print("  – Travel Free: robots.txt zakazuje PDF (Disallow: /*.pdf$), přeskakuji")
        return []
    r = session.get(ZDROJ, timeout=90)
    r.raise_for_status()
    out, videne = [], set()
    for m in PDF.finditer(r.text):
        if m.group(1) in videne:
            continue
        videne.add(m.group(1))
        y1, m1, d1, y2, m2, d2 = (int(x) for x in m.groups()[1:])
        try:
            od, do = dt.date(y1, m1, d1), dt.date(y2, m2, d2)
        except ValueError:
            continue
        out.append(Letak(
            obchod_slug=SLUG, obchod_nazev=NAZEV, externi_id=m.group(1),
            titul=f"{NAZEV} akční nabídka", od=od, do=do, zdroj_url=ZDROJ,
            pdf_url="https://www.travel-free.cz" + m.group(0),
        ))
    return out
