"""Seed for the diet teaching notebook. Writes the notebook without outputs; execute it afterwards (README.md here)."""
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "notebooks", "01_lp_formulation", "diet.ipynb")
cells = []


def md(t):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": t.strip("\n").splitlines(keepends=True)})


def code(t):
    cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
                  "source": t.strip("\n").splitlines(keepends=True)})


md(r"""
# The diet problem: the first LP, and the direction of an inequality

Six foods, each with a price per serving. Four nutrients, each with a daily minimum. A table saying
how much of each nutrient a serving of each food delivers. Find the cheapest basket that meets every
minimum.

This is the first LP most people meet, and it is small enough to hold in your head: one variable per
food, one constraint per nutrient, one line for the cost. The formulation is the whole lesson. In
particular, **every constraint has a direction, and the solver will honour the one you typed** — it
has no way of knowing the one you meant.
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
    os.chdir("/content/teaching-code/notebooks/01_lp_formulation")
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
## The instance is a table

Costs, minimums and a food-by-nutrient grid: instance data indexed by the model's own sets, named
nowhere in the prose. So it lives in `data/raw/` and both this notebook and the package read the same
two files.

The model will look values up by `(food, nutrient)`, so the dictionary form is printed as well as the
grid — the key is the thing every constraint below is built from.
""")
code(r'''
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join("..", "..", "src")))
from orteach import tolerance
from orteach.diet import load_diet

inst = load_diet("macros")

print(f"{'food':8} {'$/serv':>7} " + " ".join(f"{n:>9}" for n in inst.nutrients))
for f in inst.foods:
    print(f"{f:8} {inst.cost[f]:7.2f} " + " ".join(f"{inst.content[f, n]:9.1f}" for n in inst.nutrients))
print(f"{'minimum':8} {'':7} " + " ".join(f"{inst.minimum[n]:9.1f}" for n in inst.nutrients))
print()
print("content[('milk', 'protein')] =", inst.content["milk", "protein"])
print("minimum['calories']          =", inst.minimum["calories"])

# to try a different price, edit the loaded table and the same value flows into both the
# hand-built model and the package check at the bottom:
# inst.cost["cheese"] = 4.00
''')

md(r"""
## Predict before building anything

Look at the table. For each nutrient, which food delivers it most cheaply per unit? Write down the two
or three foods you expect the cheapest basket to be made of — and one you expect it never to touch.
""")

md(r"""
## The model, and one variable per food

Servings are continuous and cannot be negative; nothing else is known about them yet.
""")
code(r'''
m = gp.Model("diet", env=env)
tolerance.apply(m)

x = m.addVars(inst.foods, lb=0.0, name="servings")
print(len(x), "variables:", list(x.keys()))
''')

md(r"""
## The objective is the grocery bill

Cost per serving times servings, summed over foods. Minimised.
""")
code(r'''
m.setObjective(gp.quicksum(inst.cost[f] * x[f] for f in inst.foods), GRB.MINIMIZE)
m.update()
print(m.getObjective())
''')

md(r"""
## One constraint per nutrient — written out once

The protein row, longhand: protein per serving times servings, summed over foods, **at least** the
minimum. The `>=` is the decision in this line. Say to yourself why it is not `<=`. Gurobi reports
the sense back as a single character — `>` for `>=`.
""")
code(r'''
protein = m.addConstr(
    gp.quicksum(inst.content[f, "protein"] * x[f] for f in inst.foods) >= inst.minimum["protein"],
    name="nutrient[protein]")
m.update()
print(m.getRow(protein), protein.Sense, protein.RHS)
''')

md(r"""
The other three rows have identical shape, so a loop is honest here — it repeats a step you have
already seen, it does not hide a decision.
""")
code(r'''
rows = {"protein": protein}
for n in ["fat", "carbs", "calories"]:
    rows[n] = m.addConstr(
        gp.quicksum(inst.content[f, n] * x[f] for f in inst.foods) >= inst.minimum[n],
        name=f"nutrient[{n}]")
m.update()
print(m.NumConstrs, "constraints")
''')

md(r"""
## Read back what you built

Before solving, print the constraints the model actually holds — name, sense, right-hand side. Read it
the way you would if you suspected a typo somewhere in the model: which column would you check first?
""")
code(r'''
for c in m.getConstrs():
    print(f"{c.ConstrName:20} sense {c.Sense}  rhs {c.RHS:6.1f}    {m.getRow(c)}")
''')

