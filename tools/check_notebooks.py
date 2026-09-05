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
    no defs in teaching zero ``def``/``class``/named ``lambda`` before the
                        streamlined-version heading
    predict prompt      at least one before the first solve, fit or random draw
    agreement           an ``assert`` comparing notebook and package is present
    tolerance literal   no ``1e-9`` (or other tolerance) written in the notebook -
                        it must be imported from orteach.tolerance (Part 4 amendment)
    seeds printed       if the notebook draws random numbers, a seed is set and printed
    cell length         longest code cell under the scroll limit
    prose numbers       every specific number quoted in markdown (a decimal with
                        three or more digits, or a comma-grouped thousand) appears
                        in some output of the same notebook (Part 7: every number
                        in the prose came from that run)
    setup cell          the Colab setup cell names this notebook's own folder
    licence id          no Gurobi licence banner in any output
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
DEF_RE = re.compile(r"^\s*(def|class)\s+\w+|^\s*\w+\s*=\s*lambda\b", re.M)
PREDICT_RE = re.compile(r"predict|write down|before (you )?(run|solv|build)", re.I)
SOLVE_RE = re.compile(r"\.optimize\(\)|\.solve\(|\.fit\(|default_rng\(|np\.random\.", re.I)
AGREE_RE = re.compile(r"assert\s+\w*\s*<\s*AGREEMENT_RTOL", re.I)
TOL_LITERAL_RE = re.compile(r"(?<![\w.])1e-(?:6|7|8|9|10|11|12)(?![\w])")
RANDOM_RE = re.compile(r"np\.random|default_rng|random\.(seed|Random|normalvariate|choice|uniform)")
SEED_SET_RE = re.compile(r"SEED\s*=|seed\s*=\s*SEED|default_rng\(SEED\)|random\.Random\(", re.I)
SEED_PRINT_RE = re.compile(r"print\(.*seed", re.I)
# a number worth checking: comma-grouped thousands, or a decimal fraction, carrying three or more
# digits. Plain integers (a year, a count of scenarios, a step size) are not checked.
PROSE_NUM_RE = re.compile(r"(?<![\w.\-])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+)(?![\w])")
CODE_SPAN_RE = re.compile(r"`[^`]*`|\$\$.*?\$\$|\$[^$\n]*\$", re.S)
EXERCISES_RE = re.compile(r"^#+\s*where to take this next.*", re.I | re.M | re.S)
LICENCE_RE = re.compile(r"LicenseID to value|Academic license|Restricted license")


def _numbers_in_prose(md_text: str) -> list[str]:
    """Numbers the prose presents as results. The closing exercises name values
    the reader is asked to try, so they are not checked."""
    text = EXERCISES_RE.sub(" ", CODE_SPAN_RE.sub(" ", md_text))
    out = []
    for m in PROSE_NUM_RE.finditer(text):
        raw = m.group(1)
        if len(raw.replace(",", "").replace(".", "")) < 3:
            continue
        out.append(raw.replace(",", ""))
    return out


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

    # every output as text, for the prose-number and licence checks
    out_text = []
    for c in code_cells:
        for o in c.get("outputs", []):
            if "text" in o:
                out_text.append("".join(o["text"]))
            if "data" in o:
                out_text.append("".join(o["data"].get("text/plain", "")))
    outputs = "\n".join(out_text)
    if LICENCE_RE.search(outputs):
        fails.append("a Gurobi licence banner is in the outputs")

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
        fails.append("function/class/lambda defined in the teaching section at cell(s) %s" % defs)
    if wrap_at is None:
        fails.append("no 'Now the streamlined version' heading")

    # predict prompt before the first solve, fit or random draw
    first_solve = next((i for i, c in enumerate(cells) if c.get("cell_type") == "code" and SOLVE_RE.search(src(c))), None)
    if first_solve is not None:
        before = "\n".join(src(c) for c in cells[:first_solve] if c.get("cell_type") == "markdown")
        if not PREDICT_RE.search(before):
            fails.append("no predict-before-you-run prompt before the first result (cell %d)" % first_solve)
    else:
        fails.append("no solve, fit or random draw found - the predict-prompt check would pass vacuously")

    # agreement assertion, and the tolerance imported rather than typed
    if not AGREE_RE.search(all_code):
        fails.append("no agreement assertion against AGREEMENT_RTOL")
    assert_lines = [l for l in all_code.splitlines() if "assert" in l and TOL_LITERAL_RE.search(l)]
    if assert_lines:
        fails.append("tolerance literal inside an assert - import it from orteach.tolerance: %s"
                     % assert_lines[0].strip()[:70])
    # a threshold assigned to a name and then asserted on is the same literal one line away
    thresh_lines = [l for l in all_code.splitlines()
                    if TOL_LITERAL_RE.search(l) and re.search(r"[<>]=?\s*1e-|1e-\d+\s*[<>]", l)]
    if thresh_lines:
        fails.append("tolerance literal used as a threshold - name it in orteach.tolerance: %s"
                     % thresh_lines[0].strip()[:70])

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

    # every specific number in the prose came from this run
    flat_outputs = outputs.replace(",", "")
    missing = sorted({n for n in _numbers_in_prose(all_md) if n not in flat_outputs})
    if missing:
        fails.append("number(s) in the prose not found in any output: %s" % missing[:8])

    # the setup cell names this notebook's own folder
    folder = path.parent.name
    setup = [c for c in code_cells if "REPO_URL" in src(c)]
    if not setup:
        fails.append("no Colab setup cell (REPO_URL)")
    elif ("notebooks/%s" % folder) not in src(setup[0]):
        fails.append("setup cell does not chdir to notebooks/%s" % folder)

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
