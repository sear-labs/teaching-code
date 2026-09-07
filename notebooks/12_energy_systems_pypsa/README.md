# 12 — Energy systems and PyPSA

`dispatch_to_pypsa.ipynb` is REE 4301's Module 0: one hour of dispatch on paper, in gurobipy and in
PyPSA; then a day with a battery; then capacity as a decision. Package: `orteach.energy`.

## This notebook needs PyPSA, and PyPSA needs its own environment

PyPSA 1.3 requires pandas 3, which the Anaconda base environment on the authoring machine does not
have (and upgrading it would break other things). So the notebook runs in its own environment, and
its kernel metadata says so: `orteach-energy`. To make one:

```bash
python -m venv <short-path>/orteach-energy          # a SHORT path: Windows long-path limits broke the first attempt
<short-path>/orteach-energy/Scripts/pip install pypsa highspy "gurobipy>=11,<14" ipykernel nbconvert matplotlib pytest
<short-path>/orteach-energy/Scripts/python -m ipykernel install --user --name orteach-energy --display-name "Python (orteach-energy: pypsa)"
```

Then open the notebook with that kernel, or execute it with
`jupyter nbconvert --execute --ExecutePreprocessor.kernel_name=orteach-energy`. The PyPSA half of
`tests/test_energy.py` skips in the base environment and runs in this one:

```bash
<short-path>/orteach-energy/Scripts/python -m pytest tests/test_energy.py
```

On Colab the setup cell installs PyPSA itself.

## The rest of REE 4301 is its own repository now

[`sear-labs/energy-system-modeling`](https://github.com/sear-labs/energy-system-modeling) — created
2026-09-07 with fresh history out of the private course folder, which keeps the exams and the book.
**It is private for now**, so that link 404s until the notebooks are made public.

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
