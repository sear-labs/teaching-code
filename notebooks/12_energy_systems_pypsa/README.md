# 12 — Energy systems and PyPSA

`dispatch_to_pypsa.ipynb` is REE 4301's Module 0: one hour of dispatch on paper, in gurobipy and in
PyPSA; then a day with a battery; then capacity as a decision. It ends with an **Explore**
section: sliders for the battery day and the build decision, a cell where the reader writes a
gurobipy constraint, and one that moves the demand peak. The sliders call the package, and the
first Explore cell checks that, at the table's numbers, they rebuild the day built by hand.
Package: `orteach.energy`.

## This notebook needs PyPSA, and PyPSA needs pandas 3

PyPSA 1.3 requires pandas 3, so the notebook's kernel metadata names its own environment,
`orteach-energy`. The repository's `energy` extra declares what it needs. To make one:

```bash
python -m venv <short-path>/orteach-energy          # a SHORT path, and NOT under a Temp folder (see below)
<short-path>/orteach-energy/Scripts/pip install -e ".[dev,energy]" ipykernel nbconvert
<short-path>/orteach-energy/Scripts/python -m ipykernel install --user --name orteach-energy --display-name "Python (orteach-energy: pypsa)"
```

Keep it out of any Temp folder. The first one was built in `AppData\Local\Temp`, which Windows
cleaned; the kernel registration survived and pointed at nothing, so `nbconvert` could not start
it.

Then open the notebook with that kernel, or execute it with
`jupyter nbconvert --execute --ExecutePreprocessor.kernel_name=orteach-energy`. The PyPSA half of
`tests/test_energy.py` skips in the base environment and runs in this one:

```bash
<short-path>/orteach-energy/Scripts/python -m pytest tests/test_energy.py
```

On Colab the setup cell installs PyPSA itself, and ipywidgets is already there. CI runs the PyPSA
tests in a job of their own that fails if PyPSA will not import.

## The rest of REE 4301 is its own repository now

[`sear-labs/energy-system-modeling`](https://github.com/sear-labs/energy-system-modeling) — created
2026-09-07 with fresh history out of the private course folder, which keeps the exams and the book.
Public since 2026-09-13.

`dispatch_to_pypsa.ipynb` here **is** that series' first foundation notebook, and it deliberately
did not travel: the series points at this folder instead of keeping a second copy, because the
method library teaches the method on a small self-contained instance and the series carries it on a
real one. Copying it across would have made two copies with nothing comparing them.

Twelve notebooks moved: the model boundary, a one-house energy balance, representative days, end-use
disaggregation, capital cost and LCOE, pipeline transport, DC power flow and LMP, a real network
import, material requirements, a multi-city Texas buildout, the facility decision, and the graduate
model-diversity companion. They are named for the chapter of *Introduction to Energy System
Modeling* they first serve.

**All twelve now execute**, which they did not when this library was built — every one shipped with
zero outputs then. What that took is recorded in that repository's commit log; the short version is
that three could never have run on Colab, one defaulted to a solver its own table said could not
solve it, and one download had never worked.

M4's supply-chain sourcing LP stayed here as `13_supply_chain`; only the material-intensity half
went across.

Solution keys (`Assignment_*_SOLUTION_KEY.ipynb`, `PyPSA Mastery Document Solution Key.ipynb`) are
excluded from this library on purpose.
