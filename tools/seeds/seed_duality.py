"""Seed for the primal/dual teaching notebook. Writes the notebook without outputs; execute it afterwards (README.md here)."""
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "notebooks", "03_duality_and_sensitivity", "primal_and_dual.ipynb")
cells = []


def md(t):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": t.strip("\n").splitlines(keepends=True)})


def code(t):
    cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
                  "source": t.strip("\n").splitlines(keepends=True)})


md(r"""
# Primal and dual: the same answer from the other side

Every linear program has a twin. Each constraint of one is a variable of the other, each variable a
constraint; the objective coefficients and right-hand sides trade places; the matrix is transposed.
Solve either and you have solved both — and the solver hands the twin's optimum back as `Pi`, the
**shadow prices**.

That is a claim worth checking rather than believing. This notebook builds a small LP, reads its
`Pi`, then builds the dual by hand as a second LP and solves that. Then it tests a shadow price the
only honest way — by buying one more unit and re-solving. And at the end it does something three
years of this course's notebooks did: asks an integer program for `Pi`, to see what comes back.
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
    os.chdir("/content/teaching-code/notebooks/03_duality_and_sensitivity")
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
## The LP is a table

Taha's example 4.2-1, chosen because its two constraints have different senses — one `<=`, one `=` —
and the dual treats them differently. An LP in coefficient form is a small tableau: an objective row,
a row per constraint, a column per variable, then the sense and right-hand side. It lives in
`data/raw/` and both sides read it.
""")
code(r'''
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join("..", "..", "src")))
from orteach import tolerance
from orteach.duality import load_lp

lp = load_lp("lp_taha_4_2_1.csv")

print(f"{'':10} " + " ".join(f"{j:>5}" for j in lp.variables) + "   sense    rhs")
print(f"{lp.objective:10} " + " ".join(f"{lp.c[j]:5.0f}" for j in lp.variables))
for r in lp.rows:
    print(f"{r:10} " + " ".join(f"{lp.A[r, j]:5.0f}" for j in lp.variables) + f"   {lp.sense[r]:>5} {lp.b[r]:6.0f}")
print()
print("A[('c2', 'x2')] =", lp.A["c2", "x2"], "   b['c1'] =", lp.b["c1"], "   sense['c2'] =", lp.sense["c2"])

# to change a coefficient, edit the loaded table; the same value reaches the package check at the bottom:
# lp.b["c1"] = 12.0
''')

md(r"""
## The primal, longhand

Three variables and two rows are few enough to write out in full, which is the point: you should be
able to see the dual's shape in these lines before it is built. The coefficients are read from the
table rather than retyped, so an edit to the table reaches this model and the check at the bottom.

$$\max\; 5x_1 + 12x_2 + 4x_3 \quad\text{s.t.}\quad x_1 + 2x_2 + x_3 \le 10,\qquad 2x_1 - x_2 + 3x_3 = 8,\qquad x \ge 0$$
""")
code(r'''
A, b, obj = lp.A, lp.b, lp.c           # the table's coefficients

p = gp.Model("primal", env=env)
tolerance.apply(p)
x1 = p.addVar(lb=0.0, name="x1")
x2 = p.addVar(lb=0.0, name="x2")
x3 = p.addVar(lb=0.0, name="x3")

c1 = p.addConstr(A["c1", "x1"] * x1 + A["c1", "x2"] * x2 + A["c1", "x3"] * x3 <= b["c1"], name="c1")
c2 = p.addConstr(A["c2", "x1"] * x1 + A["c2", "x2"] * x2 + A["c2", "x3"] * x3 == b["c2"], name="c2")
p.setObjective(obj["x1"] * x1 + obj["x2"] * x2 + obj["x3"] * x3, GRB.MAXIMIZE)
p.update()
print(p.NumVars, "variables,", p.NumConstrs, "constraints")
''')

md(r"""
Predict before you run: which of the two rows is worth more per unit of right-hand side? And the
second row is an equality — if its 8 became a 9, would you expect the objective to rise or fall?
""")
code(r'''
p.optimize()
print(f"\nprimal objective {p.ObjVal:.4f}")
print(f"x = ({x1.X:.4f}, {x2.X:.4f}, {x3.X:.4f})")
print(f"Pi: c1 {c1.Pi:+.4f}   c2 {c2.Pi:+.4f}")
''')

