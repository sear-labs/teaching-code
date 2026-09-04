"""Domain invariants for the Monte Carlo estimators.

The hard part of testing a stochastic routine is that "close enough" is a
statistical claim, not a tolerance somebody picked. So every tolerance here is
expressed in **standard errors**, and the seed is fixed — which makes these
deterministic tests of a random procedure rather than flaky ones.

Uses math.erf for the exact normal CDF rather than scipy, so the test suite does
not add a dependency the package itself does not have.
"""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

from orteach import montecarlo as mc  # noqa: E402

SEED = 20260904


def normal_cdf(x, mu, sigma):
    return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2.0))))


def test_pi_lands_within_four_standard_errors():
    r = mc.estimate_pi(200_000, seed=SEED)
    # r.estimate is the proportion inside; pi is 4x it, so the error on pi is 4x.
    err = abs(4 * r.estimate - math.pi)
    assert err < 4 * 4 * r.std_error, "pi off by %.2e, which is more than 4 SE" % err


def test_normal_interval_matches_the_analytic_answer():
    lo, hi, mu, sigma = 3, 6, 1, 10
    r = mc.estimate_normal_interval(lo, hi, mu, sigma, n=200_000, seed=SEED)
    exact = normal_cdf(hi, mu, sigma) - normal_cdf(lo, mu, sigma)
    assert abs(r.estimate - exact) < 4 * r.std_error


def test_spinner_simulation_brackets_the_exact_probability():
    """The whole point of computing the exact answer: the simulation has
    something true to be checked against, rather than against itself."""
    r = mc.simulate_spinner(200_000, seed=SEED)
    exact = mc.exact_spinner_probability()
    lo, hi = r.ci95()
    assert lo <= exact <= hi, \
        "exact %.6f outside the 95%% CI [%.6f, %.6f]" % (exact, lo, hi)


def test_the_exact_distribution_is_a_probability():
    """A shape assert. If the convolution loses mass the answer is wrong in a way
    that still looks like a plausible number."""
    p = mc.exact_spinner_probability()
    assert 0.0 <= p <= 1.0


def test_exact_probability_is_one_when_losing_is_certain():
    """Every wedge negative: the total is always negative, so P = 1 exactly.
    Guards the convolution against an off-by-one in the comparison."""
    assert mc.exact_spinner_probability(wedges=(-1, -2), spins=3) == pytest.approx(1.0)


def test_exact_probability_is_zero_when_losing_is_impossible():
    assert mc.exact_spinner_probability(wedges=(1, 2), spins=3) == pytest.approx(0.0)


def test_error_shrinks_as_one_over_root_n():
    """The defining property of Monte Carlo, asserted rather than described:
    a hundredfold more samples should roughly halve the error twice over."""
    small = mc.simulate_spinner(10_000, seed=SEED)
    large = mc.simulate_spinner(1_000_000, seed=SEED)
    ratio = small.std_error / large.std_error
    # sqrt(100) = 10; allow a generous band because the estimates differ slightly.
    assert 7 < ratio < 14, "SE ratio %.2f is not consistent with 1/sqrt(n)" % ratio


def test_the_same_seed_reproduces_the_same_answer():
    """Without this the notebook's printed numbers decay on the next run, which
    is the bug the original Monte Carlo notebooks all had."""
    a = mc.simulate_spinner(50_000, seed=SEED)
    b = mc.simulate_spinner(50_000, seed=SEED)
    assert a.estimate == b.estimate


def test_different_seeds_give_different_answers():
    """The companion check: if this fails, the seed is being ignored and the
    reproducibility above is an illusion."""
    a = mc.simulate_spinner(50_000, seed=1)
    b = mc.simulate_spinner(50_000, seed=2)
    assert a.estimate != b.estimate
