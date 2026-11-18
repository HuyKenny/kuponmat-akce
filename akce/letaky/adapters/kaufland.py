"""Adaptér: Kaufland (kaufland.cz).

PROČ TAKHLE: `kaufland.cz` vrací na obyčejný request **403** (proto starší zápis
v runbooku tvrdil, že nás blokuje — platí to jen pro curl, prohlížeč projde).
Stránka s letákem je na `prodejny.kaufland.cz/letak.html` a odkazuje na PDF:

    https://assets.leaflets.schwarz/leaflets/pdfs/{uuid}/Kaufland-30-09-2026-06-10-2026-00.pdf

**Datum platnosti je přímo v názvu souboru** (od-do), takže se nic neodvozuje.
Samotné PDF už jde stáhnout obyčejným requestem — prohlížeč je potřeba jen na
tu jednu stránku.

Pozor na sourozence: Lidl je ze stejné skupiny (Schwarz) a používá týž
`imgproxy.leaflets.schwarz`, ale PDF **nevydává** — proto má Lidl vlastní,
mnohem dražší adaptér s listováním v prohlížeči.

Ověřeno 30. 9. 2026: leták 30. 9. – 6. 10., PDF 17,4 MB, 54 stran.
"""
from __future__ import annotations

import datetime as dt
import re
import subprocess
from pathlib import Path

from km_letaky_model import Letak

NAZEV = "Kaufland"
SLUG = "kaufland"
WEB = "https://www.kaufland.cz/"
ZDROJ = "https://prodejny.kaufland.cz/letak.html"

PROHLIZEC = Path(__file__).resolve().parent.parent / "km-letaky-html.js"
# Kaufland-30-09-2026-06-10-2026-00.pdf
NAZEV_PDF = re.compile(
    r"/(?P<jmeno>[A-Za-z]+)-(?P<d1>\d{2})-(?P<m1>\d{2})-(?P<r1>\d{4})"
    r"-(?P<d2>\d{2})-(?P<m2>\d{2})-(?P<r2>\d{4})-(?P<poradi>\d+)\.pdf$")


def stahni(session) -> list[Letak]:
    v = subprocess.run(["node", str(PROHLIZEC), ZDROJ, "5000"],
                       capture_output=True, text=True, timeout=300)
    if v.returncode != 0 or not v.stdout:
        raise RuntimeError(f"Kaufland: prohlížeč nevrátil stránku ({v.stderr[:150]})")

    odkazy = sorted(set(re.findall(
        r"https://assets\.leaflets\.schwarz/leaflets/pdfs/[^\"'\s\\]+\.pdf", v.stdout)))
    if not odkazy:
        raise RuntimeError("Kaufland: na stránce není odkaz na PDF letáku — nejspíš redesign")

    letaky: list[Letak] = []
    videne: set[str] = set()
    for url in odkazy:
        m = NAZEV_PDF.search(url)
        if not m:
            print(f"  ! Kaufland: z názvu {url.split('/')[-1][:50]} nejde vyčíst platnost, přeskakuji")
            continue
        g = m.groupdict()
        try:
            od = dt.date(int(g["r1"]), int(g["m1"]), int(g["d1"]))
            do = dt.date(int(g["r2"]), int(g["m2"]), int(g["d2"]))
        except ValueError as e:
            print(f"  ! Kaufland: nesmyslné datum v názvu ({e}), přeskakuji")
            continue

        # Týž leták bývá na stránce pod víc UUID; klíč je platnost + pořadí,
        # ne URL, jinak by se tentýž leták založil dvakrát.
        klic = f"{od}|{do}|{g['poradi']}"
        if klic in videne:
            continue
        videne.add(klic)

        poradi = int(g["poradi"])
        letaky.append(Letak(
            obchod_slug=SLUG,
            obchod_nazev=NAZEV,
            externi_id=f"{od.isoformat()}-{g['poradi']}",
            titul=f"{NAZEV} leták",
            od=od,
            do=do,
            zdroj_url=ZDROJ,
            pdf_url=url,
            # Kaufland vydává i víc letáků naráz (00, 01, …) — bez rozlišení by
            # měly stejný slug. Ten první je hlavní týdenní, dál se čísluje.
            varianta=None if poradi == 0 else f"c{poradi}",
            oznaceni=None if poradi == 0 else f"leták {poradi + 1}",
        ))
    return letaky
