"""Single-queue performance measures - M/M/1 and M/M/c in closed form, and an
M/M/1 simulation to check them against - written once for a machine.

The course taught these through R's ``queueing`` package. The formulas are
the same in any language; what the package hid was that each of them is one
line, and that Little's law ties the four measures together. The teaching
notebook in ``notebooks/09_queueing_and_markov/`` writes the lines out and
then simulates the queue with a printed seed. ``simulate_mm1`` here draws
the same numbers in the same order from the same seed, so the notebook's
hand-written recursion and this function must agree exactly, not just
statistically.

Arrival rate lambda and service rate mu are KNOBS - two scalars the story
names - so they are arguments, not a table.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import factorial

import numpy as np


@dataclass
class Measures:
    rho: float          # utilisation per server
    P0: float           # probability the system is empty
    L: float            # mean number in the system
    Lq: float           # mean number waiting
    W: float            # mean time in the system
    Wq: float           # mean time waiting
    label: str = ""


def mm1(lam: float, mu: float) -> Measures:
    """One server, Poisson arrivals, exponential service. Needs lam < mu."""
    if lam >= mu:
        raise ValueError("unstable queue: lambda %.3f >= mu %.3f" % (lam, mu))
    rho = lam / mu
    L = rho / (1.0 - rho)
    Lq = rho * rho / (1.0 - rho)
    return Measures(rho, 1.0 - rho, L, Lq, L / lam, Lq / lam, "M/M/1")


def mmc(lam: float, mu: float, c: int) -> Measures:
    """c identical servers. The Erlang C formula gives P0 and Lq; the rest
    follows from Little's law."""
    a = lam / mu                      # offered load, in servers
    rho = a / c
    if rho >= 1.0:
        raise ValueError("unstable queue: lambda/(c mu) = %.3f" % rho)
    P0 = 1.0 / (sum(a ** k / factorial(k) for k in range(c)) + a ** c / (factorial(c) * (1.0 - rho)))
    Lq = P0 * a ** c * rho / (factorial(c) * (1.0 - rho) ** 2)
    Wq = Lq / lam
    W = Wq + 1.0 / mu
    return Measures(rho, P0, lam * W, Lq, W, Wq, "M/M/%d" % c)


def p_n(lam: float, mu: float, n: int) -> float:
    """M/M/1 probability of exactly n in the system."""
    rho = lam / mu
    return (1.0 - rho) * rho ** n


@dataclass
class Simulation:
    seed: int
    customers: int
    Wq: float           # mean wait in queue
    W: float            # mean time in system
    L: float            # mean number in system, by Little's law from the observed arrival rate
    lam_observed: float


def simulate_mm1(lam: float, mu: float, customers: int, seed: int) -> Simulation:
    """Lindley's recursion. Draw every interarrival time first, then every
    service time, from one generator seeded once - that draw order is the
    contract the notebook's hand-built loop must follow to agree exactly."""
    rng = np.random.default_rng(seed)
    interarrival = rng.exponential(1.0 / lam, customers)
    service = rng.exponential(1.0 / mu, customers)
    wait = np.zeros(customers)
    for k in range(1, customers):
        wait[k] = max(0.0, wait[k - 1] + service[k - 1] - interarrival[k])
    Wq = float(wait.mean())
    W = float((wait + service).mean())
    lam_obs = customers / float(interarrival.sum())
    return Simulation(seed, customers, Wq, W, lam_obs * W, lam_obs)
