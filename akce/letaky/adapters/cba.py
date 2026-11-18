"""Adaptér: CBA (cba.cz).

PROČ TAKHLE: `/letaky/` má tři sekce (CBA PREMIUM / POTRAVINY / MARKET), v každé řádek „Platnost: 18. 11. - 24. 11. 2026"
a 3D flipbook. Jeho data jsou v HTML jako base64 JSON (`"posts":{...,"title":"CBA PREMIUM","data":{"guid":".../uploads/.../X.pdf"}}`),
odtud je odkaz na PDF. Datum je tedy přímo na webu, nic se neodvozuje. Jde obyčejným requestem, bez prohlížeče.
Varianta MARKET je v PDF jen obrázek (bez textové vrstvy) → vynechána (obrázkový leták by se musel číst jinak).
POZOR: stránka cba.cz/letaky obsahovala 18. 11. 2026 podstrčené spamové odkazy (web je zřejmě napadený). Berou se
VÝHRADNĚ odkazy na PDF z `cba.cz/wp-content/uploads/`, žádný jiný odkaz se nesleduje ani nestahuje.
Ověřeno 18. 11. 2026: PREMIUM 46A 18.–24. 11. (4 strany), POTRAVINY 23A 11.–22. 11. (4 strany).
"""
from __future__ import annotations

import base64
import datetime as dt
import json
import re

from km_letaky_model import Letak

NAZEV = "CBA"
SLUG = "cba"
WEB = "https://cba.cz/"
STRANKA = "https://cba.cz/letaky/"

VARIANTY = {"PREMIUM": "premium", "POTRAVINY": "potraviny"}      # MARKET je obrázkový → záměrně chybí
_PDF = re.compile(r"^https://(?:www\.)?cba\.cz/wp-content/uploads/[\w/.\-]+\.pdf$")
_BLOB = re.compile(r"[A-Za-z0-9+/=]{200,}")
_SEKCE = re.compile(r"CBA\s+(PREMIUM|POTRAVINY|MARKET)\s*Platnost:\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(?:(\d{4})\s*)?[-–]\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})")


def _pdfka(html: str) -> dict[str, str]:
    """{'PREMIUM': url, ...} z base64 JSON flipbooku; jiné než cba.cz/uploads odkazy se zahazují."""
    out = {}
    for blob in _BLOB.findall(html):
        try:
            j = json.loads(base64.b64decode(blob + "=" * (-len(blob) % 4)).decode("utf-8"))
            posts = j["posts"].values()
        except Exception:
            continue
        for p in posts:
            try:
                m = re.fullmatch(r"CBA\s+(\w+)", p["title"].strip())
                url = p["data"]["guid"].replace("\\/", "/")
            except Exception:
                continue
            if m and _PDF.match(url):
                out[m.group(1).upper()] = url
    return out


def stahni(session) -> list[Letak]:
    r = session.get(STRANKA, timeout=90, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    pdfka = _pdfka(r.text)
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", r.text, flags=re.S)
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text).replace("&nbsp;", " "))
    letaky: list[Letak] = []
    for var, d1, m1, y1, d2, m2, y2 in _SEKCE.findall(text):
        if var not in VARIANTY or var not in pdfka:
            continue
        y2 = int(y2)
        od, do = dt.date(int(y1) if y1 else y2, int(m1), int(d1)), dt.date(y2, int(m2), int(d2))
        pdf = pdfka[var]
        letaky.append(Letak(
            obchod_slug=SLUG,
            obchod_nazev=NAZEV,
            externi_id=pdf.rsplit("/", 1)[-1].removesuffix(".pdf"),
            titul=f"{NAZEV} {var.capitalize()}",
            od=od,
            do=do,
            zdroj_url=STRANKA,
            pdf_url=pdf,
            varianta=VARIANTY[var],
            oznaceni=f"{var.capitalize()} leták",
        ))
    return letaky
