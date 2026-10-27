"""Seed for the saddle-point teaching notebook (10_game_theory). Writes the notebook without outputs; execute it afterwards (README.md here)."""
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "notebooks", "10_game_theory", "saddle_points.ipynb")
cells = []


def md(t):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": t.strip("\n").splitlines(keepends=True)})


def code(t):
    cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
                  "source": t.strip("\n").splitlines(keepends=True)})


md(r"""
# When the table already holds the answer, and when one entry takes it away

`zero_sum_game.ipynb` in this folder builds both players' LPs for a game that needs them. This one
asks a prior question: when does a game need an LP at all?

Three games. The coin game, whose answer you already know. The flu-medicine advertising game from
Taha's *Operations Research* (the game theory chapter), whose answer can be read straight off its
table. And the same advertising game with
one entry changed, whose answer cannot.
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
REF = "v1.0.0"                               # the release this notebook ships in: Colab clones THIS

try:
    import google.colab                      # noqa: F401 - succeeds only on Colab
    ON_COLAB = True
except ImportError:
    ON_COLAB = False

if ON_COLAB:
    if not os.path.isdir("/content/teaching-code"):
        subprocess.run(["git", "clone", "--quiet", "--depth", "1", "--branch", REF, REPO_URL, "/content/teaching-code"], check=True)
    os.chdir("/content/teaching-code/notebooks/10_game_theory")
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
## The coin game

Both players show heads or tails at once. A match pays the row player one dollar; a mismatch costs
one. Each table is instance data, so it lives in `data/raw/` and this notebook and the package read
the same file.
""")
code(r'''
from orteach import tolerance
from orteach.games import load_game

coin = load_game("coin_2x2.csv")
print(f"{'':7}" + "".join(f"{c:>7}" for c in coin.cols))
for r in coin.rows:
    print(f"{r:7}" + "".join(f"{coin.payoff[r, c]:7.0f}" for c in coin.cols))
''')

md(r"""
You already know the answer here. Write down the mix and the value before running, so the LP has
something to agree or disagree with. The row player's LP has one constraint per column: against
each, the expected payment must be at least $v$.
""")
code(r'''
mc = gp.Model("coin, row player", env=env)
tolerance.apply(mc)
pc = mc.addVars(coin.rows, lb=0.0, name="p")
vc = mc.addVar(lb=-GRB.INFINITY, name="value")
mc.addConstr(pc["heads"] + pc["tails"] == 1, name="probability")
mc.addConstr(coin.payoff["heads", "heads"] * pc["heads"] + coin.payoff["tails", "heads"] * pc["tails"] >= vc, name="against[heads]")
mc.addConstr(coin.payoff["heads", "tails"] * pc["heads"] + coin.payoff["tails", "tails"] * pc["tails"] >= vc, name="against[tails]")
mc.setObjective(vc, GRB.MAXIMIZE)
mc.optimize()
coin_value = mc.ObjVal + 0.0                 # + 0.0 turns a printed -0.0 into 0.0
coin_p = {r: pc[r].X for r in coin.rows}
print(f"value {coin_value:.4f}   p {({r: round(x, 4) for r, x in coin_p.items()})}")
''')

md(r"""
## Taha's advertising game

Two companies sell flu medicine. A advertises on radio, TV or in newspapers (A1–A3); B on radio,
TV, in newspapers or by e-mail (B1–B4). Each entry is the share of the market, in percent, that A
gains from B.

Before any LP, the pure-strategy check from the lecture: the row player's maximin (the best of each
row's worst column) and the column player's minimax (the least of each column's worst row).
""")
code(r'''
flu = load_game("flu_advertising_3x4.csv")
print(f"{'':5}" + "".join(f"{c:>5}" for c in flu.cols))
for r in flu.rows:
    print(f"{r:5}" + "".join(f"{flu.payoff[r, c]:5.0f}" for c in flu.cols))

row_worst = {r: min(flu.payoff[r, c] for c in flu.cols) for r in flu.rows}
col_worst = {c: max(flu.payoff[r, c] for r in flu.rows) for c in flu.cols}
print("\neach row's worst   ", row_worst, " -> maximin", max(row_worst.values()))
print("each column's worst", col_worst, " -> minimax", min(col_worst.values()))
''')

md(r"""
They meet. Predict what the row player's LP will do with that, then build it: four constraints, one
per column, each reading its three coefficients from the table. The `against` dictionary keeps a
handle on each constraint, because the next section changes one of them.
""")
code(r'''
m = gp.Model("advertising, row player", env=env)
tolerance.apply(m)
p = m.addVars(flu.rows, lb=0.0, name="p")
v = m.addVar(lb=-GRB.INFINITY, name="value")
a = flu.payoff
m.addConstr(p["A1"] + p["A2"] + p["A3"] == 1, name="probability")
against = {}
against["B1"] = m.addConstr(a["A1", "B1"] * p["A1"] + a["A2", "B1"] * p["A2"] + a["A3", "B1"] * p["A3"] >= v, name="against[B1]")
against["B2"] = m.addConstr(a["A1", "B2"] * p["A1"] + a["A2", "B2"] * p["A2"] + a["A3", "B2"] * p["A3"] >= v, name="against[B2]")
against["B3"] = m.addConstr(a["A1", "B3"] * p["A1"] + a["A2", "B3"] * p["A2"] + a["A3", "B3"] * p["A3"] >= v, name="against[B3]")
against["B4"] = m.addConstr(a["A1", "B4"] * p["A1"] + a["A2", "B4"] * p["A2"] + a["A3", "B4"] * p["A3"] >= v, name="against[B4]")
m.setObjective(v, GRB.MAXIMIZE)
m.optimize()
flu_value = m.ObjVal
flu_p = {r: p[r].X for r in flu.rows}
flu_q = {c: -against[c].Pi + 0.0 for c in flu.cols}  # minus the duals: the column player's mix (+ 0.0: no -0.0)
print(f"value {flu_value:.4f}")
print("p", {r: round(x, 4) for r, x in flu_p.items()})
print("q from the duals", {c: round(x, 4) for c, x in flu_q.items()})
''')

