"""Adaptér: Globus (globus.cz).

PROČ TAKHLE: `globus.cz/globus/letaky` je SSR Nuxt (jde obyčejným requestem, bez
prohlížeče) a v `<script id="__NUXT_DATA__">` má celý seznam letáků jako strukturovaný
JSON (devalue = ploché pole, hodnoty jsou odkazy na indexy). Každý leták má:

    actionOfferId, actionOfferName ("42_26_L1"), offerType ("MainFlyer"/"Catalogue"),
    isComplete, validFrom, validTo (SKUTEČNÉ datum od–do, nic se neodvozuje),
    pdfAsset (https://gapi.globus.cz/OnlineAsset/3/asset?assetID=… — přímé PDF), slug

⚠️ PRÁVNÍ: globus.cz/robots.txt zakazuje `/*/letaky/akcni-letak-*` (detaily). Kenny
(majitel kuponmat.cz) potvrdil 12. 10. 2026, že má od Globusu souhlas obsah
používat. Adaptér detail nikdy nenačítá — vše je na seznamu a PDF je na gapi.globus.cz.

Letáky jsou po prodejnách (stránka /{prodejna}/letaky vypisuje stejné centrální
letáky + lokální varianty s příponou slugu). Bere se jen CELOSTÁTNÍ hlavní leták:
`offerType == MainFlyer` a `isComplete` (kompletní, všechny strany). Lokální varianty
(`40_26_L1` s `actionOfferId` zakončeným `-2/-3/-4`, isComplete=false, 2–6 stran)
a katalogy (`Catalogue`: elektro, textil, nápoje…) se vynechávají — jsou to cílené
nebo tematické výřezy, ne týdenní leták. Chceš-li katalogy, stačí povolit
`offerType == "Catalogue"` s `varianta` z `actionOfferName`.

Ověřeno 12. 10. 2026: 41_26_L1 (7.–13. 10., 47 stran) a 42_26_L1 (14.–20. 10., 56 stran).
"""
from __future__ import annotations

import datetime as dt
import json
import re

from km_letaky_model import Letak

NAZEV = "Globus"
SLUG = "globus"
WEB = "https://www.globus.cz/"
ZDROJ = "https://www.globus.cz/globus/letaky"

_NUXT = re.compile(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', re.S)


def _rozbal(data: list, i, hloubka: int = 0):
    """Rozbalí devalue odkaz (index do plochého pole) na běžnou hodnotu."""
    if not isinstance(i, int) or hloubka > 4:
        return i
    v = data[i]
    if isinstance(v, dict):
        return {k: _rozbal(data, x, hloubka + 1) for k, x in v.items()}
    if isinstance(v, list):
        if v and v[0] in ("Reactive", "ShallowReactive", "Ref") and len(v) == 2:
            return _rozbal(data, v[1], hloubka + 1)
        return [_rozbal(data, x, hloubka + 1) for x in v]
    return v


def _datum(s: str) -> dt.date:
    return dt.date.fromisoformat(s[:10])  # '2026-10-14T00:00:00.000+02:00'


def stahni(session) -> list[Letak]:
    r = session.get(ZDROJ, timeout=90)
    r.raise_for_status()
    m = _NUXT.search(r.text)
    if not m:
        raise RuntimeError("Globus: na stránce není __NUXT_DATA__ — oprav adaptér")
    data = json.loads(m.group(1))

    nabidky = []
    for v in data:
        if isinstance(v, dict) and "actionOfferId" in v and "validFrom" in v:
            n = {k: _rozbal(data, x) for k, x in v.items() if k != "jpgAssetsProcessed"}
            nabidky.append(n)
    if not nabidky:
        raise RuntimeError("Globus: v datech nejsou žádné letáky (actionOfferId) — oprav adaptér")

    letaky: list[Letak] = []
    videno = set()
    for n in sorted(nabidky, key=lambda x: x["validFrom"]):
        if n.get("offerType") != "MainFlyer" or not n.get("isComplete"):
            continue
        if not n.get("pdfAsset"):
            print(f"  ! Globus {n['actionOfferName']}: bez PDF, přeskakuji")
            continue
        if n["actionOfferId"] in videno:
            continue
        videno.add(n["actionOfferId"])
        od, do = _datum(n["validFrom"]), _datum(n["validTo"])
        letaky.append(Letak(
            obchod_slug=SLUG,
            obchod_nazev=NAZEV,
            externi_id=n["actionOfferId"],
            titul=f"{NAZEV} leták {n['actionOfferName']}",
            od=od,
            do=do,
            zdroj_url=f"https://www.globus.cz/globus/letaky/{n['slug']}",
            pdf_url=n["pdfAsset"],
        ))
    return letaky
