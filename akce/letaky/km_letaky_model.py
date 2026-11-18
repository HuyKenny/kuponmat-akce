"""Společný model letáku + pomocníci pro adaptéry.

Každý řetězec publikuje letáky jinak, takže adaptér je vždy malý modul, který
umí jediné: vrátit seznam `Letak`. Všechno ostatní (stažení PDF, rozřezání na
stránky, upload, založení postu) dělá orchestrátor `km-letaky-sync.py` jednotně
pro všechny. Když se řetězec redesignuje, opravuje se jeden adaptér, ne pipeline.

Adaptér musí vystavit:

    NAZEV   = 'Albert'        # jak se obchod jmenuje
    SLUG    = 'albert'        # slug termu km_letak_obchod
    WEB     = 'https://www.albert.cz/'

    def stahni(session) -> list[Letak]

`session` je sdílená `requests.Session` s opakováním (viz `km_net.py`) — z Maliny
selže zhruba 1 TLS handshake ze 40 a adaptér, který si otevírá vlastní spojení,
by padal uprostřed běhu.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import re
from dataclasses import dataclass, field


@dataclass
class Letak:
    """Jeden leták jednoho řetězce."""

    obchod_slug: str
    obchod_nazev: str
    externi_id: str            # ID u řetězce — primární klíč pro dedup
    titul: str
    od: dt.date
    do: dt.date
    zdroj_url: str             # stránka, ze které to je (kvůli dohledatelnosti)
    pdf_url: str | None = None
    obrazky: list[str] = field(default_factory=list)   # když PDF není
    varianta: str | None = None   # „hypermarket" / „supermarket" — část řetězců vydává víc letáků naráz
    oznaceni: str | None = None   # čitelný název varianty do titulku, když `varianta` je jen slug
    end_derived: bool = False     # konec platnosti není ve zdroji (Lidl SK: jen „platný od“) → dopočten z dalšího letáku; web píše jen „platí od“

    def __post_init__(self):
        if not self.pdf_url and not self.obrazky:
            raise ValueError(f"{self.obchod_slug}/{self.externi_id}: leták nemá PDF ani obrázky")
        if self.do < self.od:
            raise ValueError(f"{self.obchod_slug}/{self.externi_id}: konec platnosti je před začátkem")

    @property
    def hash(self) -> str:
        """Otisk pro dedup.

        Schválně stojí na `externi_id` + datumech, NE na URL: část řetězců mění
        v odkazu podpis nebo `?ts=`, takže URL se liší při každém načtení a dedup
        podle ní by zakládal tentýž leták pořád dokola.
        """
        konec = "open" if self.end_derived else self.do.isoformat()   # dopočtený konec se mění, otisk musí zůstat stejný
        zaklad = f"{self.obchod_slug}|{self.externi_id}|{self.od.isoformat()}|{konec}"
        return hashlib.sha1(zaklad.encode("utf-8")).hexdigest()[:16]

    @property
    def slug(self) -> str:
        """URL slug letáku, ve tvaru `albert-hypermarket-letak-30-9-2026`."""
        casti = [self.obchod_slug]
        if self.varianta:
            casti.append(odstran_diakritiku(self.varianta))
        casti.append("letak")
        casti.append(f"{self.od.day}-{self.od.month}-{self.od.year}")
        return "-".join(c for c in casti if c)

    @property
    def titul_zobrazeny(self) -> str:
        """Titulek pro web.

        `titul` z adaptéru je často interní název řetězce („Albert - 40HM_akcni_letak"),
        který na stránku nepatří. Zobrazený titulek se proto skládá jednotně pro
        všechny řetězce — ať se web nečte jako výpis z cizího CMS.

        `oznaceni` má přednost před `varianta`: Lidl vydává čtyři letáky týdně a jejich
        varianty jsou slugy bez diakritiky („spotrebni-zbozi"), které by v titulku
        vypadaly jako chyba. Adaptér proto dodá čitelný název zvlášť.
        """
        if self.oznaceni:
            return f"{self.obchod_nazev} {self.oznaceni}"
        if self.varianta:
            return f"{self.obchod_nazev} {self.varianta.capitalize()} leták"
        return f"{self.obchod_nazev} leták"

    @property
    def plati(self) -> bool:
        return self.od <= dt.date.today() <= self.do


def odstran_diakritiku(text: str) -> str:
    """Slugifikace pro české texty.

    POZOR: `\\w` v PCRE ani `str.isalnum()` tu nestačí — viz paměť
    `pcre-w-neni-diakritika`. Proto explicitní mapa, ne regex nad `\\w`.
    """
    mapa = str.maketrans(
        "áäčďéěíľĺňóôöřŕšťúůüýžÁÄČĎÉĚÍĽĹŇÓÔÖŘŔŠŤÚŮÜÝŽ",
        "aacdeeillnooorrstuuuyzAACDEEILLNOOORRSTUUUYZ",
    )
    t = text.translate(mapa).lower()
    t = re.sub(r"[^a-z0-9]+", "-", t)
    return t.strip("-")


def datum_cz(text: str) -> dt.date:
    """Rozparsuje české datum. Zvládá `30.09.2026`, `30. 9. 2026` i `2026-09-30`.

    Vrací `date`, nebo vyhodí `ValueError` — adaptér nesmí tiše podstrčit dnešek,
    protože datum platnosti rozhoduje o tom, co se návštěvníkovi ukáže.
    """
    text = text.strip()
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", text)
    if m:
        r, me, d = (int(x) for x in m.groups())
        return dt.date(r, me, d)
    m = re.match(r"^(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})$", text)
    if m:
        d, me, r = (int(x) for x in m.groups())
        return dt.date(r, me, d)
    raise ValueError(f"nerozpoznané datum: {text!r}")
