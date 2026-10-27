"""Seed for the tableau simplex notebook (02). Writes the notebook without outputs; execute it afterwards (README.md here)."""
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "notebooks", "02_simplex_and_bases", "simplex_by_hand.ipynb")
cells = []


def md(t):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": t.strip("\n").splitlines(keepends=True)})


def code(t):
    cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
                  "source": t.strip("\n").splitlines(keepends=True)})


md(r"""
# Corners, bases and the simplex tableau, by hand

A linear program's optimum sits at a corner of its feasible region. That is a picture with two
variables and a theorem with many, and the simplex method is how the theorem gets used: walk from
corner to neighbouring corner, never downhill, until no neighbour is better.

This notebook does it on the course's tableau example, by hand, with numpy doing only the
arithmetic. First every corner, feasible or not; then the walk, one pivot at a time.
""")

md(r"""
## Setup: where the package lives

This notebook builds everything by hand and then checks it against `orteach`, the package in
`src/`. Run from a clone of the repository, `../../src` is right there. On Colab there is no clone
until this cell makes one, and no `gurobipy` until it installs it. Nothing here needs a secret.
""")
code(r'''
import os, subprocess, sys

REPO_URL = "https://github.com/sear-labs/teaching-code"
REF = "v1.0.0"                               # the release this notebook ships in: Colab clones THIS

try:
    import google.colab                      # noqa: F401 - succeeds only on Colab
    ON_COLAB = True
except ImportError:
    ON_COLAB = False

if ON_COLAB:
    if not os.path.isdir("/content/teaching-code"):
        subprocess.run(["git", "clone", "--quiet", "--depth", "1", "--branch", REF, REPO_URL, "/content/teaching-code"], check=True)
    os.chdir("/content/teaching-code/notebooks/02_simplex_and_bases")
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "gurobipy>=11,<14"], check=True)

sys.path.insert(0, os.path.abspath(os.path.join("..", "..", "src")))
try:
    import orteach                            # noqa: F401
except ImportError:
    raise SystemExit("orteach not found: run this notebook from its own folder inside the repository, "
                     "so that ../../src exists.")
root = os.path.abspath(os.path.join("..", ".."))
print("package:", os.path.relpath(os.path.dirname(orteach.__file__), root))
''')

md(r"""
## Licence setup

Only the cross-check at the end uses a solver. Nothing here needs a key: `pip install gurobipy`
ships a size-limited licence and this model is tiny. The environment starts silent, so no licence
number lands in an output cell.
""")
code(r'''
import gurobipy as gp
from gurobipy import GRB

env = gp.Env(empty=True)
env.setParam("OutputFlag", 0)        # start silent: the licence banner, and its licence number, stay out of the outputs
try:
    from google.colab import userdata
    try:
        env.setParam("WLSACCESSID", userdata.get("GRB_WLSACCESSID"))
        env.setParam("WLSSECRET",   userdata.get("GRB_WLSSECRET"))
        env.setParam("LICENSEID",   int(userdata.get("GRB_LICENSEID")))
        licence = "Colab Secrets (WLS)"
    except (userdata.SecretNotFoundError, userdata.NotebookAccessError):
        licence = "the size-limited licence pip ships"     # no key needed; see the note above
except ImportError:
    licence = "local gurobi.lic"
env.start()
print("licence:", licence)
''')

md(r"""
## The LP, and its standard form

Two products, two resources: maximise $40x_1 + 50x_2$ subject to $x_1 + 2x_2 \le 40$ and
$4x_1 + 3x_2 \le 120$. It is a table in `data/raw/`, read by the same loader the duality notebook
uses.

The simplex method works on equations, so each `<=` row gets a slack variable, $s_1$ and $s_2$:
how much of that resource is left over. Two equations, four unknowns.
""")
code(r'''
import numpy as np
from orteach.duality import load_lp

lp = load_lp("lp_simplex_40_50.csv")
names = ["x1", "x2", "s1", "s2"]
A = np.array([[lp.A["c1", "x1"], lp.A["c1", "x2"], 1.0, 0.0],
              [lp.A["c2", "x1"], lp.A["c2", "x2"], 0.0, 1.0]])
b = np.array([lp.b["c1"], lp.b["c2"]])
c = np.array([lp.c["x1"], lp.c["x2"], 0.0, 0.0])
print("A =\n", A, "\nb =", b, "\nc =", c)
''')