md(r"""
## Two side conditions, as bounds rather than rows

The course version of this problem insists on at least half a serving of fish and at most one serving
of milk. Each involves one variable, so each is a **bound** on that variable, not a constraint row —
the solver treats bounds more cheaply and the model reads more honestly.
""")
code(r'''
FISH_MIN = 0.5      # servings, at least
MILK_MAX = 1.0      # servings, at most

x["fish"].LB = FISH_MIN
x["milk"].UB = MILK_MAX
m.update()
print("fish bounds", (x["fish"].LB, x["fish"].UB), "   milk bounds", (x["milk"].LB, x["milk"].UB))
''')

md(r"""
## Solve

Predict the bill to within a dollar before running this, and which of the four minimums will be met
exactly.
""")
code(r'''
m.optimize()
print(f"\ncheapest basket: ${m.ObjVal:.2f} per day")
''')

md(r"""
## The basket, and which minimums bind

A nutrient whose intake sits exactly on its minimum is one the solver had to work for. The others
came along for free with the foods chosen for the binding ones.
""")
code(r'''
print(f"{'food':8} {'servings':>9}")
for f in inst.foods:
    if x[f].X > tolerance.FEASIBILITY_ATOL:
        print(f"{f:8} {x[f].X:9.3f}")
print()
print(f"{'nutrient':10} {'minimum':>8} {'intake':>8}   binding?")
for n in inst.nutrients:
    got = sum(inst.content[f, n] * x[f].X for f in inst.foods)
    tight = abs(got - inst.minimum[n]) < tolerance.FEASIBILITY_ATOL
    print(f"{n:10} {inst.minimum[n]:8.1f} {got:8.2f}   {'yes' if tight else ''}")
''')

md(r"""
Compare with what you wrote down. Which foods surprised you, and does the binding column explain them?

---

## The same model, one character different

Three term folders of this course shipped this exact instance with the protein row written `<=`.
Everything else was identical. Here is that model, built the same way, so you can see what the solver
made of it.
""")
code(r'''
m_flip = gp.Model("diet, protein row reversed", env=env)
tolerance.apply(m_flip)
xf = m_flip.addVars(inst.foods, lb=0.0, name="servings")
xf["fish"].LB = FISH_MIN
xf["milk"].UB = MILK_MAX
m_flip.setObjective(gp.quicksum(inst.cost[f] * xf[f] for f in inst.foods), GRB.MINIMIZE)

rows_flip = {}
rows_flip["protein"] = m_flip.addConstr(
    gp.quicksum(inst.content[f, "protein"] * xf[f] for f in inst.foods) <= inst.minimum["protein"],
    name="nutrient[protein]")                                            # <-- the one character
for n in ["fat", "carbs", "calories"]:
    rows_flip[n] = m_flip.addConstr(
        gp.quicksum(inst.content[f, n] * xf[f] for f in inst.foods) >= inst.minimum[n],
        name=f"nutrient[{n}]")
m_flip.update()
print(m_flip.NumVars, "variables,", m_flip.NumConstrs, "constraints — same counts as before")
''')

md(r"""
Before you run it: will this bill be higher or lower than the one above, and why? The feasible
regions are different, not nested, so the answer is not automatic.
""")
code(r'''
m_flip.optimize()
print(f"\nbasket with protein reversed: ${m_flip.ObjVal:.2f} per day   (correct model: ${m.ObjVal:.2f})")
print()
print(f"{'food':8} {'servings':>9}")
for f in inst.foods:
    if xf[f].X > tolerance.FEASIBILITY_ATOL:
        print(f"{f:8} {xf[f].X:9.3f}")
print()
print(f"{'nutrient':10} {'minimum':>8} {'intake':>8}")
for n in inst.nutrients:
    got = sum(inst.content[f, n] * xf[f].X for f in inst.foods)
    print(f"{n:10} {inst.minimum[n]:8.1f} {got:8.2f}")
''')

md(r"""
Look at the protein line. The model is sitting exactly on 10 — from which side? What question did the
solver think it was answering, and why did the bill go the way it went?

## Where the evidence was

The original notebooks printed their constraint table after solving. Here is the same table for the
reversed model. The evidence is one character wide.
""")
code(r'''
for c in m_flip.getConstrs():
    print(f"{c.ConstrName:20} sense {c.Sense}  rhs {c.RHS:6.1f}")
''')

