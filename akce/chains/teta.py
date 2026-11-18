"""Teta drogerie: title = Tahoma-Bold brand + Tahoma name 10-11 pt, detail Tahoma 6 pt ("100 ml = 106,60 Kč"),
price BebasNeue 27 pt integer + 15 pt decimals in a red badge (white text), regular price a crossed 9 pt "49" + 5 pt "90"
above it, discount "-50 %" (BebasNeue 20-21) on a yellow/black badge. Multi-buy tiles ("1+1 ZDARMA", "2+1") print the
per-piece price and "za 1 ks při koupi 2 ks" (BebasNeue 6) below it; club prices carry "klubová cena" (BebasNeue 6).
Quirks handled here (all by mutating spans, since pdfparse is shared):
 - the name span starts 0.01 pt before the brand span ends -> read as a new tile, continuation spans are nudged right;
 - span bboxes are taller than the glyphs, so the 6 pt unit-price line "starts inside" the title -> y1 shortened;
 - the text layer carries hidden discounts ("-20 %" under the "GARANCE / NEJNIŽŠÍ CENA" badge) and big banner
   percentages: a discount is only kept when a regular price stands next to it (page level clean-up, runs when the
   first detail span of a page is asked for, i.e. after every title span of that page was seen);
 - a name ending right before the bold brand of the next column (gap < one em) would be glued to it: its x1 is cut;
 - pages "Jen na e-shopu" (coupon prices, different terms) are dropped;
 - the old price "49 " + "90" would be read as the decimals of the main price -> its x0 is moved right."""
import math
import re

from akce.layouts import Layout

DISC = re.compile(r"-\s?\d{1,2}\s?%?")
DETAIL_BEBAS = re.compile(r"(?i)za\s+\d\s*ks|při\s*koupi|klubov")


