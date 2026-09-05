"""The newsvendor model, written once for a machine.

The teaching notebook in ``notebooks/07_stochastic_and_newsvendor/`` builds this
same model by hand, cell by cell. That duplication is deliberate — standard
Part 4 — because the hand-built version is the lesson and this version is the
code. The agreement assertion at the end of the notebook is what keeps the two
honest.

**Every solver here takes ``demand`` as an argument and never reads a file.**
That is a Part 4 requirement, not a style preference: a reader who edits a
demand value in the notebook must see it flow into both the hand-built model and
the check, or the assertion punishes experimenting and gets switched off.

The four solvers answer four different questions about the same situation:

    solve_stochastic          one order quantity, good across all scenarios
    solve_expected_value      one order quantity, chosen as if demand were certain
    solve_perfect_information one order quantity PER scenario - a clairvoyant
    solve_max_worst_case      the order that makes the worst scenario least bad

The gaps between them are the content: EVPI is what clairvoyance would be worth,
VSS is what modelling uncertainty is worth.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean, stdev

import gurobipy as gp

from . import tolerance


@dataclass
class NewsvendorResult:
    """What one solve produced. ``profits`` is per scenario, in scenario order."""

    order: float
    profits: list[float] = field(repr=False)
    label: str = ""

    @property
    def expected_profit(self) -> float:
        return mean(self.profits)

    @property
    def worst_profit(self) -> float:
        return min(self.profits)

    @property
    def std_error(self) -> float:
        """Standard error of the mean — the sampling noise on expected_profit."""
        n = len(self.profits)
        return stdev(self.profits) / (n ** 0.5) if n > 1 else 0.0

    def ci95(self) -> tuple[float, float]:
        half = 1.96 * self.std_error
        return (self.expected_profit - half, self.expected_profit + half)


def _bounds(demand, cost, retail, recover):
    """Tight bounds on profit, so the LP relaxation is not wide open.

    Best case: sell every unit at retail. Worst case: buy the largest demand
    seen, scrap all of it, and sell only the smallest demand.
    """
    hi = max(demand) * (retail - cost)
    lo = max(demand) * (recover - cost) + min(demand) * retail
    return lo, hi


def _check_economics(cost, retail, recover):
    if recover >= cost:
        raise ValueError(
            "recover (%g) must be strictly less than cost (%g), or buying "
            "unlimited stock to scrap is profitable and the model is unbounded."
            % (recover, cost))
    if retail <= cost:
        raise ValueError(
            "retail (%g) must exceed cost (%g), or ordering nothing is optimal "
            "and the problem is not interesting." % (retail, cost))


def solve_stochastic(demand, cost, retail, recover, env=None) -> NewsvendorResult:
    """One order quantity, chosen before demand is known, good on average.

    This is the two-stage recourse model: ``order`` is the first-stage decision,
    and ``sales``/``discount`` are the second-stage recourse, chosen per scenario
    after demand is revealed.
    """
    _check_economics(cost, retail, recover)
    n = len(demand)
    lo, hi = _bounds(demand, cost, retail, recover)

    with gp.Model(env=env) as m:
        tolerance.apply(m)          # solve as tightly as the notebook asserts
        m.ModelSense = gp.GRB.MAXIMIZE
        order = m.addVar(name="order")
        profit = m.addVars(n, obj=1.0 / n, lb=lo, ub=hi, name="profit")
        sales = m.addVars(n, ub=demand, name="sales")
        discount = m.addVars(n, name="discount")
        m.addConstrs((profit[i] == -order * cost + sales[i] * retail
                      + recover * discount[i] for i in range(n)), name="profit")
        m.addConstrs((sales[i] + discount[i] == order for i in range(n)), name="demand")
        m.optimize()
        return NewsvendorResult(order.X, [profit[i].X for i in range(n)], "stochastic")


def evaluate_order(demand, cost, retail, recover, order) -> NewsvendorResult:
    """Profit per scenario for an order quantity decided some other way.

    No solver needed — once the order is fixed, each scenario's outcome is
    arithmetic. This is how a candidate order is scored fairly against the
    stochastic one: same scenarios, same accounting.
    """
    profits = []
    for d in demand:
        sold = min(order, d)
        scrapped = order - sold
        profits.append(-order * cost + sold * retail + recover * scrapped)
    return NewsvendorResult(float(order), profits, "evaluated")


def solve_expected_value(demand, cost, retail, recover, env=None) -> NewsvendorResult:
    """Order as if demand were certain at its mean, then score that order honestly.

    The trap this illustrates: solving with the average demand is easy and gives
    a *worse* answer than solving with the distribution. The difference is the
    Value of the Stochastic Solution.
    """
    _check_economics(cost, retail, recover)
    mu = mean(demand)
    # With demand certain, the newsvendor orders exactly demand: every unit sells.
    result = evaluate_order(demand, cost, retail, recover, mu)
    result.label = "expected value"
    return result


def solve_perfect_information(demand, cost, retail, recover, env=None) -> NewsvendorResult:
    """A different order for every scenario — a vendor who knows tomorrow's demand.

    Not achievable. It is an upper bound, and the gap to the stochastic solution
    is the Expected Value of Perfect Information.
    """
    _check_economics(cost, retail, recover)
    # Knowing demand, order exactly demand: sell everything, scrap nothing.
    profits = [d * (retail - cost) for d in demand]
    return NewsvendorResult(float("nan"), profits, "perfect information")


def solve_max_worst_case(demand, cost, retail, recover, env=None) -> NewsvendorResult:
    """Maximise the worst scenario's profit rather than the average.

    A risk-averse objective. It buys protection against the bad tail, and the
    price of that protection shows up as lower expected profit.
    """
    _check_economics(cost, retail, recover)
    n = len(demand)
    lo, hi = _bounds(demand, cost, retail, recover)

    with gp.Model(env=env) as m:
        tolerance.apply(m)          # solve as tightly as the notebook asserts
        m.ModelSense = gp.GRB.MAXIMIZE
        worst = m.addVar(lb=lo, ub=hi, obj=1, name="worst")
        order = m.addVar(name="order")
        profit = m.addVars(n, lb=lo, ub=hi, name="profit")
        sales = m.addVars(n, ub=demand, name="sales")
        discount = m.addVars(n, name="discount")
        m.addConstrs((profit[i] == -order * cost + sales[i] * retail
                      + recover * discount[i] for i in range(n)), name="profit")
        m.addConstrs((sales[i] + discount[i] == order for i in range(n)), name="demand")
        m.addConstrs((worst <= profit[i] for i in range(n)), name="worst")
        m.optimize()
        return NewsvendorResult(order.X, [profit[i].X for i in range(n)], "max worst case")


def evpi(stochastic: NewsvendorResult, perfect: NewsvendorResult) -> float:
    """Expected Value of Perfect Information — what clairvoyance would be worth."""
    return perfect.expected_profit - stochastic.expected_profit


def vss(stochastic: NewsvendorResult, expected_value: NewsvendorResult) -> float:
    """Value of the Stochastic Solution — what modelling the uncertainty is worth."""
    return stochastic.expected_profit - expected_value.expected_profit
