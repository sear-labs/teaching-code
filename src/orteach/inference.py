"""Hypothesis tests and least-squares regression, by their formulas - written
once for a machine.

The course taught these through R's ``t.test``, ``var.test``, ``chisq.test``
and ``lm``, and the shipped notebooks are R-kernel notebooks. This module
writes each test out as a statistic, a reference distribution and a p-value,
in the conventions R reports - statistic, df, p-value, interval - so that a
line of ``t.test`` output can be reproduced term by term. Only the tail areas come from
``scipy.stats``; the statistics are arithmetic.

TABLES in ``data/raw/``:

    exam_scores.csv     two synthetic exam-score vectors, generated here from a
                        printed seed. The course's notebook typed two real
                        class score vectors; those are not published.
    mtcars.csv          R's Motor Trend data (32 cars), public domain
    cars.csv            R's stopping-distance data (50 observations), public

``ols`` fits by the normal equations and reports what R's ``summary(lm)``
reports, so the mtcars regressions can be pinned to R's printed coefficients.
"""
from __future__ import annotations

import csv
import math
import os
from dataclasses import dataclass, field

import numpy as np
from scipy import stats

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data", "raw")

SCORES_CSV = os.path.join(DATA_DIR, "exam_scores.csv")
SCORES_SEED = 20260905
SCORES_N = 22
SCORES_SHAPE = {"exam1": (75.0, 22.0, 100.0), "exam2": (70.0, 27.0, 105.0)}   # mean, sd, cap


# ------------------------------------------------------------------- tables

def generate_scores(seed: int = SCORES_SEED, n: int = SCORES_N) -> dict:
    """Two synthetic score vectors with the shape of the course's real ones:
    Normal draws, rounded to a half point, clipped to [0, cap]."""
    rng = np.random.default_rng(seed)
    out = {}
    for name, (mu, sd, cap) in SCORES_SHAPE.items():
        raw = rng.normal(mu, sd, n)
        out[name] = [float(min(max(round(v * 2) / 2, 0.0), cap)) for v in raw]
    return out


def write_scores(path: str = SCORES_CSV) -> None:
    scores = generate_scores()
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["student", "exam1", "exam2"])
        for i in range(SCORES_N):
            w.writerow([i + 1, scores["exam1"][i], scores["exam2"][i]])


def load_scores(path: str = SCORES_CSV) -> dict:
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {"exam1": [float(r["exam1"]) for r in rows], "exam2": [float(r["exam2"]) for r in rows]}


