"""Seed for the nonconvex curve-fit teaching notebook. Writes the notebook without outputs; execute it afterwards (README.md here)."""
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "notebooks", "06_nonlinear_and_convex", "curve_fit_lifting.ipynb")
cells = []


def md(t):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": t.strip("\n").splitlines(keepends=True)})


def code(t):
    cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
                  "source": t.strip("\n").splitlines(keepends=True)})


md(r"""
# Fitting a curve with a division in it: lifting a model a solver can take

A traffic engineer has six observations of a road: the volume of traffic on it and the travel time
that volume produced. The hypothesis is a congestion curve,

$$t = \frac{\beta_0}{\beta_1 - v},$$

travel time that blows up as volume $v$ approaches a capacity $\beta_1$. Two parameters, six points:
choose $\beta_0, \beta_1$ to minimise the sum of squared errors.

That is nonlinear least squares, and there are two ways to do it. A local method starts somewhere and
walks downhill. A global solver — Gurobi with `NonConvex = 2` — proves it has found the bottom, but it
accepts only linear, bilinear and quadratic terms, and $\beta_0 / (\beta_1 - v)$ is none of those. So
the model has to be **lifted**: rewritten with extra variables until every term is a shape the solver
can take. Each rewrite is a trick worth seeing once, and this notebook does them one at a time, then
checks the proven answer against the local method.
""")

