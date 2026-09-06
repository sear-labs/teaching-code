# Teaching Code — one library, organised by subject

> **The rules are not in this file.** Everything portable — archetypes, naming, the teaching
> standard, the engineering/teaching boundary, verification, working alongside other sessions —
> lives in one document and is deliberately **not restated** here:
>
>     https://github.com/sear-labs/code-standard    canonical - the same from any machine
>     a local clone, if you have one                faster; on the UTA desktop that is
>                                                   Documents\Classes\Code Standard\
>
> **Read it first and last.** First because it decides how the work is done; last because a change
> you are about to make may be one it already settles.
>
> This file used to hold an 814-line *copy* of that standard. It was 23 lines behind the source and
> nothing said so — which is why copies were abandoned on 2026-09-04 in favour of pointing. Do not
> paste it back.

---

# Part 11 — This project specifically

**Archetype A + T.** `src/orteach/` is Parts 1–2 territory; `notebooks/` is Part 3 territory; Part 4
governs the boundary between them.

## The organising decision, and why it is not obvious

**One library, not one repo per course.** The subjects are shared — LP formulation, duality,
networks and stochastic programming each serve more than one of IE 3315, IE 5301 and REE 4301 — so
splitting by course would duplicate every shared subject and guarantee the copies drift.

This is written down rather than left implicit because it is the decision somebody will reasonably
want to undo the first time a course needs something the library does not have. **The answer is to
add the subject here, not to fork a course-shaped copy.**

## Layout

```
src/orteach/        the package
notebooks/NN_subject/   01_lp_formulation ... 14_probability_and_stats
data/raw/  tests/
```

**`notebooks/NN_subject` is the sort-key rule from Part 1 applied.** Zero-padded, so `01`–`14` order
correctly and a fifteenth would too. Keep the padding when adding one.

## Status, measured 2026-09-05

Seventeen notebooks across twelve subjects (`02` empty on purpose), sixteen package modules, thirty-
odd tables in `data/raw/`, 170 tests, and `tools/check_notebooks.py`. README.md has the table.

**What to run before believing anything:** `python -m pytest tests/ -q`,
`python tools/check_notebooks.py` and `python tools/check_seeds.py`. All three must be clean before
a commit; the checker exists because three reviews found problems the tests could not — a number in
the prose no output produced, a tied solution compared entry by entry, an objective printed in the
wrong units.

**Eleven notebooks are generated from `tools/seeds/`, and that is where to edit them.** Change the
seed, run it, re-execute the notebook. The other six (`04` both, `05`, `07`, `08`, `11`) were last
edited in place and the notebook is their source; `check_seeds.py` knows which is which.

**`REVIEW_QUEUE.md` is the open work.** It holds the two most recent fresh-context reviews verbatim
with a status line per finding, and the list of what must change before the first push.

**Conventions this library settled, beyond the standard:**

- Every notebook opens with the same setup cell (`REPO_URL`, clone-or-`../../src`) and, when it
  solves, the same licence cell (silent `gp.Env`, Colab Secrets, `NotebookAccessError` caught).
  Patch them everywhere or nowhere.
- Tolerances are named in `orteach.tolerance` and nowhere else; every hand-built Gurobi model calls
  `tolerance.apply(m)`.
- When an optimum is not unique, the agreement assertion compares what every optimum shares and the
  prose teaches the tie. It does not compare the solver's path.
- The commit message carries the defect record: which source, which term folders, what was wrong,
  what the notebook now does. That record was the point of the migration.
- `12` runs in its own kernel (`orteach-energy`) because PyPSA 1.3 needs pandas 3; its README says
  how. Its PyPSA tests skip, visibly, in the base environment.

**Not done:** the 174 files the migration queue could not classify by name were only partly read;
the ones that were (Pooling, Portfolio Selection, Gandhi Cloth, StochasticLP, the Monte Carlo set,
the REE modules beyond M0) are either migrated or named in a folder README. Fixed-charge / logical
constraints (`Gandhi_Cloth`, `Portfolio Selection`) would be a second `05` notebook; the two-stage
server farm (`StochasticLP`, 14 copies) and the bakery VSS/EVPI example a second `07`.
