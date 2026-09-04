"""Monte Carlo estimators, written once for a machine.

The teaching notebook in ``notebooks/08_monte_carlo_and_simulation/`` builds each
of these by hand. Part 4 duplication, checked by the agreement assertion at the
end of that notebook.

All three estimators are the same idea wearing different clothes: **an expectation
is an average, so sample and average.** What differs is only what is being
averaged — an indicator of "inside the circle", an indicator of "in the interval",
an indicator of "the game was lost".

Every function takes an explicit ``seed``. Standard Part 10: seeds are set *and
printed* wherever anything is stochastic, otherwise a number in the prose cannot
be reproduced and the notebook's own claims decay.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class MCResult:
    """An estimate, with the honesty of a standard error attached."""

    estimate: float
    n: int
    seed: int
    samples: np.ndarray = field(default=None, repr=False)
    label: str = ""

    @property
    def std_error(self) -> float:
        """Standard error of a proportion: sqrt(p(1-p)/n).

        This is the number that says how much to trust the estimate, and it is
        why Monte Carlo converges as 1/sqrt(n) rather than 1/n — a hundredfold
        more samples buys one more decimal digit.
        """
        p = self.estimate
        return float(np.sqrt(max(p * (1 - p), 0.0) / self.n))

    def ci95(self) -> tuple[float, float]:
        half = 1.96 * self.std_error
        return (self.estimate - half, self.estimate + half)


def estimate_pi(n=1_000_000, seed=0) -> MCResult:
    """Pi, by throwing darts at a square and counting the ones inside the circle.

    A quarter of the unit square's area argument in disguise: the circle of
    radius 1 inscribed in the square [-1,1]^2 occupies pi/4 of it, so the
    fraction landing inside, times 4, estimates pi.
    """
    rng = np.random.default_rng(seed)
    xs = rng.uniform(-1, 1, n)
    ys = rng.uniform(-1, 1, n)
    inside = xs * xs + ys * ys <= 1.0
    # The estimate is a proportion times 4; std_error below is for the proportion.
    r = MCResult(float(inside.mean()), n, seed, inside, "pi/4")
    return r


def estimate_normal_interval(lo, hi, mu=1.0, sigma=10.0, n=1_000_000, seed=0) -> MCResult:
    """P(lo <= X <= hi) for X ~ Normal(mu, sigma), by sampling.

    This is Monte Carlo *integration*: the probability is the integral of the
    density over [lo, hi], and sampling estimates it without ever writing the
    integral down.
    """
    rng = np.random.default_rng(seed)
    sims = rng.normal(loc=mu, scale=sigma, size=n)
    inside = (sims >= lo) & (sims <= hi)
    return MCResult(float(inside.mean()), n, seed, sims, "P(%g<=X<=%g)" % (lo, hi))


# The spinner: four equally likely wedges, spun ten times, and you lose if the
# total is negative. Written out rather than loaded because four values named in
# the narration are KNOBS, not a table (Part 4).
SPINNER_WEDGES = (1, 1, -1, 2)
SPINNER_SPINS = 10


def simulate_spinner(n=100_000, wedges=SPINNER_WEDGES, spins=SPINNER_SPINS, seed=0) -> MCResult:
    """P(total < 0) after `spins` spins, by playing the game `n` times."""
    rng = np.random.default_rng(seed)
    draws = rng.choice(wedges, size=(n, spins), replace=True)
    lost = draws.sum(axis=1) < 0
    return MCResult(float(lost.mean()), n, seed, lost, "P(total<0)")


def exact_spinner_probability(wedges=SPINNER_WEDGES, spins=SPINNER_SPINS) -> float:
    """The same probability, computed exactly by convolving the distribution.

    This exists so the notebook has something TRUE to converge to. The original
    plot drew a red line labelled "True Probability" that was in fact the final
    Monte Carlo estimate — so it showed the estimate converging to itself, which
    is guaranteed and means nothing.

    Exact because the state space is small: ten spins of four outcomes is
    4^10 ≈ 10^6 paths, but the distribution over *sums* has only a few dozen
    values, so convolution is instant.
    """
    from collections import defaultdict

    p_each = 1.0 / len(wedges)
    dist = {0: 1.0}
    for _ in range(spins):
        nxt = defaultdict(float)
        for total, p in dist.items():
            for w in wedges:
                nxt[total + w] += p * p_each
        dist = dict(nxt)
    return sum(p for total, p in dist.items() if total < 0)
