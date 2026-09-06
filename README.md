# Teaching Code — one library, organised by subject

Erick C. Jones Jr., IMSE, UT Arlington. Scaffolded 2026-09-03.

The curated home for teaching notebooks across IE 3315, IE 5301 and REE 4301. One library rather
than one repo per course, because the subjects are shared: LP formulation, duality, networks and
stochastic programming all serve more than one course.

`CLAUDE.md` here **points at** the Code and Teaching Standard rather than copying it, and carries
this library's `Part 11`. Claude Code reads it automatically in every session in this folder; the
standard itself is read from `sear-labs/code-standard`, or a local clone outside any syncing
folder - on this machine `C:\dev\code-standard\`. It used to be a copy, which drifted 23 lines
behind with nothing to say so.

---

## Why `src/` and `notebooks/` are separate

This is the split Part 4 of the standard governs, and it is the point of the whole structure.

| | written for | governed by |
|---|---|---|
| **`src/orteach/`** | a machine, to run a thousand times | Parts 1–2 — the engineering half |
| **`notebooks/`** | a person, to read once | Part 3 — the teaching half |

**`src/` is the package.** "Source", in the ordinary programming sense: the importable Python that
holds each model *once*, written the way production code is written — functions, parameters, no
repetition, tested. Nothing in it is meant to be read as a lesson. It exists so that the model has
one definitive implementation, so a script can call it a thousand times, and so a notebook has
something to check itself against.

**`notebooks/` is the teaching.** The same model, built by hand, step by step, one idea per cell,
with markdown above each cell saying what it does and why. No function definitions in the teaching
section. Hardcoded knobs are **correct here, not debt** — refactoring them into a config dict would
delete the lesson.

**Both hold the same model, on purpose.** That is deliberate duplication, and the standard is
explicit that it is right. What makes it safe is the mechanism below.

### The agreement assertion

Deliberate duplication removes the usual protection, which is that only one copy exists. Something
has to replace it. **Every teaching notebook ends with a cell that imports the package, runs the same
case, and asserts the two agree:**

```python
from orteach.models import build_model
packaged = build_model(**PARAMS_USED_ABOVE).solve()
rel = abs(packaged.value - hand_built.value) / abs(hand_built.value)
assert rel < 1e-9, f"notebook and package disagree by {rel:.2e}"
print(f"notebook and package agree to {rel:.1e}")
```

**A teaching notebook without this cell is not finished.** Without the package there is nothing for
the assertion to compare against — which is why `src/` is not optional if this library is ever going
to be public.

### The other two folders

- **`data/raw/`** — instance *tables*: many entries, indexed by the model's own sets, named nowhere
  in the prose. Both the notebook and the package read them from here. A scalar carrying a concept —
  a rate, a count, a breakpoint — is a **knob** and stays written out inline in the cell.
- **`tests/`** — at minimum a smoke test asserting the domain invariants: totals that must balance,
  quantities that cannot go negative.

---

## Subject folders

Numbered so they sort in teaching order rather than alphabetically — otherwise game theory files
ahead of LP formulation, which is backwards.

```
01_lp_formulation              08_monte_carlo_and_simulation
02_simplex_and_bases           09_queueing_and_markov
03_duality_and_sensitivity     10_game_theory
04_networks_and_transport      11_decision_analysis
05_integer_and_branch_bound    12_energy_systems_pypsa
06_nonlinear_and_convex        13_supply_chain
07_stochastic_and_newsvendor   14_probability_and_stats
```

## What is here, measured 2026-09-05

Seventeen teaching notebooks in twelve subjects, each with its package module, its tables and its
tests. `02_simplex_and_bases` is empty on purpose. Every notebook ships executed, ends in the
agreement assertion, and passes `tools/check_notebooks.py`.

| folder | notebooks | package |
|---|---|---|
| 01 | `diet`, `goal_programming` | `diet`, `goal_programming` |
| 03 | `primal_and_dual` | `duality` |
| 04 | `transportation`, `assignment` | `transportation`, `assignment` |
| 05 | `facility_location` | `facility_location` |
| 06 | `curve_fit_lifting`, `pooling` | `nonconvex` |
| 07 | `newsvendor` | `newsvendor`, `data` |
| 08 | `monte_carlo` | `montecarlo` |
| 09 | `markov_and_queues` | `markov`, `queueing` |
| 10 | `zero_sum_game` | `games` |
| 11 | `capital_budgeting` | `capital_budgeting` |
| 12 | `dispatch_to_pypsa` (own kernel — see its README) | `energy` |
| 13 | `sourcing_and_resilience` | `sourcing` |
| 14 | `distributions_and_clt`, `inference_and_regression` | `distributions`, `inference` |

`orteach.tolerance` is the one home of every tolerance and of the solver settings that make the
agreement assertion honest.

**The defect record is the git log.** Every migration commit says what the source notebooks got
wrong, in which term folders, and what the notebook does about it — a protein row pointing the wrong
way for three terms, a goal-programming deviation pointing the wrong way for five, a game solved
with its payoffs missing for four, a least-squares fit that could only over-predict, a MIP asked for
duals in ten folders, a ranging bound wrong by half. Read `git log` before assuming a course copy
is right.

The lithium supply-chain material (`sear-labs/advopt-lithiumsc`, public) and the rest of REE 4301 (a
git repository on OneDrive, not yet pushed) are pointed at from `06`, `10`, `12` and `13`, not copied.

## Checking the work

```bash
python -m pytest tests/ -q                    # domain invariants, regression pins, R and textbook values
python tools/check_notebooks.py               # Part 10, the machine-checkable half, every notebook
python tools/check_seeds.py                   # every seed still reproduces its committed notebook
```

The checker refuses: an unexecuted notebook or an error output, an orphan code cell, a function or
named lambda before the "Now the streamlined version" heading, no predict-before-you-run prompt, no
agreement assertion, a tolerance literal used as a threshold, a seed set but not printed, a cell too
long to read without scrolling, a number in the prose that no output produced, a licence banner in
an output, and a notebook without the Colab setup cell.

Eleven of the notebooks are written by a script in `tools/seeds/`, which is where to edit them: change
the seed, run it, then execute the notebook in place so it ships with outputs. `tools/check_seeds.py`
fails if any seed has fallen behind its notebook, because running a stale one would silently undo
whatever was fixed since.

To re-execute a notebook: `jupyter nbconvert --to notebook --execute --inplace <path>` (for `12`, add
`--ExecutePreprocessor.kernel_name=orteach-energy`).

Every notebook has been read by a fresh-context reviewer against Parts 3, 4 and 10. The first nine
reviews are folded into commit `9054550`, the probability pair into `3084cf3`, and `09`/`10`/`12`
into `33d47b6`. **`REVIEW_QUEUE.md` holds the two most recent reviews verbatim with a status line per
finding; the nine on `06` and `13` are still open.** It also lists what has to change before the
first push.

---

## Before this goes public

- **Rotate the Gurobi WLS key.** It is still live in shared Drive copies. Nothing in this repository
  needs it: no notebook contains a key, and the setup cell falls back to the size-limited licence
  `pip install gurobipy` ships when no Colab Secret is set.
- **`07` is the one notebook that needs a licence of its own.** Its scenario models reach 3,002
  variables against the free licence's documented two thousand. Every other notebook is under five
  hundred. `07` says this in its own licence cell.
- The academic licence on the authoring machine expires **2026-12-04**, mid-semester. That is a
  problem for re-executing notebooks here, not for a reader on Colab.
- Exclude other people's material: `Krejci IE 3315 Lecture Notes` and `CorleyFiles` are not yours to
  publish. Solution keys are already excluded; the exam-score vectors in `14` are synthetic.
- **`REE 4301` is pointed at by path**, from this file and from `notebooks/12_energy_systems_pypsa/`,
  because it is a git repository on OneDrive with no remote. Push it and those two pointers become
  URLs. The lithium material is already public at `sear-labs/advopt-lithiumsc`.
