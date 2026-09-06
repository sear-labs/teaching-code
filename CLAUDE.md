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

### Why this is the standard's answer, not an exception to it

The doubt is worth answering once with citations, because "surely each of these should be its own
repository" is a reasonable first instinct and it has already been raised once.

- **The granularity rule is Part 2b:** *a repo is a unit that is versioned, released and cloned
  together — ask whether anyone would ever want this without the rest of it.* It is not one repo per
  notebook, per course, or per model. Nothing here is released on its own, and every notebook
  depends on `src/orteach` and on the agreement assertion that ties the two halves together.
- **Part 2 routes this shape here on purpose.** It says A + C should be split so one repo does not
  have to satisfy two rigor levels, and then says **A + T is the subject of Part 4** — that is, a
  package and its teaching notebooks stay together and Part 4 governs the boundary between them.
  Splitting `src/` from `notebooks/` would break the one property Part 4 exists to create.
- **Part 0 names this library in the singular and endorses its organisation:** *the teaching library
  sits beside this document, not below it. It is organised by topic rather than by course or
  semester, so one notebook serves several courses across several years.*
- **The split Part 0 does demand is about visibility, not granularity:** public topic material on
  one side, consolidated observations on student work on the other, because one repository has one
  visibility and the stricter rule would otherwise win. That split is already made, and `.gitignore`
  enforces it by pattern rather than by good intentions.

### The series / topic-library boundary, decided 2026-09-05

`sear-labs/advopt-lithiumsc` has the same *shape* as this repository — executed teaching notebooks,
a package, an agreement assertion — so "why are these two things not one thing" needed an answer.

> **The boundary is the instance, not the subject.** A **series** is notebooks that share one running
> instance and are read in order. A **topic library** is notebooks that each stand alone on their own
> instance and are chosen by subject. The test for any notebook is: **does it need the instance built
> by the notebook before it?**

Measured rather than asserted, on 2026-09-05:

| | `advopt-lithiumsc` | this repository |
|---|---|---|
| notebooks on one shared instance | 14 of 15 | 0 of 17 |
| reading order | `00_start_here`, then `01`→`05`; `04d` assumes `04c` | none; folders are subjects |
| instance tables | one supply chain | 34, roughly two per notebook |
| cited as a work | yes, `CITATION.cff` | no |

**So advopt stays where it is, and does not fold in.** Splitting a series into topic folders destroys
the sequence, and the sequence is its content. It is also cited as one work, which a topic library
is not.

**REE 4301 becomes its own series repository when it is pushed**, for the same reason — its modules
run over one energy system in order. It is not a merge into this one.

**A method may appear in both, and that is not duplication to remove.** Here it is taught on a small
self-contained instance; there it is carried on a real one. The folder READMEs in `06`, `10`, `12`
and `13` are what keeps the two honest: **the library teaches the method, the series carries the
case.** That `12` is REE's Module 0 is the rule working, not an exception to it — Module 0 stands
alone on one hour of dispatch, so it belongs here, while the modules that assume it belong to the
series.

**Where does new material go?** Ask whether it needs the instance before it. No — a subject folder
here. Yes — the series it continues. A new arc over a new single instance — a new series repository.

This is a decision about which of these repositories holds what, not a portable rule. Making it
portable means petitioning Part 2b of the standard, which is Jones's call and not this file's.

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
