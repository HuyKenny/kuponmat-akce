"""Download current leaflet PDFs of chains (dev / reference work).

    python -m tools.fetch_pdfs <outdir> [chain ...]
Saves <outdir>/<chain>/<leaflet-slug>.pdf
"""
import sys
from pathlib import Path

from akce.leaflets import current_leaflets, download

out = Path(sys.argv[1])
for chain, l in current_leaflets(sys.argv[2:] or None):
    d = out / chain
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{l.slug}.pdf"
    if not f.exists():
        download(l, f)
    print(chain, l.slug, l.od, l.do, f.stat().st_size)
