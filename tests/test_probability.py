"""The formulas against scipy, and against what R printed.

Every distribution formula in orteach.distributions is checked against
scipy.stats at the parameters the course notebook used, and against the
three-decimal values R's p-functions printed there. Every test in
orteach.inference is checked against scipy.stats where scipy has the test
and against its own definition where it does not; the mtcars regressions are
pinned to the coefficients R's summary(lm) printed, which is a genuine
cross-language check on public data.
"""
import math
import os
import sys

import numpy as np
import pytest
from scipy import stats

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

from orteach import distributions as d, inference as inf  # noqa: E402
from orteach.tolerance import AGREEMENT_RTOL, FEASIBILITY_ATOL, rel_diff  # noqa: E402

R_ROUNDED = 5e-4     # R printed three decimals


# ---------------------------------------------------------------- formulas

def test_binomial_matches_scipy():
    for k in (0, 10, 25, 40, 100):
        assert rel_diff(d.binom_pmf(k, 100, 0.25), stats.binom.pmf(k, 100, 0.25)) < AGREEMENT_RTOL
        assert rel_diff(d.binom_cdf(k, 100, 0.25), stats.binom.cdf(k, 100, 0.25)) < AGREEMENT_RTOL


def test_negative_binomial_matches_scipy_and_r():
    """R's pnbinom(1600, 500, 0.25) printed 0.901; scipy's nbinom uses the
    same failures-before-r-successes convention."""
    assert rel_diff(d.nbinom_pmf(1500, 500, 0.25), stats.nbinom.pmf(1500, 500, 0.25)) < AGREEMENT_RTOL
    assert rel_diff(d.nbinom_cdf(1600, 500, 0.25), stats.nbinom.cdf(1600, 500, 0.25)) < 1e-8
    assert abs(d.nbinom_cdf(1600, 500, 0.25) - 0.901) < R_ROUNDED


def test_geometric_matches_r_convention():
    """R's dgeom counts failures before the first success; scipy's geom
    counts trials, so scipy's k is R's x + 1. R printed pgeom(40, 0.05) =
    0.878."""
    assert rel_diff(d.geom_pmf(25, 0.05), stats.geom.pmf(26, 0.05)) < AGREEMENT_RTOL
    assert rel_diff(d.geom_cdf(40, 0.05), stats.geom.cdf(41, 0.05)) < AGREEMENT_RTOL
    assert abs(d.geom_cdf(40, 0.05) - 0.878) < R_ROUNDED


def test_poisson_matches_scipy_and_r():
    assert rel_diff(d.poisson_pmf(20, 20.0), stats.poisson.pmf(20, 20.0)) < AGREEMENT_RTOL
    assert rel_diff(d.poisson_cdf(25, 20.0), stats.poisson.cdf(25, 20.0)) < 1e-8
    assert abs(d.poisson_cdf(25, 20.0) - 0.888) < R_ROUNDED


def test_continuous_formulas_match_scipy_and_r():
    assert rel_diff(d.exponential_cdf(0.2, 20.0), stats.expon.cdf(0.2, scale=1 / 20.0)) < AGREEMENT_RTOL
    assert abs(d.exponential_cdf(0.2, 20.0) - 0.982) < R_ROUNDED
    assert rel_diff(d.exponential_quantile(0.95, 20.0), stats.expon.ppf(0.95, scale=1 / 20.0)) < AGREEMENT_RTOL
    assert rel_diff(d.erlang_cdf(0.2, 3, 20.0), stats.gamma.cdf(0.2, 3, scale=1 / 20.0)) < 1e-8
    assert abs(d.erlang_cdf(0.2, 3, 20.0) - 0.762) < R_ROUNDED
    assert rel_diff(d.normal_cdf(40, 50, 10), stats.norm.cdf(40, 50, 10)) < 1e-8
    assert abs(d.normal_cdf(40, 50, 10) - 0.159) < R_ROUNDED
    assert rel_diff(d.lognormal_cdf(3.0, 0.8, 0.3), stats.lognorm.cdf(3.0, 0.3, scale=math.exp(0.8))) < 1e-8
    assert abs(d.lognormal_cdf(3.0, 0.8, 0.3) - 0.84) < 5e-3       # R printed two decimals for this one
    for x in (-1.0, 0.0, 2.5):
        assert rel_diff(d.normal_pdf(x, 50, 10), stats.norm.pdf(x, 50, 10)) < 1e-8


