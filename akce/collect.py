"""Collect offers from all sources -> data/offers/<date>.json (+ tile crops for PDF offers).

    python -m akce.collect [--chains albert,lidl] [--out data] [--crops dist/akce/img]

Sources: chain websites (akce.sources.web) and leaflet PDFs parsed by akce.pdfparse with the chain layout.
A chain is used only when listed in ENABLED (accuracy checked, see README).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import tempfile
from pathlib import Path

import pymupdf

from .layouts import LAYOUTS
from .pdfparse import parse_pdf
from .taxonomy import TYPE_BY_SLUG, brand, classify, norm
from .units import parse_details

ROOT = Path(__file__).resolve().parent.parent

# chains with a verified PDF layout (tools/accuracy.py >= 90 % same price) and web sources
ENABLED_PDF = ["albert", "kaufland", "hruska", "billa", "coop"]
ENABLED_WEB = ["lidl", "penny"]

CHAIN_NAMES = {"albert": "Albert", "kaufland": "Kaufland", "globus": "Globus", "billa": "Billa", "coop": "COOP",
               "norma": "Norma", "hruska": "Hruška", "teta": "Teta", "dm": "dm", "lidl": "Lidl", "penny": "Penny", "tesco": "Tesco"}


def offer_id(o):
    k = f"{o['retezec']}|{norm(o['nazev'])}|{o.get('baleni') or ''}|{o['od']}|{o['do']}|{o['cena']}"
    return hashlib.sha1(k.encode()).hexdigest()[:12]


def enrich(o):
    today = dt.date.today()
    o["od"] = o.get("od") or today.isoformat()
    o["do"] = o.get("do") or (dt.date.fromisoformat(o["od"]) + dt.timedelta(days=6)).isoformat()
    o["retezec_nazev"] = CHAIN_NAMES.get(o["retezec"], o["retezec"].title())
    if o.get("jednotka_text") and not o.get("jednotkova_cena"):
        info = parse_details(o["jednotka_text"])
        o["jednotkova_cena"], o["jednotka"] = info["jc"], info["jedn"]
    o["typ"] = classify(o["nazev"], o.get("detail") or "", o.get("kat_retezce") if o["retezec"] == "lidl" and "Kategorie/" in (o.get("kat_retezce") or "") else None)
    o["kategorie"] = TYPE_BY_SLUG[o["typ"]]["kategorie"] if o["typ"] else None
    o["znacka"] = o.get("znacka") or brand(o["nazev"])
    o["id"] = offer_id(o)
    return o


_IMG_CACHE = {}


def _photos(page):
    """Bounding boxes of embedded raster images (product photos) on a page."""
    key = (id(page.parent), page.number)
    if key not in _IMG_CACHE:
        area = page.rect.width * page.rect.height
        boxes = []
        for info in page.get_image_info():
            b = pymupdf.Rect(info["bbox"]) & page.rect
            if b.is_empty:
                continue
            a = b.width * b.height
            if 0.006 * area < a < 0.22 * area and min(b.width, b.height) > 30 and 0.25 < b.width / b.height < 4:
                boxes.append(b)
        _IMG_CACHE[key] = boxes
    return _IMG_CACHE[key]


def _gap(a, b):
    dx = max(a.x0 - b.x1, 0, b.x0 - a.x1)
    dy = max(a.y0 - b.y1, 0, b.y0 - a.y1)
    return (dx * dx + dy * dy) ** 0.5


def crop(pdf_doc, o, bbox, outdir: Path):
    """Product photo of a PDF offer: the embedded image nearest to the tile; else the tile itself."""
    page = pdf_doc[o["strana"] - 1]
    r = page.rect
    x0, y0, x1, y1 = bbox
    tile = pymupdf.Rect(x0, y0, x1, y1)
    w, h = x1 - x0, y1 - y0
    c = ((x0 + x1) / 2, (y0 + y1) / 2)
    photos = sorted(_photos(page), key=lambda b: ((b.x0 + b.x1) / 2 - c[0]) ** 2 + ((b.y0 + b.y1) / 2 - c[1]) ** 2)
    if photos and _gap(photos[0], tile) < max(30, w * 0.5):
        clip = (photos[0] | tile) & r
        clip = pymupdf.Rect(clip.x0 - 4, clip.y0 - 4, clip.x1 + 4, clip.y1 + 4) & r
    else:
        clip = pymupdf.Rect(max(r.x0, x0 - w * 0.35), max(r.y0, y0 - h * 0.35), min(r.x1, x1 + w * 0.35), min(r.y1, y1 + h * 0.35))
    if clip.width < 20 or clip.height < 20:
        return None
    zoom = min(3.0, 260 / max(clip.width, clip.height))
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=clip)
    name = f"{o['id']}.jpg"
    (outdir / name).write_bytes(pix.tobytes("jpeg", jpg_quality=72))
    return name


def from_pdfs(chains, crops: Path | None):
    from .leaflets import current_leaflets, download
    out = []
    for chain, l in current_leaflets(chains):
        L = LAYOUTS.get(chain)
        if not L:
            continue
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "l.pdf"
            try:
                download(l, f)
            except Exception as e:
                print(f"! {chain} {l.slug}: download failed: {e}", file=sys.stderr)
                continue
            items = parse_pdf(str(f), L, with_bbox=True)
            doc = pymupdf.open(str(f)) if crops else None
            seen = set()
            for it in items:
                k = (norm(it["nazev"]), it["cena"], it.get("baleni"))
                if k in seen:
                    continue
                seen.add(k)
                bbox = it.pop("bbox", None)
                o = {**it, "retezec": chain, "od": l.od.isoformat(), "do": l.do.isoformat(), "zdroj": "letak",
                     "letak_slug": l.slug, "letak_hash": l.hash, "url": f"https://kuponmat.cz/letak/{l.slug}/#strana-{it['strana']}"}
                enrich(o)
                if crops and bbox:
                    try:
                        o["img"] = crop(doc, o, bbox, crops)
                    except Exception as e:
                        print(f"! crop {o['id']}: {e}", file=sys.stderr)
                out.append(o)
            print(f"{chain} {l.slug}: {len(items)} offers", file=sys.stderr)
    return out


def from_web(chains):
    from .sources.web import SOURCES
    out = []
    for c in chains:
        try:
            items = SOURCES[c]()
        except Exception as e:
            print(f"! web {c}: {e}", file=sys.stderr)
            continue
        for o in items:
            o["img_url"] = o.pop("obrazek", None)
            out.append(enrich(o))
        print(f"{c} web: {len(items)} offers", file=sys.stderr)
    return out


def dedupe(offers):
    """Hyper- and supermarket leaflets of one chain repeat offers -> keep one."""
    best = {}
    for o in offers:
        k = (o["retezec"], norm(o["nazev"]), o.get("baleni"), o["cena"], o["od"])
        if k not in best:
            best[k] = o
    return list(best.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chains")
    ap.add_argument("--out", default=str(ROOT / "data"))
    ap.add_argument("--crops")
    a = ap.parse_args()
    want = a.chains.split(",") if a.chains else None
    pdf_chains = [c for c in ENABLED_PDF if not want or c in want]
    web_chains = [c for c in ENABLED_WEB if not want or c in want]
    crops = Path(a.crops) if a.crops else None
    if crops:
        crops.mkdir(parents=True, exist_ok=True)
    offers = dedupe(from_pdfs(pdf_chains, crops) + from_web(web_chains))
    today = dt.date.today().isoformat()
    offers = [o for o in offers if (o.get("do") or today) >= today]
    od = Path(a.out) / "offers"
    od.mkdir(parents=True, exist_ok=True)
    (od / f"{today}.json").write_text(json.dumps(offers, ensure_ascii=False, indent=0))
    print(f"total {len(offers)} offers -> {od / (today + '.json')}", file=sys.stderr)


if __name__ == "__main__":
    main()
