"""Keep the data branch small: offers snapshots of the last 21 days, crops of offers that are still referenced.

    python tools/prune_data.py <data-dir>
"""
import datetime as dt
import json
import sys
from pathlib import Path

d = Path(sys.argv[1])
cut = (dt.date.today() - dt.timedelta(days=21)).isoformat()
files = sorted((d / "offers").glob("*.json"))
for f in files:
    if f.stem < cut:
        f.unlink()
files = sorted((d / "offers").glob("*.json"))
keep = set()
for f in files[-3:]:
    keep |= {o["img"] for o in json.loads(f.read_text()) if o.get("img")}
for img in (d / "img").glob("*.jpg"):
    if img.name not in keep:
        img.unlink()
print(f"offers files {len(files)}, crops kept {len(keep)}")
