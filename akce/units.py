"""Package sizes, unit prices and conditions from the small detail lines of a leaflet tile."""
from __future__ import annotations

import re

N = r"(\d+(?:[,.]\d+)?)"
UNIT = r"(kg|g|ml|l|ks|rolí|role|dávek|dávka|tablet|kusů|kusy|kus|bm|m)"

# "100 g = 11,16 Kč", "1 l = 31,80 Kč", "(=100 ml 4,98)", "(100 g 29,95)", "1 kg = 369,– Kč", "100 g od 21,13 Kč"
UNIT_PRICE = re.compile(r"\(?=?\s*" + N + r"\s*(kg|g|ml|l|ks)\s*(?:=|od)?\s*(\d+(?:[,.]\d{1,2})?)\s*(?:[,.][-–])?\s*(?:Kč|KC|\))?", re.I)
PACK = re.compile(r"(?<![\d=,])(\d+(?:[,.]\d+)?(?:\s*[-–]\s*\d+(?:[,.]\d+)?)?(?:\s*x\s*\d+(?:[,.]\d+)?)?)\s*(kg|g|ml|l|ks|rolí|role|dávek|tablet|kusů|kusy|kus)\b", re.I)

FACT = {"g": ("kg", 1000), "kg": ("kg", 1), "ml": ("l", 1000), "l": ("l", 1), "ks": ("ks", 1)}


def num(s: str) -> float:
    return float(s.replace(",", ".").replace(" ", ""))


def unit_price(text: str):
    """Price per kg / l / ks printed in the leaflet (the first one = the promo one)."""
    for m in UNIT_PRICE.finditer(text):
        q, u, p = m.group(1), m.group(2).lower(), m.group(3)
        try:
            q, p = num(q), num(p)
        except ValueError:
            continue
        if q <= 0 or p <= 0:
            continue
        jedn, f = FACT[u]
        jc = round(p / q * f, 2)
        if 0.05 < jc < 100000:
            return jc, jedn
    return None, None


MULTIPACK = re.compile(r"(\d{1,3})\s*[×x]\s*(\d+(?:[,.]\d+)?)\s*(kg|g|ml|l)\b", re.I)


def package(text: str):
    t = UNIT_PRICE.sub(" ", text)
    mm = MULTIPACK.search(t)
    if mm:
        return f"{mm.group(1)}× {mm.group(2)} {mm.group(3)}"
    m = PACK.search(t)
    if not m:
        return None
    return re.sub(r"\s+", " ", f"{m.group(1)} {m.group(2)}").replace(" - ", "-").replace(" – ", "-")


COND = [
    (re.compile(r"aplikac|lidl plus|penny kart|s kartou|kartou|členy klubu|clubcard|klubov|s kupónem|kupón", re.I), "s aplikací/kartou"),
]
MULTI = re.compile(r"(při (?:koupi|nákupu) (?:\d+|dvou|tří|2 a více|3 a více)[^•|;]*|\d\s*\+\s*\d(?: zdarma)?|kupte \d[^•|;]*zaplaťte \d|od \d ks)", re.I)


def parse_details(text: str) -> dict:
    jc, jedn = unit_price(text)
    out = {"baleni": package(text), "jc": jc, "jedn": jedn, "podminka": None}
    conds = []
    m = MULTI.search(text)
    if m:
        conds.append(m.group(1).strip(" ,.;").lower())
    v = re.search(r"platí (?:do|od) [\d. ]+\d{4}", text)
    if v:
        conds.append(v.group(0))
    if conds:
        out["podminka"] = "; ".join(dict.fromkeys(conds))
    return out


def qty_range(baleni):
    """'250 g' -> (0.25, 0.25, 'kg'); '70-80 g' -> (0.07, 0.08, 'kg'); '0,5 l' -> (0.5, 0.5, 'l'); '8 rolí' -> None."""
    if not baleni:
        return None
    k = 1
    mm = re.match(r"(\d{1,3})\s*[×x]\s*(.*)$", baleni.strip())
    if mm:
        k, baleni = int(mm.group(1)), mm.group(2)
    m = re.match(r"(\d+(?:[,.]\d+)?)(?:\s*-\s*(\d+(?:[,.]\d+)?))?\s*(kg|g|ml|l|ks)$", baleni.strip(), re.I)
    if not m:
        return None
    a = num(m.group(1)); b = num(m.group(2)) if m.group(2) else a
    jedn, f = FACT[m.group(3).lower()]
    return a * k / f, b * k / f, jedn


def consistent(price, jc, jedn, baleni, tol=0.04):
    """True/False when the printed unit price can confirm the price, None when it cannot tell."""
    q = qty_range(baleni)
    if not (q and jc and jedn == q[2]):
        return None
    lo, hi = q[0] * jc * (1 - tol), q[1] * jc * (1 + tol)
    return lo - 0.1 <= price <= hi + 0.1
