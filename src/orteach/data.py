"""Instance tables — the data both the notebook and the package read.

Standard Part 4, "tables versus knobs": a scalar carrying a concept (cost,
retail, the mean demand) is a **knob** and stays written out in the notebook cell
where the narration explains it. Many entries indexed by the model's own sets,
named nowhere in the prose, are a **table** — and a table lives in one file both
sides read, because the agreement assertion cannot prove two independently typed
copies of the data agree.

The demand scenarios are a table. Before this file existed the notebook generated
them with ``random.normalvariate`` at run time, which meant **every number in the
prose was wrong on the next run** and the agreement assertion compared two
different problems.
"""
from __future__ import annotations

import csv
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data", "raw")
DEMAND_CSV = os.path.join(DATA_DIR, "newsvendor_demand.csv")

# The generating parameters, recorded so the table can be rebuilt exactly.
# Truncated at zero: demand cannot be negative.
DEMAND_SEED = 20260904
DEMAND_MU = 400.0
DEMAND_SIGMA = 100.0
DEMAND_N = 1000


def generate_demand(n=DEMAND_N, mu=DEMAND_MU, sigma=DEMAND_SIGMA, seed=DEMAND_SEED):
    """Rebuild the demand scenarios deterministically.

    Uses ``random.Random(seed)`` rather than numpy so the result does not depend
    on a numpy version's generator internals.
    """
    import random
    rng = random.Random(seed)
    return [round(max(rng.normalvariate(mu, sigma), 0.0), 6) for _ in range(n)]


def write_demand(path=DEMAND_CSV):
    """Write the table. The script is the source of truth; the CSV is a build
    output, and ``tests/test_data.py`` checks that regenerating reproduces it."""
    rows = generate_demand()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "demand"])
        for i, d in enumerate(rows):
            w.writerow([i, d])
    return path


def load_demand(path=DEMAND_CSV):
    """Read the demand table. Both the notebook and the package call this, and
    then pass the RESULT into the solvers — the solvers never read the file."""
    with open(path, encoding="utf-8") as f:
        return [float(r["demand"]) for r in csv.DictReader(f)]


if __name__ == "__main__":
    print("wrote %s" % write_demand())
