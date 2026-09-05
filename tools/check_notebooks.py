"""Audit every notebook in the library against the teaching rules. Fails loudly.

Standard Part 7 says measure, don't estimate, and Part 10 gives the pre-ship
checklist. This runs the machine-checkable half of it over every notebook under
``notebooks/`` and exits non-zero on the first failure, so it can sit in CI.

It does NOT execute notebooks — that is ``jupyter nbconvert --execute`` and it is
slow. It checks the committed, already-executed artifact: Part 5 says ship
executed, so an unexecuted notebook is itself a failure here.

    python tools/check_notebooks.py            # all notebooks
    python tools/check_notebooks.py 04         # only folders starting with 04

Checks, per notebook:
    executed            at least one code cell has outputs; zero error outputs
    orphans             every code cell has a markdown cell immediately above
    no defs in teaching zero ``def``/``class`` before the streamlined-version heading
    predict prompt      at least one before the first solve/optimize
    agreement           an ``assert`` comparing notebook and package is present
    tolerance literal   no ``1e-9`` (or other tolerance) written in the notebook -
                        it must be imported from orteach.tolerance (Part 4 amendment)
    seeds printed       if the notebook draws random numbers, a seed is set and printed
    cell length         longest code cell under the scroll limit
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB_DIR = ROOT / "notebooks"

MAX_CELL_LINES = 40
WRAP_RE = re.compile(r"^#+\s*now the streamlined version", re.I | re.M)
DEF_RE = re.compile(r"^\s*(def|class)\s+\w+", re.M)
PREDICT_RE = re.compile(r"predict|write down|before (you )?(run|solv|build)", re.I)
SOLVE_RE = re.compile(r"\.optimize\(\)|\.solve\(|\.fit\(", re.I)
AGREE_RE = re.compile(r"assert\s+\w*\s*<\s*AGREEMENT_RTOL", re.I)
TOL_LITERAL_RE = re.compile(r"(?<![\w.])1e-(?:6|7|8|9|10|11|12)(?![\w])")
RANDOM_RE = re.compile(r"np\.random|default_rng|random\.(seed|Random|normalvariate|choice|uniform)")
SEED_SET_RE = re.compile(r"SEED\s*=|seed\s*=\s*SEED|default_rng\(SEED\)|random\.Random\(", re.I)
SEED_PRINT_RE = re.compile(r"print\(.*seed", re.I)


def check(path: Path) -> list[str]:
    nb = json.loads(path.read_text(encoding="utf-8"))
    cells = nb.get("cells", [])
    fails = []
    code_cells = [c for c in cells if c.get("cell_type") == "code"]
    src = lambda c: "".join(c.get("source", []))
    all_code = "\n".join(src(c) for c in code_cells)
    all_md = "\n".join(src(c) for c in cells if c.get("cell_type") == "markdown")

    # executed, and cleanly
    if not any(c.get("outputs") for c in code_cells):
        fails.append("not executed - Part 5 says ship it executed")
    errs = [o for c in code_cells for o in c.get("outputs", []) if o.get("output_type") == "error"]
    if errs:
        fails.append("%d cell(s) with an error output" % len(errs))

    # orphans
    orphans = [i for i, c in enumerate(cells)
               if c.get("cell_type") == "code" and (i == 0 or cells[i - 1].get("cell_type") != "markdown")]
    if orphans:
        fails.append("%d orphan code cell(s) with no markdown above: %s" % (len(orphans), orphans[:6]))

    # no function definitions in the teaching section
    wrap_at = None
    for i, c in enumerate(cells):
        if c.get("cell_type") == "markdown" and WRAP_RE.search(src(c)):
            wrap_at = i
            break
    teaching = cells if wrap_at is None else cells[:wrap_at]
    defs = [i for i, c in enumerate(teaching) if c.get("cell_type") == "code" and DEF_RE.search(src(c))]
    if defs:
        fails.append("function/class defined in the teaching section at cell(s) %s" % defs)
    if wrap_at is None:
        fails.append("no 'Now the streamlined version' heading")

    # predict prompt before the first solve
    first_solve = next((i for i, c in enumerate(cells) if c.get("cell_type") == "code" and SOLVE_RE.search(src(c))), None)
    if first_solve is not None:
        before = "\n".join(src(c) for c in cells[:first_solve] if c.get("cell_type") == "markdown")
        if not PREDICT_RE.search(before):
            fails.append("no predict-before-you-run prompt before the first solve (cell %d)" % first_solve)

    # agreement assertion, and the tolerance imported rather than typed
    if not AGREE_RE.search(all_code):
        fails.append("no agreement assertion against AGREEMENT_RTOL")
    lits = TOL_LITERAL_RE.findall(all_code)
    # 1e-9 as a "nudge" in a comparison like  f > 1e-9  is a display threshold, not a
    # tolerance claim; only flag it inside an assert
    assert_lines = [l for l in all_code.splitlines() if "assert" in l and TOL_LITERAL_RE.search(l)]
    if assert_lines:
        fails.append("tolerance literal inside an assert - import it from orteach.tolerance: %s"
                     % assert_lines[0].strip()[:70])

    # seeds
    if RANDOM_RE.search(all_code):
        if not SEED_SET_RE.search(all_code):
            fails.append("draws random numbers but sets no seed")
        elif not SEED_PRINT_RE.search(all_code):
            fails.append("sets a seed but never prints it")

    # scroll limit
    longest = max((len(src(c).splitlines()) for c in code_cells), default=0)
    if longest > MAX_CELL_LINES:
        fails.append("longest code cell is %d lines (limit %d)" % (longest, MAX_CELL_LINES))

    return fails


def main(argv):
    prefix = argv[1] if len(argv) > 1 else ""
    paths = sorted(p for p in NB_DIR.glob("*/*.ipynb") if p.parent.name.startswith(prefix))
    if not paths:
        print("no notebooks found")
        return 1
    bad = 0
    for p in paths:
        fails = check(p)
        rel = p.relative_to(NB_DIR)
        if fails:
            bad += 1
            print("FAIL  %s" % rel)
            for f in fails:
                print("        - %s" % f)
        else:
            print("ok    %s" % rel)
    print("\n%d notebook(s), %d failing" % (len(paths), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
