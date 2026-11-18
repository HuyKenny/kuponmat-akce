"""Billa: tiles with a centred / right-aligned title (Axiforma-Black 7.5-9, some 11), details Axiforma-Medium 5.5-6.5
(package, "100 g = 9,95 Kč", "cena za 1 kg", "při koupi 1 ks 24,90"), price PoliticaCrossed-ExtraBold ~28 pt as one
span "34,90" (red) with the old price as a small crossed "49,90 /" (8 pt) and the red "-50%" in Axiforma-Black 23.
Multi-buy tiles carry Axiforma-Black micro labels ("OD 2 KS" / "PŘI KOUPI", "KUPTE 3 / ZAPLAŤTE 2", "1 + 1") that are read
as detail lines, so the promo unit price stays in ``cena`` and the condition lands in ``podminka``; the "při koupi 1 ks 39,90"
line (price of a single piece) is rewritten so it is not mistaken for the condition.
Quirks handled here: title lines are not left aligned (is_title snaps x0 of the lines of one tile), package span + unit
price span would read as "125 g = 100" (separator added). The "s Klubem / bez Klubu" lines are only unit prices, so no
member price (cena_bez) is produced.
Measured 18. 11. 2026 on billa-letak-11-11-2026: see tools.accuracy."""
import re
from akce.layouts import Layout


LABEL = re.compile(r"(?i)^\s*(od\s+\d\s*ks|při\s*koupi|kupte\s+\d|zaplaťte\s+\d|cena\s+za\s+1\s*ks|\d\s*\+\s*\d)")


class BillaLayout(Layout):
    _recent: list = []
    _phase = "title"
    _in_detail = False

    def is_detail(self, s):
        self._phase = "detail"
        self._in_detail = True
        try:
            return self._is_detail(s)
        finally:
            self._in_detail = False

    def _is_detail(self, s):
        ok = super().is_detail(s)
        if not ok:
            # micro labels of multi-buy tiles (Black < 7 pt) and "cena za 1 ks při koupi 2 ks" (Politica-Bold)
            ok = ((re.search(r"Axiforma-Black", s.font) and 3 <= s.size < 8.6 and LABEL.match(s.text) or re.search(r"Axiforma-Black", s.font) and 3 <= s.size < 7 and not re.fullmatch(r"[\d\s,.%+\-]+", s.text))
                  or (re.search(r"^Politica-Bold", s.font) and 4.5 <= s.size <= 7)) and not self.is_title(s)
            if ok and re.fullmatch(r"(?i)běžná cena\s*", s.text):
                return False
        if ok and not getattr(s, "_sep", False):
            s._sep = True
            self._snap_detail(s)
            t = s.text
            if re.search(r"(?i)=\s*od\s+\d", t):
                s.text = ""                       # "100 g = od 16,90 Kč": from-price over several variants, unusable
            elif re.fullmatch(r"(?i)\s*od\s+(\d)\s*ks\s*", t):
                s.text = "při koupi " + re.search(r"\d", t).group(0) + " a více ks •"
            elif re.fullmatch(r"(?i)\s*při koupi\s*", t) and re.search(r"Black", s.font):
                s.text = ""                       # "PŘI KOUPI" label next to "OD 2 KS"
            elif re.fullmatch(r"(?i)\s*při\s*koupi\s*", t) or re.fullmatch(r"(?i)\s*1\s*ks\s+\d+[,.]\d\d\s*", t):
                s.text = ""                       # "při koupi" / "1 ks 39,90" split over two lines
            elif re.search(r"(?i)při\s*koupi\s*1\s*ks\s*\d", t):
                s.text = ""                       # price of a single piece, not the promo price
            elif re.search(r"(?i)při\s*koupi\s*1\s*ks\s*$", t):
                s.text = ""
            elif re.match(r"(?i)\s*cena\s+za\s+1\s*ks\s+při\s*koupi\s+\d\s*ks", t):
                s.text = ""                       # repeats the KUPTE/ZAPLAŤTE label
            elif re.match(r"(?i)\s*cena\s+za\s+1\s*ks\s*$", t):
                s.text = "cena za kus"
            elif re.search(r"(?:kg|g|ml|l|ks)\s*$", t):
                s.text = t.rstrip() + " •"        # "125 g" + "100 g = 38,32 Kč" must not read as "125 g = 100"
        return ok

    def _snap_detail(self, s):
        """Detail lines are centred too, can start left of the title, and labels like "KUPTE 2" sit far below it.
        build_blocks attaches by distance from the lowest line already attached while spans arrive in stream order,
        so every detail is parked right under its title group (x0 = group x0 + tiny offset keeps the line order)."""
        label = bool(LABEL.match(s.text))
        best, bd = None, 1e9
        for grp in self._recent:
            gx0 = min(x.x0 for x in grp)
            gx1 = max(x.x1 for x in grp)
            dy = s.y0 - max(x.y1 for x in grp)
            dist = abs(s.cx - (gx0 + gx1) / 2)
            if -2 <= dy < (130 if label else 45) and dist < (120 if label else max(14, (gx1 - gx0) * 0.6)):
                if dist + dy < bd:
                    best, bd = grp, dist + dy
        if best:
            top = max(x.y1 for x in best)
            s.x0 = min(x.x0 for x in best) + max(0.0, s.y0 - top) * 0.001
            s.y0, s.y1 = top, top + 1

    def is_title(self, s):
        if self._phase == "detail" and not self._in_detail:   # build_blocks asks titles first, then details: a new page
            self._recent.clear()
            self._phase = "title"
        ok = super().is_title(s) and not LABEL.match(s.text)
        if ok and not getattr(s, "_snapped", False):
            s._snapped = True
            s.orig_x0 = s.x0
            for grp in self._recent[-6:]:
                last = grp[-1]
                dy = s.y0 - last.y0
                if (0 < dy < s.size * 1.6 and abs(s.size - last.size) < 1.0
                        and (abs(s.cx - last.cx) < 10 or abs(s.x1 - last.x1) < 4 or abs(s.x0 - last.x0) < 3)):
                    grp.append(s)
                    x0 = min(x.orig_x0 for x in grp)
                    for x in grp:
                        x.x0 = x0
                    break
            else:
                self._recent.append([s])
        return ok

    def skip_title(self, t):
        # all-caps strips ("NA POMAZÁNKY Z PULTU LAHŮDEK", "OD 12. 11.") are banners, not products
        return super().skip_title(t) or not re.search(r"[a-zá-ž]", t)


LAYOUT = BillaLayout(
    chain="billa",
    title_font=r"Axiforma-Black",
    title_size=(7, 11.5),
    detail_font=r"Axiforma-Medium",
    detail_size=(5, 7.6),
    detail_gap=75,
    price_font=r"PoliticaCrossed",
    min_price_size=7,
    main_size=20,
    max_dist=110,
    price_side="below",
    member_rx=r"(?!x)x",
    skip_words=("platnost", "nabídka platí", "více víkendových"),
)
