"""CBA (cba.cz, weekly Premium and Potraviny leaflets; Market leaflet is image-only and not parsed).
Tile: title FuturaTOT-Bold 13 pt in red (one to three lines), under it FuturaTOT-Book 9 pt lines: variants, package and the
printed unit price "400 g (100 g = 12,48 Kč)", sometimes "V nabídce také ..." (a second product, same detail font).
Price = big integer FuturaTOT-Bold 22 pt + superscript decimals 12.8 pt in a red-outlined oval BELOW the title and the photo.
No regular price is printed. Verified 18. 11. 2026."""
import re

from akce.layouts import Layout


class CbaLayout(Layout):
    """Titles are often right-aligned (page 3): lines of one title start at different x -> unify x0 while the page's
    titles are being collected (build_blocks groups by x0). Detail lines: "pevný podíl: 170 - 175 g" would read as a
    package and its number as a price -> numbers dropped; a line ending with a unit gets a separator."""

    def is_title(self, s):
        if self.__dict__.get("_in_detail"):
            return super().is_title(s)
        if self.__dict__.get("_phase") != "title":
            self._tl = []
            self._phase = "title"
        if re.fullmatch(r"\d{1,2}\s?%", s.text.strip()):         # "85 % masa" badge is not a discount flag
            s.text = re.sub(r"\s?%", "\u2009%", s.text.strip())
        ok = super().is_title(s)
        if ok and not any(a is s for a in self._tl):
            s.x1 -= 5                                              # neighbouring columns are only ~10 pt apart: keep them from merging
            self._tl.append(s)
            changed = True
            while changed:                                         # right-aligned / centred lines: unify x0 (cascading)
                changed = False
                for up in self._tl:
                    for lo in self._tl:
                        if 10 <= lo.y0 - up.y0 <= 18 and abs(up.size - lo.size) < 0.3 and abs(up.x0 - lo.x0) > 2 \
                                and (abs(up.x1 - lo.x1) < 4 or abs(up.cx - lo.cx) < 3):
                            up.x0 = lo.x0 = min(up.x0, lo.x0)
                            changed = True
        return ok

    def is_detail(self, s):
        self._phase = "other"
        self._in_detail = True
        try:
            ok = super().is_detail(s)
        finally:
            self._in_detail = False
        if ok and (s.color == 0xE30613 or re.match(r"\s*(V nabídce také|za \d)", s.text)):
            s.font = "x"                   # "V nabídce také <other product> 150 g za 24,90 Kč": a second product, not this tile
            return False
        if ok and not getattr(s, "_ft", False):
            s._ft = True
            if s.text.startswith("pevný podíl"):
                s.text = "pevný podíl"
            elif re.search(r"\d\s*(kg|g|ml|l|ks)\s*$", s.text):
                s.text = s.text.rstrip() + " |"
        return ok

LAYOUT = CbaLayout(
    chain="cba",
    title_font=r"FuturaTOT-Bold$",
    title_size=(12.5, 13.5),
    detail_font=r"FuturaTOT-Book",
    detail_size=(6.5, 9.5),
    price_font=r"FuturaTOT-Bold$",
    min_price_size=12,
    main_size=18,
    int_prices=True,
    price_side="below",
    max_dist=170,
    detail_gap=60,
    skip_words=("bim karta", "nákupy pro"),
    title_fixes=[(r"\s*\*+", "")],              # footnote asterisks ("Vysočina*", "Kobliha s náplní**")
)