def load_table(filename: str) -> dict:
    """A CSV as {column: list}, numeric where every entry parses."""
    with open(os.path.join(DATA_DIR, filename), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = {}
    for col in rows[0].keys():
        vals = [r[col] for r in rows]
        try:
            out[col] = [float(v) for v in vals]
        except ValueError:
            out[col] = vals
    return out


# ------------------------------------------------------------- mean tests

@dataclass
class TestResult:
    statistic: float
    df: float
    p_value: float
    conf_int: tuple
    estimate: dict
    alternative: str
    method: str


def _tail(stat, df, alternative, dist):
    if alternative == "two-sided":
        return 2.0 * dist.sf(abs(stat), df)
    if alternative == "less":
        return dist.cdf(stat, df)
    if alternative == "greater":
        return dist.sf(stat, df)
    raise ValueError("alternative must be two-sided, less or greater")


def _ci(center, se, df, alternative, conf):
    if alternative == "two-sided":
        h = stats.t.ppf(0.5 + conf / 2.0, df) * se
        return (center - h, center + h)
    h = stats.t.ppf(conf, df) * se
    return (-math.inf, center + h) if alternative == "less" else (center - h, math.inf)


def t_one_sample(x, mu0: float, alternative: str = "two-sided", conf: float = 0.95) -> TestResult:
    """t = (xbar - mu0) / (s / sqrt n), df = n - 1."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    xbar, s = x.mean(), x.std(ddof=1)
    se = s / math.sqrt(n)
    t = (xbar - mu0) / se
    return TestResult(t, n - 1, _tail(t, n - 1, alternative, stats.t), _ci(xbar, se, n - 1, alternative, conf),
                      {"mean": xbar, "sd": s}, alternative, "one-sample t")


def t_two_sample(x, y, equal_var: bool = True, alternative: str = "two-sided", conf: float = 0.95) -> TestResult:
    """Pooled (equal variances, df = n + m - 2) or Welch (unequal, Welch-
    Satterthwaite df) test of the difference in means."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    n, m = len(x), len(y)
    vx, vy = x.var(ddof=1), y.var(ddof=1)
    if equal_var:
        sp2 = ((n - 1) * vx + (m - 1) * vy) / (n + m - 2)
        se = math.sqrt(sp2 * (1.0 / n + 1.0 / m))
        df = n + m - 2
        method = "two-sample t, pooled variance"
    else:
        se = math.sqrt(vx / n + vy / m)
        df = (vx / n + vy / m) ** 2 / ((vx / n) ** 2 / (n - 1) + (vy / m) ** 2 / (m - 1))
        method = "Welch two-sample t"
    diff = x.mean() - y.mean()
    t = diff / se
    return TestResult(t, df, _tail(t, df, alternative, stats.t), _ci(diff, se, df, alternative, conf),
                      {"mean_x": x.mean(), "mean_y": y.mean()}, alternative, method)


# --------------------------------------------------------- variance tests

def chi2_variance(x, sigma0_sq: float, conf: float = 0.95) -> TestResult:
    """(n-1) s^2 / sigma0^2 against chi-squared with n-1 df; two-sided p is
    twice the smaller tail, as R's EnvStats::varTest reports it."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    s2 = x.var(ddof=1)
    stat = (n - 1) * s2 / sigma0_sq
    lower, upper = stats.chi2.cdf(stat, n - 1), stats.chi2.sf(stat, n - 1)
    p = min(1.0, 2.0 * min(lower, upper))
    a = (1.0 - conf) / 2.0
    ci = ((n - 1) * s2 / stats.chi2.ppf(1.0 - a, n - 1), (n - 1) * s2 / stats.chi2.ppf(a, n - 1))
    return TestResult(stat, n - 1, p, ci, {"variance": s2}, "two-sided", "chi-squared test on one variance")


def f_variance_ratio(x, y, conf: float = 0.95) -> TestResult:
    """s_x^2 / s_y^2 against F(n-1, m-1); two-sided p twice the smaller tail."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    n, m = len(x), len(y)
    ratio = x.var(ddof=1) / y.var(ddof=1)
    lower, upper = stats.f.cdf(ratio, n - 1, m - 1), stats.f.sf(ratio, n - 1, m - 1)
    p = min(1.0, 2.0 * min(lower, upper))
    a = (1.0 - conf) / 2.0
    ci = (ratio / stats.f.ppf(1.0 - a, n - 1, m - 1), ratio / stats.f.ppf(a, n - 1, m - 1))
    return TestResult(ratio, (n - 1, m - 1), p, ci, {"ratio": ratio}, "two-sided", "F test of two variances")


# ------------------------------------------------------ chi-squared tests

def chi2_goodness_of_fit(observed, expected) -> TestResult:
    """sum (O - E)^2 / E against chi-squared with (bins - 1) df."""
    o, e = np.asarray(observed, dtype=float), np.asarray(expected, dtype=float)
    if abs(o.sum() - e.sum()) > 1e-6 * max(o.sum(), 1.0):
        raise ValueError("observed and expected totals differ: %.3f vs %.3f" % (o.sum(), e.sum()))
    stat = float(((o - e) ** 2 / e).sum())
    df = len(o) - 1
    return TestResult(stat, df, float(stats.chi2.sf(stat, df)), (math.nan, math.nan), {}, "greater", "chi-squared goodness of fit")


def chi2_independence(table) -> TestResult:
    """Row and column totals give the expected counts under independence;
    df = (rows - 1)(cols - 1)."""
    t = np.asarray(table, dtype=float)
    expected = np.outer(t.sum(axis=1), t.sum(axis=0)) / t.sum()
    stat = float(((t - expected) ** 2 / expected).sum())
    df = (t.shape[0] - 1) * (t.shape[1] - 1)
    return TestResult(stat, df, float(stats.chi2.sf(stat, df)), (math.nan, math.nan),
                      {"expected": expected}, "greater", "chi-squared test of independence")


# --------------------------------------------------------------- regression

@dataclass
class OLSFit:
    names: list
    coef: np.ndarray
    se: np.ndarray
    t: np.ndarray
    p: np.ndarray
    r2: float
    adj_r2: float
    f_stat: float
    f_p: float
    resid_se: float
    df_resid: int
    fitted: np.ndarray
    residuals: np.ndarray
    ss_model: float = field(default=math.nan)
    ss_resid: float = field(default=math.nan)

    def predict(self, X):
        X = np.column_stack([np.ones(len(np.atleast_2d(X)[:, 0]) if np.ndim(X) > 1 else len(X)), np.atleast_2d(X).T if np.ndim(X) == 1 else X])
        return X @ self.coef


def ols(X, y, names=None) -> OLSFit:
    """Least squares with an intercept, by the normal equations. ``X`` is the
    n x p matrix of regressors WITHOUT an intercept column (a 1-D array is one
    regressor); ``names`` labels those p columns."""
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X[:, None]
    y = np.asarray(y, dtype=float)
    n, p = X.shape
    names = ["(Intercept)"] + list(names if names is not None else ["x%d" % (j + 1) for j in range(p)])
    A = np.column_stack([np.ones(n), X])
    coef = np.linalg.solve(A.T @ A, A.T @ y)
    fitted = A @ coef
    resid = y - fitted
    df_resid = n - p - 1
    ss_resid = float(resid @ resid)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    sigma2 = ss_resid / df_resid
    cov = sigma2 * np.linalg.inv(A.T @ A)
    se = np.sqrt(np.diag(cov))
    t = coef / se
    pvals = 2.0 * stats.t.sf(np.abs(t), df_resid)
    r2 = 1.0 - ss_resid / ss_tot
    adj_r2 = 1.0 - (1.0 - r2) * (n - 1) / df_resid
    f_stat = ((ss_tot - ss_resid) / p) / sigma2
    f_p = float(stats.f.sf(f_stat, p, df_resid))
    return OLSFit(names, coef, se, t, pvals, r2, adj_r2, f_stat, f_p, math.sqrt(sigma2), df_resid,
                  fitted, resid, ss_tot - ss_resid, ss_resid)


def split_indices(n: int, train_frac: float, seed: int):
    """A reproducible train/test split of range(n): a seeded permutation, the
    first ``round(train_frac * n)`` rows to train."""
    perm = np.random.default_rng(seed).permutation(n)
    k = int(round(train_frac * n))
    return np.sort(perm[:k]), np.sort(perm[k:])