def test_the_r_values_the_formulas_do_not_cover():
    """chi-squared, F and t have no elementary cdf; the notebook uses scipy
    for them. R printed pchisq(25, 20) = 0.799 and pf(1.5, 20, 30) = 0.846."""
    assert abs(stats.chi2.cdf(25, 20) - 0.799) < R_ROUNDED
    assert abs(stats.f.cdf(1.5, 20, 30) - 0.846) < R_ROUNDED


def test_sample_means_shrink_like_one_over_root_n():
    rng = np.random.default_rng(1)
    pop = rng.exponential(4.0, 10_000)
    sds = {n: d.sample_means(pop, n, 2000, np.random.default_rng(2)).std(ddof=1) for n in (30, 100, 1000)}
    for a, b in ((30, 100), (100, 1000)):
        ratio = sds[a] / sds[b]
        assert 0.8 * math.sqrt(b / a) < ratio < 1.25 * math.sqrt(b / a), (a, b, ratio)


# ------------------------------------------------------------------ tables

@pytest.fixture(scope="module")
def scores():
    return inf.load_scores()


def test_the_score_table_regenerates_exactly(scores):
    gen = inf.generate_scores()
    assert gen["exam1"] == scores["exam1"] and gen["exam2"] == scores["exam2"]
    assert len(scores["exam1"]) == inf.SCORES_N


def test_mtcars_and_cars_have_their_published_shapes():
    mt = inf.load_table("mtcars.csv")
    assert len(mt["mpg"]) == 32 and set(mt) >= {"mpg", "disp", "hp", "wt"}
    cars = inf.load_table("cars.csv")
    assert len(cars["speed"]) == 50


# ---------------------------------------------------------------- t tests

@pytest.mark.parametrize("alt,scipy_alt", [("two-sided", "two-sided"), ("less", "less"), ("greater", "greater")])
def test_one_sample_t_matches_scipy(scores, alt, scipy_alt):
    for mu0 in (60.0, 70.0, 80.0):
        mine = inf.t_one_sample(scores["exam2"], mu0, alt)
        ref = stats.ttest_1samp(scores["exam2"], mu0, alternative=scipy_alt)
        assert rel_diff(mine.statistic, ref.statistic) < AGREEMENT_RTOL
        assert rel_diff(mine.p_value, ref.pvalue) < 1e-8
        lo, hi = ref.confidence_interval(0.95)
        for a, b in ((mine.conf_int[0], lo), (mine.conf_int[1], hi)):
            if math.isfinite(b):
                assert rel_diff(a, b) < 1e-8


@pytest.mark.parametrize("equal_var", [True, False])
def test_two_sample_t_matches_scipy(scores, equal_var):
    mine = inf.t_two_sample(scores["exam1"], scores["exam2"], equal_var=equal_var)
    ref = stats.ttest_ind(scores["exam1"], scores["exam2"], equal_var=equal_var)
    assert rel_diff(mine.statistic, ref.statistic) < AGREEMENT_RTOL
    assert rel_diff(mine.p_value, ref.pvalue) < 1e-8
    assert rel_diff(mine.df, ref.df) < 1e-8


def test_variance_tests_agree_with_their_definitions(scores):
    x, y = np.array(scores["exam1"]), np.array(scores["exam2"])
    v = inf.chi2_variance(y, 25.0 ** 2)
    assert rel_diff(v.statistic, (len(y) - 1) * y.var(ddof=1) / 625.0) < AGREEMENT_RTOL
    assert v.conf_int[0] < y.var(ddof=1) < v.conf_int[1]
    f = inf.f_variance_ratio(x, y)
    assert rel_diff(f.statistic, x.var(ddof=1) / y.var(ddof=1)) < AGREEMENT_RTOL
    assert 0.0 < f.p_value <= 1.0


