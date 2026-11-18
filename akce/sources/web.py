"""Promo offers published as structured data on the chains' own websites (no AI, no PDF).

* Lidl  — campaign pages /c/<name>/a<id> carry every product as JSON in `data-grid-data`
          (title, price, old price, discount, packaging, unit price, validity, image).
* Penny — /category/vsechny-akce-99000000 is a Nuxt page; `__NUXT_DATA__` holds the products
          (price in hellers, crossed price, Penny card price, validity, image).
Only publicly served pages are read, politely (one request at a time, pauses). A 403 / block is
reported and skipped, never worked around.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import sys
import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (compatible; KuponmatAkce/1.0; +https://kuponmat.cz/akce/)", "Accept-Language": "cs-CZ,cs;q=0.9"}
S = requests.Session()
S.headers.update(UA)


def _get(url):
    for i in range(3):
        try:
            r = S.get(url, timeout=60)
            if r.status_code == 200:
                return r.text
            print(f"! {url}: HTTP {r.status_code}", file=sys.stderr)
            if r.status_code in (403, 404, 410):
                return None
        except requests.RequestException as e:
            print(f"! {url}: {e}", file=sys.stderr)
        time.sleep(3 * (i + 1))
    return None


def _date(s):
    if not s:
        return None
    if isinstance(s, (int, float)):
        return dt.datetime.fromtimestamp(s, dt.timezone.utc).astimezone().date().isoformat()
    s = str(s)
    if "T" in s:
        d = dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(dt.timezone(dt.timedelta(hours=1)))
        return d.date().isoformat()
    return s[:10]


# ---------------------------------------------------------------- Lidl
LIDL = "https://www.lidl.cz"


def lidl_pages():
    t = _get(LIDL + "/") or ""
    pages = set(re.findall(r'href="(/c/[a-z0-9-]+(?:/[a-z0-9-]+)?/a1\d{7})"', t))
    extra = _get(LIDL + "/c/akcni-letak/s10008644") or ""
    pages |= set(re.findall(r'href="(/c/[a-z0-9-]+(?:/[a-z0-9-]+)?/a1\d{7})"', extra))
    return sorted(pages)


def lidl():
    out, seen = [], set()
    today = dt.date.today().isoformat()
    for p in lidl_pages():
        t = _get(LIDL + p)
        time.sleep(1.0)
        if not t:
            continue
        for m in re.finditer(r'data-grid-data="([^"]*)"', t):
            try:
                d = json.loads(html.unescape(m.group(1)))
            except ValueError:
                continue
            pid = d.get("productId")
            if pid in seen:
                continue
            reg = (d.get("regionsPrices") or {}).get("1", {}).get("currentPrice") or d.get("price") or {}
            price = reg.get("price")
            if not price:
                continue
            disc = reg.get("discount") or {}
            old = reg.get("oldPrice") or disc.get("deletedPrice")
            do = _date(reg.get("endDate")) or _date(d.get("storeEndDate"))
            od = _date(reg.get("startDate")) or _date(d.get("storeStartDate"))
            if do and do < today:
                continue
            if not old and not disc.get("percentageDiscount"):
                continue          # regular assortment shown on a campaign page, not a promo
            seen.add(pid)
            img = ""
            for il in d.get("imageList_V2") or []:
                for v in il.get("variants", []):
                    img = img or (v.get("sizes") or {}).get("mediumUrl", "")
            img = img or d.get("image") or ""
            base = ((reg.get("basePrice") or {}).get("text") or "")
            cond = []
            if disc.get("fromNormalPriceForLidlPlus") or "lidl plus" in json.dumps(disc, ensure_ascii=False).lower():
                cond.append("s aplikací Lidl Plus")
            out.append({
                "retezec": "lidl",
                "nazev": d.get("fullTitle") or d.get("title"),
                "znacka": (d.get("brand") or {}).get("name") if isinstance(d.get("brand"), dict) else None,
                "baleni": ((reg.get("packaging") or {}).get("text") or "").strip() or None,
                "cena": float(price),
                "cena_bez": None,
                "puvodni_cena": float(old) if old else None,
                "sleva_pct": disc.get("percentageDiscount") or None,
                "jednotka_text": base or None,
                "podminka": "; ".join(cond) or None,
                "od": od, "do": do,
                "zdroj": "web",
                "url": LIDL + (d.get("canonicalUrl") or ""),
                "obrazek": img,
                "kat_retezce": (d.get("keyfacts") or {}).get("analyticsCategory"),
            })
    return out


# ---------------------------------------------------------------- Penny
PENNY = "https://www.penny.cz"


def _nuxt(t):
    m = re.search(r'id="__NUXT_DATA__"[^>]*>(.*?)</script>', t, re.S)
    if not m:
        return []
    a = json.loads(m.group(1))

    def r(i, d=0):
        v = a[i] if isinstance(i, int) and 0 <= i < len(a) else i
        if d > 7:
            return v
        if isinstance(v, dict):
            return {k: r(x, d + 1) for k, x in v.items()}
        if isinstance(v, list) and v and v[0] in ("Reactive", "ShallowReactive", "Ref", "ShallowRef"):
            return r(v[1], d + 1)
        if isinstance(v, list):
            return [r(x, d + 1) for x in v]
        return v
    return [r(i) for i, v in enumerate(a) if isinstance(v, dict) and "sku" in v and "price" in v]


def _penny_unit(pr, block):
    """Penny gives the price per `basePriceFactor` × base unit (e.g. per 100 g) -> per kg / l / ks."""
    v = (block or {}).get("perStandardizedQuantity")
    u = (pr.get("baseUnitShort") or "").lower()
    try:
        f = float(pr.get("basePriceFactor") or 1)
    except ValueError:
        f = 1
    if not v or u not in ("g", "ml", "kg", "l", "ks"):
        return {"jednotkova_cena": None, "jednotka": None}
    v = v / 100
    if u in ("g", "ml"):
        return {"jednotkova_cena": round(v * 1000 / f, 2), "jednotka": "kg" if u == "g" else "l"}
    return {"jednotkova_cena": round(v / f, 2), "jednotka": u}


def penny():
    out, seen = [], set()
    page = 1
    while page < 30:
        t = _get(f"{PENNY}/category/vsechny-akce-99000000" + (f"?page={page}" if page > 1 else ""))
        time.sleep(1.0)
        if not t:
            break
        prods = _nuxt(t)
        new = [p for p in prods if p["sku"] not in seen]
        if not new:
            break
        for p in new:
            seen.add(p["sku"])
            pr = p.get("price") or {}
            reg = pr.get("regular") or {}
            loy = pr.get("loyalty") or {}
            val = reg.get("value")
            if not val:
                continue
            cena, cena_bez, cond = val / 100, None, []
            if loy.get("value") and loy["value"] < val:
                cena, cena_bez = loy["value"] / 100, val / 100
                cond.append("s PENNY kartou")
            if (reg.get("promotionQuantity") or 1) > 1:
                cond.append(f"při koupi {reg['promotionQuantity']} ks")
            old = (pr.get("crossed") or 0) / 100 or None
            amount = p.get("amount")
            unit = p.get("volumeLabelShort") or ""
            baleni = f"{amount} {unit}".strip() if amount and unit and p.get("packageLabelKey") != "kg" else (p.get("descriptionShort") or None)
            img = (p.get("images") or [""])[0]
            out.append({
                "retezec": "penny",
                "nazev": p.get("name"),
                "znacka": p.get("brandMarketing") or None,
                "baleni": baleni,
                "cena": cena,
                "cena_bez": cena_bez,
                "puvodni_cena": old if old and old > cena else None,
                "sleva_pct": abs(pr.get("discountPercentage") or 0) or None,
                **_penny_unit(pr, cena == val / 100 and reg or loy or reg),
                "jednotka_text": None,
                "podminka": "; ".join(cond) or None,
                "od": pr.get("validityStart"), "do": pr.get("validityEnd"),
                "zdroj": "web",
                "url": f"{PENNY}/produkty/{p.get('slug')}",
                "obrazek": img,
                "kat_retezce": p.get("category"),
            })
        page += 1
    return out


SOURCES = {"lidl": lidl, "penny": penny}