md(r"""
One price is negative. Hold that thought until the dual has been built by hand and it can be seen
where the sign comes from.

## The rules for writing the dual

For a maximisation with $x \ge 0$:

| primal | dual |
|---|---|
| a `<=` row | a variable $y \ge 0$ |
| a `>=` row | a variable $y \le 0$ |
| an `=` row | a variable $y$ **free** |
| a variable $x_j \ge 0$ | a `>=` row with right-hand side $c_j$ |
| objective $\max\, c^\top x$ | objective $\min\, b^\top y$ |

Row `c1` is `<=`, so $y_1 \ge 0$. Row `c2` is `=`, so $y_2$ is free. There is one dual row per primal
variable, built from that variable's *column*.

$$\min\; 10y_1 + 8y_2 \quad\text{s.t.}\quad y_1 + 2y_2 \ge 5,\qquad 2y_1 - y_2 \ge 12,\qquad y_1 + 3y_2 \ge 4$$
""")
code(r'''
d = gp.Model("dual", env=env)
tolerance.apply(d)
y1 = d.addVar(lb=0.0, name="y1")
y2 = d.addVar(lb=-GRB.INFINITY, name="y2")            # free: it came from an equality row

d1 = d.addConstr(A["c1", "x1"] * y1 + A["c2", "x1"] * y2 >= obj["x1"], name="col x1")
d2 = d.addConstr(A["c1", "x2"] * y1 + A["c2", "x2"] * y2 >= obj["x2"], name="col x2")
d3 = d.addConstr(A["c1", "x3"] * y1 + A["c2", "x3"] * y2 >= obj["x3"], name="col x3")
d.setObjective(b["c1"] * y1 + b["c2"] * y2, GRB.MINIMIZE)
d.update()
print(f"{d.NumVars} variables, {d.NumConstrs} constraints   (the primal had {p.NumVars} variables, {p.NumConstrs} constraints)")
''')

md(r"""
Predict the dual's objective value before running it. You have already seen the number.
""")
code(r'''
d.optimize()
print(f"\ndual objective   {d.ObjVal:.4f}      primal objective {p.ObjVal:.4f}")
print(f"y = ({y1.X:+.4f}, {y2.X:+.4f})     Pi from the primal = ({c1.Pi:+.4f}, {c2.Pi:+.4f})")
''')

md(r"""
Equal objectives is strong duality. The dual's variables are the primal's `Pi`. The rules table
*allowed* $y_2$ to be negative; it does not say why it is. What is it about row `c2` — the one that
must hold with equality — that makes one more unit of its right-hand side cost something? Go back
to the prediction you wrote about the 8 becoming a 9.

## Complementary slackness

The two solutions lock together pairwise. Where a primal variable is positive, its dual row is tight;
where a dual row has room to spare, the primal variable is zero. Gurobi reports the primal side of
that as the **reduced cost** `RC`. Compare it to the dual row's rhs − lhs (negative for a `>=` row
means a surplus: the row holds with room to spare).
""")
code(r'''
print(f"{'variable':9} {'x':>7} {'RC':>8}   {'dual row':9} {'lhs':>7} {'rhs':>5} {'rhs-lhs':>8}")
for v, row in ((x1, d1), (x2, d2), (x3, d3)):
    lhs = d.getRow(row).getValue()
    print(f"{v.VarName:9} {v.X:7.3f} {v.RC:+8.3f}   {row.ConstrName:9} {lhs:7.3f} {row.RHS:5.0f} {row.RHS - lhs:+8.3f}")
''')

md(r"""
## Test a price by paying it

A shadow price is a prediction: *one more unit on this row's right-hand side moves the objective by
this much.* Check it by actually adding the unit and re-solving. Do it for both rows, including the
one with the negative price.
""")
code(r'''
base = p.ObjVal
said = {row.ConstrName: row.Pi for row in (c1, c2)}        # the prediction, captured before any re-solve
for row in (c1, c2):
    row.RHS += 1.0
    p.optimize()
    print(f"{row.ConstrName}: rhs {row.RHS - 1:.0f} -> {row.RHS:.0f}   objective {base:.3f} -> {p.ObjVal:.3f}   "
          f"change {p.ObjVal - base:+.3f}   Pi said {said[row.ConstrName]:+.3f}")
    row.RHS -= 1.0
p.optimize()
''')

md(r"""
How far could you keep adding units before the price stopped being right? Nothing above answers that.
Gurobi's `SARHSLow` and `SARHSUp` attributes do, and the transportation notebook in
`04_networks_and_transport/` asks the same question of an objective coefficient instead of a
right-hand side.

---

## A second table: resources with slack

Two products, three resources, all `<=`. This one has a resource that is not fully used — predict
which, from the table, and what its shadow price must therefore be.
""")
code(r'''
prod = load_lp("lp_production_ab.csv")

print(f"{'':10} " + " ".join(f"{j:>5}" for j in prod.variables) + "   sense    rhs")
print(f"{prod.objective:10} " + " ".join(f"{prod.c[j]:5.0f}" for j in prod.variables))
for r in prod.rows:
    print(f"{r:10} " + " ".join(f"{prod.A[r, j]:5.0f}" for j in prod.variables) + f"   {prod.sense[r]:>5} {prod.b[r]:6.0f}")
''')

