"""Adaptér: COOP (coopclub.cz).

PROČ TAKHLE: `coop.cz` je starý web (a `skupina.coop` o letácích nic nemá), ale
oficiální aktuální letáky COOP Centrum vydává **COOP Club** (WordPress, vyrábí ho
Delex pro COOP Centrum): `https://www.coopclub.cz/letaky/`. Jde **obyčejným
requestem, bez prohlížeče**. Na seznamu je u každého letáku sekce (nadpis),
titulek „CSC 21 (od 7.10. do 20.10.)", **datum od–do v plném tvaru**
(`07.10.2026` / `20.10.2026`) a odkaz na detail; detail má odkaz
`wp-content/uploads/…/{id}-CSC-21-26.pdf`. Nic se neodvozuje.

COOP je družstevní: kromě celostátních letáků vydávají letáky i regionální
Jednoty (Jihočeský, Středočeský, Východočeský, Západočeský region). Ty se
**přeskakují** (nejsou pro celé Česko; zapnout jde `VCETNE_REGIONALNICH`).
Bere se: „COOP Cena" (CSC), „TIP - EXTRA", „TUTY TIP - MENU" — tytéž tři letáky,
které má na COOPu i kupi.cz.

Robots: coopclub.cz/robots.txt je 404 (bez omezení); crawl-delay 5 s je jen u
skupina.coop, kterou nepoužíváme. Mezi detaily přesto děláme krátkou pauzu.

Ověřeno 12. 10. 2026: CSC 21 (7.–20. 10.), TUTY TIP MENU 21 (7.–20. 10.),
TIP EXTRA 20 (30. 9.–13. 10.).
"""
from __future__ import annotations

import datetime as dt
import html
import re
import time

from km_letaky_model import Letak, odstran_diakritiku

NAZEV = "Coop"
SLUG = "coop"
WEB = "https://www.coop.cz/"
ZDROJ = "https://www.coopclub.cz/letaky/"

VCETNE_REGIONALNICH = False
# Sekce na seznamu, které bereme (nadpis h3 → čitelný název do titulku).
CELOSTATNI = {
    "COOP Cena": "Cena",
    "TIP - EXTRA": "Tip Extra",
    "TUTY TIP - MENU": "Tuty Tip Menu",
}

SEKCE = re.compile(r'<h3 class="ui dividing header">(.*?)</h3>(.*?)(?=<h3 class="ui dividing header">|\Z)', re.S)
KARTA = re.compile(
    r'data-href="(https://www\.coopclub\.cz/letaky/[^"]+/)".*?class="header">\s*(.*?)\s*</a>'
    r'.*?check icon"></i>\s*(\d{2})\.(\d{2})\.(\d{4}).*?remove icon"></i>\s*(\d{2})\.(\d{2})\.(\d{4})', re.S)
PDF = re.compile(r'https://www\.coopclub\.cz/wp-content/uploads/[^"\'<> ]+\.pdf')


def stahni(session) -> list[Letak]:
    r = session.get(ZDROJ, timeout=90)
    r.raise_for_status()
    sekce = SEKCE.findall(r.text)
    if not sekce:
        raise RuntimeError("COOP: na stránce nejsou sekce letáků — nejspíš redesign")

    letaky: list[Letak] = []
    for nadpis, telo in sekce:
        nadpis = html.unescape(re.sub(r"\s+", " ", nadpis)).strip()
        nazev_sekce = CELOSTATNI.get(nadpis)
        if nazev_sekce is None and not VCETNE_REGIONALNICH:
            continue
        nazev_sekce = nazev_sekce or nadpis
        for url, titul, d1, m1, y1, d2, m2, y2 in KARTA.findall(telo):
            titul = html.unescape(re.sub(r"\s+", " ", titul)).strip()
            try:
                od = dt.date(int(y1), int(m1), int(d1))
                do = dt.date(int(y2), int(m2), int(d2))
            except ValueError as e:
                print(f"  ! COOP: nesmyslné datum u {titul} ({e}), přeskakuji")
                continue
            time.sleep(1.5)
            d = session.get(url, timeout=90)
            m = PDF.search(d.text) if d.status_code == 200 else None
            if not m:
                print(f"  – COOP: {titul} nemá PDF (HTTP {d.status_code}), přeskakuji")
                continue
            letaky.append(Letak(
                obchod_slug=SLUG,
                obchod_nazev=NAZEV,
                externi_id=url.rstrip("/").split("/")[-1] + "-" + m.group(0).rsplit("/", 1)[-1][:-4],
                titul=f"{NAZEV} {nazev_sekce} {titul}",
                od=od,
                do=do,
                zdroj_url=url,
                pdf_url=m.group(0),
                varianta=odstran_diakritiku(nazev_sekce),
                oznaceni=nazev_sekce,
            ))
    return letaky