class TetaLayout(Layout):
    _seen: list = []
    _phase = "detail"
    _busy = False

    def is_title(self, s):
        if self._busy:
            return super().is_title(s)
        if self._phase == "detail":
            self._phase = "title"
            self._seen = []
        self._seen.append(s)
        ok = super().is_title(s)
        if ok:
            for o in self._seen[:-1]:             # a tile ending a line right before the brand of the next column
                if not getattr(o, "_title", False) or abs(o.y0 - s.y0) > 2:
                    continue
                for a, b in ((o, s), (s, o)):     # a = left, b = right neighbour
                    gap = b.x0 - a.x1
                    # next column: bold brand right after a name, or a name line next to another name line (gap of a few pt)
                    if ((b.font.endswith("Bold") and not a.font.endswith("Bold") and 0 <= gap < a.size + 2)
                            or (not a.font.endswith("Bold") and not b.font.endswith("Bold") and 5 < gap < a.size + 2)) and not getattr(a, "_cut", False):
                        a._cut = True
                        a.x1 -= a.size + 4        # the same-line rule of build_blocks must not glue two columns
            s._title = True
        if ok and not getattr(s, "_nudged", False):
            s._nudged = True
            if not s.font.endswith("Bold"):
                s.x0 += 0.6
            s.y1 = s.y0 + s.size * 0.95
        return ok

    def _cleanup(self):
        bebas = [s for s in self._seen if "BebasNeue" in s.font]
        if any(re.search(r"(?i)pouze online|jen na e-shopu|pouze na e-shopu", s.text) for s in self._seen):
            for s in bebas:                        # e-shop-only pages: coupon prices, other terms -> not parsed
                if s.size >= 18:
                    s.text = ""
        olds = [s for s in bebas if 8.4 <= s.size <= 9.6 and re.fullmatch(r"\d{1,4}", s.text.strip())]
        for s in bebas:
            if s.size >= 18 and DISC.fullmatch(s.text.strip()):
                if not any(-25 <= o.x0 - s.x0 <= 110 and -25 <= o.y0 - s.y0 <= 45 for o in olds):
                    s.text = ""
        for o in olds:
            o.x0 += 3
        self._drop_odd_discounts(bebas)
        self._park_labels(bebas)

    def _drop_odd_discounts(self, bebas):
        """A printed "-30 %" must agree with the printed regular price (+-3 points), otherwise it belongs to another tile."""
        from akce import pdfparse
        discs = [s for s in bebas if s.size >= 18 and DISC.fullmatch(s.text.strip())]
        for p in pdfparse.build_prices(self._seen, self):
            if p.discount is None or not p.others:
                continue
            old = max(q.value for q in p.others)
            if old > p.value and abs((1 - p.value / old) * 100 - p.discount) > 3:
                near = [s for s in discs if math.hypot(s.x0 - p.x0, s.y0 - p.y0) < p.size * 4]
                for s in near:
                    if str(p.discount) in s.text:
                        s.text = ""

    def _park_labels(self, bebas):
        """"za 1 ks při koupi 2 ks" / "klubová cena" sit under the price badge, often far from the title.
        Pair tiles and prices exactly as the parser will (same matching), then park every label under its tile."""
        from akce import pdfparse
        labs = [s for s in bebas if 4.5 <= s.size <= 8 and DETAIL_BEBAS.search(s.text)]
        if not labs:
            return
        blocks = pdfparse.build_blocks(self._seen, self)
        prices = pdfparse.build_prices(self._seen, self)
        pairs = pdfparse.match(blocks, prices, self)
        for lab in labs:
            above = bool(re.search(r"(?i)klubov", lab.text))      # "klubová cena" sits above the price, "za 1 ks při koupi" below
            ps = [(b, p) for b, p in pairs if (-45 <= lab.y0 - p.y0 <= 4 if above else 10 <= lab.y0 - p.y0 < 50)
                  and p.x0 - 30 <= lab.cx <= p.x1 + 45]
            if not ps:
                lab.text = ""                      # no clear price above it: better no condition than a wrong one
                continue
            b, p = min(ps, key=lambda bp: abs(bp[1].cx - lab.cx) + abs(bp[1].y1 - lab.y0))
            lab.text = re.sub(r"(?i)^za\s+\d\s*ks\s+při\s*koupi\s+(\d)\s*ks", lambda m: "při koupi " + {"2": "dvou", "3": "tří"}.get(m.group(1), m.group(1)) + " kusů", lab.text).strip() + " •"
            # (digits + "ks" would be read as the package size and break the unit-price check)
            lab.x0 = b.x0
            lab.y0 = max(x.y1 for x in b.spans)
            lab.y1 = lab.y0 + 1

    def is_detail(self, s):
        if self._busy:
            return self._is_detail(s)
        if self._phase == "title":
            self._phase = "detail"
            self._busy = True
            try:
                self._cleanup()
            finally:
                self._busy = False
        return self._is_detail(s)

    def _is_detail(self, s):
        if re.match(r"\*{2,}\s", s.text):
            return False                           # "** produkty lze libovolně kombinovat ..." page footnotes
        if "BebasNeue" in s.font:
            return 4.5 <= s.size <= 8 and bool(DETAIL_BEBAS.search(s.text))
        ok = super().is_detail(s) and bool(re.search(r"=|Kč", s.text))   # content lists of sets ("65+ 50 ml") are no unit prices
        if ok and not getattr(s, "_star", False):
            s._star = True
            m = re.match(r"^(.*?),\s*\*\s*(.+)$", s.text)   # "100 ml = 199,80 Kč, *100 ml = 119,88 Kč": the starred one is the promo price
            if m and re.search(r"=|od", m.group(2)):
                s.text = m.group(2)
        return ok


LAYOUT = TetaLayout(
    chain="teta",
    title_font=r"^Tahoma",
    title_size=(9.5, 12.5),
    detail_font=r"^Tahoma",
    detail_size=(5, 8.5),
    price_font=r"BebasNeue",
    min_price_size=8,
    main_size=20,
    price_side="any",
    old_above=False,
    max_dist=70,
    member_label="s klubovou kartou",
    skip_words=("novinka", "pouze online", "e-shop"),
)
