"""Globus: title Akrobat-ExtraBold 10 pt (brand "VÁŠ VÝBĚR" is the first title line), details Akrobat-Regular/SemiBold 6-8 pt,
prices Akrobat-Bold: big red integer 34 pt + small "90" (13 or 16 pt), crossed regular price (Akrobat-Bold 17 + 8 pt) above it,
discount "-25" Akrobat-Black + "%". The price tile sits ABOVE the title and details. "Můj Globus" tiles show the member
price on top and the regular price (also 34 pt) below; the parser keeps the upper one (member price, listed as cena).
Verified 18. 11. 2026: 99 % matched, 99 % same price vs reference (501 offers)."""
import re

from akce.layouts import Layout


class GlobusLayout(Layout):
    """The core has no per-page hook, so page boundaries are inferred from the call order: for every page
    build_blocks() calls is_title()/is_detail() over all spans, then build_prices() calls is_price()."""
    _seen = None
    _drop = None
    _last = "p"

    def _call(self, kind):
        if kind == "t" and self._last == "p" or self._seen is None:   # first title test after a price pass = new page
            self._seen = []
        self._last = kind

    def is_title(self, s):
        self._call("t")
        # member tiles: the "-38 %" of the no-card (AKCE) price would be taken as the discount of the member price; blank it
        if "Black" in s.font and 12 <= s.size <= 14 and re.fullmatch(r"\s*-\s*\d{1,2}\s*", s.text):
            s.text = ""
            return False
        if len(s.text.strip()) <= 2 or re.fullmatch(r"[a-zá-ž]{1,4}", s.text.strip()):          # stray overlapping suffix span ("dka" over "Hanácká vodka")
            return False
        return super().is_title(s)

    def is_detail(self, s):
        self._last = "d" if self._last != "t" else "t"
        ok = super().is_detail(s)
        # "AC: 100 g = 29,35 KC: 100 g = 26,41": AC = unit price of the AKCE (no-card) price, KC = of the member price we keep
        if ok and "AC:" in s.text:
            s.text = re.sub(r"AC:.*?(?=KC:)", "", s.text) if "KC:" in s.text else ""
            ok = bool(s.text.strip())
        # a bare package "0,5 l" must not be glued to the following "1 l = 19,80" unit price by the core regex
        if ok and len(s.text.strip()) <= 2:
            return False                       # black clipped remnants under white text ("rů", "10")
        if ok and re.search(r"\d\s*%", s.text) and "-" not in s.text:
            s.text = s.text.replace("%", "% obj.")   # alcohol strength is not a discount
        if ok and re.search(r"\d\s*(?:ml|l|g|kg)\s*$", s.text) and "=" not in s.text:
            s.text = s.text.rstrip() + ","
        return ok

    def is_price(self, s):
        self._last = "p"
        ok = super().is_price(s)
        prev, self._drop = self._drop, None
        if not ok:
            return False
        if 23 <= s.size <= 25.5 and re.search(r"\d", s.text):
            self._drop = s                     # 24 pt "29" = no-card AKCE price in a member tile (crossed old price kept)
            return False
        if prev is not None and s.size < 15 and 0 <= s.x0 - prev.x1 < 8 and abs(s.y0 - prev.y0) < 25:
            return False                       # ... and its small decimal part, which follows it in the span order
        key = (s.text.strip(), round(s.size))
        for k, x, y in self._seen:             # texts printed twice with a small offset (shadow / second layer): keep one
            if k == key and abs(s.x0 - x) <= 9 and abs(s.y0 - y) <= 5:
                if re.fullmatch(r"\s*\d{1,5}\s*", s.text):
                    self._drop = s             # its decimal part follows and must go too
                return False
        self._seen.append((key, s.x0, s.y0))
        # the 16 pt decimal part ("90") overlaps the 34 pt integer by ~3 pt; nudge it so the core finds it
        if 15.5 <= s.size < 20 and re.fullmatch(r"\d{2}", s.text.strip()) and not getattr(s, "_nudged", False):
            s.x0 += 4
            s._nudged = True
        return True


LAYOUT = GlobusLayout(
    chain="globus",
    title_font=r"Akrobat-ExtraBold",
    title_size=(9.5, 10.5),
    detail_font=r"Akrobat-(Regular|SemiBold)",
    detail_size=(5.5, 8.5),
    price_font=r"Akrobat-Bold",
    min_price_size=12,
    main_size=30,
    int_prices=True,
    price_side="above",
    max_dist=110,
    member_label="s kartou Můj Globus",
    member_rx=r"globus|kartou",
)
