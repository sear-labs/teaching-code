"""Domain invariants for zero-sum games.

The minimax theorem - row value equals column value - is the headline. The
checks that catch bugs are cheaper: a mixed strategy must guarantee its
claimed value against every pure reply, the row LP's duals must be a valid
column strategy, and a game with no saddle point must have its value strictly
between the pure maximin and minimax. The undergraduate notebooks shipped a
row LP whose payoff terms had silently vanished, giving value 0; the last
test would have caught that on the first run.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

from orteach import games  # noqa: E402
from orteach.tolerance import AGREEMENT_RTOL, FEASIBILITY_ATOL, rel_diff  # noqa: E402


@pytest.fixture(scope="module")
def game():
    return games.load_game("zero_sum_2x4.csv")


@pytest.fixture(scope="module")
def row(game):
    return games.solve_row(game)


@pytest.fixture(scope="module")
def col(game):
    return games.solve_column(game)


def test_the_table_has_the_expected_shape(game):
    assert len(game.rows) == 2 and len(game.cols) == 4
    assert game.payoff["r1", "c4"] == -1.0


def test_minimax_theorem(row, col):
    assert rel_diff(row.value, col.value) < AGREEMENT_RTOL


def test_strategies_are_distributions(row, col):
    for s in (row, col):
        assert abs(sum(s.probs.values()) - 1.0) < FEASIBILITY_ATOL
        assert all(p >= -FEASIBILITY_ATOL for p in s.probs.values())


def test_a_strategy_guarantees_its_value_against_every_pure_reply(game, row, col):
    assert games.worst_case(game, row.probs, "row") >= row.value - FEASIBILITY_ATOL
    assert games.worst_case(game, col.probs, "column") <= col.value + FEASIBILITY_ATOL


def test_no_saddle_point_so_mixing_is_needed(game, row):
    lo, _ = games.maximin(game)
    hi, _ = games.minimax(game)
    assert not games.has_saddle_point(game)
    assert lo < row.value - FEASIBILITY_ATOL < hi - 2 * FEASIBILITY_ATOL


def test_row_lp_duals_are_a_column_strategy(game, row, col):
    """Minus the duals of the row player's column constraints is an optimal
    column strategy: sums to one, non-negative, and holds every row to the
    game value. It need not equal solve_column's answer - the column optimum
    here is not unique - so it is checked as a strategy, not as a vector."""
    q = {c: -row.duals[c] for c in game.cols}
    assert abs(sum(q.values()) - 1.0) < FEASIBILITY_ATOL
    assert all(v >= -FEASIBILITY_ATOL for v in q.values())
    assert games.worst_case(game, q, "column") <= col.value + FEASIBILITY_ATOL


def test_the_value_is_not_zero(row):
    """Four IE 3315 term folders shipped this game with value 0.0 and the row
    player putting everything on one row, because the payoff terms had
    dropped out of the constraints. The correct value is 2.5."""
    assert abs(row.value - 2.5) < FEASIBILITY_ATOL
    assert abs(row.probs["r1"] - 0.5) < FEASIBILITY_ATOL


def test_column_optimum_is_a_segment(game, col):
    """Every q = (0, 0.5 - 4d, 0.5 + 3d, d) for d in [0, 1/8] holds both rows
    to 2.5. Pinning the degeneracy so the notebook can teach it."""
    for d in (0.0, 0.0625, 0.125):
        q = {"c1": 0.0, "c2": 0.5 - 4 * d, "c3": 0.5 + 3 * d, "c4": d}
        assert games.worst_case(game, q, "column") <= col.value + FEASIBILITY_ATOL
