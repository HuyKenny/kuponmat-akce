"""Purge changed pages in Cloudflare and announce them via IndexNow (Bing, Seznam).

    python -m tools.after_deploy dist/changed-urls.txt
Env: CF_ZONE_ID, CF_API_TOKEN (cache purge permission only), INDEXNOW_KEY. Missing values = step skipped.
"""
import os
import sys
from pathlib import Path

import requests

urls = [u for u in Path(sys.argv[1]).read_text().split("\n") if u] if Path(sys.argv[1]).exists() else []
always = ["https://kuponmat.cz/akce/index.json", "https://kuponmat.cz/akce/sitemap.xml", "https://kuponmat.cz/akce/akce.css", "https://kuponmat.cz/akce/akce.js"]
zone, tok = os.environ.get("CF_ZONE_ID"), os.environ.get("CF_API_TOKEN")
if zone and tok:
    todo = urls + always
    for i in range(0, len(todo), 30):
        r = requests.post(f"https://api.cloudflare.com/client/v4/zones/{zone}/purge_cache",
                          headers={"Authorization": f"Bearer {tok}"}, json={"files": todo[i:i + 30]}, timeout=60)
        print("purge", r.status_code, r.json().get("success"))
key = os.environ.get("INDEXNOW_KEY")
if key and urls:
    for ep in ("https://api.indexnow.org/indexnow", "https://search.seznam.cz/indexnow"):
        r = requests.post(ep, json={"host": "kuponmat.cz", "key": key, "keyLocation": f"https://kuponmat.cz/{key}.txt", "urlList": urls[:10000]}, timeout=60)
        print("indexnow", ep, r.status_code)
print(f"{len(urls)} changed pages")
