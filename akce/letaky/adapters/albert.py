"""Adaptér: Albert (albert.cz).

PROČ TAKHLE: Albert je Next.js a celý seznam letáků má v `__NEXT_DATA__` jako
strukturovaný JSON — včetně `validityStartDateFormatted`, `validityEndDateFormatted`,
`downloadUrl` (přímé PDF přes Publitas) a `locationType`. Parsuje se tedy JSON,
ne HTML: značkování se při redesignu mění, klíče v datové vrstvě mnohem míň.

Albert vydává **dva letáky naráz** (HYPERMARKET a SUPERMARKET) se stejnou platností
a jiným obsahem — proto `varianta`, jinak by si přepsaly slug.

Ověřeno 30. 9. 2026: stránka 1,07 MB, v `__NEXT_DATA__` dva záznamy
`documentType: LEAFLET`, platnost 30.09.–06.10.2026, obě PDF stažitelná.
"""
from __future__ import annotations

import json
import re

from km_letaky_model import Letak, datum_cz

NAZEV = "Albert"
SLUG = "albert"
WEB = "https://www.albert.cz/"
ZDROJ = "https://www.albert.cz/aktualni-letaky"

# Interní typ prodejny → jak se varianta pojmenuje v URL a titulku.
# Co tu není, se použije tak, jak přišlo (malými písmeny) — radši neznámá
# varianta v URL než spadlý běh nebo dva letáky se stejným slugem.
VARIANTY = {
    "HYPERMARKET": "hypermarket",
    "SUPERMARKET": "supermarket",
}


def _najdi_letaky(uzel, nalezene: list):
    """Projde JSON a posbírá všechny uzly, které vypadají jako leták.

    Rekurze schválně: Albert má ten seznam zanořený hluboko v Apollo cache a
    cesta se mezi buildy mění. Hledat podle tvaru dat je odolnější než podle cesty.
    """
    if isinstance(uzel, dict):
        if uzel.get("documentType") == "LEAFLET" and uzel.get("downloadUrl"):
            nalezene.append(uzel)
        for v in uzel.values():
            _najdi_letaky(v, nalezene)
    elif isinstance(uzel, list):
        for v in uzel:
            _najdi_letaky(v, nalezene)


def stahni(session) -> list[Letak]:
    r = session.get(ZDROJ, timeout=90)
    r.raise_for_status()
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
    if not m:
        raise RuntimeError("Albert: v stránce není __NEXT_DATA__ — nejspíš redesign, oprav adaptér")
    data = json.loads(m.group(1))

    syrove: list[dict] = []
    _najdi_letaky(data, syrove)
    if not syrove:
        raise RuntimeError("Albert: __NEXT_DATA__ neobsahuje žádný LEAFLET s downloadUrl")

    letaky: list[Letak] = []
    videne: set[str] = set()
    for s in syrove:
        ext = str(s.get("id") or "").strip()
        if not ext or ext in videne:
            continue
        videne.add(ext)
        try:
            od = datum_cz(s["validityStartDateFormatted"])
            do = datum_cz(s["validityEndDateFormatted"])
        except (KeyError, ValueError) as e:
            # Jeden rozbitý leták nesmí shodit ostatní — přeskoč a nech stopu.
            print(f"  ! Albert {ext}: přeskakuji, {e}")
            continue
        typ = str(s.get("locationType") or "").upper()
        letaky.append(Letak(
            obchod_slug=SLUG,
            obchod_nazev=NAZEV,
            externi_id=ext,
            titul=(s.get("title") or f"{NAZEV} leták").strip(),
            od=od,
            do=do,
            zdroj_url=s.get("viewUrl") or ZDROJ,
            pdf_url=s["downloadUrl"],
            varianta=VARIANTY.get(typ, typ.lower() or None),
        ))
    return letaky