md(r"""
## Every corner is a choice of basis

Pick two of the four columns to be **basic**, set the other two to zero, and solve the two
equations for the basic pair. Every corner of the feasible region is one such choice. The converse
fails: some choices give a point with a negative variable, which is a corner of the lines but not of
the region.

There are $\binom{4}{2} = 6$ choices. Predict before running: how many are feasible, and which is
best?
""")
code(r'''
from itertools import combinations

corners = []
for basis in combinations(range(4), 2):                     # the same three lines for every choice
    x = np.zeros(4)
    x[list(basis)] = np.linalg.solve(A[:, basis], b)
    corners.append((basis, x, bool((x >= 0).all()), float(c @ x)))

print(f"{'basic':12} {'x1':>7} {'x2':>7} {'s1':>7} {'s2':>7}  feasible  objective")
for basis, x, ok, z in corners:
    print(f"{names[basis[0]] + ', ' + names[basis[1]]:12} " + " ".join(f"{v:7.2f}" for v in x) + f"  {ok!s:8}  {z:9.2f}")
''')

md(r"""
Enumerating is fine for six. With 50 variables and 30 constraints there are 80 columns and
$inom{80}{30}$ choices, about $9 	imes 10^{21}$.
The simplex method visits a handful of them, always moving to a neighbour that is no worse.

## The tableau

The objective becomes a row too: $z - 40x_1 - 50x_2 = 0$. Row 0 is that equation, rows 1 and 2
are the constraints, the last column is the right-hand side. The slacks are the starting basis,
which is the corner at the origin.
""")
code(r'''
T = np.zeros((3, 5))
T[0, :4] = -c + 0.0                              # + 0.0: a printed -0.00 becomes 0.00
T[1:, :4] = A
T[1:, 4] = b
basis = [2, 3]                                   # s1, s2

print("        x1      x2      s1      s2     rhs")
for label, row in zip(["z"] + [names[j] for j in basis], T):
    print(f"{label:4}" + "".join(f"{v:8.2f}" for v in row))
''')

md(r"""
## First pivot

**Entering:** a negative number in row 0 means raising that variable raises $z$. Take the most
negative. **Leaving:** raise the entering variable until some basic variable hits zero; the ratio
of right-hand side to the entering column, over rows where that column is positive, says which
hits zero first. Predict both before running.
""")
code(r'''
enter = int(np.argmin(T[0, :4]))
ratios = [T[i, 4] / T[i, enter] if T[i, enter] > 0 else np.inf for i in (1, 2)]
leave_row = 1 + int(np.argmin(ratios))
print("entering", names[enter], "  ratios", [round(float(r), 2) for r in ratios], "  leaving", names[basis[leave_row - 1]])
''')

md(r"""
The pivot itself is three row operations: scale the leaving row so the entering column holds a 1
there, then subtract multiples of it to clear that column from the other two rows. Written out.
""")
code(r'''
T[leave_row] = T[leave_row] / T[leave_row, enter]
T[0] = T[0] - T[0, enter] * T[leave_row]
other = 3 - leave_row                            # the constraint row that did not leave
T[other] = T[other] - T[other, enter] * T[leave_row]
basis[leave_row - 1] = enter

print("        x1      x2      s1      s2     rhs")
for label, row in zip(["z"] + [names[j] for j in basis], T):
    print(f"{label:4}" + "".join(f"{v:8.2f}" for v in row))
corner_1 = np.zeros(4)
corner_1[basis] = T[1:, 4]
print("\nnow at", dict(zip(names, corner_1.round(4).tolist())), "  z =", T[0, 4])
''')

md(r"""
Which corner from the enumeration is this? Is row 0 free of negative numbers yet?

## Second pivot

The same two choices, on the new tableau. Predict which variable enters and which leaves.
""")
code(r'''
enter = int(np.argmin(T[0, :4]))
ratios = [T[i, 4] / T[i, enter] if T[i, enter] > 0 else np.inf for i in (1, 2)]
leave_row = 1 + int(np.argmin(ratios))
print("entering", names[enter], "  ratios", [round(float(r), 2) for r in ratios], "  leaving", names[basis[leave_row - 1]])

T[leave_row] = T[leave_row] / T[leave_row, enter]
T[0] = T[0] - T[0, enter] * T[leave_row]
other = 3 - leave_row
T[other] = T[other] - T[other, enter] * T[leave_row]
basis[leave_row - 1] = enter

print("\n        x1      x2      s1      s2     rhs")
for label, row in zip(["z"] + [names[j] for j in basis], T):
    print(f"{label:4}" + "".join(f"{v:8.2f}" for v in row))
corner_2 = np.zeros(4)
corner_2[basis] = T[1:, 4]
print("\nnow at", dict(zip(names, corner_2.round(4).tolist())), "  z =", T[0, 4])
''')

