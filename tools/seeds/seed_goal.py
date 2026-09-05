"""Seed for the goal programming teaching notebook. Writes the notebook without outputs; execute it afterwards (README.md here)."""
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "notebooks", "01_lp_formulation", "goal_programming.ipynb")
cells = []


def md(t):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": t.strip("\n").splitlines(keepends=True)})


def code(t):
    cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
                  "source": t.strip("\n").splitlines(keepends=True)})


md(r"""
# Goal programming: when the targets cannot all be met

An advertising agency has a contract to promote a product on radio and television. A minute of each
reaches a known number of people, costs a known amount, and ties up a known amount of the agency's
staff. There are ten person-minutes of staff time, and the contract caps radio at six minutes.

Management has two targets: reach at least 45 million people, and spend no more than $100 thousand. Call
them **goals** rather than constraints, and check first whether any plan can meet both — a
constraint that cannot be met makes the whole problem infeasible, and goal programming exists for
that case: *by how little must each target be missed, in order of importance?*

This is Taha's TopAd example. The formulation is small; the decision that matters is not visible in
the notation.
""")

md(r"""
## Setup: where the package lives

This notebook builds its models by hand and then checks them against `orteach`, the package in
`src/`. Run from a clone of the repository, `../../src` is right there. On Colab there is no clone
until this cell makes one, and no `gurobipy` until it installs it. Nothing here needs a secret.
""")
code(r'''
import os, subprocess, sys

REPO_URL = None      # the public GitHub URL, once this library is published; Colab clones from it

try:
    import google.colab                      # noqa: F401 - succeeds only on Colab
    ON_COLAB = True
except ImportError:
    ON_COLAB = False

if ON_COLAB:
    if REPO_URL is None:
        raise SystemExit("This library is not published yet: open the notebook from a clone of the repository.")
    if not os.path.isdir("/content/teaching-code"):
        subprocess.run(["git", "clone", "--quiet", REPO_URL, "/content/teaching-code"], check=True)
    os.chdir("/content/teaching-code/notebooks/01_lp_formulation")
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "gurobipy>=11,<14"], check=True)

sys.path.insert(0, os.path.abspath(os.path.join("..", "..", "src")))
try:
    import orteach                            # noqa: F401
except ImportError:
    raise SystemExit("orteach not found: run this notebook from its own folder inside the repository, "
                     "so that ../../src exists.")
print("package:", os.path.dirname(orteach.__file__))
''')

