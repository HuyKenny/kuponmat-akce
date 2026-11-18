# kuponmat-akce

Static section **kuponmat.cz/akce/** — what is on promo this week in Czech supermarkets (like Kupi.cz), built **without AI**:

- **Leaflet PDFs** (Albert, Kaufland, Billa, COOP Cena, Hruška, …): the PDF text layer is read with PyMuPDF; per-chain
  layout rules (`akce/chains/<chain>.py`) tell title / detail / price fonts apart, tiles are rebuilt by matching every title
  block with its price (Hungarian assignment, checked against the printed unit price). Product image = crop of the tile.
- **Chain websites with structured data**: Lidl (`data-grid-data` JSON), Penny (`__NUXT_DATA__`).
- **Taxonomy** (`akce/taxonomy.py`): keyword rules -> 22 categories, ~65 product types, brand pages (`/akce/cokolada-milka/`).
- **Pages**: hub, categories, product types, brands, chains, search (client side, `index.json`), favourites + shopping list
  (localStorage), price history chart (SVG), FAQ + JSON-LD, `sitemap.xml`.

Not possible without AI/OCR: image-only leaflets (Lidl PDF, Penny PDF, COOP Tip/Tuty, JIP, Rossmann…) and Tesco
(its PDF font has a scrambled encoding). Kaufland/Tesco websites answer 403 — never worked around.

## Run
```
pip install -r requirements.txt
python -m akce.collect --crops data/img      # offers -> data/offers/<date>.json
python -m akce.build                        # -> dist/akce (needs cache/shell.html = a kuponmat.cz page)
python -m tools.health dist
```
GitHub Actions (`.github/workflows/akce.yml`): full run 03:10, light run 07:40, `quick` = rebuild only.
Data (offers snapshots, price history, crops) live in the `data` branch.

## Adding / fixing a chain
`python -m tools.try_pdf <chain> <pdf> [page]` prints parsed offers, `python -m tools.accuracy <chain> <pdf> <reference.json> -v`
compares with a reference. Enable a chain in `akce/collect.py` (`ENABLED_PDF`) only with >= 90 % same price.
Leaflet adapters in `akce/letaky/` are copies of `ai/scripts/kuponmat/letaky` (kuponmat.cz/letaky) — keep them in sync.
