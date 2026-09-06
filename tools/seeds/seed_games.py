"""Seed for the zero-sum game teaching notebook. Writes the notebook without outputs; execute it afterwards (README.md here)."""
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "notebooks", "10_game_theory", "zero_sum_game.ipynb")
cells = []


def md(t):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": t.strip("\n").splitlines(keepends=True)})


def code(t):
    cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
                  "source": t.strip("\n").splitlines(keepends=True)})


md(r"""
# A zero-sum game, solved as two linear programs

Two players choose at the same time. The row player picks one of two rows, the column player one of
four columns, and the table says what the column player then pays the row player. Neither can see
the other's choice, and whatever one gains the other loses — that is what *zero-sum* means.

If either player always picked the same row or column, the other would learn it and exploit it. So
the question is not "which row?" but "with what probabilities?" — and the answer, for both players
at once, is a pair of linear programs that turn out to be duals of each other. The transportation
and duality notebooks in this library were about that pairing in economic clothes; here it is in
its purest form.
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
    os.chdir("/content/teaching-code/notebooks/10_game_theory")
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
## The payoff matrix is a table

Rows and columns are the two players' pure strategies; entries are payments to the row player. It is
instance data indexed by the model's own sets, so it lives in `data/raw/` and both this notebook and
the package read the same file. The model will look entries up by `(row, col)`.
""")
code(r'''
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join("..", "..", "src")))
from orteach import tolerance
from orteach.games import load_game

game = load_game("zero_sum_2x4.csv")

print(f"{'':6}" + "".join(f"{c:>6}" for c in game.cols))
for r in game.rows:
    print(f"{r:6}" + "".join(f"{game.payoff[r, c]:6.0f}" for c in game.cols))
print()
print("payoff[('r2', 'c4')] =", game.payoff["r2", "c4"])

# to change an entry, edit the loaded table; the same value reaches the package check at the bottom:
# game.payoff["r1", "c4"] = 1.0
''')

md(r"""
## Pure strategies first

If the row player must commit to one row, the cautious choice is the row whose *worst* column is
best — the **maximin**. The column player, paying, picks the column whose worst row costs least — the
**minimax**. Compute both. Predict before running: will they be equal?
""")
code(r'''
row_worst = {r: min(game.payoff[r, c] for c in game.cols) for r in game.rows}
col_worst = {c: max(game.payoff[r, c] for r in game.rows) for c in game.cols}

maximin_value = max(row_worst.values())
minimax_value = min(col_worst.values())
print("worst column for each row  :", row_worst, "  -> maximin", maximin_value)
print("worst row for each column  :", col_worst, "  -> minimax", minimax_value)
print("saddle point:", maximin_value == minimax_value)
''')

md(r"""
The row player can guarantee 2 by playing pure; the column player can hold the loss to 3 by playing
pure. The gap between them is the room that mixing fills.

## The row player's LP

Let $p_1, p_2$ be the probabilities on the two rows and $v$ the payoff the mix guarantees. Against
each column, the expected payment must be at least $v$; the probabilities sum to one; maximise $v$.
One constraint per column, written out, each reading its two coefficients from the table — so an
edit to the table reaches the model — and then printed, so you can see what was built.
""")
code(r'''
m = gp.Model("row player", env=env)
tolerance.apply(m)

p = m.addVars(game.rows, lb=0.0, name="p")
v = m.addVar(lb=-GRB.INFINITY, name="value")

a = game.payoff                    # (row, col) -> what the column player pays the row player
prob = m.addConstr(p["r1"] + p["r2"] == 1, name="probability")
against = {}
against["c1"] = m.addConstr(a["r1", "c1"] * p["r1"] + a["r2", "c1"] * p["r2"] >= v, name="against[c1]")
against["c2"] = m.addConstr(a["r1", "c2"] * p["r1"] + a["r2", "c2"] * p["r2"] >= v, name="against[c2]")
against["c3"] = m.addConstr(a["r1", "c3"] * p["r1"] + a["r2", "c3"] * p["r2"] >= v, name="against[c3]")
against["c4"] = m.addConstr(a["r1", "c4"] * p["r1"] + a["r2", "c4"] * p["r2"] >= v, name="against[c4]")
m.setObjective(v, GRB.MAXIMIZE)
m.update()

for c in m.getConstrs():
    print(f"{c.ConstrName:14} {m.getRow(c)}  {c.Sense}  {c.RHS}")
''')

md(r"""
That printed table is the check to make before solving. These rows are easy to build with a `prod`
call whose index pattern matches nothing; the table then reads `-1.0 value >= 0` on every line, the
payoffs having silently dropped out, and the game solved has value 0. Look at the coefficients
before you solve.

Predict: where between 2 and 3 will $v$ land, and what will $p$ be?
""")
code(r'''
m.optimize()
value_row = m.ObjVal
p_hand = {r: p[r].X for r in game.rows}
print(f"\nvalue of the game (row player) {value_row:.4f}")
print("row strategy", {r: round(x, 4) for r, x in p_hand.items()})
''')

md(r"""
## Which columns bind, and what the duals say

Print the slack and the dual of every column constraint. Gurobi reports a row's slack as right-hand
side minus activity, so a loose `>=` row shows a negative number. How many columns are tight? What
sign do the duals have, and what do they sum to?
""")
code(r'''
print(f"{'column':8} {'expected payoff':>16} {'slack':>7} {'dual':>7}")
for c in game.cols:
    row = against[c]
    print(f"{c:8} {m.getRow(row).getValue() + v.X:16.4f} {row.Slack:7.3f} {row.Pi:7.3f}")
print("probability row dual:", round(prob.Pi, 4))
''')

