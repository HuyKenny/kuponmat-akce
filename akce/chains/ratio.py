"""Ratio (cash & carry, ratio.cz): 88-page monthly Heyzine flipbook PDF, 4-column tiles with the photo above, product name under it.
Title Oswald-Regular 11 pt (upper case), package / variety Oswald-Light 8 pt ("500g", "více druhů, 2x160g", producer).
Price: coloured box with the consumer price WITH VAT "33,90" (Oswald-Bold, white, label "včetně DPH" right under it) and a
small box with the price WITHOUT VAT "30,27" (label "bez DPH" next to it). Sizes vary per page (14/9, 18/11 pt ...), so the
role is taken from the label, not from the size: the number sitting on a "včetně DPH" label is rewritten to a main price
(size 20), the one on a "bez DPH" label to a small one (size 9, ignored by the core: it is lower than the main price and
there is no member condition) - cena is never the without-VAT price.
The price box sits above the title. No regular (crossed) prices in this leaflet; the weekly "Cena platí 1.-8. listopad" blocks
are not read, offers carry the validity of the whole leaflet."""
import re

from akce.layouts import Layout


class RatioLayout(Layout):
    def _finalize(self):
        sp = self.__dict__.get("_keep", [])
        # page 1 gives every product its own week ("CENA PLATÍ 9.-15. LISTOPAD"); the offer model has one validity
        # per leaflet, so such a page gives no offers (an expired week would look valid)
        self._skip = any(s.text.strip().upper().startswith("CENA PLATÍ") for s in sp)
        for s in sp:                       # "40%" = alcohol content in the name, this leaflet prints no discounts
            if re.fullmatch(r"\d{1,2}\s?%", s.text.strip()):
                s.text = "x"
        nums = [s for s in sp if re.fullmatch(r"\d[\d ]*,\d\d", s.text.strip()) and "Bold" in s.font]
        for lab in sp:
            t = lab.text.strip().lower()
            if t not in ("včetně dph", "bez dph", "vcetne dph"):
                continue
            vat = t != "bez dph"
            best, bd = None, 1e9
            for n in nums:
                if vat:                   # label directly under the big number
                    ok = abs(n.x0 - lab.x0) < 12 and -3 < lab.y0 - n.y0 < n.size * 1.6 and n.y1 > lab.y0 - 4
                    dd = abs(n.x0 - lab.x0) + abs(lab.y0 - n.y1)
                else:                     # label right of the small number, same line
                    ok = abs(n.cy - lab.cy) < 6 and -2 <= lab.x0 - n.x1 < 12
                    dd = abs(lab.x0 - n.x1) + abs(n.cy - lab.cy)
                if ok and dd < bd:
                    best, bd = n, dd
            if best is not None:
                best.size = 20.0 if vat else 9.0
                best.text = best.text.replace(" ", "")

    def is_title(self, s):
        if self.__dict__.get("_phase") == "other":
            self.__dict__.update(_keep=[], _skip=False)
        self._phase = "title"
        self.__dict__.setdefault("_keep", []).append(s)
        return (s.color == 0 or "Regular" in s.font) and super().is_title(s)   # white Bold = price boxes / labels; white Regular = titles on dark pages

    def is_detail(self, s):
        if self.__dict__.get("_phase") == "title":
            self._finalize()
        self._phase = "other"
        # (Layout.is_detail calls self.is_title, which would reset the page state: test the base rules directly)
        if not (re.search(self.detail_font, s.font) and self.detail_size[0] <= s.size <= self.detail_size[1]
                and not Layout.is_title(self, s)):
            return False
        s.text = re.sub(r"(?i)cena za\s*1\s*(kg|ks|l)\b", r"cena za \1", s.text)   # "cena za 1Kg" = price per kg, not a 1 kg pack
        if not getattr(s, "nudged", False):
            s.nudged = True
            s.y0 += 3.0                    # package line is set tight under the title (boxes overlap by ~2 pt)
        return True

    def is_price(self, s):
        self._phase = "other"
        return not self.__dict__.get("_skip") and super().is_price(s)


LAYOUT = RatioLayout(
    chain="ratio",
    title_font=r"Oswald-(Regular|Bold)",
    title_size=(10, 12),
    detail_font=r"Oswald-Light",
    detail_size=(6.5, 9),
    price_font=r"Oswald-Bold",
    min_price_size=8,
    main_size=15,
    price_side="above",
    side_penalty=100,
    max_dist=110,
    member_rx=r"zzzz-never",
)
