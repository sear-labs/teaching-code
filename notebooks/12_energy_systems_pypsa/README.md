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

## The rest of REE 4301 lives in the course repository

`Classes\REE 4301 - Energy System Modeling\` is a git repository on OneDrive (not yet on GitHub).
Its `2026 Fall\Notebooks\` folder holds the course as it will be taught: M0 (migrated here), M0B,
M3 transport and power-flow companions, M4 supply chain (its Part B is migrated to
`13_supply_chain`), M5 facility decision, SB1–SB6 sidebars, 1N, GRAD_M and GRAD_N. Every one of them
shipped with zero outputs — none had been executed when this library was built.

What has been verified, by running it:

| notebook | status |
|---|---|
| M0 Toy LP to PyPSA | every number its prose names holds (this folder) |
| M4 Supply Chain, Part B (gurobipy) | all four stated costs hold; Part C's PyPSA mirror omits the processor-capacity rows — silent only because demand equals one processor's capacity exactly (see `13_supply_chain`) |
| everything else | not executed; assume wrong until checked |

Solution keys (`Assignment_*_SOLUTION_KEY.ipynb`, `PyPSA Mastery Document Solution Key.ipynb`) are
excluded from this library on purpose.
