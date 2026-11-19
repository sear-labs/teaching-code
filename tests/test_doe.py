"""Design of experiments: the designs have the properties the notebooks claim, the
alias algebra agrees with the columns, and the reactor table regenerates exactly.

The fraction checks compare two independent routes to the same answer - the
algebraic one (multiplying words in the defining relation) and the numerical one
(finding which columns are identical in the selected rows) - because a teaching
claim like "D is aliased with AB" should hold however it is derived.
"""
import itertools
import os
import sys

import numpy as np
import pytest
from scipy import stats

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

from orteach import doe  # noqa: E402
from orteach.tolerance import AGREEMENT_RTOL, rel_diff  # noqa: E402

HALF = {"E": "ABCD"}
QUARTER = {"D": "AB", "E": "AC"}


@pytest.fixture(scope="module")
def reactor():
    r = doe.load_reactor()
    corner = np.array(r["kind"]) == "factorial"
    X = np.column_stack([np.array(r[f])[corner] for f in doe.FACTORS]).astype(float)
    y = np.array(r["yield"])[corner]
    yc = np.array(r["yield"])[~corner]
    return X, y, yc


# ------------------------------------------------------------------ the table

def test_reactor_table_regenerates_exactly():
    gen, table = doe.generate_reactor(), doe.load_reactor()
    assert gen == table
    assert table["kind"].count("center") == doe.REACTOR_CENTER_RUNS
    assert sorted(table["run_order"]) == list(range(1, len(table["run"]) + 1))


def test_reactor_corners_are_the_full_factorial_in_standard_order(reactor):
    X, _, _ = reactor
    assert (X == doe.full_factorial(5)).all()


# ------------------------------------------------------------- full factorial

@pytest.mark.parametrize("k", [2, 3, 5])
def test_full_factorial_is_balanced_and_orthogonal(k):
    X = doe.full_factorial(k)
    assert X.shape == (2 ** k, k)
    assert (X.sum(axis=0) == 0).all()
    assert (X.T @ X == 2 ** k * np.eye(k)).all()
    assert (X[:, 0] == np.tile([-1, 1], 2 ** (k - 1))).all()     # first column fastest


def test_all_effect_columns_are_mutually_orthogonal():
    X = doe.full_factorial(5)
    cols = np.column_stack([doe.column(X, w) for w in doe.words()])
    assert cols.shape[1] == 31
    assert (cols.T @ cols == 32 * np.eye(31)).all()


def test_coefficients_are_half_the_effects_on_an_orthogonal_design(reactor):
    X, y, _ = reactor
    eff = doe.effects(X, y)
    terms = ["A", "B", "C", "D", "E", "AB"]
    coef = doe.coefficients(X, y, terms)
    for w in terms:
        assert rel_diff(coef[w], eff[w] / 2) < AGREEMENT_RTOL
    assert rel_diff(coef["intercept"], y.mean()) < AGREEMENT_RTOL


def test_full_factorial_recovers_the_true_model(reactor):
    """With sigma 1.5 and 32 runs a coefficient's standard error is 1.5/sqrt(32),
    about 0.27; every true term must be inside four of them."""
    X, y, _ = reactor
    coef = doe.coefficients(X, y, ["A", "B", "C", "D", "E", "AB"])
    se = doe.REACTOR_SIGMA / np.sqrt(32)
    for w in ["A", "B", "C", "AB"]:
        assert abs(coef[w] - doe.REACTOR_TRUTH[w]) < 4 * se
    for w in ["D", "E"]:
        assert abs(coef[w]) < 4 * se


# ----------------------------------------------------------------- fractions

def _numerical_aliases(X, mask, word):
    cols = {w: doe.column(X, w)[mask] for w in doe.words()}
    return sorted((v for v in cols if v != word and (cols[v] == cols[word]).all()),
                  key=lambda w: (len(w), w))


@pytest.mark.parametrize("gens, size, res", [(HALF, 16, 5), (QUARTER, 8, 3)])
def test_fraction_size_and_resolution(gens, size, res):
    X = doe.full_factorial(5)
    mask = doe.fraction(X, gens)
    assert mask.sum() == size
    assert (X[mask].sum(axis=0) == 0).all()                           # still balanced
    assert doe.resolution(doe.defining_relation(gens)) == res


@pytest.mark.parametrize("gens", [HALF, QUARTER])
def test_alias_algebra_matches_the_columns(gens):
    X = doe.full_factorial(5)
    mask = doe.fraction(X, gens)
    rel = doe.defining_relation(gens)
    for w in doe.words(max_order=2):
        assert doe.aliases(w, rel) == _numerical_aliases(X, mask, w), w


def test_quarter_fraction_aliases_d_with_ab_and_the_half_does_not():
    assert "AB" in doe.aliases("D", doe.defining_relation(QUARTER))
    assert doe.aliases("D", doe.defining_relation(HALF)) == ["ABCE"]
    assert doe.defining_relation(QUARTER) == ["ABD", "ACE", "BCDE"]


