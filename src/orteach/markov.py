"""Discrete-time Markov chains - transition matrices, n-step distributions,
steady states and absorption - written once for a machine.

A chain is a TABLE (Part 4): a square matrix whose rows sum to one, read from
``data/raw/`` with the state names in the first column and the header. Two
ship with the course: a three-zone taxi chain that has a steady state, and a
four-state chain with an absorbing state.

The linear algebra is numpy; nothing here needs a solver. The teaching
notebook in ``notebooks/09_queueing_and_markov/`` does the same arithmetic by
hand - matrix powers, the steady-state equations solved as a linear system,
the fundamental matrix - and checks itself against this module.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass

import numpy as np

from . import tolerance

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data", "raw")

ROW_SUM_ATOL = tolerance.LINALG_ATOL


@dataclass
class Chain:
    states: list
    P: np.ndarray           # P[i, j] = probability of moving from state i to state j
    name: str = "chain"

    def __post_init__(self):
        self.P = np.asarray(self.P, dtype=float)
        n = len(self.states)
        if self.P.shape != (n, n):
            raise ValueError("P is %s but there are %d states" % (self.P.shape, n))
        bad = np.abs(self.P.sum(axis=1) - 1.0) > ROW_SUM_ATOL
        if bad.any():
            raise ValueError("rows do not sum to one: %s" % [self.states[i] for i in np.where(bad)[0]])
        if (self.P < 0).any():
            raise ValueError("negative transition probability")

    def index(self, state):
        return self.states.index(state)


def load_chain(filename: str) -> Chain:
    with open(os.path.join(DATA_DIR, filename), encoding="utf-8") as f:
        recs = list(csv.DictReader(f))
    states = [k for k in recs[0].keys() if k != "state"]
    P = np.array([[float(r[s]) for s in states] for r in recs])
    return Chain(states, P, name=filename.replace(".csv", ""))


def n_step(chain: Chain, n: int) -> np.ndarray:
    """P^n: the n-step transition matrix."""
    return np.linalg.matrix_power(chain.P, n)


def distribution_after(chain: Chain, start, n: int) -> np.ndarray:
    """Where the chain is after n steps, starting from a state name or a
    probability vector over states."""
    if isinstance(start, str):
        pi0 = np.zeros(len(chain.states)); pi0[chain.index(start)] = 1.0
    else:
        pi0 = np.asarray(start, dtype=float)
    return pi0 @ n_step(chain, n)


def steady_state(chain: Chain) -> np.ndarray:
    """The stationary distribution pi with pi P = pi and sum pi = 1, found by
    solving that linear system directly: replace one of the (dependent)
    balance equations with the normalisation."""
    n = len(chain.states)
    A = chain.P.T - np.eye(n)
    A[-1, :] = 1.0
    b = np.zeros(n); b[-1] = 1.0
    return np.linalg.solve(A, b)


def absorbing_states(chain: Chain) -> list:
    return [s for i, s in enumerate(chain.states) if chain.P[i, i] == 1.0]


@dataclass
class Absorption:
    transient: list
    absorbing: list
    N: np.ndarray               # fundamental matrix (I - Q)^-1, transient x transient
    expected_steps: dict        # transient state -> expected steps until absorbed
    probability: dict           # (transient, absorbing) -> probability of ending there


def absorption(chain: Chain) -> Absorption:
    """Fundamental-matrix analysis of an absorbing chain. With Q the
    transient-to-transient block and R the transient-to-absorbing block,
    N = (I - Q)^-1 counts expected visits, N 1 is expected time to absorption
    and N R is the absorption probability."""
    absorbing = absorbing_states(chain)
    if not absorbing:
        raise ValueError("chain has no absorbing state")
    transient = [s for s in chain.states if s not in absorbing]
    ti = [chain.index(s) for s in transient]
    ai = [chain.index(s) for s in absorbing]
    Q = chain.P[np.ix_(ti, ti)]
    R = chain.P[np.ix_(ti, ai)]
    N = np.linalg.inv(np.eye(len(ti)) - Q)
    steps = N.sum(axis=1)
    B = N @ R
    return Absorption(transient, absorbing, N,
                      {s: float(steps[k]) for k, s in enumerate(transient)},
                      {(s, a): float(B[k, j]) for k, s in enumerate(transient) for j, a in enumerate(absorbing)})
