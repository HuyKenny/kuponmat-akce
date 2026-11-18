"""Adaptér: Norma (norma-online.cz -> norma-online.de/cz/).

PROČ TAKHLE: `norma-online.cz` přesměruje na `www.norma-online.de/cz/angebote/` (český
web Normy běží na německé doméně). Stránka (SSR, obyčejný request) vypisuje aktuální
letáky jako bloky `flippingbookBox` s nadpisem „Nabídka na týden od pondělí 12.10." a
tlačítkem „PDF ke stažení" -> `/cz/angebote/online-prospekt/2026-42_CZ.pdf` (celý leták
v jednom PDF, ~28 MB). Číslo kalendářního týdne a rok jsou v názvu souboru.

Datum:
  - ZAČÁTEK je od Normy (den.měsíc z nadpisu; rok z názvu souboru `RRRR-KT_CZ.pdf`).
  - KONEC SE ODVOZUJE: Norma na webu konec neuvádí, jen „od pondělí". Nabídka platí
    týden, prodejny mají otevřeno po–so, proto se bere **začátek + 5 dní (sobota)**.
    Je to odhad, ne údaj od Normy.
Bere se jen leták, který už platí (`od <= dnes`); „příští týden" se načte, až začne.

robots.txt: norma-online.de zakazuje jen `/ws/` a pár konkrétních botů (ne naše UA).
Ověřeno 12. 10. 2026: KT 42, od 12. 10. 2026 (PDF 28 MB).
"""
from __future__ import annotations

import datetime as dt
import html
import re

from km_letaky_model import Letak

NAZEV = "Norma"
SLUG = "norma"
WEB = "https://www.norma-online.cz/"
ZDROJ = "https://www.norma-online.de/cz/angebote/"
DNU_PLATNOSTI = 5   # pondělí + 5 = sobota

_BLOK = re.compile(
    r'<h3 class="headline h2">([^<]*?(\d{1,2})\.\s*(\d{1,2})\.)\s*</h3>.*?'
    r'href="(/cz/angebote/online-prospekt/(\d{4})-(\d{1,2})_CZ\.pdf)"', re.S)


def stahni(session) -> list[Letak]:
    r = session.get(ZDROJ, timeout=90)
    r.raise_for_status()
    t = r.content.decode("utf-8", errors="replace")
    nalezeno = _BLOK.findall(t)
    if not nalezeno:
        raise RuntimeError("Norma: na stránce nejsou bloky letáků s PDF — oprav adaptér")

    dnes = dt.date.today()
    letaky: list[Letak] = []
    for nadpis, d, m, cesta, rok, kt in nalezeno:
        od = dt.date(int(rok), int(m), int(d))
        if od > dnes:
            continue
        letaky.append(Letak(
            obchod_slug=SLUG,
            obchod_nazev=NAZEV,
            externi_id=f"{rok}-{int(kt):02d}",
            titul=html.unescape(nadpis).strip(),
            od=od,
            do=od + dt.timedelta(days=DNU_PLATNOSTI),
            zdroj_url=ZDROJ,
            pdf_url="https://www.norma-online.de" + cesta,
        ))
    return letaky
