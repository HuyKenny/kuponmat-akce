"""Adaptér: Makro (makro.cz).

PROČ TAKHLE: `makro.cz/aktualni-nabidka` skládá seznam letáků z JSON API
`components.me-catalogues.metronom.com/api/catalog-filter` (feed `makro-letaky-a-katalogy`,
bez prohlížeče jde obyčejným requestem). Položka nese `validFrom`/`validTo` (**platnost
přímo od Makra, nic se neodvozuje**), `name`, `slug` a `FOLDER` (leták/katalog). Detail
`letaky.makro.cz/{slug}/` je Publitas a v HTML má přímý odkaz na PDF.

Bere se jen to, co Makro samo označí jako `FOLDER=leták` a má obě data a platí dnes.
Katalogy a „stálé" nabídky bez konce platnosti (`validTo` null) se přeskakují.
Letáky jsou celostátní (v `STORE` je všech 13 prodejen); regionální letáky
(„Hradec Králové - 8. 10. 2026") z API nejdou a jsou jen na letaky.makro.cz.
Makro vydává víc letáků naráz (Gastronomie, Maloobchod, Bar…) → každý má `varianta`.

robots.txt: makro.cz — `Disallow: /*abv2$`, `/not-found-page`; letaky.makro.cz a API
robots nemají (404). POZOR: `www.makro.cz` vrací curlu 403 (jen prohlížeč), proto se
nesahá na www, jen na API a letaky.makro.cz, které curlem jdou.
Ověřeno 12. 10. 2026: 9 platných letáků (7. 10. – 13. 10. až 3. 11. 2026).
"""
from __future__ import annotations

import datetime as dt
import html
import re

from km_letaky_model import Letak, odstran_diakritiku

NAZEV = "Makro"
SLUG = "makro"
WEB = "https://www.makro.cz/"
ZDROJ = "https://www.makro.cz/aktualni-nabidka"
API = ("https://components.me-catalogues.metronom.com/api/catalog-filter"
       "?resolution=600&feeds=makro-letaky-a-katalogy&metatags%5B%5D=channel=website")

_PDF = re.compile(r'https://view\.publitas\.com/\d+/\d+/pdfs/[0-9a-f-]+\.pdf[^"\'<>\s]*')


VYNECHAT = ("bar", "profesionální úklid", "profesionalni uklid")


def stahni(session) -> list[Letak]:
    r = session.get(API, timeout=90)
    r.raise_for_status()
    polozky = r.json().get("items")
    if not polozky:
        raise RuntimeError("Makro: API catalog-filter nevrátilo žádné položky — oprav adaptér")

    dnes = dt.date.today()
    letaky: list[Letak] = []
    for p in polozky:
        meta = {m.get("category"): m.get("values") or [] for m in p.get("metatags") or []}
        if "leták" not in meta.get("FOLDER", []):
            continue
        if not (p.get("validFrom") and p.get("validTo")):
            continue
        # Úzce B2B letáky (rozhodnutí Kennyho 12. 10. 2026) — čtenáře webu nezajímají.
        if any(x in (p.get("name") or "").lower() for x in VYNECHAT):
            continue
        try:
            od = dt.date.fromisoformat(p["validFrom"][:10])
            do = dt.date.fromisoformat(p["validTo"][:10])
        except ValueError:
            continue
        if not od <= dnes <= do:
            continue
        slug = p["slug"]
        zdroj = f"https://letaky.makro.cz/{slug}/"
        det = session.get(zdroj, timeout=90)
        m = _PDF.search(det.text) if det.status_code == 200 else None
        if not m:
            print(f"  ! Makro: {zdroj} nemá odkaz na PDF (HTTP {det.status_code}), přeskakuji")
            continue
        nazev = html.unescape(p.get("name") or slug).strip()
        letaky.append(Letak(
            obchod_slug=SLUG,
            obchod_nazev=NAZEV,
            externi_id=slug,
            titul=nazev,
            od=od,
            do=do,
            zdroj_url=zdroj,
            pdf_url=html.unescape(m.group(0)),
            varianta=odstran_diakritiku(nazev),
            oznaceni=f"leták {nazev}",
        ))
    return letaky
