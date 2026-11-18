"""Parse one leaflet PDF with a chain layout and print the offers (dev tool).

    python -m tools.try_pdf albert path/to/file.pdf [page ...]
"""
import sys

from akce.layouts import LAYOUTS
from akce.pdfparse import parse_pdf

chain, path, *pages = sys.argv[1:]
items = parse_pdf(path, LAYOUTS[chain], [int(p) for p in pages] or None)
for i in items:
    print(f"{i['strana']:3} {i['cena']:8.2f} {str(i['cena_bez'] or ''):7} {str(i['puvodni_cena'] or ''):7} {str(i['sleva_pct'] or ''):3} | {i['nazev'][:45]:45} | {i['baleni'] or ''} | {i['jednotkova_cena'] or ''}/{i['jednotka'] or ''} | {i['podminka'] or ''}")
print(len(items), "offers")
