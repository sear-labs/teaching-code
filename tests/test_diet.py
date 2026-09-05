"""Domain invariants for the diet problem.

The one that matters is the direction of the nutrient rows: every intake at or
above its minimum. The source notebooks shipped with the protein row reversed,
which the solver accepted without complaint, so the tests pin both that the
correct model meets every minimum and that the reversed one is a different,
more expensive answer - a defect that changed the number, not a cosmetic one.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

from orteach import diet  # noqa: E402
from orteach.tolerance import AGREEMENT_RTOL, FEASIBILITY_ATOL, rel_diff  # noqa: E402

SIDE = dict(lower={"fish": 0.5}, upper={"milk": 1.0})


@pytest.fixture(scope="module")
def macros():
    return diet.load_diet("macros")


@pytest.fixture(scope="module")
def vitamins():
    return diet.load_diet("vitamins")


@pytest.fixture(scope="module")
def basket(macros):
    return diet.solve(macros, **SIDE)


def test_the_tables_have_the_expected_shape(macros, vitamins):
    assert len(macros.foods) == 6 and len(macros.nutrients) == 4
    assert len(vitamins.foods) == 4 and len(vitamins.nutrients) == 4
    assert len(macros.content) == 24 and len(vitamins.content) == 16


@pytest.mark.parametrize("stem", ["macros", "vitamins"])
def test_every_minimum_is_met(stem):
    inst = diet.load_diet(stem)
    b = diet.solve(inst, **(SIDE if stem == "macros" else {}))
    for n in inst.nutrients:
        assert b.intake[n] >= inst.minimum[n] - FEASIBILITY_ATOL, n


def test_objective_is_the_grocery_bill(macros, basket):
    bill = sum(macros.cost[f] * basket.servings[f] for f in macros.foods)
    assert rel_diff(bill, basket.objective) < AGREEMENT_RTOL


def test_side_bounds_hold(basket):
    assert basket.servings["fish"] >= 0.5 - FEASIBILITY_ATOL
    assert basket.servings["milk"] <= 1.0 + FEASIBILITY_ATOL


def test_side_bounds_cost_money(macros, basket):
    """Removing restrictions cannot raise a minimum. If it did, the bounds
    were being applied as something other than bounds."""
    free = diet.solve(macros)
    assert free.objective <= basket.objective + FEASIBILITY_ATOL


def test_at_least_one_minimum_binds(macros, basket):
    """A cost-minimising diet with no binding nutrient would be one the
    solver could make cheaper; that would mean the objective is wrong."""
    tight = [n for n in macros.nutrients if abs(basket.intake[n] - macros.minimum[n]) < FEASIBILITY_ATOL]
    assert tight


def test_nutrient_prices_are_nonnegative(basket):
    """Minimising subject to >= rows: relaxing a minimum can only help, so
    every shadow price is >= 0. A negative one means a row points the wrong
    way."""
    for n, pi in basket.nutrient_price.items():
        assert pi >= -FEASIBILITY_ATOL, n


def test_the_reversed_protein_row_changes_the_answer(macros, basket):
    """The defect the source carried. With protein written as a maximum the
    solver sits on the ceiling from below and buys a different, dearer
    basket. This pins that the two are genuinely different answers, so a
    future 'cleanup' that made flip= a no-op would be caught."""
    wrong = diet.solve(macros, flip=("protein",), **SIDE)
    assert wrong.intake["protein"] <= macros.minimum["protein"] + FEASIBILITY_ATOL
    assert abs(wrong.intake["protein"] - macros.minimum["protein"]) < FEASIBILITY_ATOL
    assert rel_diff(wrong.objective, basket.objective) > 1e-2
    assert wrong.objective > basket.objective


def test_the_reversed_row_reproduces_what_shipped(macros):
    """The three IE 3315 term folders printed $12.08 for this instance. The
    number is recorded here so the defect stays identifiable, not because it
    is a target."""
    wrong = diet.solve(macros, flip=("protein",), **SIDE)
    assert abs(wrong.objective - 12.0813) < 1e-3
