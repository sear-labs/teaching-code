"""Two-person zero-sum games, solved as linear programs - written once for a
machine.

A payoff matrix is a TABLE (Part 4): rows are the row player's pure
strategies, columns the column player's, entries are what the column player
pays the row player. ``data/raw/zero_sum_2x4.csv`` is the course's example.

The row player picks a probability vector p over rows to make the worst
column as good as possible; the column player picks q over columns to make
the worst row as cheap as possible. Each is an LP, and they are duals of each
other - the minimax theorem is strong duality in costume. ``solve_row``
returns the row LP's duals as well, because minus those duals is an optimal
strategy for the column player, which the teaching notebook in
``notebooks/10_game_theory/`` checks.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field

import gurobipy as gp

from . import tolerance

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data", "raw")


@dataclass
class Game:
    rows: list
    cols: list
    payoff: dict            # (row, col) -> payoff to the row player
    name: str = "game"


def load_game(filename: str) -> Game:
    """Matrix layout: first column names the row, header names the columns."""
    with open(os.path.join(DATA_DIR, filename), encoding="utf-8") as f:
        recs = list(csv.DictReader(f))
    cols = [k for k in recs[0].keys() if k != "row"]
    rows = [r["row"] for r in recs]
    return Game(rows, cols, {(r["row"], c): float(r[c]) for r in recs for c in cols},
                name=filename.replace(".csv", ""))


def maximin(game: Game):
    """Best pure strategy for the row player: the row whose worst column is
    largest. Returns (value, row)."""
    return max((min(game.payoff[r, c] for c in game.cols), r) for r in game.rows)


def minimax(game: Game):
    """Best pure strategy for the column player: the column whose worst row
    (largest payment) is smallest. Returns (value, col)."""
    return min((max(game.payoff[r, c] for r in game.rows), c) for c in game.cols)


def has_saddle_point(game: Game) -> bool:
    return abs(maximin(game)[0] - minimax(game)[0]) < tolerance.FEASIBILITY_ATOL


@dataclass
class Mixed:
    value: float
    probs: dict             # strategy -> probability
    duals: dict             # opponent's strategy -> dual of its constraint
    label: str = ""

    def support(self):
        return [s for s, p in self.probs.items() if p > tolerance.FEASIBILITY_ATOL]


def solve_row(game: Game, env=None) -> Mixed:
    """max v  s.t.  sum_r p_r a[r,c] >= v for every column c,  sum p = 1,  p >= 0."""
    with gp.Model(env=env) as m:
        tolerance.apply(m)
        p = m.addVars(game.rows, lb=0.0, name="p")
        v = m.addVar(lb=-gp.GRB.INFINITY, name="value")
        m.addConstr(p.sum() == 1.0, name="probability")
        against = {c: m.addConstr(gp.quicksum(game.payoff[r, c] * p[r] for r in game.rows) >= v,
                                  name="against[%s]" % c) for c in game.cols}
        m.setObjective(v, gp.GRB.MAXIMIZE)
        m.optimize()
        if m.Status != gp.GRB.OPTIMAL:
            raise RuntimeError("row LP ended with status %d" % m.Status)
        return Mixed(m.ObjVal, {r: p[r].X for r in game.rows},
                     {c: against[c].Pi for c in game.cols}, "row player")


def solve_column(game: Game, env=None) -> Mixed:
    """min w  s.t.  sum_c q_c a[r,c] <= w for every row r,  sum q = 1,  q >= 0."""
    with gp.Model(env=env) as m:
        tolerance.apply(m)
        q = m.addVars(game.cols, lb=0.0, name="q")
        w = m.addVar(lb=-gp.GRB.INFINITY, name="value")
        m.addConstr(q.sum() == 1.0, name="probability")
        against = {r: m.addConstr(gp.quicksum(game.payoff[r, c] * q[c] for c in game.cols) <= w,
                                  name="against[%s]" % r) for r in game.rows}
        m.setObjective(w, gp.GRB.MINIMIZE)
        m.optimize()
        if m.Status != gp.GRB.OPTIMAL:
            raise RuntimeError("column LP ended with status %d" % m.Status)
        return Mixed(m.ObjVal, {c: q[c].X for c in game.cols},
                     {r: against[r].Pi for r in game.rows}, "column player")


def worst_case(game: Game, probs: dict, player: str) -> float:
    """What a mixed strategy guarantees against the opponent's best pure
    reply. For the row player, the smallest expected payoff over columns; for
    the column player, the largest expected payment over rows."""
    if player == "row":
        return min(sum(probs[r] * game.payoff[r, c] for r in game.rows) for c in game.cols)
    return max(sum(probs[c] * game.payoff[r, c] for c in game.cols) for r in game.rows)
