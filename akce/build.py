"""Static site for kuponmat.cz/akce/ from data/offers/<latest>.json (+ data/history.json).

    python -m akce.build [--data data] [--shell cache/shell.html] [--out dist] [--today 2026-11-18]

Pages (Kupi.cz-like):
  /akce/                         hub: search, categories, biggest discounts, chains
  /akce/kategorie/<cat>/         category: product types + offers
  /akce/<type>/                  product type (keeps the 32 original slugs: cokolada, maslo, …)
  /akce/<type>-<brand>/          product of a brand (cokolada-milka)
  /akce/obchod/<chain>/          everything on promo at one chain
  /akce/hledat/                  client-side search (index.json)
  /akce/oblibene/                favourites + shopping list (localStorage)
  /akce/sitemap.xml
Header/footer come from a live kuponmat.cz page (shell), so the section looks like the rest of the site.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .taxonomy import BRAND_ALIAS, CAT_NAME, CATEGORIES, TYPE_BY_SLUG, TYPES, norm, slugify

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://kuponmat.cz"
BASE = "/akce/"
MONTHS = ["", "ledna", "února", "března", "dubna", "května", "června", "července", "srpna", "září", "října", "listopadu", "prosince"]
LETAK_CHAINS = {"albert", "kaufland", "globus", "billa", "coop", "norma", "hruska", "teta", "lidl", "penny", "tesco", "dm"}
MIN_BRAND_OFFERS = 1


def kc(v):
    if v is None:
        return ""
    s = f"{v:,.2f}".replace(",", " ").replace(".", ",")
    s = s[:-3] if s.endswith(",00") else s
    return s.replace(" ", " ") + " Kč"


def d_short(iso):
    d = dt.date.fromisoformat(iso)
    return f"{d.day}. {d.month}."


def d_long(iso):
    d = dt.date.fromisoformat(iso)
    return f"{d.day}. {MONTHS[d.month]} {d.year}"


def plural(n, one, few, many):
    return one if n == 1 else few if 2 <= n <= 4 else many


class Shell:
    """Header/footer of a live kuponmat.cz page with its SEO tags removed."""

    def __init__(self, path: Path):
        t = path.read_text(encoding="utf-8")
        head_end = t.index("</head>")
        head = t[:head_end]
        head = re.sub(r"<title>.*?</title>", "", head, flags=re.S)
        head = re.sub(r'<meta (?:name|property)="(?:description|robots|og:[^"]*|twitter:[^"]*|article:[^"]*)"[^>]*>\s*', "", head)
        head = re.sub(r'<link rel="(?:canonical|alternate|shortlink|next|prev)"[^>]*>\s*', "", head)
        head = re.sub(r'<script type="application/ld\+json"[^>]*>.*?</script>\s*', "", head, flags=re.S)
        self.head = head
        body_start = t.index("<body", head_end)
        main_start = t.index("<main", body_start)
        main_end = t.index("</main>", main_start) + len("</main>")
        body_tag = re.match(r"<body[^>]*>", t[body_start:]).group(0)
        body = t[body_start + len(body_tag):main_start]
        # the shell comes from /letaky/ -> move the "current" menu state from Letáky to Akce
        body = re.sub(r"\s(?:current-menu-item|current_page_item|current-menu-ancestor|current_page_parent)\b", "", body)
        body = body.replace(' aria-current="page"', "")
        body = re.sub(r'(<li[^>]*class=")([^"]*)("[^>]*>\s*<a[^>]*href="https://kuponmat\.cz/akce/")',
                      lambda m: m.group(1) + m.group(2) + " current-menu-item" + m.group(3).replace("<a", '<a aria-current="page"', 1), body, count=1)
        self.body_open = '<body class="km-akce-static">' + body
        self.foot = t[main_end:]


class Site:
    def __init__(self, offers, history, today, shell, out):
        self.today = today
        self.offers = offers
        self.history = history
        self.shell = shell
        self.out = out
        self.env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=select_autoescape(["html"]))
        self.env.filters.update(kc=kc, d_short=d_short, d_long=d_long)
        kat = ROOT / "static" / "kat"
        cat_img = {p.stem: f"{BASE}kat/{p.name}" for p in kat.glob("*.jpg")} if kat.exists() else {}
        self.env.globals.update(BASE=BASE, SITE=SITE, CAT_NAME=CAT_NAME, plural=plural, today=today, cat_img=cat_img)
        self.pages = []   # (path, indexable)

    # ------------------------------------------------------------ helpers
    def state(self, o):
        if o["od"] > self.today:
            return "budouci"
        if o["do"] == self.today:
            return "konci"
        return "plati"

    def card(self, o):
        img = None
        if o.get("img"):
            img = f"{BASE}img/{o['img']}"
        elif o.get("img_url"):
            img = o["img_url"]
        link = o.get("url") or ""
        return {**o, "stav": self.state(o), "img_src": img, "link": link,
                "link_label": (f"Leták, str. {o['strana']}" if o.get("zdroj") == "letak" else f"Na webu {o['retezec_nazev']}"),
                "key": o.get("produkt") or o.get("typ") or "", "days_left": (dt.date.fromisoformat(o["do"]) - dt.date.fromisoformat(self.today)).days}

    def sort_offers(self, items):
        return sorted(items, key=lambda o: (o["od"] > self.today, o.get("jednotkova_cena") or 1e9 if False else 0, o["cena"]))

    def render(self, path, tpl, indexable=True, **ctx):
        ctx.setdefault("robots", "index, follow" if indexable else "noindex, follow")
        ctx["canonical"] = SITE + path
        ctx["shell"] = self.shell
        page = self.env.get_template(tpl).render(**ctx)
        f = self.out / path.lstrip("/") / "index.html"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(page, encoding="utf-8")
        self.pages.append((path, indexable))

    def chart(self, key):
        """Static SVG: daily lowest promo price per chain (last 180 days)."""
        h = self.history.get(key) or {}
        days = sorted(h)[-180:]
        if len(days) < 2:
            return None
        chains = sorted({c for d in days for c in h[d]})
        vals = [v for d in days for v in h[d].values()]
        lo, hi = min(vals), max(vals)
        if hi - lo < 0.01:
            hi = lo + 1
        W, H, P = 640, 220, 34
        d0, d1 = dt.date.fromisoformat(days[0]), dt.date.fromisoformat(days[-1])
        span = max(1, (d1 - d0).days)
        colors = ["#e4002b", "#0050aa", "#00843d", "#f39200", "#7a2e8e", "#00a0b0", "#6b6b6b", "#c8102e", "#004b87", "#8a6d00"]
        lines = []
        for i, c in enumerate(chains):
            pts = []
            for d in days:
                if c in h[d]:
                    x = P + (dt.date.fromisoformat(d) - d0).days / span * (W - 2 * P)
                    y = H - P - (h[d][c] - lo) / (hi - lo) * (H - 2 * P)
                    pts.append(f"{x:.1f},{y:.1f}")
            if pts:
                lines.append({"chain": c, "color": colors[i % len(colors)], "pts": " ".join(pts), "last": pts[-1].split(",")})
        return {"W": W, "H": H, "P": P, "lines": lines, "lo": lo, "hi": hi, "d0": days[0], "d1": days[-1]}

    # ------------------------------------------------------------ build
    def build(self):
        cur = [o for o in self.offers if o["do"] >= self.today]
        for o in cur:
            if o.get("typ") and o.get("znacka") and slugify(o["znacka"]):
                o["produkt"] = f"{o['typ']}-{slugify(o['znacka'])}"
        by_type, by_cat, by_chain, by_prod = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
        for o in cur:
            by_chain[o["retezec"]].append(o)
            if o.get("typ"):
                by_type[o["typ"]].append(o)
                by_cat[o["kategorie"]].append(o)
            if o.get("produkt"):
                by_prod[o["produkt"]].append(o)
        self.by_type, self.by_prod = by_type, by_prod
        chain_names = {o["retezec"]: o["retezec_nazev"] for o in self.offers}
        chains = sorted(by_chain, key=lambda c: -len(by_chain[c]))

        # product (type + brand) pages
        prods = {}
        for k, items in by_prod.items():
            if len(items) >= MIN_BRAND_OFFERS:
                t = TYPE_BY_SLUG[items[0]["typ"]]
                prods[k] = {"slug": k, "nazev": f"{t['nazev'].split(' a ')[0]} {items[0]['znacka']}" if t["slug"] not in ("nealko", "pivo", "vino") else f"{items[0]['znacka']}",
                            "typ": t, "znacka": items[0]["znacka"], "items": items}
        self.prods = prods
        # also keep pages of products seen in history (no current offer) -> noindex "není ve slevě"
        hist_prods = {k for k in self.history if k not in prods and "-" in k and k.split("-")[0] and k not in TYPE_BY_SLUG}

        for t in TYPES:
            items = by_type.get(t["slug"], [])
            if not items and t["slug"] not in self.history:
                continue
            sub = sorted([p for p in prods.values() if p["typ"]["slug"] == t["slug"]], key=lambda p: -len(p["items"]))
            cc = Counter(o["retezec"] for o in items)
            tlinks = [(f"{BASE}{t['slug']}/{c}/", chain_names[c], n) for c, n in cc.most_common() if n >= 3]
            self.listing_page(BASE + t["slug"] + "/", items, title=t["nazev"], h=t["h"], typ=t, products=sub, chain_links=tlinks,
                              crumbs=[("Akce", BASE), (CAT_NAME[t["kategorie"]], f"{BASE}kategorie/{t['kategorie']}/"), (t["nazev"], "")],
                              history_key=t["slug"], related=[x for x in TYPES if x["kategorie"] == t["kategorie"] and x["slug"] != t["slug"] and by_type.get(x["slug"])])
        for k, p in prods.items():
            t = p["typ"]
            self.listing_page(BASE + k + "/", p["items"], title=p["nazev"], h=p["nazev"], typ=t, products=[], brand=p["znacka"],
                              crumbs=[("Akce", BASE), (t["nazev"], BASE + t["slug"] + "/"), (p["nazev"], "")], history_key=k,
                              related=sorted([q for q in prods.values() if q["typ"]["slug"] == t["slug"] and q["slug"] != k], key=lambda q: -len(q["items"]))[:16])
        for k in hist_prods:
            t = TYPE_BY_SLUG.get(k.split("-")[0]) or next((x for x in TYPES if k.startswith(x["slug"] + "-")), None)
            if not t:
                continue
            nm = self.history.get("_names", {}).get(k, k.replace("-", " ").title())
            self.listing_page(BASE + k + "/", [], title=nm, h=nm, typ=t, products=[], crumbs=[("Akce", BASE), (t["nazev"], BASE + t["slug"] + "/"), (nm, "")],
                              history_key=k, related=[])

        MIN_X = 3   # category x chain / type x chain page only with enough offers (no thin pages)
        for cs, cn in CATEGORIES:
            items = by_cat.get(cs, [])
            if not items:
                continue
            types = [dict(t, n=len(by_type[t["slug"]])) for t in TYPES if t["kategorie"] == cs and by_type.get(t["slug"])]
            per = defaultdict(list)
            for o in items:
                per[o["retezec"]].append(o)
            links = [(f"{BASE}kategorie/{cs}/{c}/", chain_names[c], len(v)) for c, v in sorted(per.items(), key=lambda kv: -len(kv[1])) if len(v) >= MIN_X]
            self.listing_page(f"{BASE}kategorie/{cs}/", items, title=cn, h=cn.lower(), typ=None, products=[], types=types, category=cs,
                              crumbs=[("Akce", BASE), (cn, "")], history_key=None, related=[], chain_links=links)
            for c, v in per.items():
                if len(v) >= MIN_X:
                    self.listing_page(f"{BASE}kategorie/{cs}/{c}/", v, title=f"{cn} {chain_names[c]}", h=f"{cn.lower()} v {chain_names[c]}",
                                      typ=None, products=[], category=cs, crumbs=[("Akce", BASE), (cn, f"{BASE}kategorie/{cs}/"), (chain_names[c], "")],
                                      history_key=None, related=[], chain_links=[l for l in links if l[1] != chain_names[c]])
        for t in TYPES:
            per = defaultdict(list)
            for o in by_type.get(t["slug"], []):
                per[o["retezec"]].append(o)
            for c, v in per.items():
                if len(v) >= MIN_X:
                    self.listing_page(f"{BASE}{t['slug']}/{c}/", v, title=f"{t['nazev']} {chain_names[c]}", h=f"{t['h']} v {chain_names[c]}", typ=t,
                                      products=[], crumbs=[("Akce", BASE), (t["nazev"], f"{BASE}{t['slug']}/"), (chain_names[c], "")],
                                      history_key=None, related=[])
        for c in chains:
            cn = chain_names[c]
            self.listing_page(f"{BASE}obchod/{c}/", by_chain[c], title=f"Akce {cn}", h=f"akce {cn}", typ=None, products=[], chain=c, chain_name=cn,
                              crumbs=[("Akce", BASE), (cn, "")], history_key=None, related=[], group_by_cat=True)

        top = sorted([o for o in cur if o.get("sleva_pct") and o["od"] <= self.today and o.get("typ")], key=lambda o: -o["sleva_pct"])
        seen, top_u = set(), []
        for o in top:
            if o["typ"] in seen:
                continue
            seen.add(o["typ"]); top_u.append(self.card(o))
        cats = [{"slug": cs, "nazev": cn, "n": len(by_cat.get(cs, [])),
                 "types": [t for t in TYPES if t["kategorie"] == cs and by_type.get(t["slug"])]} for cs, cn in CATEGORIES if by_cat.get(cs)]
        popular = sorted(prods.values(), key=lambda p: -len(p["items"]))[:40]
        cn = [chain_names[c] for c in chains]
        week_end = max((o["do"] for o in cur if o["od"] <= self.today), default=self.today)
        faq = [
            ("Které obchody máte v přehledu akcí?", f"Tento týden: {', '.join(f'{chain_names[c]} ({len(by_chain[c])})' for c in chains)}. "
             "Letáky čteme každý den, nové akce se objeví zpravidla ve středu a ve čtvrtek ráno."),
            ("Jak najdu nejlevnější nabídku?", "Otevřete druh zboží (např. máslo nebo pivo) a seřaďte nabídky podle ceny za kg/l – tak porovnáte i různě velká balení. "
             "Filtrem nahoře zobrazíte jen jeden obchod."),
            ("Do kdy aktuální akce platí?", f"Většina letáků tohoto týdne platí do {d_long(week_end)}; přesné datum je u každé nabídky. Akce, které teprve začnou, jsou v části Budoucí akce."),
            ("Co znamená cena s aplikací nebo kartou?", "Řada řetězců dává nejnižší cenu jen členům věrnostního programu. Takovou cenu ukazujeme jako akční a pod ní uvádíme i cenu bez karty."),
        ]
        schema = {"@context": "https://schema.org", "@graph": [
            {"@type": "CollectionPage", "name": "Akce v letácích", "url": SITE + BASE, "isPartOf": {"@type": "WebSite", "name": "KupónMat", "url": SITE + "/"},
             "hasPart": [{"@type": "WebPage", "name": c["nazev"], "url": f"{SITE}{BASE}kategorie/{c['slug']}/"} for c in cats]},
            {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q, a_ in faq]}]}
        self.render(BASE, "hub.html", title=f"Akce v letácích tento týden – {len(cur)} slev v {', '.join(cn[:4])}",
                    description=f"Co je tento týden v akci? {len(cur)} akčních nabídek z letáků {', '.join(cn)} podle produktů: ceny za kg, platnost do {d_short(week_end)} a srovnání obchodů.",
                    cats=cats, top=top_u[:24], chains=[(c, chain_names[c], len(by_chain[c])) for c in chains], n=len(cur), popular=popular,
                    faq=faq, schema=schema, og_image=SITE + BASE + "kat/mlecne-vyrobky-a-vejce.jpg")
        self.render(BASE + "hledat/", "search.html", indexable=False, title="Hledat v akcích", description="Vyhledávání v aktuálních akcích z letáků.")
        self.render(BASE + "oblibene/", "favorites.html", indexable=False, title="Oblíbené a nákupní seznam", description="Vaše oblíbené produkty a nákupní seznam z akcí.")
        self.write_index(cur)
        self.write_sitemap()

    STOP = {"vybrane", "druhy", "ruzne", "druhu", "vice", "chlazene", "chlazena", "chlazeny", "baleni", "kus", "ks", "akce", "cena", "nase"}

    def core_name(self, o):
        """Normalized product line without sizes / 'vybrané druhy' -> groups the same product of a no-brand offer."""
        w = [x for x in re.findall(r"[a-z]{3,}", norm(o["nazev"])) if x not in self.STOP]
        return " ".join(w[:3])

    def product_groups(self, offers):
        """Kupi-like view: one block per product (type+brand, else same line name) with all chains' offers under it."""
        g = defaultdict(list)
        for o in offers:
            g[o.get("produkt") or f"{o.get('typ') or 'x'}|{self.core_name(o)}"].append(o)
        out = []
        for k, items in g.items():
            items = sorted(items, key=lambda o: o["cena"])
            p = self.prods.get(k)
            img_o = next((o for o in items if o.get("img") or o.get("img_url")), items[0])
            units = [o for o in items if o.get("jednotkova_cena") and o.get("jednotka")]
            out.append({
                "key": k, "nazev": p["nazev"] if p else items[0]["nazev"], "url": f"{BASE}{k}/" if p else None,
                "img": self.card(img_o)["img_src"], "od": items[0]["cena"], "do": max(o["cena"] for o in items),
                "chains": sorted({o["retezec_nazev"] for o in items}), "n": len(items),
                "unit": min(units, key=lambda o: o["jednotkova_cena"]) if units else None,
                "rows": [self.card(o) for o in items[:12]],
            })
        out.sort(key=lambda x: (-len(x["chains"]), -x["n"], x["od"]))
        return out

    def listing_page(self, path, items, *, title, h, typ, products, crumbs, history_key, related, types=None, category=None,
                     chain=None, chain_name=None, brand=None, group_by_cat=False, chain_links=None):
        now = [o for o in items if o["od"] <= self.today]
        fut = [o for o in items if o["od"] > self.today]
        now = sorted(now, key=lambda o: (o["cena"] if not o.get("jednotkova_cena") else o["cena"], o["retezec"]))
        fut = sorted(fut, key=lambda o: o["cena"])
        chains = Counter(o["retezec_nazev"] for o in items)
        cheapest = min(now, key=lambda o: o["cena"]) if now else None
        unit = [o for o in now if o.get("jednotkova_cena") and o.get("jednotka")]
        best_unit = min(unit, key=lambda o: o["jednotkova_cena"]) if unit else None
        od = min([o["od"] for o in now], default=None)
        do = max([o["do"] for o in now], default=None)
        indexable = bool(now) and (brand is None or len(now) >= 2)
        if chain:
            seo_title = f"{title}: {len(now)} {plural(len(now), 'nabídka', 'nabídky', 'nabídek')} z letáku" + (f" | do {d_short(do)}" if do else "")
        elif cheapest:
            seo_title = f"{title} v akci: od {kc(cheapest['cena'])} | {d_short(od)}–{d_short(do)}"
        else:
            seo_title = f"{title} v akci – aktuálně není ve slevě"
        if cheapest and not chain:
            desc = (f"{title} v akci tento týden: {len(now)} {plural(len(now), 'nabídka', 'nabídky', 'nabídek')} v {', '.join(list(chains)[:5])}. "
                    f"Nejlevněji {kc(cheapest['cena'])} ({cheapest['nazev']}, {cheapest['retezec_nazev']}), platí do {d_short(do)}.")
        elif chain:
            desc = f"Všechny akce {chain_name} na jednom místě: {len(now)} akčních nabídek z aktuálního letáku, ceny za kg a platnost."
        else:
            desc = f"{title}: momentálně v žádném letáku v akci. Podívejte se na poslední akční ceny a nastavte si hlídání v oblíbených."
        groups = None
        if group_by_cat:
            g = defaultdict(list)
            for o in now:
                g[o.get("kategorie") or "ostatni"].append(self.card(o))
            groups = [(CAT_NAME.get(k, "Ostatní"), k, sorted(v, key=lambda c: -(c.get("sleva_pct") or 0))[:36], len(v))
                      for k, v in sorted(g.items(), key=lambda kv: [c for c, _ in CATEGORIES].index(kv[0]) if kv[0] in CAT_NAME else 99)]
        faq = []
        if cheapest and not chain:
            faq.append((f"Kde je teď {h} v akci nejlevněji?", f"Nejnižší akční cena je {kc(cheapest['cena'])} – {cheapest['nazev']} v {cheapest['retezec_nazev']}"
                        + (f", platí do {d_long(cheapest['do'])}." if cheapest.get("do") else ".")
                        + (f" V přepočtu na {best_unit['jednotka']} vychází nejlépe {best_unit['nazev']} ({best_unit['retezec_nazev']}) za {kc(best_unit['jednotkova_cena'])}/{best_unit['jednotka']}." if best_unit else "")))
            faq.append((f"Ve kterých obchodech je {h} v akci?", "Tento týden v: " + ", ".join(f"{c} ({n})" for c, n in chains.most_common()) + "."))
        if do:
            faq.append(("Do kdy akce platí?", f"Nejdéle platí do {d_long(do)}. U každé nabídky je uvedeno její datum; nabídky, které ještě nezačaly, jsou v části Budoucí akce."))
        faq.append(("Odkud ceny jsou?", "Z aktuálních letáků řetězců a z jejich webů. U každé nabídky je odkaz na stranu letáku nebo na produkt na webu obchodu. Ceny nezaručujeme, před nákupem je ověřte v prodejně."))
        seo_text, seo_h2 = [], ""
        if now:
            disc = [o["sleva_pct"] for o in now if o.get("sleva_pct")]
            brands = Counter(o["znacka"] for o in now if o.get("znacka"))
            top_chain = chains.most_common(1)[0]
            seo_h2 = f"{title} v akci: přehled tohoto týdne" if not chain else f"Co je v akci v {chain_name}"
            p1 = (f"Tento týden je {h} v akci v {len(chains)} {plural(len(chains), 'obchodě', 'obchodech', 'obchodech')}"
                  f" ({', '.join(c for c, _ in chains.most_common())}). Nejvíc nabídek má {top_chain[0]} ({top_chain[1]}).") if not chain else (
                  f"V aktuálním letáku {chain_name} je {len(now)} akčních nabídek v {len({o.get('kategorie') for o in now if o.get('kategorie')})} kategoriích.")
            if disc:
                p1 += f" Průměrná sleva je {round(sum(disc) / len(disc))} %, nejvyšší {max(disc)} %."
            seo_text.append(p1)
            if brands and not brand:
                seo_text.append("V akci jsou mimo jiné značky " + ", ".join(b for b, _ in brands.most_common(8)) + ". "
                                "Na stránce každé značky najdete jen její nabídky a vývoj akční ceny.")
            if best_unit and not chain:
                seo_text.append(f"Při porovnání balení rozhoduje cena za {best_unit['jednotka']}: nejvýhodněji teď vychází {best_unit['nazev']}"
                                f" v {best_unit['retezec_nazev']} ({kc(best_unit['jednotkova_cena'])}/{best_unit['jednotka']}). "
                                "Nabídky si můžete seřadit podle ceny za kg nebo litr přepínačem nad výpisem.")
        hero = (category or (typ["kategorie"] if typ else None))
        graph = [{"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, **({"item": SITE + u} if u else {"item": SITE + path})}
            for i, (n, u) in enumerate([("Domů", "/")] + list(crumbs))]}]
        pg = self.product_groups(now)[:80] if now and not chain and not brand and len(now) > 3 else None
        if pg:   # product view: one Product with an AggregateOffer (price range over chains) per product block
            graph.append({"@type": "ItemList", "name": f"{title} v akci", "numberOfItems": len(pg), "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "item": {
                    "@type": "Product", "name": g["nazev"],
                    **({"image": (g["img"] if g["img"].startswith("http") else SITE + g["img"])} if g["img"] else {}),
                    **({"url": SITE + g["url"]} if g["url"] else {}),
                    "offers": {"@type": "AggregateOffer", "priceCurrency": "CZK", "lowPrice": f"{g['od']:.2f}", "highPrice": f"{g['do']:.2f}",
                               "offerCount": g["n"], "availability": "https://schema.org/InStoreOnly"}}}
                for i, g in enumerate(pg[:20])]})
        elif now:
            graph.append({"@type": "ItemList", "name": f"{title} v akci", "numberOfItems": len(now), "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "item": {
                    "@type": "Product", "name": o["nazev"], **({"brand": {"@type": "Brand", "name": o["znacka"]}} if o.get("znacka") else {}),
                    **({"image": (SITE + BASE + "img/" + o["img"]) if o.get("img") else o.get("img_url")} if (o.get("img") or o.get("img_url")) else {}),
                    "offers": {"@type": "Offer", "price": f"{o['cena']:.2f}", "priceCurrency": "CZK", "availability": "https://schema.org/InStoreOnly",
                               "validFrom": o["od"], "priceValidUntil": o["do"], "seller": {"@type": "Organization", "name": o["retezec_nazev"]}}}}
                for i, o in enumerate(now[:20])]})
        if faq:
            graph.append({"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q, a_ in faq]})
        self.render(path, "listing.html", indexable=indexable, schema={"@context": "https://schema.org", "@graph": graph},
                    seo_text=seo_text, seo_h2=seo_h2, og_image=(f"{SITE}{BASE}kat/{hero}.jpg" if hero and (ROOT / "static" / "kat" / f"{hero}.jpg").exists() else None), title=seo_title, description=desc, h1=(f"{title} v akci" if not chain else title),
                    name=title, h=h, now=[self.card(o) for o in now][:300], fut=[self.card(o) for o in fut][:120], n_now=len(now), n_fut=len(fut),
                    chains=chains.most_common(), cheapest=cheapest, best_unit=best_unit, od=od, do=do, typ=typ, products=products, crumbs=crumbs,
                    chart=self.chart(history_key) if history_key else None, related=related, types=types, category=category, chain=chain,
                    chain_name=chain_name, brand=brand, groups=groups, faq=faq, letak_chain=(chain if chain in LETAK_CHAINS else None),
                    last=self.last_prices(history_key) if not now and history_key else None,
                    pgroups=pg,
                    chain_links=chain_links)

    def last_prices(self, key):
        h = self.history.get(key) or {}
        if not h:
            return None
        d = max(h)
        return {"date": d, "prices": sorted(h[d].items(), key=lambda kv: kv[1])}

    def write_index(self, cur):
        rows = []
        for o in cur:
            c = self.card(o)
            rows.append([o["id"], o["nazev"], o["retezec_nazev"], o["cena"], o.get("puvodni_cena"), o.get("baleni") or "", o["od"], o["do"],
                         c["img_src"] or "", o.get("typ") or "", o.get("produkt") or "", c["link"], o.get("jednotkova_cena"), o.get("jednotka") or ""])
        (self.out / BASE.strip("/") / "index.json").write_text(json.dumps({"d": self.today, "o": rows}, ensure_ascii=False, separators=(",", ":")))

    def write_sitemap(self):
        urls = "".join(f"<url><loc>{SITE}{p}</loc><lastmod>{self.today}</lastmod></url>" for p, ix in self.pages if ix)
        (self.out / BASE.strip("/") / "sitemap.xml").write_text(
            f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')


def update_history(history, offers, today):
    """history[key][date][chain] = lowest current promo price (type and type-brand keys)."""
    names = history.setdefault("_names", {})
    day = defaultdict(dict)
    for o in offers:
        if not (o["od"] <= today <= o["do"]) or not o.get("typ"):
            continue
        keys = [o["typ"]]
        if o.get("znacka") and slugify(o["znacka"]):
            k = f"{o['typ']}-{slugify(o['znacka'])}"
            keys.append(k)
            t = TYPE_BY_SLUG[o["typ"]]
            names[k] = f"{t['nazev'].split(' a ')[0]} {o['znacka']}" if t["slug"] not in ("nealko", "pivo", "vino") else o["znacka"]
        for k in keys:
            c = o["retezec_nazev"]
            if c not in day[k] or o["cena"] < day[k][c]:
                day[k][c] = o["cena"]
    for k, v in day.items():
        history.setdefault(k, {})[today] = v
    cutoff = (dt.date.fromisoformat(today) - dt.timedelta(days=400)).isoformat()
    for k in list(history):
        if k == "_names":
            continue
        for d in [d for d in history[k] if d < cutoff]:
            del history[k][d]
    return history


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data"))
    ap.add_argument("--shell", default=str(ROOT / "cache/shell.html"))
    ap.add_argument("--out", default=str(ROOT / "dist"))
    ap.add_argument("--today", default=dt.date.today().isoformat())
    ap.add_argument("--no-history", action="store_true", help="do not write today into history (quick rebuilds)")
    a = ap.parse_args()
    data = Path(a.data)
    files = sorted((data / "offers").glob("*.json"))
    offers = json.loads(files[-1].read_text()) if files else []
    from .collect import CHAIN_NAMES
    from .taxonomy import brand as _brand, classify as _classify
    for o in offers:   # re-classify with the current taxonomy (taxonomy fixes need no new download)
        lidl_path = o.get("kat_retezce") if o["retezec"] == "lidl" and "Kategorie/" in (o.get("kat_retezce") or "") else None
        o["typ"] = _classify(o["nazev"], o.get("detail") or "", lidl_path)
        o["kategorie"] = TYPE_BY_SLUG[o["typ"]]["kategorie"] if o["typ"] else None
        if o.get("zdroj") == "letak" or not o.get("znacka"):
            o["znacka"] = _brand(o["nazev"]) or (o.get("znacka") if o.get("zdroj") != "letak" else None)
        if o.get("znacka"):
            o["znacka"] = BRAND_ALIAS.get(o["znacka"], o["znacka"])
        o["retezec_nazev"] = CHAIN_NAMES.get(o["retezec"], o.get("retezec_nazev"))
    for o in offers:   # snapshots written before od/do defaults existed
        o["od"] = o.get("od") or a.today
        o["do"] = o.get("do") or (dt.date.fromisoformat(o["od"]) + dt.timedelta(days=6)).isoformat()
    hf = data / "history.json"
    history = json.loads(hf.read_text()) if hf.exists() else {}
    if not a.no_history:
        history = update_history(history, offers, a.today)
        hf.write_text(json.dumps(history, ensure_ascii=False, separators=(",", ":")))
    out = Path(a.out)
    (out / BASE.strip("/")).mkdir(parents=True, exist_ok=True)
    for f in (ROOT / "static").glob("*"):
        if f.is_dir():
            shutil.copytree(f, out / BASE.strip("/") / f.name, dirs_exist_ok=True)
        else:
            shutil.copy(f, out / BASE.strip("/") / f.name)
    site = Site(offers, history, a.today, Shell(Path(a.shell)), out)
    site.build()
    print(f"{len(site.pages)} pages ({sum(1 for _, i in site.pages if i)} indexable), {len(offers)} offers")


if __name__ == "__main__":
    main()