md(r"""
The same three steps as before, over the table's sets this time. The loop over resources repeats one
identical `<=` row; the senses are all the same, which is why it can be a loop.
""")
code(r'''
q = gp.Model("production", env=env)
tolerance.apply(q)
make = q.addVars(prod.variables, lb=0.0, name="make")
use = {r: q.addConstr(gp.quicksum(prod.A[r, j] * make[j] for j in prod.variables) <= prod.b[r], name=r)
       for r in prod.rows}
q.setObjective(gp.quicksum(prod.c[j] * make[j] for j in prod.variables), GRB.MAXIMIZE)
q.optimize()

print(f"\nprofit {q.ObjVal:.2f}   make = " + ", ".join(f"{j} {make[j].X:.2f}" for j in prod.variables))
print(f"{'resource':10} {'used':>6} {'of':>4} {'Pi':>7}")
for r in prod.rows:
    print(f"{r:10} {q.getRow(use[r]).getValue():6.1f} {prod.b[r]:4.0f} {use[r].Pi:7.3f}")
''')

md(r"""
Buy one more unit of each resource in turn and watch the profit. Which one was not worth buying, and
did the table say so before the solve?
""")
code(r'''
base_q = q.ObjVal
said_q = {r: use[r].Pi for r in prod.rows}
for r in prod.rows:
    use[r].RHS += 1.0
    q.optimize()
    print(f"{r:10} +1 unit: profit {base_q:.3f} -> {q.ObjVal:.3f}   change {q.ObjVal - base_q:+.3f}   Pi said {said_q[r]:+.3f}")
    use[r].RHS -= 1.0
q.optimize()
''')

md(r"""
---

## Asking an integer program for a price

The original notebook followed the LP with a small transportation problem — two plants, three
wholesalers — declared its flows `INTEGER`, solved, and asked for `Pi`. Here is that model, from its
table.
""")
code(r'''
from orteach.transportation import load_instance

pw = load_instance("plants_wholesalers_arcs.csv", "plants_wholesalers_nodes.csv",
                   cost_col="cost_per_unit", qty_col="units", name="plants to wholesalers")
print(f"{'arc':12} {'$/unit':>7}")
for (i, j), c in pw.arcs.items():
    print(f"{i + ' -> ' + j:12} {c:7.0f}")
print("supply", pw.supply, "  demand", pw.demand, "  balanced:", pw.balanced)
''')

md(r"""
Flows integer, supplies as ceilings, demands as floors. Predict the cost: it is small enough to do by
inspection, cheapest arc first.
""")
code(r'''
t = gp.Model("transport, integer", env=env)
tolerance.apply(t)
flow = t.addVars(pw.arcs.keys(), lb=0.0, vtype=GRB.INTEGER, name="flow")
sup = t.addConstrs((flow.sum(i, "*") <= pw.supply[i] for i in pw.supply), name="supply")
dem = t.addConstrs((flow.sum("*", j) >= pw.demand[j] for j in pw.demand), name="demand")
t.setObjective(flow.prod(pw.arcs), GRB.MINIMIZE)
t.optimize()

print(f"\ncost {t.ObjVal:,.0f}")
for a, v in flow.items():
    if v.X > tolerance.FEASIBILITY_ATOL:
        print(f"  {a[0]} -> {a[1]}  {v.X:7.0f}")
''')

md(r"""
Now ask it what one more unit of demand at each wholesaler would cost. This is the cell the original
notebooks ended on.
""")
code(r'''
try:
    print({j: dem[j].Pi for j in pw.demand})
except (gp.GurobiError, AttributeError) as e:      # which one depends on the Gurobi version
    print(type(e).__name__ + ":", e)
''')

md(r"""
An integer program has no dual in the LP sense: its feasible set is a scatter of points, not a
region with faces, so there is no plane whose slope is "the price of one more unit". What would you
have to change to get a price — and a price of what? One route is to drop the integrality. Before
running it, predict whether the flows will change.
""")
code(r'''
for v in flow.values():
    v.VType = GRB.CONTINUOUS
t.optimize()

print(f"\ncost as an LP {t.ObjVal:,.0f}   (same flows: "
      f"{all(abs(v.X - round(v.X)) < tolerance.FEASIBILITY_ATOL for v in flow.values())})")
print("price of one more unit of demand:", {j: round(dem[j].Pi, 2) for j in pw.demand})
print("price of one more unit of supply:", {i: round(sup[i].Pi, 2) for i in pw.supply})
''')

