"""One-off: fill data/history.json with daily lowest promo prices from older extraction outputs
(ai/reports/kuponmat-akce/<date>/<chain>-<leaflet>.json, 12. 10. – 18. 11. 2026), so price charts have weeks of data at launch.

    python -m tools.backfill_history <reports-dir> <history.json>

Existing dates in history.json are never overwritten (live data wins).
"""
import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path

from akce.collect import CHAIN_NAMES
from akce.taxonomy import BRAND_ALIAS, TYPE_BY_SLUG, brand, classify, slugify

reports, hist_path = Path(sys.argv[1]), Path(sys.argv[2])
history = json.loads(hist_path.read_text()) if hist_path.exists() else {}
names = history.setdefault("_names", {})

leaflets = {}   # leaflet file name -> latest version (re-read leaflets: newest folder wins)
for f in sorted(reports.glob("*/*.json")):
    leaflets[f.name] = f
days = defaultdict(lambda: defaultdict(dict))   # day -> key -> chain -> min price
for f in leaflets.values():
    d = json.loads(f.read_text())
    try:
        od, do = dt.date.fromisoformat(d["od"]), dt.date.fromisoformat(d["do"])
    except (KeyError, ValueError):
        continue
    chain = CHAIN_NAMES.get(d.get("obchod"), d.get("obchod_nazev") or d.get("obchod"))
    for it in d.get("items", []):
        cena = it.get("cena")
        if not isinstance(cena, (int, float)) or cena <= 0:
            continue
        typ = classify(it.get("nazev") or "") or (it.get("kategorie") if it.get("kategorie") in TYPE_BY_SLUG else None)
        if not typ:
            continue
        keys = [typ]
        b = brand(it.get("nazev") or "")
        if b:
            b = BRAND_ALIAS.get(b, b)
            k = f"{typ}-{slugify(b)}"
            keys.append(k)
            t = TYPE_BY_SLUG[typ]
            names.setdefault(k, f"{t['nazev'].split(' a ')[0]} {b}" if typ not in ("nealko", "pivo", "vino") else b)
        day = od
        while day <= do:
            ds = day.isoformat()
            for k in keys:
                cur = days[ds][k].get(chain)
                if cur is None or cena < cur:
                    days[ds][k][chain] = cena
            day += dt.timedelta(days=1)

added = 0
today = dt.date.today().isoformat()
for ds, keys in days.items():
    if ds >= today:
        continue
    for k, v in keys.items():
        h = history.setdefault(k, {})
        if ds not in h:
            h[ds] = v
            added += 1
hist_path.write_text(json.dumps(history, ensure_ascii=False, separators=(",", ":")))
print(f"added {added} key-days, {len(days)} days, keys {len([k for k in history if k != '_names'])}")