md(r"""
Nobody told the LP there was a saddle point; it put all its weight on one row anyway, and the duals
put all of B's on one column. Which cell of the table is that?

## Change one entry

Set A's payoff for TV against TV, the saddle cell, from 5 to 2. It is the knob this section turns,
so it is written out here and passed to everything below, including the package check.
""")
code(r'''
TV_VS_TV = 2.0

flu2 = load_game("flu_advertising_3x4.csv")
flu2.payoff["A2", "B2"] = TV_VS_TV
row_worst2 = {r: min(flu2.payoff[r, c] for c in flu2.cols) for r in flu2.rows}
col_worst2 = {c: max(flu2.payoff[r, c] for r in flu2.rows) for c in flu2.cols}
print("maximin", max(row_worst2.values()), "  minimax", min(col_worst2.values()))
''')

md(r"""
They no longer meet, so the value must lie strictly between them, and nothing on the table says
where. Predict the value and the support of A's mix.

The model is still in memory. One coefficient changed, so change one coefficient: `chgCoeff` sets
the entry for $p_{A2}$ in the constraint against B2. Nothing else in the model moves.
""")
code(r'''
m.chgCoeff(against["B2"], p["A2"], TV_VS_TV)
m.optimize()
flu2_value = m.ObjVal
flu2_p = {r: p[r].X for r in flu2.rows}
flu2_q = {c: -against[c].Pi + 0.0 for c in flu2.cols}
print(f"value {flu2_value:.4f}")
print("p", {r: round(x, 4) for r, x in flu2_p.items()})
print("q from the duals", {c: round(x, 4) for c, x in flu2_q.items()})
print("slack against each column", {c: round(against[c].Slack, 4) for c in flu2.cols})
''')

md(r"""
Look at which columns B mixes over and which constraints have zero slack. What does complementary
slackness say the connection is, and would you have guessed those two columns from the table?

---

# Now the streamlined version

Three LPs built by hand, one of them edited in place, so the package owns the construction from
here: `games.solve_row` and `games.solve_column` for the two LPs, `games.has_saddle_point` for the
check you did by hand. Each takes the same game objects, including the edited one.
""")
code(r'''
from orteach import games
from orteach.tolerance import AGREEMENT_RTOL, rel_diff

pkg = {name: (games.solve_row(g, env=env), games.solve_column(g, env=env), games.has_saddle_point(g))
       for name, g in (("coin", coin), ("flu", flu), ("flu, one entry changed", flu2))}
for name, (row, col, saddle) in pkg.items():
    print(f"{name:24} value {row.value + 0.0:7.4f}   saddle point {saddle}   p {({k: round(x, 4) for k, x in row.probs.items()})}")
''')

md(r"""
## The agreement assertion

Values and both players' strategies, hand-built against the package, for all three games. Each
optimal mix here is unique (checked when this notebook was written, by maximising and minimising
every probability over the optimal set), so whole vectors are compared, not only guarantees.
""")
code(r'''
checks = [("coin value", coin_value, pkg["coin"][0].value),
          ("flu value", flu_value, pkg["flu"][0].value),
          ("changed value", flu2_value, pkg["flu, one entry changed"][0].value),
          ("changed: row = column value", flu2_value, pkg["flu, one entry changed"][1].value)]
for r in coin.rows:
    checks.append((f"coin p[{r}]", coin_p[r], pkg["coin"][0].probs[r]))
for r in flu.rows:
    checks.append((f"flu p[{r}]", flu_p[r], pkg["flu"][0].probs[r]))
    checks.append((f"changed p[{r}]", flu2_p[r], pkg["flu, one entry changed"][0].probs[r]))
for c in flu.cols:
    checks.append((f"flu q[{c}]", flu_q[c], pkg["flu"][1].probs[c]))
    checks.append((f"changed q[{c}]", flu2_q[c], pkg["flu, one entry changed"][1].probs[c]))
assert pkg["flu"][2] and not pkg["flu, one entry changed"][2] and not pkg["coin"][2], "saddle-point verdicts differ"

worst = max(rel_diff(h, k) for _, h, k in checks)
print(f"{len(checks)} comparisons, plus the three saddle-point verdicts")
for name, hand, packaged in checks[:4]:
    print(f"  {name:28} hand {hand + 0.0:8.4f}   package {packaged + 0.0:8.4f}   rel {rel_diff(hand, packaged):.2e}")
print("  ...")
assert worst < AGREEMENT_RTOL, f"notebook and package disagree by {worst:.2e}"
print(f"\nnotebook and package agree to {worst:.1e}")
''')

md(r"""
---

## Where to take this next

- Add 100 to every entry of the changed game and re-solve. Predict which numbers move and which do
  not, then check.
- Is any of B's columns dominated in the changed game, by another column or by a mix of two? If
  you find one, delete it from the table and confirm the value does not change.
- With A's mix fixed at the changed game's optimum, compute A's expected payoff against each of
  B's four columns. Which ones equal the value, and is that the set B mixes over?
- Try `TV_VS_TV` at 4. Is there a saddle point, and what does the LP do?
""")

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                   "language_info": {"name": "python", "version": "3.13"}}, "nbformat": 4, "nbformat_minor": 5}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    f.write("\n")
print("wrote %s  (%d cells)" % (OUT, len(cells)))
