"""Copy crops referenced by the current offers from data/img into dist/akce/img.

    python -m tools.keep_crops <data> <dist-img-dir>
"""
import json
import shutil
import sys
from pathlib import Path

data, dst = Path(sys.argv[1]), Path(sys.argv[2])
files = sorted((data / "offers").glob("*.json"))
need = {o["img"] for o in (json.loads(files[-1].read_text()) if files else []) if o.get("img")}
dst.mkdir(parents=True, exist_ok=True)
n = 0
for name in need:
    src = data / "img" / name
    if src.exists():
        shutil.copy(src, dst / name)
        n += 1
print(f"crops {n}/{len(need)}")
