"""Leaflet PDF -> offers, without any AI.

Retail leaflets made in InDesign keep a real text layer: every product tile has a title in one
font, small detail lines (package, unit price, conditions) in another and the price set in a
display font, usually split into a big integer part and a small superscript decimal part
("26" + "90"). This module reads spans with position, size and font (PyMuPDF) and rebuilds the tiles:

  1. classify spans by font/size rules of the chain (``LAYOUTS`` in ``layouts.py``)
  2. merge title lines into title blocks and attach the detail lines under them
  3. build price clusters from price-font spans and read main / old price and discount
  4. match every price cluster to the closest title block (directional cost per chain)

Anything that does not parse cleanly is dropped: fewer offers is better than wrong ones.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

import pymupdf

from .units import consistent, parse_details


@dataclass
class Span:
    x0: float
    y0: float
    x1: float
    y1: float
    size: float
    font: str
    color: int
    text: str

    @property
    def cx(self):
        return (self.x0 + self.x1) / 2

    @property
    def cy(self):
        return (self.y0 + self.y1) / 2


@dataclass
class Block:
    spans: list = field(default_factory=list)
    details: list = field(default_factory=list)

    @property
    def x0(self):
        return min(s.x0 for s in self.spans)

    @property
    def y0(self):
        return min(s.y0 for s in self.spans)

    @property
    def x1(self):
        return max(s.x1 for s in self.spans)

    @property
    def y1(self):
        return max(s.y1 for s in (self.spans + self.details))

    @property
    def detail_text(self):
        return clean(" ".join(d.text for d in sorted(self.details, key=lambda d: (round(d.y0), d.x0))))

    @property
    def title(self):
        return clean(" ".join(s.text for s in sorted(self.spans, key=lambda s: (round(s.y0), s.x0))))


@dataclass
class Price:
    value: float
    size: float
    x0: float
    y0: float
    x1: float
    y1: float
    old: float | None = None
    discount: int | None = None
    color: int = 0
    others: list = field(default_factory=list)

    @property
    def cx(self):
        return (self.x0 + self.x1) / 2

    @property
    def cy(self):
        return (self.y0 + self.y1) / 2


def clean(t: str) -> str:
    t = t.replace("\xa0", " ").replace("­", "").replace("–", "-").replace("—", "-")
    t = re.sub(r"\s+", " ", t).strip(" •·|,")
    t = re.sub(r"\s+([,.)])", r"\1", t)
    return t


def spans_of(page) -> list[Span]:
    out, seen = [], set()
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                t = s["text"].strip()
                if not t:
                    continue
                k = (round(s["bbox"][0]), round(s["bbox"][1]), t)
                if k in seen:          # some leaflets (Norma) print every text twice (two layers)
                    continue
                seen.add(k)
                x0, y0, x1, y1 = s["bbox"]
                out.append(Span(x0, y0, x1, y1, s["size"], s["font"], s["color"], t))
    return out


NUM = re.compile(r"^\d{1,5}$")
DEC = re.compile(r"^[,.]?(\d{2}|-|–)$")
FULL = re.compile(r"^(\d{1,5})(?:[,.](\d{2}|-|–))?,?-?$")


def _val(i: str, d: str | None) -> float:
    if d is None or d in ("-", "–"):
        return float(i)
    return float(f"{i}.{d}")


def _discounts(spans, used):
    """'-20 %' in any form: one span '-20%', or '-' + '20' + '%' spans on one line."""
    out = []
    for s in spans:
        t = s.text.replace(" ", "").replace("\xa0", "").replace("−", "-")
        m = re.fullmatch(r"-?(\d{1,2})%", t) or re.fullmatch(r"-(\d{1,2})", t)
        pct = [x for x in spans if x is not s and x.text.strip() in ("%",) and abs(x.cy - s.cy) < s.size * 0.7 and -1 <= x.x0 - s.x1 < s.size * 0.6]
        if not m and re.fullmatch(r"\d{1,2}", t) and pct:
            m = re.fullmatch(r"(\d{1,2})", t)
        if not m:
            continue
        d = int(m.group(1))
        if not 3 <= d <= 90:
            continue
        used.add(id(s))
        for x in pct:
            used.add(id(x))
        for x in spans:   # the lone '-' before the number
            if x.text.strip() in ("-", "−", "–") and abs(x.cy - s.cy) < s.size * 0.7 and -1 <= s.x0 - x.x1 < s.size * 0.6:
                used.add(id(x))
        out.append((d, s.cx, s.cy, s.size))
    return out


def build_prices(spans: list[Span], L) -> list[Price]:
    """Main prices with their secondary prices (regular / without card) and discount attached."""
    used = set()
    discounts = _discounts(spans, used)
    ps = [s for s in spans if L.is_price(s) and id(s) not in used]
    allp = []
    for s in sorted(ps, key=lambda s: -s.size):
        if id(s) in used:
            continue
        t = s.text.replace(" ", "").replace("\xa0", "").rstrip("/")
        val = None
        box = [s.x0, s.y0, s.x1, s.y1]
        m = FULL.match(t)
        if m and m.group(2) is not None:
            val = _val(m.group(1), m.group(2))
        elif NUM.match(t.rstrip(",.")) and s.size >= L.min_price_size:
            # decimal part to the right: smaller span, top-aligned (superscript) or same baseline
            cand = [o for o in ps if id(o) not in used and o is not s and o.size < s.size * 0.95
                    and -1 <= o.x0 - s.x1 < s.size * 0.6 and abs(o.y0 - s.y0) < s.size * 0.6
                    and DEC.match(o.text.replace(" ", ""))]
            if cand:
                o = min(cand, key=lambda o: o.x0 - s.x1)
                used.add(id(o))
                val = _val(t.rstrip(",."), o.text.replace(" ", "").lstrip(",."))
                box = [s.x0, min(s.y0, o.y0), o.x1, max(s.y1, o.y1)]
            elif t.endswith(",") or L.int_prices:
                val = float(t.rstrip(",."))
        if val is None or not (L.min_price <= val <= L.max_price):
            continue
        used.add(id(s))
        allp.append(Price(val, s.size, *box, color=s.color))
    mains = [p for p in allp if p.size >= L.main_size]
    for p in mains:
        p.others = []
    for q in allp:
        if q.size >= L.main_size or not mains:
            continue
        m = min(mains, key=lambda p: math.hypot(p.cx - q.cx, p.cy - q.cy))
        if math.hypot(m.cx - q.cx, m.cy - q.cy) < m.size * L.secondary_reach:
            m.others.append(q)
    for d, x, y, sz in discounts:
        if not mains:
            break
        m = min(mains, key=lambda p: math.hypot(p.cx - x, p.cy - y))
        if math.hypot(m.cx - x, m.cy - y) < m.size * 3 and m.discount is None:
            m.discount = d
    return mains


def build_blocks(spans: list[Span], L) -> list[Block]:
    titles = sorted([s for s in spans if L.is_title(s)], key=lambda s: (s.y0, s.x0))
    blocks: list[Block] = []
    for s in titles:
        for b in blocks:
            last = b.spans[-1]
            same_col = abs(s.x0 - b.x0) < max(3, s.size * 0.6) or (abs(s.y0 - last.y0) < 1 and 0 <= s.x0 - last.x1 < s.size)
            if same_col and 0 <= s.y0 - last.y0 < s.size * L.title_line_gap and abs(s.size - last.size) < 1.5:
                b.spans.append(s)
                break
        else:
            blocks.append(Block([s]))
    details = [s for s in spans if L.is_detail(s)]
    for d in details:
        best, bd = None, 1e9
        for b in blocks:
            last_y = max(x.y1 for x in b.spans + b.details)
            dy = d.y0 - last_y
            dx = d.x0 - b.x0
            if -2 <= dy < L.detail_gap and -4 <= dx < (b.x1 - b.x0) + 30:
                score = dy + abs(dx) * 0.2
                if score < bd:
                    best, bd = b, score
        if best is not None:
            best.details.append(d)
    return [b for b in blocks if len(b.title) >= 3 and not L.skip_title(b.title)]


def rect_dist(b: Block, p: Price, L) -> float:
    dx = max(b.x0 - p.x1, 0, p.x0 - b.x1)
    dy = max(b.y0 - p.y1, 0, p.y0 - b.y1)
    cost = math.hypot(dx, dy)
    # directional preference of the chain: where the price sits relative to the title block
    pen = getattr(L, "side_penalty", 60.0)
    if L.price_side == "above" and p.cy > b.y1 + 5:
        cost += pen
    if L.price_side == "below" and p.cy < b.y0 - 5:
        cost += pen
    if L.price_side == "right" and p.cx < b.x0:
        cost += pen
    return cost


def _hungarian(cost):
    """Min-cost assignment for a rectangular matrix (rows <= cols handled by padding)."""
    n = max(len(cost), len(cost[0]) if cost else 0)
    INF = 1e9
    C = [[(cost[i][j] if i < len(cost) and j < len(cost[0]) else INF / 10) for j in range(n)] for i in range(n)]
    u, v, p, way = [0] * (n + 1), [0] * (n + 1), [0] * (n + 1), [0] * (n + 1)
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [INF] * (n + 1)
        used = [False] * (n + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], INF, 0
            for j in range(1, n + 1):
                if not used[j]:
                    cur = C[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j], way[j] = cur, j0
                    if minv[j] < delta:
                        delta, j1 = minv[j], j
            for j in range(n + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    res = {}
    for j in range(1, n + 1):
        if p[j] and p[j] - 1 < len(cost) and j - 1 < len(cost[0]):
            res[p[j] - 1] = j - 1
    return res


def match(blocks: list[Block], prices: list[Price], L) -> list[tuple[Block, Price]]:
    """1:1 title block <-> main price, minimal total distance; pairs over max_dist are dropped."""
    if not blocks or not prices:
        return []
    cost = []
    for b in blocks:
        info = parse_details(b.detail_text)
        row = []
        for p in prices:
            c = rect_dist(b, p, L)
            vals = [p.value] + [q.value for q in p.others]
            ok = [consistent(v, info["jc"], info["jedn"], info["baleni"]) for v in vals]
            if any(o is True for o in ok):
                c = max(0.0, c - 40)          # printed unit price confirms this pair
            elif ok[0] is False:
                c += 80
            row.append(c)
        cost.append(row)
    capped = [[min(c, L.max_dist * 3) for c in row] for row in cost]
    out = []
    for i, j in _hungarian(capped).items():
        if cost[i][j] <= L.max_dist:
            out.append((blocks[i], prices[j]))
    return out


def parse_pdf(path: str, L, pages: list[int] | None = None, with_bbox: bool = False) -> list[dict]:
    doc = pymupdf.open(path)
    out = []
    for pi in range(len(doc)):
        if pages and pi + 1 not in pages:
            continue
        spans = spans_of(doc[pi])
        if not spans:
            continue
        blocks = build_blocks(spans, L)
        prices = build_prices(spans, L)
        for b, main in match(blocks, prices, L):
            ps = [main] + sorted(main.others, key=lambda p: (-p.size, p.value))
            det_text = clean(" ".join(d.text for d in sorted(b.details, key=lambda d: (round(d.y0), d.x0))))
            info = parse_details(det_text)
            cena, cena_bez, podminka, old = main.value, None, info.get("podminka"), main.old
            member = bool(re.search(L.member_rx, det_text, re.I))
            for q in ps[1:]:
                if q.size >= main.size * 0.8:
                    continue                                  # two big prices = two products, keep the first
                if q.value <= cena:
                    if member and q.value < cena:
                        cena_bez, cena = cena, q.value
                    continue
                if L.old_above and q.cy < main.y0 + 2 and old is None:
                    old = q.value                             # "běžná cena" label above the price
                elif member and cena_bez is None and q.value <= cena * 1.6:
                    cena_bez = q.value                        # "bez aplikace / karty" price
                elif old is None:
                    old = q.value
            if cena_bez:
                podminka = podminka or L.member_label
                if L.member_label not in (podminka or ""):
                    podminka = L.member_label + "; " + podminka
            if old and old <= cena:
                old = None
            chk = [consistent(v, info.get("jc"), info.get("jedn"), info.get("baleni")) for v in (cena, cena_bez, old) if v]
            disc = main.discount
            if not disc and old:
                disc = round((1 - cena / old) * 100)
            out.append({
                "nazev": L.fix_title(b.title),
                "detail": det_text,
                "baleni": info.get("baleni"),
                "cena": cena,
                "cena_bez": cena_bez,
                "puvodni_cena": old,
                "sleva_pct": disc if disc and 1 <= disc <= 90 else None,
                "jednotkova_cena": info.get("jc"),
                "jednotka": info.get("jedn"),
                "podminka": podminka,
                "strana": pi + 1,
                "overeno": any(c is True for c in chk),
                **({"bbox": [min(b.x0, *[p.x0 for p in ps]), min(b.y0, *[p.y0 for p in ps]),
                             max(b.x1, *[p.x1 for p in ps]), max(b.y1, *[p.y1 for p in ps])]} if with_bbox else {}),
            })
    return out
