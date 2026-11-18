"""Norma: two-layer PDF (every text drawn twice, plus per-character fragments), tiles are tall: title (FrutigerCE-ExtraBlackCn
9-12 pt, or OptusTCE-Regular 9.5 for the wine tiles on the cover) and bullet details (FrutigerCE-Cn 7 pt, "• 200 g (100 g 29,95)")
at the TOP of the tile, the whole price ("49,90" in one FrutigerCE-BlackCn span, 22-42 pt) at the BOTTOM, a crossed old price
(small ExtraBlackCn / Cn) above or beside it and "levnější o 38 %" next to it. Cover page: right- or left-aligned titles and
prices lower than the neighbour's title, handled with span tweaks below (the core has no per-page hook).
Verified 16. 11. 2026: 84 % matched, 93 % same price vs reference (198 offers); non-food pages 3-5/8 can swap prices of neighbours."""
import re

from akce.layouts import Layout

JUNK = re.compile(r"super cena|cena za|levnější|novinka|bomba|týdne|nabídka|ilustrační|příklady|najdete|ceny měsíce|víno měsíce|otevřeno|státní svátek|hodin|listopad|www\.", re.I)
SHIFT = 110.0
SHIFT2 = 60.0


class NormaLayout(Layout):
    """Page boundary is inferred from the call order (is_title over all spans, then is_detail, then is_price)."""
    _page = None
    _ids = None
    _last = "p"
    _cover = None

    def _call(self, kind, s=None):
        if (kind == "t" and self._last == "p") or self._page is None:
            self._page, self._ids, self._cover = [], set(), None
        if kind == "t" and id(s) not in self._ids:
            self._ids.add(id(s))
            self._page.append(s)
        if kind != "t" or self._last == "p":
            self._last = kind if not (kind == "d" and self._last == "t") else "t"
        if kind == "p":
            self._last = "p"

    def _is_cover(self):
        if self._cover is None:
            self._cover = any(x.size >= 33 and x.font.endswith("-BlackCn") for x in self._page)
        return self._cover

    def _redundant(self, s):
        """Fragments / re-drawn copies: another span of the page holds the same text at the same place."""
        t = re.sub(r"\s+", "", s.text)
        for i, o in enumerate(self._page):
            if o is s or len(o.text) < len(s.text):
                continue
            if o.x0 - 1.5 <= s.x0 and s.x1 <= o.x1 + 1.5 and o.y0 - 2 <= s.y0 and s.y1 <= o.y1 + 2:
                ot = re.sub(r"\s+", "", o.text)
                if t in ot and (len(ot) > len(t) or i < self._page.index(s)):
                    return True
        return False

    def _lone_lower(self, s):
        """Lower-case title line ("pruhovaný běhoun", "koupelové bomby"): a continuation or a title that starts lower-case."""
        return s.size >= 8.5 and s.font.endswith("ExtraBlackCn") and not re.search(r"cca|\d\s*[×x]|^\W", s.text)

    def is_title(self, s):
        self._call("t", s)
        tx = s.text.strip()
        if JUNK.search(tx) or tx[:1] in "–-" or (tx[:1].islower() and not self._lone_lower(s)) or self._redundant(s):
            return False
        ok = super().is_title(s)
        if ok and not getattr(s, "_al", False):
            s._al = True
            # right-aligned multi-line titles (cover): same x1 as the previous line but another x0 -> take its x0 so the
            # core merges the lines into one block
            i = self._page.index(s)
            for p in reversed(self._page[max(0, i - 4):i]):
                if getattr(p, "_al", False) and abs(p.size - s.size) < 0.5 and 0 < s.y0 - p.y0 < s.size * 1.6 \
                        and abs(s.x0 - p.x0) >= 3.5 and (abs(s.x1 - p.x1) < 3.5 or abs(s.cx - p.cx) < 3.5 or -35 <= s.x0 - p.x0 <= 3):
                    s.x0 = p.x0
                    break
        return ok

    def is_detail(self, s):
        self._call("d")
        ok = super().is_detail(s)
        if ok and self._redundant(s):
            return False
        if ok and re.search(r"\d\s*%", s.text) and "-" not in s.text:
            s.text = s.text.replace("%", "% obj.")           # alcohol strength is not a discount
        # cover page: lift the "levnější o 20 %" discount together with the price (see is_price)
        if re.fullmatch(r"\d{1,2}%", s.text.strip()) and s.size >= 20 and not getattr(s, "_up", False):
            d = SHIFT if self._is_cover() else 0
            s.y0 -= d
            s.y1 -= d
            s._up = True
        return ok

    def is_price(self, s):
        self._call("p")
        ok = super().is_price(s) and not self._redundant(s)
        if ok and not getattr(s, "_up", False):
            # The price sits at the bottom of a tall tile and is nearer to the NEXT row's title than to its own, while the
            # core only has a fixed 60 pt wrong-side penalty: lift every price (cover: the big ones, 110 pt; else 60 pt).
            if self._is_cover():
                d = SHIFT if (s.color != 0xffffff and (s.size >= 33 or (9.5 <= s.size <= 10.5 and "ExtraBlack" in s.font))) else 0
            else:
                d = 0
            s.y0 -= d
            s.y1 -= d
            s._up = True
        return ok


LAYOUT = NormaLayout(
    chain="norma",
    title_font=r"FrutigerCE-ExtraBlackCn|OptusTCE-Regular",
    title_size=(8.5, 12.6),
    detail_font=r"FrutigerCE-(Cn|BoldCn)$",
    detail_size=(5, 10.2),
    price_font=r"FrutigerCE-(Black|ExtraBlack)Cn",
    min_price_size=12,
    main_size=20,
    price_side="below",
    side_penalty=150,
    max_dist=150,
    member_label="s kartou",
)
