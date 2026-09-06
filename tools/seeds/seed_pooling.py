"""Seed for the pooling-problem teaching notebook. Writes the notebook without outputs; execute it afterwards (README.md here)."""
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "notebooks", "06_nonlinear_and_convex", "pooling.ipynb")
cells = []


def md(t):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": t.strip("\n").splitlines(keepends=True)})


def code(t):
    cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
                  "source": t.strip("\n").splitlines(keepends=True)})


md(r"""
# The pooling problem: when a quality is an unknown times an unknown

Three crude sources with different sulfur contents and prices. Two of them can only be delivered
through a shared pool, where they mix; the third goes straight to the customers. Two products, each
with a sulfur cap and a demand cap and a price. Decide the flows to make the most money.

If the sulfur content of the pool were known, this would be an LP. It is not known: it depends on
how much of each source went in, which is what you are deciding. So the sulfur balance at the pool
multiplies a quality by a flow — two unknowns — and the model is **bilinear**. That single product
is what makes the problem nonconvex, and is the reason Haverly's example from 1978 is still the
standard test of a global solver.
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
## Two tables

Sources — sulfur, price, and whether each feeds the pool or goes direct — and products — price,
sulfur cap, demand cap. Instance data indexed by the model's sets, so both live in `data/raw/` and
both this notebook and the package read them. Sulfur is stored in percent and loaded as a fraction.
""")
code(r'''
from orteach import tolerance
from orteach.nonconvex import load_pooling

inst = load_pooling()

print(f"{'source':7} {'sulfur':>7} {'$/unit':>7}  route")
for s in inst.sources:
    print(f"{s:7} {inst.sulfur[s]:7.3f} {inst.cost[s]:7.0f}  {inst.route[s]}")
print(f"\n{'product':8} {'$/unit':>7} {'max S':>7} {'demand':>7}")
for p in inst.products:
    print(f"{p:8} {inst.price[p]:7.0f} {inst.max_sulfur[p]:7.3f} {inst.demand[p]:7.0f}")
print()
print("pooled:", inst.pooled, "  direct:", inst.direct, "  sulfur['A'] =", inst.sulfur["A"])

# to try a different price, edit the loaded table; the change reaches the package check at the bottom:
# inst.price["X"] = 12.0
''')

md(r"""
## Predict before building anything

Product Y pays more than X and demands more, but its sulfur cap is tighter. Source A is the cheapest
and the dirtiest; B the cleanest and the dearest; C is in between and skips the pool. Write down which
product you would make, out of which sources, and roughly what the profit would be — then build the
model.

## Flows, with boxes

One flow per pooled source into the pool, one per product out of the pool, one per (direct source,
product). Every flow gets a finite upper bound, because spatial branch-and-bound builds its convex
envelopes over boxes and an unbounded bilinear term gives it nothing to build over. Work out the
smallest box that cannot bind before reading the next cell: what is the most any single flow could
ever carry?
""")
code(r'''
# Total demand: nothing sold exceeds a product's demand, so no one flow can exceed their sum.
# The source used 250 - above the LARGEST demand but below the sum, so it was inert at the shipped
# prices and would not have been at others.
FLOW_CAP = sum(inst.demand.values())

m = gp.Model("pooling", env=env)
tolerance.apply(m)

to_pool   = m.addVars(inst.pooled, lb=0.0, ub=FLOW_CAP, name="to_pool")
from_pool = m.addVars(inst.products, lb=0.0, ub=FLOW_CAP, name="from_pool")
direct    = m.addVars([(s, p) for s in inst.direct for p in inst.products], lb=0.0, ub=FLOW_CAP, name="direct")
m.update()
print(m.NumVars, "flow variables:", list(to_pool.keys()), list(from_pool.keys()), list(direct.keys()))
''')

md(r"""
## The quality variables — where the model stops being linear

The pool's sulfur fraction $q_P$ and each product's delivered fraction $q_j$ are unknowns. The pool's
sulfur balance says *sulfur in equals sulfur out*: the fraction times the total flow through the
pool equals the sulfur the sources brought. $q_P \times$ flow is the bilinear term. There are other
ways to write this model — one of them is the third exercise at the bottom — and every one of them
still multiplies two unknowns somewhere. Before running the cell, say where the product would go if
you eliminated $q_P$.
""")
code(r'''
q_pool = m.addVar(lb=0.0, ub=1.0, name="pool_sulfur")
q_prod = m.addVars(inst.products, lb=0.0, ub=1.0, name="product_sulfur")

pool_balance = m.addConstr(to_pool.sum() == from_pool.sum(), name="pool_balance")
pool_quality = m.addConstr(q_pool * to_pool.sum() == gp.quicksum(inst.sulfur[s] * to_pool[s] for s in inst.pooled),
                           name="pool_quality")
m.update()
print("pool balance :", m.getRow(pool_balance), "=", pool_balance.RHS)
print("pool quality :", m.getQCRow(pool_quality), "=", pool_quality.QCRHS)
''')