md(r"""
Hold those duals: minus each one is a probability, and the probability-row dual is the value of the
game. Before reading on, say what LP you think they are the solution of.

## The column player's LP

The mirror image: probabilities $q$ over columns, $w$ the payment the column player can hold the
row player to. Against each row the expected payment is at most $w$; minimise $w$. Predict its
optimal value.
""")
code(r'''
d = gp.Model("column player", env=env)
tolerance.apply(d)

q = d.addVars(game.cols, lb=0.0, name="q")
w = d.addVar(lb=-GRB.INFINITY, name="value")

d.addConstr(q.sum() == 1, name="probability")
holds = {r: d.addConstr(gp.quicksum(game.payoff[r, c] * q[c] for c in game.cols) <= w, name=f"holds[{r}]")
         for r in game.rows}
d.setObjective(w, GRB.MINIMIZE)
d.optimize()
value_col = d.ObjVal
q_hand = {c: q[c].X for c in game.cols}
print(f"\nvalue of the game (column player) {value_col:.4f}")
print("column strategy", {c: round(x, 4) for c, x in q_hand.items()})
print("minus the row LP's duals", {c: round(-against[c].Pi, 4) for c in game.cols})
''')

md(r"""
Same value from both sides: the minimax theorem, which is strong duality with the players' names on
it. The two column strategies printed may or may not be the same vector. Check what each actually
guarantees — the largest expected payment over the two rows — before deciding whether that matters.
""")
code(r'''
for label, strat in (("column LP", q_hand), ("row LP duals", {c: -against[c].Pi for c in game.cols})):
    per_row = {r: sum(strat[c] * game.payoff[r, c] for c in game.cols) for r in game.rows}
    print(f"{label:14} expected payment by row {per_row}   worst {max(per_row.values()):.4f}")
''')

md(r"""
Both hold the row player to exactly the value. If they differ, how many optimal column strategies
are there, and what do they have in common? Try $q = (0,\ 0.5-4d,\ 0.5+3d,\ d)$ for a few values of
$d$.

---

# Now the streamlined version

Two LPs built by hand from the same table, so the package owns them now: `solve_row`, `solve_column`,
the pure-strategy `maximin` / `minimax`, and `worst_case`, which scores any strategy against the
opponent's best pure reply.
""")
code(r'''
from orteach import games
from orteach.tolerance import AGREEMENT_RTOL, rel_diff

pkg_row = games.solve_row(game, env=env)
pkg_col = games.solve_column(game, env=env)
print(f"row player    value {pkg_row.value:.4f}   p {pkg_row.probs}")
print(f"column player value {pkg_col.value:.4f}   q {pkg_col.probs}")
print("pure maximin / minimax:", games.maximin(game), games.minimax(game))
''')

md(r"""
## The agreement assertion

Both values and the row strategy, hand-built against the package; two things every optimal set of
row-LP duals shares — they sum to minus one, and the probability row's dual is the value of the
game; and every column strategy in play scored by `worst_case`, which must come out at the value.
The column strategies, and the duals that encode one, are compared as guarantees and invariants,
not as vectors: the optimum on that side is a segment, and which point of it comes back is the
solver's choice, not the problem's.
""")
code(r'''
checks = [("row value", value_row, pkg_row.value),
          ("column value", value_col, pkg_col.value),
          ("minimax theorem", value_row, value_col)]
for r in game.rows:
    checks.append((f"p[{r}]", p_hand[r], pkg_row.probs[r]))
checks.append(("row duals sum to -1", sum(against[c].Pi for c in game.cols), sum(pkg_row.duals.values())))
checks.append(("probability-row dual is the value", prob.Pi, pkg_row.value))
for label, strat in (("hand q", q_hand), ("hand duals", {c: -against[c].Pi for c in game.cols}), ("package q", pkg_col.probs)):
    checks.append((f"{label} guarantee", games.worst_case(game, strat, "column"), value_row))

worst = max(rel_diff(h, k) for _, h, k in checks)
print(f"{len(checks)} comparisons")
for name, hand, packaged in checks[:4]:
    print(f"  {name:20} hand {hand:9.4f}   package {packaged:9.4f}   rel {rel_diff(hand, packaged):.2e}")
print("  ...")
assert worst < AGREEMENT_RTOL, f"notebook and package disagree by {worst:.2e}"
print(f"\nnotebook and package agree to {worst:.1e}")
''')

md(r"""
---

## Where to take this next

- Column `c1` is dominated: every entry is at least as large as `c2`'s. Delete it from the table and
  re-run. Does anything change, and should it have?
- Change `payoff["r2", "c3"]` to 3. Now compute the pure maximin and minimax before solving. Is
  there a saddle point, and what does the LP return for $p$?
- The row LP has a free variable $v$ and `>=` rows in a maximisation. Write its dual by the rules
  in `03_duality_and_sensitivity/` and show it is the column LP.
""")

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                   "language_info": {"name": "python", "version": "3.13"}}, "nbformat": 4, "nbformat_minor": 5}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    f.write("\n")
print("wrote %s  (%d cells)" % (OUT, len(cells)))
