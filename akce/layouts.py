"""Per-chain layout rules for ``pdfparse``: which font is the product title, detail text and price.

Tuned against the chain's real leaflets (``tools/inspect_pdf.py`` prints fonts and sizes).
A chain is published only after ``tools/accuracy.py`` passes (see README).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Layout:
    chain: str
    title_font: str                       # regex on font name
    title_size: tuple = (9.0, 16.0)
    detail_font: str = r"Regular|Medium|Light|Cn$"
    detail_size: tuple = (4.5, 9.5)
    price_font: str = r"."
    min_price_size: float = 12.0
    main_size: float = 20.0                # price font size from which a price is a main (big) one
    secondary_reach: float = 2.5           # how far (x main size) a small price belongs to a main one
    min_price: float = 1.0
    max_price: float = 50000.0
    int_prices: bool = False              # integer-only prices allowed (e.g. "549,-" split)
    discount_needs_minus: bool = False
    title_line_gap: float = 1.6
    detail_gap: float = 40.0
    price_side: str = "any"               # above / below / right / any
    side_penalty: float = 60.0            # cost added when the price sits on the wrong side of the title
    max_dist: float = 90.0
    member_label: str = "s aplikací/kartou"
    member_rx: str = r"aplikac|kartou|kart[ay]|klub|kupón|clubcard"
    old_above: bool = True                # a smaller price above the main one is the regular (crossed) price
    skip_words: tuple = ()
    title_fixes: list = field(default_factory=list)

    def is_title(self, s):
        return bool(re.search(self.title_font, s.font)) and self.title_size[0] <= s.size <= self.title_size[1] and not re.fullmatch(r"[\d\s,.%+\-–/=]+", s.text)

    def is_detail(self, s):
        return bool(re.search(self.detail_font, s.font)) and self.detail_size[0] <= s.size <= self.detail_size[1] and not self.is_title(s)

    def is_price(self, s):
        return bool(re.search(self.price_font, s.font)) and bool(re.fullmatch(r"[\d\s,.\-–/%]+", s.text))

    def skip_title(self, t):
        tl = t.lower()
        return any(w in tl for w in self.skip_words) or not re.search(r"[A-Za-zÁ-ž]{3}", t)

    def fix_title(self, t):
        for a, b in self.title_fixes:
            t = re.sub(a, b, t)
        return t.strip()


def _load():
    """Every chain lives in akce/chains/<chain>.py and exposes LAYOUT."""
    import importlib, pkgutil
    from . import chains
    out = {}
    for m in pkgutil.iter_modules(chains.__path__):
        try:
            mod = importlib.import_module(f"{chains.__name__}.{m.name}")
        except Exception as e:   # a broken chain file must not stop the others
            import sys
            print(f"! layout {m.name}: {e}", file=sys.stderr)
            continue
        if hasattr(mod, "LAYOUT"):
            out[mod.LAYOUT.chain] = mod.LAYOUT
    return out


LAYOUTS = _load()
