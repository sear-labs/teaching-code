"""The simplex method on a tableau, and a barrier method through the interior, written once.

The teaching notebooks in ``notebooks/02_simplex_and_bases/`` build both by hand on IE 3315's
tableau example (``data/raw/lp_simplex_40_50.csv``: max 40x1 + 50x2, x1 + 2x2 <= 40,
4x1 + 3x2 <= 120). This module is what their agreement assertions compare against.

Only a ``max`` LP with ``<=`` rows and non-negative right-hand sides is taken, which is the case
the course's tableau starts from: the slacks are then a feasible starting basis. Anything else
is refused rather than half-handled.

    standard_form     [A | I] x = b with one slack per row, and the objective padded with zeros
    basic_solutions   every choice of m basic columns: the corners, feasible or not
    tableau_path      the corners the simplex method visits, Dantzig's rule, lowest index on ties
    barrier_path      the central path: Newton centering on -t c.x - sum log x, t multiplied by MU
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np

from . import tolerance
from .duality import LP


@dataclass
class StandardForm:
    names: list             # original variables, then one slack per row ("s_<row>")
    A: np.ndarray           # m x (n + m)
    b: np.ndarray
    c: np.ndarray           # objective over all n + m columns (zeros on the slacks)
    n_original: int


def standard_form(lp: LP) -> StandardForm:
    if lp.objective != "max" or any(lp.sense[r] != "<=" for r in lp.rows) or any(lp.b[r] < 0 for r in lp.rows):
        raise ValueError("simplex.standard_form takes a max LP with <= rows and b >= 0 only, "
                         "so the slacks are a feasible first basis")
    A = np.array([[lp.A.get((r, j), 0.0) for j in lp.variables] for r in lp.rows])
    m, n = A.shape
    return StandardForm(list(lp.variables) + ["s_" + r for r in lp.rows],
                        np.hstack([A, np.eye(m)]), np.array([lp.b[r] for r in lp.rows], dtype=float),
                        np.concatenate([[lp.c[j] for j in lp.variables], np.zeros(m)]), n)


@dataclass
class Corner:
    basis: tuple            # names of the basic columns
    x: dict                 # name -> value, every column
    feasible: bool
    objective: float


def basic_solutions(lp: LP) -> list:
    """All C(n + m, m) choices of basic columns. A singular choice is skipped: no corner."""
    sf = standard_form(lp)
    m = sf.A.shape[0]
    out = []
    for cols in combinations(range(len(sf.names)), m):
        B = sf.A[:, cols]
        if abs(np.linalg.det(B)) < tolerance.LINALG_ATOL:
            continue
        x = np.zeros(len(sf.names))
        x[list(cols)] = np.linalg.solve(B, sf.b)
        out.append(Corner(tuple(sf.names[j] for j in cols), dict(zip(sf.names, x)),
                          bool((x >= -tolerance.FEASIBILITY_ATOL).all()), float(sf.c @ x)))
    return out


def tableau_path(lp: LP) -> list:
    """The corners the tableau simplex visits from the all-slack basis, as Corner objects.
    Entering: most negative reduced cost (lowest index on a tie). Leaving: smallest ratio
    (lowest index on a tie)."""
    sf = standard_form(lp)
    m, N = sf.A.shape
    T = np.zeros((m + 1, N + 1))            # row 0 is the objective row z - c.x = 0
    T[0, :N], T[1:, :N], T[1:, N] = -sf.c, sf.A, sf.b
    basis = list(range(sf.n_original, N))
    path = []
    for _ in range(100):
        x = np.zeros(N)
        x[basis] = T[1:, N]
        path.append(Corner(tuple(sf.names[j] for j in basis), dict(zip(sf.names, x)), True, float(T[0, N])))
        enter = int(np.argmin(T[0, :N]))
        if T[0, enter] >= -tolerance.LINALG_ATOL:
            return path
        col = T[1:, enter]
        ratios = [T[i + 1, N] / col[i] if col[i] > tolerance.LINALG_ATOL else np.inf for i in range(m)]
        leave = int(np.argmin(ratios))
        if not np.isfinite(ratios[leave]):
            raise ValueError("unbounded: no row limits %s" % sf.names[enter])
        T[leave + 1] /= T[leave + 1, enter]
        for i in range(m + 1):
            if i != leave + 1:
                T[i] -= T[i, enter] * T[leave + 1]
        basis[leave] = enter
    raise RuntimeError("tableau simplex did not stop in 100 pivots")


# ------------------------------------------------------------------------------- the barrier
MU = 10.0                   # how much t grows between centerings
NEWTON_MAX = 50             # Newton steps allowed per centering (it needs a handful)


def _newton_step(sf: StandardForm, x: np.ndarray, t: float) -> tuple[np.ndarray, float]:
    """One equality-constrained Newton direction for -t c.x - sum log x on A x = b, and the
    Newton decrement squared."""
    m, N = sf.A.shape
    g = -t * sf.c - 1.0 / x
    H = np.diag(1.0 / x ** 2)
    K = np.block([[H, sf.A.T], [sf.A, np.zeros((m, m))]])
    dx = np.linalg.solve(K, np.concatenate([-g, np.zeros(m)]))[:N]
    return dx, float(dx @ H @ dx)


def barrier_path(lp: LP, x0: dict, t0: float = 1.0, mu: float = MU, gap: float = None) -> list:
    """Central-path iterates (one per centering) from the strictly interior point x0, given in the
    ORIGINAL variables (the slacks follow from A x + s = b). Stops when the duality-gap bound
    (n + m) / t falls below `gap` (default CROSS_METHOD_RTOL, an absolute bound on how far the
    objective can be from optimal)."""
    sf = standard_form(lp)
    x = np.concatenate([[x0[j] for j in lp.variables], sf.b - sf.A[:, :sf.n_original] @ [x0[j] for j in lp.variables]])
    if (x <= 0).any():
        raise ValueError("x0 must be strictly inside: every variable and every slack positive")
    N = len(x)
    t = t0
    target = gap if gap is not None else tolerance.CROSS_METHOD_RTOL
    path = [dict(zip(sf.names, x))]

    def f(z):
        return -t * sf.c @ z - np.log(z).sum()

    while N / t > target:
        for _ in range(NEWTON_MAX):
            dx, lam2 = _newton_step(sf, x, t)
            if lam2 / 2 < tolerance.LINALG_ATOL:
                break
            step = 1.0
            while (x + step * dx <= 0).any() or f(x + step * dx) > f(x) - 0.25 * step * lam2:
                step *= 0.5
            x = x + step * dx
        path.append(dict(zip(sf.names, x)))
        t *= mu
    return path