md(r"""
---

## The same formulation on a different table

The graduate section used a different instance — four foods, four vitamins — with the same
formulation. Load it and the code above is unchanged; only the sets are different. That is what
keeping the table out of the notebook buys.
""")
code(r'''
vit = load_diet("vitamins")

print(f"{'food':8} {'$/serv':>7} " + " ".join(f"{n:>10}" for n in vit.nutrients))
for f in vit.foods:
    print(f"{f:8} {vit.cost[f]:7.2f} " + " ".join(f"{vit.content[f, n]:10.0f}" for n in vit.nutrients))
print(f"{'minimum':8} {'':7} " + " ".join(f"{vit.minimum[n]:10.0f}" for n in vit.nutrients))
''')

md(r"""
Same three steps — variables, objective, one `>=` row per nutrient — with no side bounds this time.
Predict which foods the basket will use.
""")
code(r'''
m2 = gp.Model("diet, vitamins", env=env)
tolerance.apply(m2)
x2 = m2.addVars(vit.foods, lb=0.0, name="servings")
m2.setObjective(gp.quicksum(vit.cost[f] * x2[f] for f in vit.foods), GRB.MINIMIZE)
rows2 = {n: m2.addConstr(gp.quicksum(vit.content[f, n] * x2[f] for f in vit.foods) >= vit.minimum[n],
                         name=f"nutrient[{n}]") for n in vit.nutrients}
m2.optimize()

print(f"\ncheapest basket: ${m2.ObjVal:.2f} per day")
for f in vit.foods:
    if x2[f].X > tolerance.FEASIBILITY_ATOL:
        print(f"  {f:8} {x2[f].X:7.3f} servings")
''')

md(r"""
---

# Now the streamlined version

Three models built from the same three steps, so they belong in one function now. The package solver
takes the instance as an argument, takes the side bounds as named arguments, and keeps the reversed
row callable as `flip=` — not as a feature, but so that the mistake stays reproducible.
""")
code(r'''
from orteach import diet
from orteach.tolerance import AGREEMENT_RTOL, rel_diff

pkg      = diet.solve(inst, lower={"fish": FISH_MIN}, upper={"milk": MILK_MAX}, env=env)
pkg_flip = diet.solve(inst, lower={"fish": FISH_MIN}, upper={"milk": MILK_MAX}, flip=("protein",), env=env)
pkg_vit  = diet.solve(vit, env=env)

for b in (pkg, pkg_flip, pkg_vit):
    print(f"{b.label:34} ${b.objective:7.2f}   {b.chosen()}")
''')

md(r"""
## The agreement assertion

Each hand-built model against the package, number by number: the bill and every serving. Both sides
solved at the same tightened tolerances, so agreement to `AGREEMENT_RTOL` is a claim the computation
supports.
""")
code(r'''
checks = [("macros bill", m.ObjVal, pkg.objective),
          ("reversed bill", m_flip.ObjVal, pkg_flip.objective),
          ("vitamins bill", m2.ObjVal, pkg_vit.objective)]
for f in inst.foods:
    checks.append((f"macros {f}", x[f].X, pkg.servings[f]))
    checks.append((f"reversed {f}", xf[f].X, pkg_flip.servings[f]))
for f in vit.foods:
    checks.append((f"vitamins {f}", x2[f].X, pkg_vit.servings[f]))

worst = max(rel_diff(h, p) for _, h, p in checks)
print(f"{len(checks)} comparisons")
for name, hand, packaged in checks[:3]:
    print(f"  {name:16} hand {hand:10.4f}   package {packaged:10.4f}   rel {rel_diff(hand, packaged):.2e}")
print("  ...")
assert worst < AGREEMENT_RTOL, f"notebook and package disagree by {worst:.2e}"
print(f"\nnotebook and package agree to {worst:.1e}")
''')

md(r"""
---

## Where to take this next

- Drop the fish minimum (`lower={}`) and re-solve. What happens to fish, and what does that say about
  why the bound was there?
- Calories usually have a ceiling as well as a floor. Add a second calories row with `<=` and a limit
  of your choosing. Two rows on one nutrient — is that a problem, and what happens if the ceiling is
  below the floor?
- Nobody eats 0.8 of a serving. Make the servings integer and compare the bill. Then look up which
  notebook in this library is about what that change does to the solver.
""")

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                   "language_info": {"name": "python", "version": "3.13"}}, "nbformat": 4, "nbformat_minor": 5}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    f.write("\n")
print("wrote %s  (%d cells)" % (OUT, len(cells)))
