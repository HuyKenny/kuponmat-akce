"""Hruška (Hruška Klub): one font (SeasonSansVF-Regular) everywhere, roles are told apart by size.
Tile: red (or green "S KLUBEM") price badge with "NAŠE CENA" label, price = big integer (26 pt) + superscript decimals (15 pt);
a second smaller badge under the green one (16 + 9 pt) is the price without the club. Below the badge: title 8 pt (name,
brand, variant on 1-3 lines), then 7 pt package ("100 g", "vybrané druhy") and 6 pt unit price ("1 kg = 149,00 Kč").
Price sits ABOVE the title. Package line is glued to the unit price line in the text layer ("100 g 1 kg = ..."), which
the generic unit parser would read as "100 g 1" -> the package span gets a separator appended.
Verified 18. 11. 2026: 94 % matched, 100 % same price vs reference."""
import re

from akce.layouts import Layout


class HruskaLayout(Layout):
    """Title lines are often right-aligned / centred, so the lines of one title start at different x. Before grouping
    (build_blocks groups by x0) the x0 of vertically stacked lines of the same alignment is unified."""

    def is_title(self, s):
        if self.__dict__.get("_in_detail"):
            return super().is_title(s)
        if self.__dict__.get("_phase") == "other":
            self._tl = []
        self._phase = "title"
        ok = super().is_title(s)
        tl = self.__dict__.setdefault("_tl", [])
        if ok and not any(a is s for a in tl):
            for a in tl:
                up, lo = (a, s) if a.y0 < s.y0 else (s, a)
                if 6 <= lo.y0 - up.y0 <= 12 and abs(up.size - lo.size) < 0.3 and abs(up.x0 - lo.x0) > 2 \
                        and (abs(up.x1 - lo.x1) < 3 or abs(up.cx - lo.cx) < 3):
                    up.x0 = lo.x0 = min(up.x0, lo.x0)
            tl.append(s)
        return ok

    def is_price(self, s):
        ok = super().is_price(s)
        if ok and s.size >= 15 and re.fullmatch(r"\d{1,4}", s.text) and not getattr(s, "_fx", False):
            s.x1 -= 0.1 * s.size                   # the superscript decimals overlap the integer by ~1.5 pt
            s._fx = True
        return ok

    def is_detail(self, s):
        self._phase = "other"
        self._in_detail = True
        try:
            ok = super().is_detail(s)
        finally:
            self._in_detail = False
        if ok and re.search(r"\d\s*(kg|g|ml|l|ks)\s*$", s.text) and not s.text.endswith("|"):
            s.text = s.text.rstrip() + " |"        # keep "100 g" apart from "1 kg = 149,00 Kč"
        return ok


LAYOUT = HruskaLayout(
    chain="hruska",
    title_font=r"SeasonSansVF",
    title_size=(7.8, 8.6),
    detail_font=r"SeasonSansVF",
    detail_size=(5.4, 7.5),
    price_font=r"SeasonSansVF",
    min_price_size=9,
    main_size=20,
    price_side="above",
    member_label="s Hruška klubem",
    member_rx=r"klub",
)
