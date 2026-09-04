# Teaching Code — one library, organised by subject

Erick C. Jones Jr., IMSE, UT Arlington. Scaffolded 2026-09-03.

The curated home for teaching notebooks across IE 3315, IE 5301 and REE 4301. One library rather
than one repo per course, because the subjects are shared: LP formulation, duality, networks and
stochastic programming all serve more than one course.

`CLAUDE.md` here is the 577-line Code and Teaching Standard, copied from `Classes\Code Standard\`.
Claude Code reads it automatically in every session in this folder. **A `Part 11 — This project
specifically` should be appended for this library**; everything above it stays generic so it can be
replaced wholesale when the standard is updated.

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

The list came from clustering the real filenames across both sources, which classified 118 of 252
distinct teaching files. The other 134 have names like `00_concepts.ipynb` that carry no subject —
their folder gets decided while reading them, during the migration pass, not before it.

---

## The migration pass

Nothing has been migrated yet. Each notebook that comes in gets, in one pass:

1. **Subject folder assigned** by reading it.
2. **Code Standard compliance** — Part 10's pre-ship checklist is the bar. Especially: no function
   definitions above the "streamlined version" heading, markdown above every teaching cell, at least
   one "predict before you run" prompt before the first result, and the agreement assertion.
3. **Colab Secrets for any Gurobi WLS credential** — never a pasted key. See
   `Inventory\classes\PASTED_KEYS.md` §5 for the exact cell.
4. **Shipped executed** — outputs and figures committed, so a reader without a licence still sees
   what the prose refers to.

Known starting point, measured 2026-09-03: **380 distinct teaching files, heavily duplicated** —
`StochasticLP.ipynb` exists in 14 places, `StarOil_NPV_*` in 10 each. The target is roughly 30
canonical notebooks. The job is curation, not polishing.

The 7 already-migrated notebooks in `Classes\Advanced Opt Modeling Examples\notebooks\` are the
reference for what "done" looks like: all executed, zero orphan cells, 6–12 prediction prompts each,
agreement assertions present.

---

## Before this goes public

- **Rotate the Gurobi WLS key first.** It is still live in a shared Drive copy.
- The licence expires **2026-12-04**, mid-semester.
- `pyproject.toml` so `pip install -e .` works — required for Colab, and it removes all `sys.path`
  fragility.
- Exclude other people's material: `Krejci IE 3315 Lecture Notes` and `CorleyFiles` are not yours to
  publish.
