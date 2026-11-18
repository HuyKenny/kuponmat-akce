"""Compare parser output with a reference (old AI extraction of the same leaflet, reports/kuponmat-akce/...).

    python -m tools.accuracy <chain> <leaflet.pdf> <reference.json>

Reference lists only items of 32 product categories, so this measures RECALL on those and price accuracy
of matched items; precision of the rest is checked by hand (tools.try_pdf + page render).
"""
import json, re, sys, unicodedata

from akce.layouts import LAYOUTS
from akce.pdfparse import parse_pdf


def toks(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return {t for t in re.findall(r"[a-z]{3,}", s)}


def main():
    chain, pdf, ref = sys.argv[1:4]
    R = json.load(open(ref))["items"]
    P = parse_pdf(pdf, LAYOUTS[chain])
    found = same = 0
    miss = []
    bad = []
    for r in R:
        cands = [p for p in P if p["strana"] == r.get("strana")]
        best, bs = None, 0
        for p in cands:
            a, b = toks(r["nazev"]), toks(p["nazev"] + " " + p["detail"])
            sc = len(a & b) / max(1, len(a))
            if sc > bs:
                best, bs = p, sc
        if best and bs >= 0.5:
            found += 1
            if abs(best["cena"] - r["cena"]) < 0.011 or (r.get("cena_bez") and abs(best["cena"] - r["cena_bez"]) < 0.011):
                same += 1
            else:
                bad.append((r["strana"], r["nazev"], r["cena"], best["nazev"], best["cena"]))
        else:
            miss.append((r.get("strana"), r["nazev"], r["cena"]))
    print(f"parser offers {len(P)} | reference {len(R)} | matched {found} ({found/len(R):.0%}) | same price {same} ({same/max(1,found):.0%} of matched)")
    if "-v" in sys.argv:
        print("\nWRONG PRICE:"); [print(" ", b) for b in bad[:40]]
        print("\nMISSING:"); [print(" ", m) for m in miss[:40]]


main()
