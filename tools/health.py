"""Stop the deploy when the build looks broken (an empty run must not wipe the live pages).

    python -m tools.health dist
"""
import json
import sys
from pathlib import Path

dist = Path(sys.argv[1]) / "akce"
ix = json.loads((dist / "index.json").read_text())
n = len(ix["o"])
chains = {r[2] for r in ix["o"]}
pages = len(list(dist.rglob("index.html")))
print(f"offers {n}, chains {sorted(chains)}, pages {pages}")
problems = []
if n < 300:
    problems.append(f"only {n} offers")
if len(chains) < 3:
    problems.append(f"only {len(chains)} chains")
for must in ["index.html", "cokolada/index.html", "maslo/index.html"]:
    if not (dist / must).exists():
        problems.append(f"missing {must}")
if problems:
    print("HEALTH FAIL: " + "; ".join(problems))
    sys.exit(1)