def test_fraction_estimate_is_the_sum_of_the_full_factorial_aliases(reactor):
    """In a fraction, the estimate of a word is exactly the sum of the full-factorial
    effects of that word and its aliases - the identity behind 'D is really D + AB'."""
    X, y, _ = reactor
    full = doe.effects(X, y)
    for gens in (HALF, QUARTER):
        mask = doe.fraction(X, gens)
        frac = doe.effects(X[mask], y[mask], max_order=1)
        rel = doe.defining_relation(gens)
        for f in doe.FACTORS:
            total = full[f] + sum(full[a] for a in doe.aliases(f, rel))
            assert rel_diff(frac[f], total) < AGREEMENT_RTOL


# ------------------------------------------------------------- center points

def test_curvature_test_matches_its_formula_and_scipy_tails(reactor):
    _, y, yc = reactor
    ct = doe.curvature_test(y, yc)
    se = yc.std(ddof=1) * np.sqrt(1 / len(y) + 1 / len(yc))
    assert rel_diff(ct.estimate, y.mean() - yc.mean()) < AGREEMENT_RTOL
    assert rel_diff(ct.t, ct.estimate / se) < AGREEMENT_RTOL
    assert ct.df == len(yc) - 1
    assert rel_diff(ct.p_value, 2 * stats.t.sf(abs(ct.t), ct.df)) < AGREEMENT_RTOL


def test_center_points_see_the_quadratic_the_corners_cannot(reactor):
    _, y, yc = reactor
    ct = doe.curvature_test(y, yc)
    assert ct.p_value < 0.05
    assert abs(ct.estimate - doe.REACTOR_TRUTH["AA"]) < 4 * ct.se


# ---------------------------------------------------------- Latin hypercubes

@pytest.mark.parametrize("n, d", [(3, 3), (16, 2), (8, 3), (10, 6)])
def test_lhs_uses_every_bin_once(n, d):
    for centered in (False, True):
        P = doe.lhs(n, d, np.random.default_rng(1), centered=centered)
        assert P.shape == (n, d) and doe.is_latin(P)
        assert ((P >= 0) & (P < 1)).all()


def test_lhs_is_reproducible_from_its_seed():
    a = doe.lhs(16, 2, np.random.default_rng(5))
    b = doe.lhs(16, 2, np.random.default_rng(5))
    assert (a == b).all()


def test_a_diagonal_is_latin_but_maximin_beats_it():
    n = 16
    diag = np.column_stack([(np.arange(n) + 0.5) / n] * 2)
    assert doe.is_latin(diag)
    best, best_d = doe.maximin_lhs(n, 2, 200, 3)
    assert doe.is_latin(best)
    assert best_d > doe.min_distance(diag)
    assert rel_diff(best_d, doe.min_distance(best)) < AGREEMENT_RTOL


def test_min_distance_against_brute_force():
    P = np.random.default_rng(2).random((9, 3))
    brute = min(np.linalg.norm(P[i] - P[j]) for i, j in itertools.combinations(range(9), 2))
    assert rel_diff(doe.min_distance(P), brute) < AGREEMENT_RTOL


def test_scipy_latin_hypercube_passes_the_same_check():
    from scipy.stats import qmc
    P = qmc.LatinHypercube(d=4, seed=0).random(12)
    assert doe.is_latin(P)


def test_lhs_estimates_an_additive_mean_with_less_spread():
    est_random, est_lhs = doe.sampling_study(16, 3, 400, 11)
    true_mean = 3 * 2 / np.pi
    assert abs(est_lhs.mean() - true_mean) < 4 * est_lhs.std() / np.sqrt(400)
    assert est_lhs.std() < est_random.std() / 3


# ------------------------------------------------------------------ planning

def test_effect_se_is_two_sigma_over_root_n_and_center_runs_add_nothing():
    two_level = np.tile([-1.0, 1.0], 16)
    assert rel_diff(doe.effect_se(two_level, 1.5), 2 * 1.5 / np.sqrt(32)) < AGREEMENT_RTOL
    with_centers = np.r_[two_level, np.zeros(4)]
    assert doe.effect_se(with_centers, 1.5) == doe.effect_se(two_level, 1.5)


def test_effect_se_matches_least_squares_on_the_full_factorial():
    X = doe.full_factorial(5)
    M = doe.model_matrix(X, doe.words(max_order=2))
    var_coef = np.diag(np.linalg.inv(M.T @ M))[1]
    assert rel_diff(doe.effect_se(X[:, 0], 1.0), 2 * np.sqrt(var_coef)) < AGREEMENT_RTOL


def test_sigma_interval_covers_sigma_at_its_stated_rate():
    rng = np.random.default_rng(4)
    reps, sigma = 2000, 2.0
    hits = sum(iv.lower <= sigma <= iv.upper for iv in
               (doe.sigma_interval(rng.normal(0, sigma, 4)) for _ in range(reps)))
    assert abs(hits / reps - 0.95) < 4 * np.sqrt(0.95 * 0.05 / reps)