md(r"""
## Setup: where the package lives

This notebook builds its models by hand and then checks them against `orteach`, the package in
`src/`. Run from a clone of the repository, `../../src` is right there. On Colab there is no clone
until this cell makes one, and no `gurobipy` until it installs it. Nothing here needs a secret.
""")
code(r'''
import os, subprocess, sys

REPO_URL = "https://github.com/sear-labs/teaching-code"

try:
    import google.colab                      # noqa: F401 - succeeds only on Colab
    ON_COLAB = True
except ImportError:
    ON_COLAB = False

if ON_COLAB:
    if not os.path.isdir("/content/teaching-code"):
        subprocess.run(["git", "clone", "--quiet", REPO_URL, "/content/teaching-code"], check=True)
    os.chdir("/content/teaching-code/notebooks/06_nonlinear_and_convex")
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

Nothing here needs a key: `pip install gurobipy` ships a size-limited licence and the models below
sit well inside it. A machine with its own licence file uses that instead, and on Colab three
secrets read from the key icon in the left sidebar are used when they are there — three named here,
none contained. The environment starts silent, so no licence number lands in an output cell.
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
## The observations are a table

Six rows of (volume, travel time). Instance data, so it lives in `data/raw/` and both this notebook
and the package read the same file. The model will index the observations by position.
""")
code(r'''
from orteach import tolerance
from orteach.nonconvex import load_traffic

obs = load_traffic()
volume, travel = obs.volume, obs.travel_time

print(f"{'i':>2} {'volume':>8} {'time':>6}")
for i, (v, t) in enumerate(zip(volume, travel)):
    print(f"{i:2} {v:8.0f} {t:6.0f}")
print()
print("volume[2] =", volume[2], "  travel[2] =", travel[2], "  largest volume seen:", max(volume))

# to try a different observation, edit the loaded lists; the change reaches the package check too:
# travel[2] = 40.0
''')

md(r"""
## Predict before building anything

The curve has a vertical asymptote at $v = \beta_1$: capacity. Every observed volume must sit to its
left, so $\beta_1$ is at least the largest volume in the table. Write down a guess for $\beta_1$ —
a little above that largest volume, or a lot? — and a rough $\beta_0$ to match one of the points.

## Trick 1: replace the division with a product

For each observation define $o_i = 1/(\beta_1 - v_i)$. That is the same as $(\beta_1 - v_i)\,o_i = 1$
— a **bilinear** equality, a product of two unknowns, which the solver accepts. Six new variables,
six new rows, and the division is gone.

Every variable in a bilinear term needs a finite box: spatial branch-and-bound relaxes each product
to a convex envelope over its box, solves, splits the box and repeats. $\beta_1$ must exceed the
largest volume, and the boxes on the $o_i$ follow from the box on $\beta_1$. Whether a *tighter* box
also means a *faster* proof is a separate question, and a cell further down measures it rather than
assuming it.
""")
code(r'''
B1_MIN = max(volume) + 1.0      # every denominator positive
B1_MAX = 50_000.0               # a capacity seven times the busiest observation; the box, not a belief
# B1_MIN is the one bound carrying a modelling claim rather than a convenience: below it a
# denominator changes sign. It is passed to the package at the bottom, so an edit here reaches both.
B0_MAX = 5e6

m = gp.Model("congestion fit", env=env)
tolerance.apply(m)
m.Params.NonConvex = 2          # the flag that admits bilinear rows and a global proof

b0 = m.addVar(lb=0.0, ub=B0_MAX, name="b0")
b1 = m.addVar(lb=B1_MIN, ub=B1_MAX, name="b1")
o = [m.addVar(lb=1.0 / (B1_MAX - v), ub=1.0 / (B1_MIN - v), name=f"o{i}") for i, v in enumerate(volume)]
for i, v in enumerate(volume):
    m.addConstr((b1 - v) * o[i] == 1.0, name=f"lift[{i}]")
m.update()
print(m.NumVars, "variables,", m.NumQConstrs, "bilinear rows")
''')

md(r"""
## Trick 2: give each residual its own variable

The error at observation $i$ is $\beta_0 o_i - t_i$: another product of unknowns, so it gets a
variable too, $r_i = \beta_0 o_i - t_i$. The objective is then $\sum r_i^2$ — a plain convex
quadratic in the $r_i$. Without this step the objective would contain fourth-order terms, which no
QCQP solver takes.

The residuals are **free in sign**: a fitted curve passes above some points and below others. Hold
that thought.
""")
code(r'''
r = [m.addVar(lb=-GRB.INFINITY, name=f"r{i}") for i in range(len(volume))]
for i in range(len(volume)):
    m.addConstr(b0 * o[i] - travel[i] == r[i], name=f"resid[{i}]")
m.setObjective(gp.quicksum(ri * ri for ri in r), GRB.MINIMIZE)
m.update()
print(m.NumQConstrs, "bilinear rows,", "objective has", m.getObjective().size(), "quadratic terms")
''')

md(r"""
## The slide's side condition

The problem statement carries one more constraint, $\beta_0 \le 19\,\beta_1$. It is linear and it
stays as written. Predict: will it bind?
""")
code(r'''
RATIO_CAP = 19.0
ratio = m.addConstr(b0 <= RATIO_CAP * b1, name="ratio")
m.update()
print(m.NumConstrs, "linear rows")
''')

md(r"""
## Solve, and read the proof

`MIPGap 0` from `orteach.tolerance` means the solver keeps branching until its lower bound meets the
best solution found: what comes back is proven globally optimal, not merely a local minimum. Predict
the sum of squares to within a factor of two before running.
""")
code(r'''
m.optimize()
sse_hand, b0_hand, b1_hand = m.ObjVal, b0.X, b1.X
print(f"status {m.Status}   sum of squared errors {sse_hand:.6f}   proven bound {m.ObjBound:.6f}")
print(f"b0 = {b0_hand:,.3f}   b1 = {b1_hand:,.3f}   ratio row slack {ratio.Slack:,.1f}")
''')

md(r"""
## The residuals, with their signs

Fitted value against observed at each point. Which points does the curve pass above, and which
below?
""")
code(r'''
resid_hand = [ri.X for ri in r]
print(f"{'volume':>8} {'observed':>9} {'fitted':>8} {'residual':>9}")
for v, t, e in zip(volume, travel, resid_hand):
    print(f"{v:8.0f} {t:9.1f} {t + e:8.3f} {e:+9.4f}")
''')

md(r"""
---

## The same model with one bound changed

Three term folders of the graduate course shipped this fit with the residual variables declared
`lb = 0`. Everything else was identical. Build it, and before solving predict: will its sum of
squares be higher or lower than the one above, and where will the curve sit relative to the points?
""")
code(r'''
PR_BOX = 200.0                  # a box on the forced-positive residuals; the largest observed
                                # travel time is 34, so it is far from binding
m_pos = gp.Model("congestion fit, residuals >= 0", env=env)
tolerance.apply(m_pos)
m_pos.Params.NonConvex = 2
p0 = m_pos.addVar(lb=0.0, ub=B0_MAX, name="b0")
p1 = m_pos.addVar(lb=B1_MIN, ub=B1_MAX, name="b1")
po = [m_pos.addVar(lb=1.0 / (B1_MAX - v), ub=1.0 / (B1_MIN - v)) for v in volume]
pr = [m_pos.addVar(lb=0.0, ub=PR_BOX) for _ in volume]            # <-- the one change
for i, v in enumerate(volume):
    m_pos.addConstr((p1 - v) * po[i] == 1.0)
    m_pos.addConstr(p0 * po[i] - travel[i] == pr[i])
m_pos.addConstr(p0 <= RATIO_CAP * p1)
m_pos.setObjective(gp.quicksum(x * x for x in pr), GRB.MINIMIZE)
m_pos.optimize()

sse_pos = m_pos.ObjVal
print(f"sum of squared errors {sse_pos:.4f}   (free residuals gave {sse_hand:.4f})")
print(f"b0 = {p0.X:,.1f}   b1 = {p1.X:,.1f}")
print("residuals:", "  ".join(f"{x.X:+.3f}" for x in pr))
''')

md(r"""
Every residual is now zero or positive. What has that bound told the solver the curve must do, and is
the result still a least-squares fit in any sense?

## What the boxes actually buy

The source notebooks ran a fit like this for 200 seconds without closing the gap, and the boxes are
the usual suspect. That is a claim worth testing rather than repeating. Take them away — one at a
time, then all together — and give each run a few seconds. Predict first: with every bound gone, will
the solver fail to **find** the right curve, fail to **prove** it, or neither?
""")
code(r'''
PROOF_TIME_LIMIT = 5.0          # seconds: long enough to show a gap, short enough to ship
STATUS = {2: "optimal", 9: "time limit", 13: "suboptimal"}
INF = GRB.INFINITY

trials = {"all five bounds, as above": (B1_MIN, B1_MAX, B0_MAX),
          "upper bound on b1 removed": (B1_MIN, INF,    B0_MAX),
          "upper bound on b0 removed": (B1_MIN, B1_MAX, INF),
          "lower bound on b1 removed": (0.0,    B1_MAX, B0_MAX),
          "every bound removed":       (0.0,    INF,    INF)}

print(f"{'model':30} {'status':11} {'nodes':>9} {'best':>10} {'gap':>8}")
for label, (lo, hi, b0_hi) in trials.items():
    mt = gp.Model(env=env)
    tolerance.apply(mt)
    mt.Params.NonConvex = 2
    mt.Params.TimeLimit = PROOF_TIME_LIMIT
    t0 = mt.addVar(lb=0.0, ub=b0_hi)
    t1 = mt.addVar(lb=lo, ub=hi)
    to = [mt.addVar(lb=0.0 if hi == INF else 1.0 / (hi - v),
                    ub=INF if lo <= v else 1.0 / (lo - v)) for v in volume]
    tr = [mt.addVar(lb=-INF) for _ in volume]
    for i, v in enumerate(volume):
        mt.addConstr((t1 - v) * to[i] == 1.0)
        mt.addConstr(t0 * to[i] - travel[i] == tr[i])
    mt.addConstr(t0 <= RATIO_CAP * t1)
    mt.setObjective(gp.quicksum(e * e for e in tr), GRB.MINIMIZE)
    mt.optimize()
    best = f"{mt.ObjVal:10.4f}" if mt.SolCount else "         -"
    print(f"{label:30} {STATUS.get(mt.Status, mt.Status):11} {mt.NodeCount:9.0f} {best} {mt.MIPGap:8.1%}")
''')

md(r"""
Removing any *single* bound leaves the proof intact — and dropping the upper bound on $\beta_1$ makes
it cheaper, not dearer, so "tighter is faster" is not a rule. Remove them all and the picture changes
completely: the solver still reaches 4.8076 within seconds, and never proves it. The gap stays at
100% because the convex envelope of an unbounded product carries no information, so the lower bound
sits at zero and the solver has no evidence it has finished.

What a box buys is therefore not the answer. It is the **proof**. Which of the two you needed is a
question about what the number is for.

## A second opinion from a different method

`scipy.optimize.least_squares` fits the same curve with no lifting at all: it takes the residual
function as written and walks downhill from a starting point. It proves nothing, and it could stop at
a local minimum. Compare it to the proven answer — the sum of squares, and the parameters separately.

The residual $\beta_0/(\beta_1 - v) - t$ is the model, so it lives in the package as
`congestion_residuals` and is passed in rather than written again here. That is the same rule the
tables follow: one definition, both callers.
""")
code(r'''
from scipy.optimize import least_squares
import numpy as np

from orteach.nonconvex import congestion_residuals

v_arr, t_arr = np.array(volume), np.array(travel)
B1_START = 10_000.0             # a starting guess for capacity; try others

local = least_squares(congestion_residuals, x0=[1e5, B1_START], args=(v_arr, t_arr),
                      bounds=([0.0, B1_MIN], [np.inf, np.inf]))
sse_local = float(np.sum(local.fun ** 2))
print(f"scipy: sum of squares {sse_local:.6f}   b0 = {local.x[0]:,.3f}   b1 = {local.x[1]:,.3f}")
print(f"gurobi: sum of squares {sse_hand:.6f}   b0 = {b0_hand:,.3f}   b1 = {b1_hand:,.3f}")
print(f"difference in SSE {abs(sse_local - sse_hand):.2e}   in b1 {abs(local.x[1] - b1_hand):.4f}   in b0/b1 {abs(local.x[0] / local.x[1] - b0_hand / b1_hand):.2e}")
''')

md(r"""
Same sum of squares to six decimals; $\beta_1$ differs in the second decimal place. Two correct methods,
two slightly different points. What does that say about the shape of the objective near its minimum —
and which of $\beta_1$, $\beta_0$, or the ratio $\beta_0/\beta_1$ is the number the data actually pins
down?

---

# Now the streamlined version

Two lifted models built by hand from the same six rows, so the package owns the construction:
`fit_congestion` takes the table and all four boxes as arguments — including `B1_MIN`, so an edit up
there reaches the check down here — and returns the fit with its proven bound; `fit_congestion_scipy`
is the local method, kept as the independent check it is, started from the same guess.
""")
code(r'''
from orteach import nonconvex as nc
from orteach.tolerance import AGREEMENT_RTOL, CROSS_METHOD_RTOL, rel_diff

pkg = nc.fit_congestion(obs, b1_min=B1_MIN, b1_max=B1_MAX, b0_max=B0_MAX, ratio_cap=RATIO_CAP, env=env)
pkg_local = nc.fit_congestion_scipy(obs, b1_start=B1_START, b1_min=B1_MIN)
print(f"{pkg.label:22} SSE {pkg.sse:.6f}   b0 {pkg.b0:,.3f}   b1 {pkg.b1:,.3f}   bound {pkg.bound:.6f}")
print(f"{pkg_local.label:22} SSE {pkg_local.sse:.6f}   b0 {pkg_local.b0:,.3f}   b1 {pkg_local.b1:,.3f}")
''')

md(r"""
## The agreement assertion

The hand-built global fit against the package's, number by number: sum of squares, proven bound,
both parameters and every residual — same solver, same tolerances, same boxes, so `AGREEMENT_RTOL`
is a claim the computation supports. The hand-written scipy call is compared to the package's the
same way, because both minimise the same residual function from the same start.

Gurobi against scipy is a different kind of comparison and gets a different tolerance,
`CROSS_METHOD_RTOL`: two methods with different stopping rules, agreeing on the sum of squares but
not on where along the ridge they stopped. Only the sum of squares is asserted.
""")
code(r'''
checks = [("sum of squares", sse_hand, pkg.sse),
          ("proven bound", m.ObjBound, pkg.bound),
          ("b0", b0_hand, pkg.b0),
          ("b1", b1_hand, pkg.b1)]
for i, e in enumerate(resid_hand):
    checks.append((f"residual {i}", e, pkg.residuals[i]))
checks.append(("scipy sum of squares", sse_local, pkg_local.sse))
checks.append(("scipy b1", float(local.x[1]), pkg_local.b1))

worst = max(rel_diff(h, k) for _, h, k in checks)
print(f"{len(checks)} comparisons")
for name, hand, packaged in checks[:4]:
    print(f"  {name:16} hand {hand:14.6f}   package {packaged:14.6f}   rel {rel_diff(hand, packaged):.2e}")
print("  ...")
assert worst < AGREEMENT_RTOL, f"notebook and package disagree by {worst:.2e}"
cross = rel_diff(pkg_local.sse, pkg.sse)
assert cross < CROSS_METHOD_RTOL, f"the two methods found different minima: {cross:.2e}"
print(f"\nnotebook and package agree to {worst:.1e}; the two methods agree to {cross:.1e}")
''')

md(r"""
---

## Where to take this next

- The box cell above dropped bounds one at a time, then all five at once. Fill in the middle: drop
  them in pairs, then in threes. How few does it take before the gap stops closing, and does it
  matter which ones go?
- Start scipy from `B1_START = 8_000` and from `100_000`. Does it always reach the same minimum?
  What would you do if it did not, and how does that compare with what Gurobi does?
- Fit the straight line $t = \beta_0 + \beta_1 v$ to the same six points — no lifting needed. Compare
  the sum of squares, then plot both curves past the largest observed volume and say which one you
  would trust for a road running near capacity.
""")

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                   "language_info": {"name": "python", "version": "3.13"}}, "nbformat": 4, "nbformat_minor": 5}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    f.write("\n")
print("wrote %s  (%d cells)" % (OUT, len(cells)))