md(r"""
The flows did not change, so the integrality bought nothing: transportation problems with whole
supplies and demands have an integral LP optimum already (the assignment notebook in
`04_networks_and_transport/` is about why), and dropping the integer declaration only gave the prices
back. When the integrality *is* needed, Gurobi's `model.fixed()` — every integer variable pinned at
its solved value, the LP that remains solved for duals — prices the rest of the model given those
choices, and it is worth saying to yourself what those prices do and do not mean.

Both plants have spare capacity and both supply prices are zero. Does that follow, and would it still
hold if total supply equalled total demand?

---

# Now the streamlined version

Three LPs and a dual built by hand, all from the same coefficient tables, so the package owns the
construction now. `duality.dual_of` applies the rules table mechanically; `duality.solve` returns the
optimum with `Pi`, reduced costs and slacks; the transportation solver is the one from
`04_networks_and_transport/`.
""")
code(r'''
from orteach import duality, transportation as tp
from orteach.tolerance import AGREEMENT_RTOL, rel_diff

pkg_p  = duality.solve(lp, env=env)
pkg_d  = duality.solve(duality.dual_of(lp), env=env)
pkg_q  = duality.solve(prod, env=env)
pkg_t  = tp.solve(pw, env=env)

print(f"{'primal':10} {pkg_p.objective:9.4f}   Pi {pkg_p.pi}")
print(f"{'dual':10} {pkg_d.objective:9.4f}   y  {pkg_d.x}")
print(f"{'production':10} {pkg_q.objective:9.4f}   Pi {pkg_q.pi}")
print(f"{'transport':10} {pkg_t.objective:9.0f}   demand prices {pkg_t.demand_price}")
print("complementary slackness gap:", duality.complementary_slackness_gap(lp, pkg_p, pkg_d))
''')

md(r"""
## The agreement assertion

Every hand-built number against the package: both objectives of the Taha pair, the primal solution,
the shadow prices from both sides, the reduced costs, the production LP's solution and prices, and
the transportation cost and flows. Both sides solved at the same tightened tolerances, so agreement
to `AGREEMENT_RTOL` is a claim the computation supports.
""")
code(r'''
checks = [("primal objective", p.ObjVal, pkg_p.objective),
          ("dual objective", d.ObjVal, pkg_d.objective),
          ("strong duality (package)", pkg_p.objective, pkg_d.objective),
          ("production profit", q.ObjVal, pkg_q.objective),
          ("transport cost", t.ObjVal, pkg_t.objective)]
for v, j in ((x1, "x1"), (x2, "x2"), (x3, "x3")):
    checks.append((f"primal {j}", v.X, pkg_p.x[j]))
    checks.append((f"reduced cost {j}", v.RC, pkg_p.reduced_cost[j]))
for row, r in ((c1, "c1"), (c2, "c2")):
    checks.append((f"Pi {r}", row.Pi, pkg_p.pi[r]))
    checks.append((f"dual y for {r}", row.Pi, pkg_d.x[r]))
for j in prod.variables:
    checks.append((f"make {j}", make[j].X, pkg_q.x[j]))
for r in prod.rows:
    checks.append((f"production Pi {r}", use[r].Pi, pkg_q.pi[r]))
for a in pw.arcs:
    checks.append((f"flow {a}", flow[a].X, pkg_t.flow[a]))
for j in pw.demand:
    checks.append((f"demand price {j}", dem[j].Pi, pkg_t.demand_price[j]))
for i in pw.supply:
    checks.append((f"supply price {i}", sup[i].Pi, pkg_t.supply_price[i]))

worst = max(rel_diff(h, k) for _, h, k in checks)
print(f"{len(checks)} comparisons")
for name, hand, packaged in checks[:5]:
    print(f"  {name:26} hand {hand:12.4f}   package {packaged:12.4f}   rel {rel_diff(hand, packaged):.2e}")
print("  ...")
assert worst < AGREEMENT_RTOL, f"notebook and package disagree by {worst:.2e}"
print(f"\nnotebook and package agree to {worst:.1e}")
''')

md(r"""
---

## Where to take this next

- Change row `c2` from `=` to `<=` in the table, and change the two lines that depend on it — the
  `==` in the hand-built primal and $y_2$'s lower bound in the hand-built dual. What happens to
  $y_2$'s sign, and to its value? (The package reads the sense from the table; the longhand cells do
  not, which is the price of writing them out.)
- Write the dual of the diet problem from `01_lp_formulation/` — a minimisation with `>=` rows. The
  dual variables are prices, one per nutrient. Prices of what, paid by whom?
- The production LP's labor price was zero. Reduce labor's capacity one unit at a time and find the
  point where it stops being zero. Then find that point without re-solving, using `SARHSLow`.
""")

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                   "language_info": {"name": "python", "version": "3.13"}}, "nbformat": 4, "nbformat_minor": 5}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    f.write("\n")
print("wrote %s  (%d cells)" % (OUT, len(cells)))
