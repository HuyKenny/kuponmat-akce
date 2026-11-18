"""Flop / Flop Top (flop-potraviny.cz): one family SizmoPro. Tile = yellow (Flop) or yellow/orange (Flop Top) price badge,
price = big integer (24.7 pt) + superscript decimals (14.4 pt); Flop Top adds a red "-25 %" flag and the regular price
(7 pt, crossed) under the badge; club tiles have "S KLUBEM" badge (28 pt) + a smaller "BEZ KLUBU" badge (17 pt).
Below the badge: brand (Medium 8 pt), title (Bold 8 pt), package (7 pt), unit price (6 pt).
Price sits ABOVE (or left of) the title."""
import re

from akce.layouts import Layout


class FlopLayout(Layout):
    """Page pre-pass (runs when the first detail span of a page is classified; by then every span of the page went
    through ``is_title``): (1) club tiles - the "S KLUBEM" badge is far above the title and the club is not named in the
    detail lines, so " s klubem" is appended to the first detail line of that tile (pdfparse then knows the second big
    price is the price without the club); (2) multi-buy tiles ("/KS" + "při koupi 2 ks a více") print the price for a
    single piece as a second big price - ignored, so it is not mistaken for the regular price."""

    def _prepass(self):
        allsp = self.__dict__.get("_all", [])
        self._skip = set()
        titles = [s for s in allsp if Layout.is_title(self, s)]
        self._in_detail = True
        try:
            details = [s for s in allsp if Layout.is_detail(self, s)]
        finally:
            self._in_detail = False
        for k in allsp:
            if re.fullmatch(r"S KLUBEM", k.text.strip()):
                ts = [t for t in titles if 0 < t.y0 - k.y1 < 220 and abs(t.x0 - k.x0) < 40]
                if not ts:
                    continue
                t = min(ts, key=lambda t: t.y0)
                ds = [d for d in details if 0 < d.y0 - t.y0 < 60 and abs(d.x0 - t.x0) < 6]
                if ds and "klub" not in min(ds, key=lambda d: d.y0).text:
                    min(ds, key=lambda d: d.y0).text += " s klubem"
            if k.text.strip() == "/KS":
                for n in allsp:
                    if re.fullmatch(r"\d{1,4}", n.text.strip()) and 16.8 <= n.size <= 19 and abs(n.cx - k.cx) < 50 and abs(n.cy - k.cy) < 50:
                        self._skip.add(id(n))
                        for dsp in allsp:
                            if re.fullmatch(r"\d{2}", dsp.text.strip()) and 8 <= dsp.size <= 11 and abs(dsp.y0 - n.y0) < 8 and -1 <= dsp.x0 - n.x1 < 6:
                                self._skip.add(id(dsp))

    def is_title(self, s):
        if self.__dict__.get("_in_detail"):
            return super().is_title(s)
        if self.__dict__.get("_phase") != "title":
            self._all = []
            self._phase = "title"
        self._all.append(s)
        return super().is_title(s)

    def is_price(self, s):
        ok = super().is_price(s) and id(s) not in self.__dict__.get("_skip", ())
        if ok and s.size >= 15 and re.fullmatch(r"\d{1,4}", s.text) and not getattr(s, "_fx", False):
            s.x1 -= 0.1 * s.size                   # the superscript decimals touch / overlap the integer
            s._fx = True
        return ok

    def is_detail(self, s):
        if self.__dict__.get("_phase") == "title":
            self._phase = "other"
            self._prepass()
        self._in_detail = True
        try:
            ok = super().is_detail(s)
        finally:
            self._in_detail = False
        if ok and not getattr(s, "_fy", False):
            s.y0 += 3.0                            # line box overlaps the title above by ~3 pt; build_blocks needs dy >= -2
            s._fy = True
        if ok and not getattr(s, "_ft", False):
            t = re.sub(r"(=\s*(?:od\s*)?\d{1,2}) (\d{3},\d{2})", r"\1\2", s.text)        # "1 299,00 Kč"
            m = re.search(r"(\d+)\s*\+\s*(\d+)\s*(g|ml)\b", t)                       # "300 + 100 g" = 400 g (not a "2+1" offer)
            if m:
                t = t[:m.start()] + f"{int(m.group(1)) + int(m.group(2))} {m.group(3)}" + t[m.end():]
            s.text, s._ft = t, True
        if ok and re.search(r"\d\s*(kg|g|ml|l|ks)\s*$", s.text) and not s.text.endswith("|"):
            s.text = s.text.rstrip() + " |"        # keep "100 g" apart from "1 kg = 149,00 Kč"
        return ok


LAYOUT = FlopLayout(
    chain="flop",
    title_font=r"SizmoPro-(Bold|Medium)$",
    title_size=(7.8, 8.4),
    detail_font=r"SizmoPro(-Bold)?$",
    detail_size=(5.5, 7.1),
    price_font=r"SizmoPro-(Bold|Medium)?$|SizmoPro$",
    min_price_size=8,
    main_size=20,
    int_prices=True,
    price_side="above",
    max_dist=70,
    member_label="s Flop klubem",
    member_rx=r"klub",
    skip_words=("nálepk", "soutěž", "platnost"),
)
