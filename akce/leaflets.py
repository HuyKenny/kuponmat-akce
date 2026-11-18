"""Current leaflets with a PDF, from the leaflet adapters shared with kuponmat.cz/letaky (akce/letaky)."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent / "letaky"
sys.path[:0] = [str(HERE), str(HERE / "adapters")]
from km_net import SESSION  # noqa: E402

PDF_CHAINS = ["albert", "kaufland", "globus", "billa", "coop", "norma", "hruska", "teta", "dm"]
SKIP_TITLES = ("katalog",)   # assortment catalogues: few promo prices, many pages


def current_leaflets(chains=None):
    for c in chains or PDF_CHAINS:
        try:
            m = importlib.import_module(c)
            items = m.stahni(SESSION)
        except Exception as e:   # one broken chain must not stop the others
            print(f"! {c}: adapter failed: {e}", file=sys.stderr)
            continue
        for l in items:
            if l.pdf_url and l.plati and not any(x in l.titul_zobrazeny.lower() for x in SKIP_TITLES):
                yield c, l


def download(l, path: Path):
    r = SESSION.get(l.pdf_url, timeout=300, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    path.write_bytes(r.content)
