"""Adaptér: Ratio (ratio.cz, cash & carry Velkotržnice Lipence).

Měsíční leták (cca 88 stran) je Heyzine flipbook. `www.ratio.cz/sluzby/` obsahuje nadpis „leták Listopad - 2026"
a odkaz `https://heyzine.com/flip-book/<id>.html`; HTML flipbooku nese přímý odkaz na PDF
`https://cdnm.heyzine.com/files/uploaded/<id><hash>.pdf` (~30 MB). Jde obyčejným requestem.

Datum: leták je měsíční („OD 1. 11. DO 30. 11. 2026", doplněno „nebo do vyprodání zásob"); web ho neuvádí jako datum,
jen jako měsíc v nadpisu. Konec se proto ODVOZUJE jako poslední den toho měsíce. První strana má navíc týdenní bloky
„Cena platí 1.-8. listopad" (jen 4 produkty) – parser tu stranu přeskakuje.
robots.txt ratio.cz: `Crawl-delay: 10`, nic nezakazuje (jen /servers/frontend/); heyzine.com: `Disallow: /convert`.
Ověřeno 18. 11. 2026: leták Listopad 2026, 88 stran.
"""
from __future__ import annotations

import calendar
import datetime as dt
import html
import re

from km_letaky_model import Letak

NAZEV = "Ratio"
SLUG = "ratio"
WEB = "https://www.ratio.cz/"
ZDROJ = "https://www.ratio.cz/sluzby/"

MESICE = ["leden", "únor", "březen", "duben", "květen", "červen", "červenec", "srpen", "září", "říjen", "listopad", "prosinec"]
FLIP = re.compile(r"https://heyzine\.com/flip-book/([0-9a-z]+)\.html")
PDF = re.compile(r"https://cdnm\.heyzine\.com/files/uploaded/([0-9a-f]+)\.pdf")
NADPIS = re.compile(r"leták\s+(" + "|".join(MESICE) + r")\s*-\s*(\d{4})", re.I)


def stahni(session) -> list[Letak]:
    r = session.get(ZDROJ, timeout=90)
    r.raise_for_status()
    t = html.unescape(r.text)
    f = FLIP.search(t)
    if not f:
        print("  – Ratio: na /sluzby/ není odkaz na flipbook, přeskakuji")
        return []
    m = NADPIS.search(t)
    if not m:
        print("  – Ratio: nejde vyčíst měsíc letáku z nadpisu, přeskakuji")
        return []
    mesic, rok = MESICE.index(m.group(1).lower()) + 1, int(m.group(2))
    od = dt.date(rok, mesic, 1)
    do = dt.date(rok, mesic, calendar.monthrange(rok, mesic)[1])
    d = session.get(f.group(0), timeout=90, headers={"User-Agent": "Mozilla/5.0"})
    if d.status_code != 200:
        print(f"  ! Ratio: flipbook vrací {d.status_code}, přeskakuji")
        return []
    p = PDF.search(d.text)
    if not p:
        print("  – Ratio: ve flipbooku není PDF, přeskakuji")
        return []
    return [Letak(
        obchod_slug=SLUG, obchod_nazev=NAZEV, externi_id=f.group(1),
        titul=f"{NAZEV} leták {m.group(1).capitalize()} {rok}", od=od, do=do,
        zdroj_url=f.group(0), pdf_url=p.group(0), end_derived=False,
    )]