def test_sigma_bound_sits_between_s_and_the_two_sided_upper_limit():
    yc = np.array([60.72, 61.72, 59.66, 59.3])
    iv = doe.sigma_interval(yc)
    assert iv.s < doe.sigma_bound(yc, 0.8) < iv.upper
    assert rel_diff(doe.sigma_bound(yc, 0.975), iv.upper) < AGREEMENT_RTOL


def test_runs_needed_gives_the_target_power_under_the_normal_approximation():
    delta, sigma = 2.0, 1.9
    n = doe.runs_needed(delta, sigma)
    se = 2 * sigma / np.sqrt(n)
    lower_tail = stats.norm.cdf(-stats.norm.ppf(0.975) - delta / se)
    assert rel_diff(doe.power(delta, se) - lower_tail, 0.8) < AGREEMENT_RTOL


def test_t_power_approaches_the_normal_and_survives_scipy_nan():
    gap = [abs(doe.power(2.0, 0.7, 10 ** k) - doe.power(2.0, 0.7)) for k in (1, 2, 4, 6)]
    assert gap == sorted(gap, reverse=True) and gap[-1] < gap[0] / 1000   # closes in like 1/df
    assert doe.power(2.0, 0.7, 5) < doe.power(2.0, 0.7, 50)        # fewer error df, less power
    p = doe.power(2.0, 0.172, 708)                                  # lower tail is nan in scipy
    assert np.isfinite(p) and p > 0.999


def test_t_power_matches_a_simulation():
    X = np.vstack([doe.full_factorial(4), np.zeros((4, 4))])
    M = doe.model_matrix(X, ["A", "B", "C", "D"], "ABCD")
    df = len(X) - M.shape[1]
    sigma, delta, reps = 1.0, 1.2, 3000
    rng = np.random.default_rng(9)
    Y = (delta / 2) * X[:, [0]] + rng.normal(0, sigma, (len(X), reps))
    B = np.linalg.solve(M.T @ M, M.T @ Y)
    s2 = ((Y - M @ B) ** 2).sum(axis=0) / df
    t = B[1] / np.sqrt(s2 * np.linalg.inv(M.T @ M)[1, 1])
    sim = (np.abs(t) > stats.t.ppf(0.975, df)).mean()
    exact = doe.power(delta, doe.effect_se(X[:, 0], sigma), df)
    assert abs(sim - exact) < 4 * np.sqrt(exact * (1 - exact) / reps)


def test_one_factor_at_a_time_effects_have_variance_two_sigma_squared():
    X = doe.full_factorial(5)[[0, 1, 2, 4, 8, 16]]
    M = doe.model_matrix(X, list("ABCDE"))
    assert np.linalg.matrix_rank(M) == 6
    assert np.linalg.matrix_rank(doe.model_matrix(X, doe.words(max_order=2))) == 6
    assert np.allclose(4 * np.diag(np.linalg.inv(M.T @ M))[1:], 2.0, rtol=AGREEMENT_RTOL, atol=0)


def test_augment_from_one_factor_at_a_time_reaches_full_rank_without_repeats():
    X = doe.full_factorial(5)
    ofat = [0, 1, 2, 4, 8, 16]
    cand = [i for i in range(32) if i not in ofat]
    terms = doe.words(max_order=2)
    chosen = doe.augment(X[ofat], X[cand], terms, 11)
    assert len(set(chosen)) == 11
    rows = ofat + [cand[i] for i in chosen]
    M = np.column_stack([doe.model_matrix(X[rows], terms), np.r_[-np.ones(6), np.ones(11)]])
    assert np.linalg.matrix_rank(M) == 17                 # 11 runs, each one a new estimable term


def test_d_efficiency_is_one_for_an_orthogonal_design_and_less_otherwise():
    X = doe.full_factorial(5)
    terms = doe.words(max_order=2)
    assert rel_diff(doe.d_efficiency(doe.model_matrix(X, terms)), 1.0) < AGREEMENT_RTOL
    half = doe.fraction(X, HALF)
    assert rel_diff(doe.d_efficiency(doe.model_matrix(X[half], terms)), 1.0) < AGREEMENT_RTOL
    chosen = doe.augment(X[[0, 1, 2, 4, 8, 16]], X, terms, 16, block=False)
    assert doe.d_efficiency(doe.model_matrix(np.vstack([X[[0, 1, 2, 4, 8, 16]], X[chosen]]), terms)) < 1.0


def test_log_det_ridge_does_not_matter_once_full_rank():
    X = doe.full_factorial(5)
    M = doe.model_matrix(X, doe.words(max_order=2))
    exact = np.linalg.slogdet(M.T @ M)[1]
    # log det is concave, so the ridge adds between 0 and AUGMENT_RIDGE * trace((M'M)^-1)
    added = doe.log_det(M) - exact
    assert 0 < added <= doe.AUGMENT_RIDGE * np.trace(np.linalg.inv(M.T @ M))
