"""The probability distributions IE 3301 teaches, as the textbook formulas -
written once for a machine.

The course taught these through R's d/p/q functions, which hide the formula
behind a name. Here each formula is written out, in the convention the R
functions use (a negative binomial counts failures before the r-th success;
a geometric counts failures before the first), so a student can read what
``pnbinom`` was computing. ``scipy.stats`` is the independent reference the
tests compare against; the teaching notebook in
``notebooks/14_probability_and_stats/`` derives the same formulas by hand and
checks itself against this module.

The formulas are written in logs where the direct form underflows - a
negative binomial with r = 500 has a p^r of 1e-301 - and the notebook shows
why that is necessary.
"""
from __future__ import annotations

import math

import numpy as np


# ------------------------------------------------------------------ discrete

def binom_pmf(k: int, n: int, p: float) -> float:
    """C(n, k) p^k (1-p)^(n-k)."""
    return math.comb(n, k) * p ** k * (1.0 - p) ** (n - k)


def binom_cdf(k: int, n: int, p: float) -> float:
    return sum(binom_pmf(i, n, p) for i in range(0, k + 1))


def nbinom_pmf(x: int, r: int, p: float) -> float:
    """P(X = x) for X = failures before the r-th success, success probability p.
    C(x + r - 1, x) p^r (1-p)^x, evaluated in logs."""
    lg = math.lgamma(x + r) - math.lgamma(x + 1) - math.lgamma(r)
    return math.exp(lg + r * math.log(p) + x * math.log1p(-p))


def nbinom_cdf(x: int, r: int, p: float) -> float:
    return sum(nbinom_pmf(i, r, p) for i in range(0, x + 1))


def geom_pmf(x: int, p: float) -> float:
    """P(X = x) for X = failures before the first success: p (1-p)^x."""
    return p * (1.0 - p) ** x


def geom_cdf(x: int, p: float) -> float:
    """1 - (1-p)^(x+1): the chance the first success arrives within x failures."""
    return 1.0 - (1.0 - p) ** (x + 1)


def poisson_pmf(k: int, lam: float) -> float:
    """e^-lam lam^k / k!, in logs."""
    return math.exp(-lam + k * math.log(lam) - math.lgamma(k + 1))


def poisson_cdf(k: int, lam: float) -> float:
    return sum(poisson_pmf(i, lam) for i in range(0, k + 1))


# ---------------------------------------------------------------- continuous

def exponential_cdf(x: float, rate: float) -> float:
    return 1.0 - math.exp(-rate * x)


def exponential_quantile(q: float, rate: float) -> float:
    return -math.log1p(-q) / rate


def erlang_cdf(x: float, k: int, rate: float) -> float:
    """Gamma with integer shape k: 1 - sum_{i<k} e^{-rate x} (rate x)^i / i!,
    the probability that the k-th arrival of a Poisson process at ``rate`` has
    happened by time x."""
    lam_x = rate * x
    return 1.0 - sum(math.exp(-lam_x + i * math.log(lam_x) - math.lgamma(i + 1)) for i in range(k))


def normal_cdf(x: float, mu: float = 0.0, sigma: float = 1.0) -> float:
    return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2.0))))


def normal_pdf(x: float, mu: float = 0.0, sigma: float = 1.0) -> float:
    z = (x - mu) / sigma
    return math.exp(-0.5 * z * z) / (sigma * math.sqrt(2.0 * math.pi))


def lognormal_cdf(x: float, meanlog: float, sdlog: float) -> float:
    return normal_cdf(math.log(x), meanlog, sdlog)


# ------------------------------------------------------------------- sampling

def sample_means(population: np.ndarray, size: int, k: int, rng: np.random.Generator) -> np.ndarray:
    """k means of samples of ``size`` drawn with replacement from ``population``,
    in one call to the generator so the draw order is fixed by the seed."""
    draws = rng.choice(population, size=(k, size), replace=True)
    return draws.mean(axis=1)
