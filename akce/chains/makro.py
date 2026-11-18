"""Makro (cash & carry, kupi.cz lists it too): 4 tiles across, text layer present.
Tile: "Kód zboží: 123" (Regular 6.5) on top, title CAMetro-ExtraBold 7.5 blue (0x4282) in capitals (+ more title lines),
bullets "• bal.: 10× 130 g" / "• cena za 130 g" (Regular 6.5), a price box to the right of / under the title: BIG white price
(19-25 pt, "9" "," "60") is WITHOUT VAT; the small "10,75 *" (5.8 pt, "*cena s DPH" in the page footer) is the consumer price
WITH VAT. We take only the small price as ``cena``. Tiered tiles (yellow price, "3BAL." / "15ks" label, blue crossed tier prices)
have no consumer price for one piece -> dropped. The package that matters is the "cena za X" basis (price is per X), not "bal.: 10× X"."""
import re

from akce.layouts import Layout

VAT_PRICE = re.compile(r"^\d{1,3}(?:[ \u00a0]?\d{3})*,\d{2}\s*[*×]$")


TIER = re.compile(r"(?i)bal\.|cena od|^\d+\s*(?:[–-]\s*\d+)?\s*ks$")


class MakroLayout(Layout):
    """Page boundary is inferred from the call order (is_title over all spans comes before is_price)."""
    _tiers: list = []
    _last = "p"

    def _call(self, kind, s=None):
        if kind == "t" and self._last == "p":
            self._tiers = []
        self._last = kind if kind != "d" else self._last
        if kind == "t" and s is not None and re.search(r"ExtraBold|Black", s.font) and s.size <= 7 and TIER.search(s.text.strip()):
            self._tiers.append(s)

    def _is_tiered(self, s):
        """A quantity-tier label ("1–3 BAL.", "15ks") right above the small price: no consumer price for one piece."""
        return any(0 <= s.y0 - t.y0 <= 52 and t.x0 - 28 <= s.x0 <= t.x1 + 28 for t in self._tiers)

    def is_title(self, s):
        self._call("t", s)
        if not re.search(r"ExtraBold", s.font) or not (s.color == 0x4282 or (s.color == 0xffffff and s.size <= 8)):
            return False                       # white 7.5 pt = title on a dark photo; bigger white = section header
        ok = super().is_title(s) and not re.fullmatch(r"[\d\s,.]+", s.text)
        if ok and not getattr(s, "_wide", False):
            # titles are short and the price box sits at the right bottom of the (4-column, ~120 pt wide) tile: widen the
            # title so that its own price is not farther away than the neighbouring tile's one
            s._wide = True
            s.x1 = max(s.x1, s.x0 + 118)
        return ok

    def is_detail(self, s):
        if re.match(r"\s*Kód zboží", s.text):
            return False
        ok = super().is_detail(s)
        if ok and not re.match(r"\s*•?\s*cena za\s", s.text) and not s.text.startswith("•  \u200b"):
            # "bal.: 10× 130 g" is the case (the price is for "cena za 130 g"), other bullets are descriptions: keep their
            # geometry (they extend the tile block towards the price box) but neutralise the text
            s.text = "• \u200b"
        m = re.match(r"\s*•?\s*cena za\s+(.*)$", s.text)
        if m and ok:
            s.text = "• " + m.group(1).replace(" od", "")
        return ok

    def is_price(self, s):
        self._last = "p"
        if not VAT_PRICE.match(s.text.strip()) or not s.font.endswith("ExtraBold") or s.color == 0xffe700 or self._is_tiered(s):
            return False
        s.text = re.sub(r"[*×\s\u00a0]", "", s.text)
        return True


LAYOUT = MakroLayout(
    chain="makro",
    title_font=r"CAMetro-ExtraBold",
    title_size=(7.2, 12),
    detail_font=r"CAMetro-Regular",
    detail_size=(6, 7.2),
    min_price_size=5,
    main_size=5,
    price_side="right",
    side_penalty=100,
    max_dist=160,
    member_label="",
    skip_words=("více zde", "bal.", "akce není", "cena za", "cena od"),
)
