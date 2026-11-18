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
 - the old price "49 " + "90" would be read as the decimals of the main price -> its x0 is moved right."""
import math
import re

from akce.layouts import Layout

DISC = re.compile(r"-\s?\d{1,2}\s?%?")
DETAIL_BEBAS = re.compile(r"(?i)za\s+\d\s*ks|při\s*koupi|klubov")


class TetaLayout(Layout):
    _seen: list = []
    _phase = "detail"

    def is_title(self, s):
        if self._phase == "detail":
            self._phase = "title"
            self._seen = []
        self._seen.append(s)
        ok = super().is_title(s)
        if ok and not getattr(s, "_nudged", False):
            s._nudged = True
            if not s.font.endswith("Bold"):
                s.x0 += 0.6
            s.y1 = s.y0 + s.size * 0.95
        return ok

    def _cleanup(self):
        bebas = [s for s in self._seen if "BebasNeue" in s.font]
        olds = [s for s in bebas if 8.4 <= s.size <= 9.6 and re.fullmatch(r"\d{1,4}", s.text.strip())]
        for s in bebas:
            if s.size >= 18 and DISC.fullmatch(s.text.strip()):
                if not any(-25 <= o.x0 - s.x0 <= 110 and -25 <= o.y0 - s.y0 <= 45 for o in olds):
                    s.text = ""
        for o in olds:
            o.x0 += 3
        self._park_labels(bebas)

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
            ps = [(b, p) for b, p in pairs if 10 <= lab.y0 - p.y0 < 50 and p.x0 - 30 <= lab.cx <= p.x1 + 45]
            if not ps:
                lab.text = ""                      # no clear price above it: better no condition than a wrong one
                continue
            b, p = min(ps, key=lambda bp: abs(bp[1].cx - lab.cx) + abs(bp[1].y1 - lab.y0))
            lab.x0 = b.x0
            lab.y0 = max(x.y1 for x in b.spans)
            lab.y1 = lab.y0 + 1

    def is_detail(self, s):
        if self._phase == "title":
            self._phase = "detail"
            self._cleanup()
        if re.match(r"\*{2,}\s", s.text):
            return False                           # "** produkty lze libovolně kombinovat ..." page footnotes
        if "BebasNeue" in s.font:
            return 4.5 <= s.size <= 8 and bool(DETAIL_BEBAS.search(s.text))
        return super().is_detail(s)


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
)
