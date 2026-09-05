"""Every seed in tools/seeds/ must reproduce its committed notebook cell for
cell. A seed that has fallen behind would silently undo a fix the next time
someone ran it, so this fails loudly on the first difference.

    python tools/check_seeds.py

Runs each seed into a temporary tree shaped like the repository, then compares
cell sources (outputs are not compared: seeds write none).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEEDS = ROOT / "tools" / "seeds"


def sources(path: Path) -> list:
    return ["".join(c["source"]) for c in json.loads(path.read_text(encoding="utf-8"))["cells"]]


def main() -> int:
    seeds = sorted(SEEDS.glob("seed_*.py"))
    if not seeds:
        print("no seeds found under", SEEDS)
        return 1
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp) / "tools" / "seeds"
        tree.mkdir(parents=True)
        for seed in seeds:
            shutil.copy(seed, tree / seed.name)
            run = subprocess.run([sys.executable, str(tree / seed.name)], capture_output=True, text=True)
            if run.returncode != 0:
                print("FAIL  %-24s did not run:\n%s" % (seed.name, run.stderr))
                failures += 1
                continue
            written = sorted((Path(tmp) / "notebooks").rglob("*.ipynb"))
            if len(written) != 1:
                print("FAIL  %-24s wrote %d notebooks, expected one" % (seed.name, len(written)))
                failures += 1
                for p in written:
                    p.unlink()
                continue
            target = written[0]
            rel = target.relative_to(tmp)
            committed = ROOT / rel
            if not committed.exists():
                print("FAIL  %-24s writes %s, which is not in the repository" % (seed.name, rel))
                failures += 1
                continue
            a, b = sources(target), sources(committed)
            if a == b:
                print("ok    %-24s %s (%d cells)" % (seed.name, rel, len(a)))
            else:
                diff = [i for i in range(max(len(a), len(b))) if i >= len(a) or i >= len(b) or a[i] != b[i]]
                print("FAIL  %-24s %s differs from the committed notebook at cells %s" % (seed.name, rel, diff[:6]))
                failures += 1
            target.unlink()
    print("\n%d seed(s), %d failure(s)" % (len(seeds), failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