def test_chi_squared_tests_match_scipy():
    gof = inf.chi2_goodness_of_fit([3, 4, 8, 7], [5.5, 5.5, 5.5, 5.5])
    ref = stats.chisquare([3, 4, 8, 7], [5.5, 5.5, 5.5, 5.5])
    assert rel_diff(gof.statistic, ref.statistic) < AGREEMENT_RTOL and rel_diff(gof.p_value, ref.pvalue) < 1e-8
    table = [[120, 90, 40], [110, 95, 45]]
    ind = inf.chi2_independence(table)
    ref = stats.chi2_contingency(table, correction=False)
    assert rel_diff(ind.statistic, ref[0]) < AGREEMENT_RTOL and rel_diff(ind.p_value, ref[1]) < 1e-8
    assert np.allclose(ind.estimate["expected"], ref[3])


def test_gof_refuses_mismatched_totals():
    with pytest.raises(ValueError):
        inf.chi2_goodness_of_fit([3, 4, 8, 7], [5, 5, 5, 5])


# -------------------------------------------------------------- regression

def test_simple_regression_matches_r_on_mtcars():
    """R printed: (Intercept) 29.599855 (se 1.229720), disp -0.041215 (se
    0.004712), residual SE 3.251 on 30 df, R^2 0.7183, F 76.51."""
    mt = inf.load_table("mtcars.csv")
    fit = inf.ols(mt["disp"], mt["mpg"], ["disp"])
    assert abs(fit.coef[0] - 29.599855) < 1e-6 and abs(fit.coef[1] + 0.041215) < 1e-6
    assert abs(fit.se[0] - 1.229720) < 1e-6 and abs(fit.se[1] - 0.004712) < 1e-6
    assert abs(fit.resid_se - 3.251) < 5e-4 and fit.df_resid == 30
    assert abs(fit.r2 - 0.7183) < 5e-5 and abs(fit.f_stat - 76.51) < 5e-3


def test_multiple_regression_matches_r_on_mtcars():
    """R printed: 37.105505, disp -0.000937, hp -0.031157, wt -3.800891;
    residual SE 2.639 on 28 df, R^2 0.8268, adjusted 0.8083, F 44.57."""
    mt = inf.load_table("mtcars.csv")
    fit = inf.ols(np.column_stack([mt["disp"], mt["hp"], mt["wt"]]), mt["mpg"], ["disp", "hp", "wt"])
    for got, want in zip(fit.coef, (37.105505, -0.000937, -0.031157, -3.800891)):
        assert abs(got - want) < 1e-6
    assert abs(fit.resid_se - 2.639) < 5e-4 and fit.df_resid == 28
    assert abs(fit.r2 - 0.8268) < 5e-5 and abs(fit.adj_r2 - 0.8083) < 5e-5 and abs(fit.f_stat - 44.57) < 5e-3


def test_ols_matches_numpy_lstsq_and_statsmodels():
    mt = inf.load_table("mtcars.csv")
    X = np.column_stack([mt["disp"], mt["hp"], mt["wt"]])
    fit = inf.ols(X, mt["mpg"])
    A = np.column_stack([np.ones(32), X])
    beta, *_ = np.linalg.lstsq(A, np.array(mt["mpg"]), rcond=None)
    assert np.allclose(fit.coef, beta, rtol=AGREEMENT_RTOL, atol=1e-12)
    sm = pytest.importorskip("statsmodels.api")
    res = sm.OLS(np.array(mt["mpg"]), A).fit()
    assert np.allclose(fit.se, res.bse, rtol=1e-9) and abs(fit.f_p - res.f_pvalue) < 1e-12


def test_split_is_reproducible_and_disjoint():
    a = inf.split_indices(50, 0.8, 100)
    b = inf.split_indices(50, 0.8, 100)
    assert list(a[0]) == list(b[0]) and len(a[0]) == 40 and len(a[1]) == 10
    assert not set(a[0]) & set(a[1]) and set(a[0]) | set(a[1]) == set(range(50))
