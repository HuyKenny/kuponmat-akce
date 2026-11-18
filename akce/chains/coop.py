"""COOP (Coop Cena / Naše super ceny): tiles in a grid, price top-left of the title.
Title FiraSans-SemiBold 9-11 pt capitals, then "vybrané druhy" (Regular 11), the package as a SemiBold line ("1240 g",
"10 × 10 ks") and "| 1 kg = 34,60 Kč" (Regular 8). Prices are a subset font ("19" 23-39 pt + ",90" 12-22 pt, sometimes ","
and "90" as two spans, white on an orange/black badge). Member tiles: big price in the badge "cena s kupónem v aplikaci"
(= coupon price in the app) and a smaller "32,90 CENA BEZ KUPÓNU" price; the hero tile prints that price nearly as big as the
main one, so spans of a price standing right above a "CENA BEZ KUPÓNU" label are shrunk below ``main_size``.
Package lines are SemiBold like the title, therefore they are routed to details here. Titles are converted from CAPITALS.
The tip-extra and tuty-tip-menu PDFs of COOP are pure images (no text layer) and cannot be parsed without OCR.
Measured 18. 11. 2026 on coop-cena-letak-18-11-2026: see tools.accuracy."""
import re
from akce.layouts import Layout

PACK_LINE = re.compile(r"^[\d,.\s×x/()+]*\d\s*(?:g|kg|ml|l|ks|PD|m|ml/\d+\s*ml)\b[\d,.\s×x/()+gkmlsPD]*$", re.I)


class CoopLayout(Layout):
    _labels: list = []
    _phase = "title"

    def _reset(self):
        if self._phase == "price":
            self._labels.clear()
            self._phase = "title"

    def is_title(self, s):
        self._reset()
        if re.search(r"FiraSans-Regular", s.font) and 10 <= s.size <= 12 and not PACK_LINE.match(s.text):
            return not re.search(r"(?i)kupón|aplikaci", s.text)      # "vybrané druhy" / "prací gel," belong to the name
        return (super().is_title(s) and not PACK_LINE.match(s.text)
                and not re.search(r"(?i)kupón|aplikaci", s.text))

    def is_detail(self, s):
        self._reset()
        if re.search(r"(?i)CENA BEZ KUPÓNU", s.text):
            self._labels.append(s)
        if re.match(r"(?i)\s*BEZ KUPÓNU", s.text):
            s.text = "bez kupónu"             # drop its unit price: only the coupon one is the promo price
        if re.search(r"FiraSans-SemiBold", s.font) and 8.5 <= s.size <= 12 and PACK_LINE.match(s.text):
            if not getattr(s, "_moved", False):
                s._moved = True
                s.y0 += 4                      # line boxes are taller than the line pitch; stay below the title's y1
                s.text = s.text.rstrip() + " •"      # else "300 g" + "1 kg = 166,33" reads as the unit price "300 g = 1"
            return True
        if re.search(r"FiraSans-Regular", s.font) and 10 <= s.size <= 12 and not PACK_LINE.match(s.text):
            return False
        return super().is_detail(s)

    def is_price(self, s):
        self._phase = "price"
        ok = super().is_price(s)
        if ok and not getattr(s, "_chk", False):
            s._chk = True
            if re.fullmatch(r"\d+", s.text.strip()):
                s.x1 -= s.size * 0.12            # integer and ",90" boxes overlap; pdfparse wants the decimals to start right of x1
        if ok and s.size >= 20:
            for l in self._labels:
                if -8 <= l.y0 - s.y1 <= 12 and abs(l.cx - s.cx) < 45:
                    s.size = 19.0
                    break
        return ok

    KEEP_UPPER = {"XXL", "XL", "BIO", "PD", "TV", "WC", "UHT", "ZOO"}

    def fix_title(self, t):
        t = super().fix_title(t)
        ws = [w.lower() if w.isupper() and w not in self.KEEP_UPPER and not re.search(r"\d", w) else w
              for w in t.split()]
        t = re.sub(r"(?<=\w)- (?=[a-zá-ž])", "", " ".join(ws))
        return t[:1].upper() + t[1:]


LAYOUT = CoopLayout(
    chain="coop",
    title_font=r"FiraSans-SemiBold",
    title_size=(8.5, 12),
    detail_font=r"FiraSans-Regular",
    detail_size=(4.5, 11.5),
    price_font=r"subse",
    min_price_size=9,
    main_size=20,
    price_side="above",
    max_dist=120,
    member_label="s kupónem v aplikaci",
    member_rx=r"kupón",
)
