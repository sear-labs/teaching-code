"""Domain invariants for Markov chains and single queues.

For chains: a steady state is a fixed point and a distribution; matrix powers
converge to it; the fundamental matrix gives absorption times that agree with
brute-force iteration. For queues: the closed forms reproduce the numbers R's
queueing package printed in the course notebooks; Little's law holds; and the
simulation, given enough customers, lands near the formula.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

from orteach import markov, queueing  # noqa: E402
from orteach.tolerance import AGREEMENT_RTOL, FEASIBILITY_ATOL, LINALG_ATOL, rel_diff  # noqa: E402


@pytest.fixture(scope="module")
def zones():
    return markov.load_chain("driver_zones.csv")


@pytest.fixture(scope="module")
def absorbing():
    return markov.load_chain("absorbing_4state.csv")


def test_tables_are_stochastic_matrices(zones, absorbing):
    for ch in (zones, absorbing):
        assert np.allclose(ch.P.sum(axis=1), 1.0)
        assert (ch.P >= 0).all()


def test_a_bad_table_is_refused():
    with pytest.raises(ValueError):
        markov.Chain(["a", "b"], [[0.5, 0.6], [0.5, 0.5]])


def test_steady_state_is_a_fixed_point_and_a_distribution(zones):
    pi = markov.steady_state(zones)
    assert abs(pi.sum() - 1.0) < FEASIBILITY_ATOL
    assert (pi > 0).all()
    assert np.allclose(pi @ zones.P, pi, atol=FEASIBILITY_ATOL)


def test_powers_converge_to_the_steady_state(zones):
    pi = markov.steady_state(zones)
    far = markov.n_step(zones, 50)
    for i in range(len(zones.states)):
        assert np.allclose(far[i], pi, atol=LINALG_ATOL)


def test_the_taxi_steady_state_by_hand(zones):
    """7/18, 1/3, 5/18 - solved on paper from pi P = pi, sum pi = 1."""
    pi = markov.steady_state(zones)
    assert np.allclose(pi, [7 / 18, 1 / 3, 5 / 18], atol=1e-12)


def test_two_state_three_step_check():
    """The R notebook's hand check: from state 1, after three steps of
    [[1/2, 1/2], [1/3, 2/3]], the chain is in state 1 with probability 29/72."""
    ch = markov.Chain(["1", "2"], [[0.5, 0.5], [1 / 3, 2 / 3]])
    assert abs(markov.distribution_after(ch, "1", 3)[0] - 29 / 72) < 1e-12


def test_absorption_matches_brute_force(absorbing):
    """Expected steps from the fundamental matrix must equal the sum over n of
    P(still transient after n steps), which is what N 1 is a closed form
    for. Truncated at 2000 steps, which is far past convergence."""
    ab = markov.absorption(absorbing)
    assert ab.absorbing == ["C"]
    ti = [absorbing.index(s) for s in ab.transient]
    for k, s in enumerate(ab.transient):
        start = np.zeros(4); start[absorbing.index(s)] = 1.0
        expected = 0.0
        dist = start.copy()
        for n in range(2000):
            expected += dist[ti].sum()
            dist = dist @ absorbing.P
        assert abs(expected - ab.expected_steps[s]) < LINALG_ATOL, s
    for s in ab.transient:
        assert abs(ab.probability[s, "C"] - 1.0) < LINALG_ATOL


def test_mm1_matches_the_r_package_output():
    """The course notebook ran R's queueing::QueueingModel on lambda=2, mu=3
    and printed L=2, Lq=4/3, W=1, Wq=2/3, P0=1/3."""
    q = queueing.mm1(2.0, 3.0)
    for got, want in ((q.L, 2.0), (q.Lq, 4 / 3), (q.W, 1.0), (q.Wq, 2 / 3), (q.P0, 1 / 3)):
        assert rel_diff(got, want) < AGREEMENT_RTOL


def test_mmc_matches_the_r_package_output():
    """Same source, M/M/2 with lambda=2, mu=3: P0=0.5, Lq=1/12, Wq=1/24,
    L=0.75, W=0.375."""
    q = queueing.mmc(2.0, 3.0, 2)
    for got, want in ((q.P0, 0.5), (q.Lq, 1 / 12), (q.Wq, 1 / 24), (q.L, 0.75), (q.W, 0.375)):
        assert rel_diff(got, want) < AGREEMENT_RTOL


def test_mmc_with_one_server_is_mm1():
    a, b = queueing.mm1(2.0, 3.0), queueing.mmc(2.0, 3.0, 1)
    for x, y in ((a.L, b.L), (a.Lq, b.Lq), (a.W, b.W), (a.Wq, b.Wq), (a.P0, b.P0)):
        assert rel_diff(x, y) < AGREEMENT_RTOL


def test_littles_law():
    for q in (queueing.mm1(2.0, 3.0), queueing.mmc(2.0, 3.0, 2), queueing.mmc(5.0, 2.0, 4)):
        lam = q.L / q.W
        assert rel_diff(q.Lq, lam * q.Wq) < AGREEMENT_RTOL


def test_unstable_queue_is_refused():
    with pytest.raises(ValueError):
        queueing.mm1(3.0, 2.0)
    with pytest.raises(ValueError):
        queueing.mmc(6.0, 3.0, 2)


def test_state_probabilities_sum_to_one():
    assert abs(sum(queueing.p_n(2.0, 3.0, n) for n in range(400)) - 1.0) < LINALG_ATOL


def test_simulation_is_reproducible_and_near_the_formula():
    a = queueing.simulate_mm1(2.0, 3.0, 200_000, seed=7)
    b = queueing.simulate_mm1(2.0, 3.0, 200_000, seed=7)
    assert a.Wq == b.Wq and a.W == b.W
    exact = queueing.mm1(2.0, 3.0)
    assert abs(a.Wq - exact.Wq) < 0.05
    assert abs(a.W - exact.W) < 0.05