md(r"""
The same balance at each product: what it receives from the pool carries the pool's fraction, what it
receives direct carries that source's known fraction, and the delivered fraction must be under the
cap. Demand is a ceiling, not a requirement — the model may make less than the market takes.
""")
code(r'''
for p in inst.products:
    inflow = from_pool[p] + direct.sum("*", p)
    m.addConstr(q_prod[p] * inflow == q_pool * from_pool[p] + gp.quicksum(inst.sulfur[s] * direct[s, p] for s in inst.direct),
                name=f"quality[{p}]")
    m.addConstr(inflow <= inst.demand[p], name=f"demand[{p}]")
    m.addConstr(q_prod[p] <= inst.max_sulfur[p], name=f"spec[{p}]")
m.update()
print(m.NumConstrs, "linear rows,", m.NumQConstrs, "bilinear rows")
''')

md(r"""
## The objective: revenue minus purchases
""")
code(r'''
revenue = gp.quicksum(inst.price[p] * (from_pool[p] + direct.sum("*", p)) for p in inst.products)
purchase = gp.quicksum(inst.cost[s] * to_pool[s] for s in inst.pooled) \
    + gp.quicksum(inst.cost[s] * direct[s, p] for s in inst.direct for p in inst.products)
m.setObjective(revenue - purchase, GRB.MAXIMIZE)
m.update()
print(m.getObjective())
''')

md(r"""
## Ask the solver as if the model were convex

Gurobi checks the shape of every quadratic row before it starts. Tell it, with `NonConvex = 0`, that
you expect a convex model, and see what it says about the bilinear rows.
""")
code(r'''
m.Params.NonConvex = 0
try:
    m.optimize()
    print("status", m.Status)
except gp.GurobiError as e:
    print("GurobiError:", e)
''')

md(r"""
## Now let it branch

`NonConvex = 2` turns on spatial branch-and-bound: the solver relaxes each product of variables to a
convex envelope over its box, solves, splits a box, and repeats until the bound meets the best
solution found. Predict the profit before running it, and which product it makes.
""")
code(r'''
m.Params.NonConvex = 2
m.optimize()
profit_hand = m.ObjVal
print(f"status {m.Status}   profit {profit_hand:.2f}   proven bound {m.ObjBound:.2f}")
print()
for s in inst.pooled:
    print(f"  {s} -> pool      {to_pool[s].X:7.2f}")
for p in inst.products:
    print(f"  pool -> {p}      {from_pool[p].X:7.2f}")
for (s, p), v in direct.items():
    print(f"  {s} -> {p} direct {v.X:7.2f}")
made = {p: from_pool[p].X + sum(direct[s, p].X for s in inst.direct) for p in inst.products}
print(f"\npool sulfur {q_pool.X:.4f}   delivered: " + "  ".join(
    f"{p} {q_prod[p].X:.4f} (cap {inst.max_sulfur[p]:.3f})" if made[p] > tolerance.FEASIBILITY_ATOL else f"{p} not made"
    for p in inst.products))
''')

md(r"""
A product that is not made has no delivered fraction: its quality row reads $q_j \times 0 = 0$, so
the variable is free to sit anywhere and its value means nothing. That is why it is not printed —
and, at the bottom, why it is not compared.

## Check the qualities from the flows alone

The quality rows are the part of the model most easily written wrong, so recompute every delivered
sulfur fraction from the flows — no quality variables, no solver — and compare.
""")
code(r'''
flows_pool = {s: to_pool[s].X for s in inst.pooled}
pool_in = sum(flows_pool.values())
pool_frac = sum(inst.sulfur[s] * f for s, f in flows_pool.items()) / pool_in if pool_in > tolerance.FEASIBILITY_ATOL else 0.0
print(f"pool sulfur from flows {pool_frac:.4f}   variable said {q_pool.X:.4f}")
for p in inst.products:
    total = from_pool[p].X + sum(direct[s, p].X for s in inst.direct)
    if total > tolerance.FEASIBILITY_ATOL:
        got = (pool_frac * from_pool[p].X + sum(inst.sulfur[s] * direct[s, p].X for s in inst.direct)) / total
        print(f"{p}: {total:6.1f} units at sulfur {got:.4f} from flows   variable said {q_prod[p].X:.4f}   cap {inst.max_sulfur[p]:.3f}")
    else:
        print(f"{p}: nothing made")
''')