md(r"""
## Licence setup

Three secrets named, none contained. Colab reads them from the key icon in the left sidebar; a
machine with a licence file needs nothing. The environment starts silent, so the licence number
never lands in an output cell.
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
    except (userdata.SecretNotFoundError, userdata.NotebookAccessError):
        raise SystemExit("Add GRB_WLSACCESSID, GRB_WLSSECRET and GRB_LICENSEID as Colab Secrets "
                         "(key icon, left sidebar), grant this notebook access to them, then re-run this cell.")
    env.start()
    print("licence: Colab Secrets (WLS)")
except ImportError:
    env.start()
    print("licence: local gurobi.lic")
''')

md(r"""
## The table, and the knobs

The per-medium numbers are a table — indexed by medium, read from `data/raw/` by both this notebook
and the package. The four scalars are knobs: each carries a concept the story names, so each is
written out here, and handed to the package explicitly at the bottom.

Exposure is in millions of people per minute; cost in thousands of dollars per minute; labor in
person-minutes per broadcast minute.
""")
code(r'''
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join("..", "..", "src")))
from orteach import tolerance
from orteach.goal_programming import load_topad

LABOR_CAP     = 10.0     # person-minutes of staff time available
RADIO_CAP     = 6.0      # minutes of radio the contract allows
EXPOSURE_GOAL = 45.0     # millions of people, want at least
BUDGET        = 100.0    # thousands of dollars, want at most

inst = load_topad(labor_cap=LABOR_CAP, radio_cap=RADIO_CAP, exposure_goal=EXPOSURE_GOAL, budget=BUDGET)

print(f"{'medium':8} {'exposure':>9} {'cost':>7} {'labor':>7}")
for i in inst.media:
    print(f"{i:8} {inst.exposure[i]:9.1f} {inst.cost[i]:7.1f} {inst.labor[i]:7.1f}")
print()
print("exposure['tv'] =", inst.exposure["tv"], "  cost['radio'] =", inst.cost["radio"])

# to try a cheaper TV minute, edit the loaded table; the change reaches the package check too:
# inst.cost["tv"] = 20.0
''')

md(r"""
## First, the plain LP

Treat the budget as a hard limit and maximise exposure. This is the model the goal program grows out
of, and its answer tells you whether goal programming is needed at all.
""")
code(r'''
lp = gp.Model("TopAd, max exposure", env=env)
tolerance.apply(lp)
minutes = lp.addVars(inst.media, lb=0.0, name="minutes")

lp.addConstr(gp.quicksum(inst.labor[i] * minutes[i] for i in inst.media) <= LABOR_CAP, name="labor")
lp.addConstr(minutes["radio"] <= RADIO_CAP, name="radio_contract")
lp.addConstr(gp.quicksum(inst.cost[i] * minutes[i] for i in inst.media) <= BUDGET, name="budget")
lp.setObjective(gp.quicksum(inst.exposure[i] * minutes[i] for i in inst.media), GRB.MAXIMIZE)
lp.update()
print(lp.NumVars, "variables,", lp.NumConstrs, "constraints")
''')

md(r"""
Predict before you run it: can 45 million be reached within ten person-minutes? Look at the labor
column and the exposure column together.
""")
code(r'''
lp.optimize()
lp_max = lp.ObjVal
print(f"\nmost exposure the hard constraints allow: {lp_max:.1f} million   (goal: {EXPOSURE_GOAL:.0f})")
for i in inst.media:
    print(f"  {i:6} {minutes[i].X:5.2f} min")
''')

md(r"""
## What happens if you insist

Add the exposure target as a constraint anyway and ask the solver. Status 3 is `GRB.INFEASIBLE`.
""")
code(r'''
insist = lp.addConstr(gp.quicksum(inst.exposure[i] * minutes[i] for i in inst.media) >= EXPOSURE_GOAL,
                      name="exposure_as_constraint")
lp.optimize()
print(f"\nstatus {lp.Status}   infeasible: {lp.Status == GRB.INFEASIBLE}")
lp.remove(insist)
''')

md(r"""
No plan exists. The LP has nothing more to say. That is the situation goal programming is for.

## Goals as equations with two deviations

Each goal becomes an *equality* with a pair of slack variables that absorb the miss in either
direction:

$$\text{exposure} = \text{goal} + \text{over} - \text{under}, \qquad
  \text{cost} = \text{budget} + \text{over} - \text{under}$$

Both deviations are non-negative, and at most one of each pair is positive at the optimum. Before
building it, write down which deviation is the *bad* one for each goal — the one you would want
small. They are not the same one.
""")
code(r'''
g = gp.Model("TopAd, goal program", env=env)
tolerance.apply(g)

x     = g.addVars(inst.media, lb=0.0, name="minutes")
over  = g.addVars(["exposure", "budget"], lb=0.0, name="over")
under = g.addVars(["exposure", "budget"], lb=0.0, name="under")
g.update()
print(g.NumVars, "variables:", list(x.keys()), list(over.keys()), list(under.keys()))
''')

md(r"""
The hard constraints are unchanged: staff time and the radio contract are physical limits, not
aspirations.
""")
code(r'''
g.addConstr(gp.quicksum(inst.labor[i] * x[i] for i in inst.media) <= LABOR_CAP, name="labor")
g.addConstr(x["radio"] <= RADIO_CAP, name="radio_contract")
g.update()
print(g.NumConstrs, "hard constraints")
''')

md(r"""
The two goal rows. Note they are equalities — the deviations do the flexing — and note that the
budget no longer appears as a `<=` anywhere. Whether it acts as a ceiling now depends entirely on
which deviation the objective punishes.
""")
code(r'''
g.addConstr(gp.quicksum(inst.exposure[i] * x[i] for i in inst.media)
            == EXPOSURE_GOAL + over["exposure"] - under["exposure"], name="goal_exposure")
g.addConstr(gp.quicksum(inst.cost[i] * x[i] for i in inst.media)
            == BUDGET + over["budget"] - under["budget"], name="goal_budget")
g.update()
for c in g.getConstrs():
    print(f"{c.ConstrName:16} {g.getRow(c)}  {c.Sense}  {c.RHS}")
''')

md(r"""
## Priority 1: miss the exposure target by as little as possible

Preemptive goal programming takes the goals in order. The first stage ignores the budget entirely and
minimises the under-achievement of exposure. Predict the answer from the LP above before running.
""")
code(r'''
g.setObjective(under["exposure"], GRB.MINIMIZE)
g.optimize()
stage1 = g.ObjVal
print(f"\nstage 1: exposure falls short by {stage1:.2f} million at best")
for i in inst.media:
    print(f"  {i:6} {x[i].X:5.2f} min")
print(f"  cost {sum(inst.cost[i] * x[i].X for i in inst.media):.1f}   over budget by {over['budget'].X:.1f}")
''')

md(r"""
## The pin

Stage 2 must not give back any of stage 1. So the first deviation is capped **at the value the solver
just found** — read from `g.ObjVal`, not typed. The original notebooks wrote `s_minus[1] == 5` here,
which is the right number for this table and silently the wrong one for any other.
""")
code(r'''
under["exposure"].UB = stage1
g.update()
print(f"under['exposure'] now bounded to [{under['exposure'].LB}, {under['exposure'].UB}]")
''')

md(r"""
## Priority 2: overspend by as little as possible, without losing stage 1

The bad deviation for a budget is the **over**spend. Minimise that, inside the pin.
""")
code(r'''
g.setObjective(over["budget"], GRB.MINIMIZE)
g.optimize()
stage2 = g.ObjVal
plan_hand = {i: x[i].X for i in inst.media}
print(f"\nstage 2: over budget by {stage2:.2f} thousand, with exposure still short by {under['exposure'].X:.2f}")
for i in inst.media:
    print(f"  {i:6} {plan_hand[i]:5.2f} min")
print(f"  cost {sum(inst.cost[i] * plan_hand[i] for i in inst.media):.1f}")
''')

md(r"""
## The other deviation

Five term folders of this course minimised `under["budget"]` at this stage — the *under*spend.
Same model, same pin, the other variable in the pair. Predict what the solver will do with the
budget before you run it.
""")
code(r'''
g.setObjective(under["budget"], GRB.MINIMIZE)
g.optimize()
plan_wrong = {i: x[i].X for i in inst.media}
print(f"\nminimising the underspend instead: objective {g.ObjVal:.2f}")
for i in inst.media:
    print(f"  {i:6} {plan_wrong[i]:5.2f} min")
print(f"  cost {sum(inst.cost[i] * plan_wrong[i] for i in inst.media):.1f}   "
      f"over budget by {over['budget'].X:.1f}   exposure short by {under['exposure'].X:.1f}")
''')

md(r"""
The objective came back zero: the model got exactly what it asked for. Now read the cost line and
compare it with the stage-2 plan above. This run returned one plan; the original notebooks' run of
the same cell returned a plan costing exactly 100, which looked fine and was never questioned. What
was this objective actually asking for, and how many plans satisfy it?

## The weights method

The other classical approach: one LP, the two deviations priced against each other. Taha weights the
exposure miss twice as heavily as the overspend. Release the pin first — it belonged to the
preemptive method.
""")
code(r'''
W_EXPOSURE, W_BUDGET = 2.0, 1.0

under["exposure"].UB = GRB.INFINITY
g.setObjective(W_EXPOSURE * under["exposure"] + W_BUDGET * over["budget"], GRB.MINIMIZE)
g.optimize()
weighted_hand = g.ObjVal
print(f"\nweighted objective {weighted_hand:.2f}   "
      f"= {W_EXPOSURE:.0f} x {under['exposure'].X:.2f} + {W_BUDGET:.0f} x {over['budget'].X:.2f}")
for i in inst.media:
    print(f"  {i:6} {x[i].X:5.2f} min")
''')

md(r"""
## How many plans meet both goals equally?

Put both pins back — exposure short by exactly the stage-1 amount, nothing over budget — and ask the
same model for the *cheapest* plan that satisfies them and then the *dearest*. Every plan between the
two is optimal for the goal program too. Predict first: are the two endpoints the same plan?
""")
code(r'''
under["exposure"].UB = stage1
over["budget"].UB = stage2
cost_expr = gp.quicksum(inst.cost[i] * x[i] for i in inst.media)

endpoints = {}
for label, sense in (("cheapest", GRB.MINIMIZE), ("dearest", GRB.MAXIMIZE)):
    g.setObjective(cost_expr, sense)
    g.optimize()
    endpoints[label] = g.ObjVal
    print(f"{label:9} plan meeting both goals: " + "  ".join(f"{i} {x[i].X:5.2f}" for i in inst.media)
          + f"   cost {g.ObjVal:6.1f}")
''')

md(r"""
---

# Now the streamlined version

The same model has been built once and re-objectived four times, so the package owns it now. It
offers the by-stages solve you just did, the weights method, and a third route: Gurobi's
multi-objective API, which takes both deviations with a priority each and performs the pin
internally.
""")
code(r'''
from orteach import goal_programming as gpg
from orteach.tolerance import AGREEMENT_RTOL, rel_diff

pkg_lp    = gpg.max_exposure(inst, env=env)
pkg_pre   = gpg.solve_preemptive(inst, env=env)
pkg_hier  = gpg.solve_hierarchical(inst, env=env)
pkg_wtd   = gpg.solve_weighted(inst, weights=(W_EXPOSURE, W_BUDGET), env=env)

print(f"{'method':40} {'radio':>6} {'tv':>6} {'exposure':>9} {'cost':>7} {'short':>6} {'over':>5}")
for r in (pkg_pre, pkg_hier, pkg_wtd):
    print(f"{r.label:40} {r.minutes['radio']:6.2f} {r.minutes['tv']:6.2f} {r.exposure:9.1f} "
          f"{r.cost:7.1f} {r.under_exposure:6.2f} {r.over_budget:5.2f}")
''')

md(r"""
Whatever minutes the two preemptive rows show, both plans lie on the segment between the cheapest and
dearest endpoints printed above, and so does every other plan that meets both goals equally. Which of
them would you actually recommend, and what would you have to add to the model to make the solver
pick it?

## The agreement assertion

Goal programming's answer is the deviations — how far short, how far over — and those are what the
assertion compares: the hand-built stages against the package's by-stages solve and against Gurobi's
hierarchical solve, plus the LP bound and the weighted objective. The minutes are not compared, because
the optimum is a segment; each package plan is checked instead for feasibility, for equal attainment,
and for lying between the two endpoints.
""")
code(r'''
checks = [("LP max exposure", lp_max, pkg_lp),
          ("stage 1 shortfall (by stages)", stage1, pkg_pre.stages[0]),
          ("stage 2 overspend (by stages)", stage2, pkg_pre.stages[1]),
          ("stage 1 shortfall (hierarchical)", stage1, pkg_hier.stages[0]),
          ("stage 2 overspend (hierarchical)", stage2, pkg_hier.stages[1]),
          ("weighted objective", weighted_hand, pkg_wtd.stages[0])]
worst = max(rel_diff(h, p) for _, h, p in checks)
for name, hand, packaged in checks:
    print(f"  {name:34} hand {hand:8.3f}   package {packaged:8.3f}   rel {rel_diff(hand, packaged):.2e}")

for r in (pkg_pre, pkg_hier):
    assert sum(inst.labor[i] * r.minutes[i] for i in inst.media) <= LABOR_CAP + tolerance.FEASIBILITY_ATOL
    assert r.minutes["radio"] <= RADIO_CAP + tolerance.FEASIBILITY_ATOL
    assert rel_diff(EXPOSURE_GOAL - r.exposure, stage1) < AGREEMENT_RTOL
    assert max(r.cost - BUDGET, 0.0) <= stage2 + tolerance.FEASIBILITY_ATOL
    assert endpoints["cheapest"] - tolerance.FEASIBILITY_ATOL <= r.cost <= endpoints["dearest"] + tolerance.FEASIBILITY_ATOL
assert worst < AGREEMENT_RTOL, f"notebook and package disagree by {worst:.2e}"
print(f"\nnotebook and package agree to {worst:.1e}")
''')

md(r"""
---

## Where to take this next

- Set `BUDGET = 90.0` and run stage 2 both ways — `over["budget"]` and `under["budget"]`. Compare
  the two objective values and `over["budget"].X`, not the minutes. Which objective reports the true
  overrun, and how could you have told without knowing the answer?
- Swap the priorities: budget first, exposure second. Does the plan change? Does the *pin* change?
- Add a third priority that breaks the tie — spend as little as possible among plans that do equally
  well on the first two. Is the plan the solver now picks the one you would have recommended?
""")

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                   "language_info": {"name": "python", "version": "3.13"}}, "nbformat": 4, "nbformat_minor": 5}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    f.write("\n")
print("wrote %s  (%d cells)" % (OUT, len(cells)))