md(r"""
## Stop

No negative number is left in row 0, so no neighbouring corner is better: this corner is optimal.
Row 0 also holds two more numbers under the slacks. Compare them with the duals the duality
notebook in `03` reads off a solver: what do they price?
""")
code(r'''
print("row 0 nonnegative:", bool((T[0, :4] >= 0).all()))
hand_path = [(0.0, 0.0, 0.0), (float(corner_1[0]), float(corner_1[1]), float(c @ corner_1)),
             (float(corner_2[0]), float(corner_2[1]), float(c @ corner_2))]
print("path (x1, x2, z):", [tuple(round(v, 4) for v in p) for p in hand_path])
print("row 0 under s1, s2:", T[0, 2:4])
''')

md(r"""
## A solver, for comparison

Gurobi's own simplex (`Method=0`) on the same table. Predict whether it reports the same corner,
and whether the duals match row 0.
""")
code(r'''
m = gp.Model("simplex check", env=env)
m.Params.Method = 0
xg = m.addVars(lp.variables, name="x")
rows = {r: m.addConstr(lp.row_expr(r, xg) <= lp.b[r], name=r) for r in lp.rows}
m.setObjective(gp.quicksum(lp.c[j] * xg[j] for j in lp.variables), GRB.MAXIMIZE)
m.optimize()
gurobi_z = m.ObjVal
print(f"Gurobi: x1 {xg['x1'].X:.4f}  x2 {xg['x2'].X:.4f}  z {gurobi_z:.4f}   duals", {r: round(rows[r].Pi, 4) for r in lp.rows})
''')

md(r"""
---

# Now the streamlined version

The enumeration and the pivots, once each, in `orteach.simplex`: `basic_solutions` returns every
choice of basis, and `tableau_path` the corners the simplex visits, with the same rules used here
(most negative entry in row 0 enters; smallest ratio leaves; lowest index on a tie).
""")
code(r'''
from orteach import simplex as sx
from orteach.tolerance import AGREEMENT_RTOL, rel_diff

pkg_corners = sx.basic_solutions(lp)
pkg_path = sx.tableau_path(lp)
print(len(pkg_corners), "bases,", sum(k.feasible for k in pkg_corners), "feasible")
print("path:", [(round(float(k.x["x1"]), 4), round(float(k.x["x2"]), 4), round(k.objective, 4)) for k in pkg_path])
''')

md(r"""
## The agreement assertion

The six bases (each point, its feasibility and its objective), the path walked, and the optimum
against Gurobi's. With no ties anywhere in this tableau, the path is the problem's and not a
tie-break's, so it is compared corner by corner.
""")
code(r'''
checks = []
assert len(pkg_corners) == len(corners), "different number of bases"
for (basis_h, x_h, ok_h, z_h), k in zip(corners, pkg_corners):
    assert ok_h == k.feasible, "feasibility differs at " + str(k.basis)
    for j, name in enumerate(names):
        checks.append((f"{k.basis} {name}", x_h[j], k.x[list(k.x)[j]]))
    checks.append((f"{k.basis} z", z_h, k.objective))
assert len(pkg_path) == len(hand_path), "different number of pivots"
for (x1, x2, z), k in zip(hand_path, pkg_path):
    checks += [("path x1", x1, k.x["x1"]), ("path x2", x2, k.x["x2"]), ("path z", z, k.objective)]
checks.append(("optimum vs Gurobi", hand_path[-1][2], gurobi_z))

worst = max(rel_diff(h, k) for _, h, k in checks)
print(f"{len(checks)} comparisons, plus feasibility of every basis")
assert worst < AGREEMENT_RTOL, f"notebook and package disagree by {worst:.2e}"
print(f"notebook and package agree to {worst:.1e}")
''')

md(r"""
---

## Where to take this next

- The slides' exercise is `lp_wyndor.csv` (max $3x_1 + 5x_2$, three plants). Load it and pivot it
  by hand: the tableau has one more row, so each pivot clears two other rows, not one.
- Change the objective to $40x_1 + 80x_2$. Row 0 at the optimum now has a zero under a nonbasic
  variable. What does that zero mean about the set of optimal solutions?
- `interior_point.ipynb` in this folder solves the same LP without visiting any corner at all.
""")

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                   "language_info": {"name": "python", "version": "3.13"}}, "nbformat": 4, "nbformat_minor": 5}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    f.write("\n")
print("wrote %s  (%d cells)" % (OUT, len(cells)))
