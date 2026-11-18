"""Adaptér: dm drogerie markt (dm.cz).

PROČ TAKHLE: dm nevydává týdenní leták, ale **měsíční „dm journal"** (magazín
s cenami). Stránka `dm.cz/journal` přesměruje (301→302) na aktuální číslo na
`journal.dm-drogeriemarkt.cz/jo_{MM}_{RRRR}_online-shop/`, což je Publitas
(stejně jako Albert a Billa). Jde **obyčejným requestem, bez prohlížeče**;
HTML číslo obsahuje přímý odkaz na PDF (`view.publitas.com/{firma}/{id}/pdfs/…`).

Datum:
  - ZAČÁTEK je od dm: meta description číslo popisuje „… Datum vydání: 02.10.2026".
  - KONEC SE ODVOZUJE: dm ho na webu neuvádí. Journal je měsíční a název čísla
    nese měsíc („JOURNAL ŘÍJEN 2026", slug `jo_10_2026`), proto se bere
    **poslední den toho měsíce**. Je to odhad, ne údaj od dm — kdyby dm vydalo
    další číslo dřív, starý leták zůstane „platný" do konce měsíce.

Robots: dm.cz/robots.txt zakazuje jen košík/účet/vyhledávání, `/journal` ne;
journal.dm-drogeriemarkt.cz/robots.txt je 404 (bez omezení).

Pozn.: `dm.cz` odpovídá 200 na jakoukoli cestu (SPA), takže jiné „letáky" se tu
neobjevily; kdyby dm začalo vydávat týdenní leták, bude potřeba druhý zdroj.

Ověřeno 12. 10. 2026: JO_10_2026, 24 stran, vydáno 2. 10. 2026.
"""
from __future__ import annotations

import calendar
import datetime as dt
import html
import re

from km_letaky_model import Letak

NAZEV = "dm"
SLUG = "dm"
WEB = "https://www.dm.cz/"
ZDROJ = "https://www.dm.cz/journal"

PDF = re.compile(r'https://view\.publitas\.com/\d+/(\d+)/pdfs/[0-9a-f-]+\.pdf\?[^"\'<> \\]+')
VYDANO = re.compile(r"Datum vydání:\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})")
SLOZKA = re.compile(r"/jo_(\d{1,2})_(\d{4})[^/]*/?")


def stahni(session) -> list[Letak]:
    r = session.get(ZDROJ, timeout=90, allow_redirects=True)
    r.raise_for_status()
    if "journal.dm-drogeriemarkt.cz" not in r.url:
        raise RuntimeError(f"dm: /journal nepřesměroval na journal.dm-drogeriemarkt.cz ({r.url[:80]}) — redesign?")

    m = PDF.search(r.text)
    if not m:
        raise RuntimeError("dm: v journalu není odkaz na PDF — oprav adaptér")
    pdf = html.unescape(m.group(0))

    s = SLOZKA.search(r.url)
    if not s:
        raise RuntimeError(f"dm: z adresy {r.url[:80]} nejde vyčíst měsíc čísla")
    mesic, rok = int(s.group(1)), int(s.group(2))

    v = VYDANO.search(html.unescape(r.text))
    if v:
        d, me, y = (int(x) for x in v.groups())
        od = dt.date(y, me, d)
    else:
        print("  ! dm: chybí „Datum vydání“, začátek = 1. den měsíce (odvozeno)")
        od = dt.date(rok, mesic, 1)
    do = dt.date(rok, mesic, calendar.monthrange(rok, mesic)[1])
    if do < od:
        od = dt.date(rok, mesic, 1)

    return [Letak(
        obchod_slug=SLUG,
        obchod_nazev=NAZEV,
        externi_id=f"journal-{rok}-{mesic:02d}-{m.group(1)}",
        titul=f"{NAZEV} journal {mesic:02d}/{rok}",
        od=od,
        do=do,
        zdroj_url=r.url,
        pdf_url=pdf,
        varianta="journal",
        oznaceni="journal",
    )]