md(r"""
---

## The landscape behind the bilinear row

Pin the pool's sulfur fraction at a few values and re-solve each time. With $q_P$ fixed the model
tells you the best you can do *given that pool*, and the profits trace the landscape a downhill
method would have to cross. Predict the shape before running: one hump, or two?
""")
code(r'''
landscape = {}
for fixed in (0.010, 0.015, 0.020, 0.025, 0.030):
    q_pool.LB = q_pool.UB = fixed
    m.optimize()
    landscape[fixed] = round(m.ObjVal, 6) + 0.0          # + 0.0 turns a solver's -0.0 into 0.0
    print(f"pool sulfur fixed at {fixed:.3f}:  profit {landscape[fixed]:8.2f}   "
          f"X {from_pool['X'].X + sum(direct[s, 'X'].X for s in inst.direct):6.1f}   "
          f"Y {from_pool['Y'].X + sum(direct[s, 'Y'].X for s in inst.direct):6.1f}")
q_pool.LB, q_pool.UB = 0.0, 1.0          # release the pin
m.optimize()
print(f"\npin released, re-solved: profit {m.ObjVal:8.2f}   pool sulfur {q_pool.X:.4f}"
      f"   <- back to the free optimum, and the values the check below reads")
''')

md(r"""
Two profitable regions with a valley between them, and the run above ends back at the free optimum.
What does each hump correspond to in terms of which product the pool serves? If a downhill method
were started at the right-hand one, what would it report, and what would it have to be given in order
to know there was anything better?

---

# Now the streamlined version

One bilinear model built by hand and solved six times, so the package owns it now:
`solve_pooling` takes the two tables and the box as arguments, `profit_of` recomputes the objective
from flows, and `delivered_sulfur` does the check above.
""")
code(r'''
from orteach import nonconvex as nc
from orteach.tolerance import AGREEMENT_RTOL, rel_diff

pkg = nc.solve_pooling(inst, flow_cap=FLOW_CAP, env=env)
pkg_landscape = nc.pooling_landscape(inst, list(landscape), flow_cap=FLOW_CAP, env=env)
print(f"{pkg.label}: profit {pkg.objective:.2f}   bound {pkg.bound:.2f}   pool sulfur {pkg.pool_sulfur:.4f}")
print("profit from flows:", round(nc.profit_of(inst, pkg), 6))
# only for products that are actually made: an unmade one has no delivered fraction to report
print("delivered sulfur :", {p: round(nc.delivered_sulfur(inst, pkg, p), 4)
                             for p in inst.products if pkg.sold(p) > tolerance.FEASIBILITY_ATOL})
print("landscape        :", pkg_landscape)
''')

md(r"""
## The agreement assertion

The hand-built model against the package, number by number: profit, proven bound, every flow, the
pool's fraction, the delivered fraction of every product that is made, and every point of the
landscape sweep. The optimum here is
unique — the cheapest way to fill Y's demand at exactly its cap is one specific blend, and X cannot
be made at a profit — so comparing flows is legitimate. A product that is not made has an undefined
quality variable on both sides, and comparing two undefined numbers would test nothing but the
solver's path, so those are left out. Both sides solved at the same tolerances with the same boxes.
""")
code(r'''
checks = [("profit", profit_hand, pkg.objective),
          ("proven bound", m.ObjBound, pkg.bound),
          ("pool sulfur", q_pool.X, pkg.pool_sulfur)]
for s in inst.pooled:
    checks.append((f"{s} -> pool", to_pool[s].X, pkg.to_pool[s]))
for p in inst.products:
    checks.append((f"pool -> {p}", from_pool[p].X, pkg.from_pool[p]))
    if made[p] > tolerance.FEASIBILITY_ATOL:
        checks.append((f"delivered sulfur {p}", q_prod[p].X, pkg.product_sulfur[p]))
for (s, p) in direct:
    checks.append((f"{s} -> {p}", direct[s, p].X, pkg.direct[s, p]))
for fixed, profit in landscape.items():
    checks.append((f"landscape at {fixed:.3f}", profit, pkg_landscape[fixed]))

worst = max(rel_diff(h, k) for _, h, k in checks)
print(f"{len(checks)} comparisons")
for name, hand, packaged in checks[:4]:
    print(f"  {name:20} hand {hand:10.4f}   package {packaged:10.4f}   rel {rel_diff(hand, packaged):.2e}")
print("  ...")
assert worst < AGREEMENT_RTOL, f"notebook and package disagree by {worst:.2e}"
print(f"\nnotebook and package agree to {worst:.1e}")
''')

md(r"""
---

## Where to take this next

- Raise X's price until the solver switches humps. At what price does it happen, and what does the
  pool's sulfur fraction do at the switch?
- Add a second pool that only C can enter and that only Y can leave. Is the answer any different, and
  what did the extra structure cost in bilinear rows?
- The quality variables can be eliminated: write each product's spec directly as
  $q_P\,f_{P,j} + \sum_i s_i f_{i,j} \le \bar{s}_j\,(\text{inflow}_j)$. Rebuild it that way. Fewer
  variables, the same bilinear terms — does the proof get faster?
""")

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                   "language_info": {"name": "python", "version": "3.13"}}, "nbformat": 4, "nbformat_minor": 5}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    f.write("\n")
print("wrote %s  (%d cells)" % (OUT, len(cells)))
