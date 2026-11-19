"""Design of experiments: planning (noise, power, run counts, augmenting runs you
already have), two-level factorials, their fractions, center points and Latin
hypercubes - written once for a machine.

The three notebooks in ``notebooks/15_design_of_experiments`` build every one of these
by hand first; this module is the copy their agreement cells check against.

Two-level designs use coded units, -1 for a factor's low setting and +1 for its high
one, in **standard order**: the first factor alternates fastest. An *effect* is the
difference between the mean response at a column's +1 rows and its -1 rows; on an
orthogonal design the least-squares *coefficient* of that column is half the effect.
Both conventions are in use and the notebooks teach the factor of two explicitly.

A fraction is named by its generators, ``{"E": "ABCD"}`` for the half fraction of a
2^5 in which column E is set to the product A*B*C*D. Aliases follow from the
defining relation by multiplying words, where a letter squared is 1 - so a product
of two words is the symmetric difference of their letters.

TABLE in ``data/raw/``:

    doe_reactor_runs.csv   a synthetic 2^5 factorial plus four center runs, generated
                           here from a printed seed and the stated true model
                           (REACTOR_TRUTH). It is synthetic on purpose: with the truth
                           known, a reader can see what each design recovers and what
                           it confuses. Every fraction in the notebook is a subset of
                           these same 32 runs, so the differences between designs are
                           aliasing alone and not fresh noise.
"""
from __future__ import annotations

import csv
import itertools
import math
import os
from dataclasses import dataclass

import numpy as np
from scipy import stats

from . import paths

# ------------------------------------------------------------- the instance

FACTORS = "ABCDE"
FACTOR_NAMES = {"A": "temperature", "B": "catalyst", "C": "time", "D": "stirring", "E": "feed rate"}
REACTOR_CSV = "doe_reactor_runs.csv"   # resolved by paths.table() when read
REACTOR_SEED = 20261118
REACTOR_SIGMA = 1.5
REACTOR_CENTER_RUNS = 4
# The true model, in coded units. Coefficients, not effects: moving A from -1 to +1
# changes the response by 2 x 6.0 = 12. "AA" is a pure quadratic in A, which equals 1 at
# every corner of the cube - so no corner run can see it - and 0 at the center.
REACTOR_TRUTH = {"intercept": 60.0, "A": 6.0, "B": 4.0, "C": -2.5, "AB": 3.0, "AA": -3.0}


def _true_mean(row: dict) -> float:
    mu = REACTOR_TRUTH["intercept"]
    for word, beta in REACTOR_TRUTH.items():
        if word == "intercept":
            continue
        mu += beta * math.prod(row[ch] for ch in word)
    return mu


def generate_reactor(seed: int = REACTOR_SEED) -> dict:
    """The 32 corner runs in standard order, then the center runs, with Normal noise
    and a randomized run order, as columns."""
    rng = np.random.default_rng(seed)
    design = full_factorial(len(FACTORS))
    rows = [dict(zip(FACTORS, r)) for r in design] + [dict.fromkeys(FACTORS, 0.0)] * REACTOR_CENTER_RUNS
    noise = rng.normal(0.0, REACTOR_SIGMA, len(rows))
    order = rng.permutation(len(rows)) + 1
    out = {"run": [], "run_order": [], "kind": [], **{f: [] for f in FACTORS}, "yield": []}
    for i, (row, e) in enumerate(zip(rows, noise)):
        out["run"].append(i + 1)
        out["run_order"].append(int(order[i]))
        out["kind"].append("factorial" if i < len(design) else "center")
        for f in FACTORS:
            out[f].append(int(row[f]))
        out["yield"].append(round(_true_mean(row) + float(e), 2))
    return out


def write_reactor(path: str | None = None) -> None:
    path = path or os.path.join(paths.SOURCE_DIR, REACTOR_CSV)   # writes the clone's own table
    cols = generate_reactor()
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(list(cols))
        for i in range(len(cols["run"])):
            w.writerow([cols[c][i] for c in cols])


def load_reactor(path: str | None = None) -> dict:
    path = path or paths.table(REACTOR_CSV)
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = {"run": [int(r["run"]) for r in rows], "run_order": [int(r["run_order"]) for r in rows],
           "kind": [r["kind"] for r in rows], "yield": [float(r["yield"]) for r in rows]}
    for fac in FACTORS:
        out[fac] = [int(r[fac]) for r in rows]
    return out


# ------------------------------------------------------- two-level designs

def full_factorial(k: int) -> np.ndarray:
    """The 2^k design in coded units, standard order (first column fastest)."""
    return np.array([row[::-1] for row in itertools.product((-1, 1), repeat=k)], dtype=float)


def words(factors: str = FACTORS, max_order: int | None = None) -> list[str]:
    """Every main effect and interaction, by order and then alphabetically."""
    top = len(factors) if max_order is None else max_order
    return ["".join(c) for r in range(1, top + 1) for c in itertools.combinations(factors, r)]


def column(X: np.ndarray, word: str, factors: str = FACTORS) -> np.ndarray:
    """The model column for one word: the elementwise product of its factors' columns."""
    return np.prod(X[:, [factors.index(ch) for ch in word]], axis=1)


def effects(X: np.ndarray, y, factors: str = FACTORS, max_order: int | None = None) -> dict:
    """Mean response where a word's column is +1, minus where it is -1."""
    y = np.asarray(y, dtype=float)
    out = {}
    for w in words(factors, max_order):
        col = column(X, w, factors)
        out[w] = float(y[col > 0].mean() - y[col < 0].mean())
    return out


def model_matrix(X: np.ndarray, terms: list[str], factors: str = FACTORS) -> np.ndarray:
    """A column of ones, then one column per named word. A center run (every factor 0)
    has 0 in every word's column, so it informs only the intercept."""
    return np.column_stack([np.ones(len(X))] + [column(X, w, factors) for w in terms])


def coefficients(X: np.ndarray, y, terms: list[str], factors: str = FACTORS) -> dict:
    """Least-squares coefficients for an intercept plus the named words."""
    M = model_matrix(X, terms, factors)
    beta = np.linalg.solve(M.T @ M, M.T @ np.asarray(y, dtype=float))
    return dict(zip(["intercept"] + list(terms), (float(b) for b in beta)))


def fraction(X: np.ndarray, generators: dict, factors: str = FACTORS) -> np.ndarray:
    """Boolean mask of the rows of a full factorial that satisfy every generator,
    e.g. ``{"E": "ABCD"}`` keeps the rows where E equals A*B*C*D."""
    keep = np.ones(len(X), dtype=bool)
    for letter, word in generators.items():
        keep &= X[:, factors.index(letter)] == column(X, word, factors)
    return keep


def multiply(a: str, b: str) -> str:
    """Product of two words: a letter that appears twice squares to 1 and drops out."""
    return "".join(sorted(set(a) ^ set(b)))


def defining_relation(generators: dict) -> list[str]:
    """Every word equal to the identity column I in the fraction: the generator words
    and all their products, shortest first."""
    base = [multiply(letter, word) for letter, word in generators.items()]
    out = set()
    for r in range(1, len(base) + 1):
        for combo in itertools.combinations(base, r):
            w = ""
            for g in combo:
                w = multiply(w, g)
            out.add(w)
    return sorted(out, key=lambda w: (len(w), w))


def aliases(word: str, relation: list[str]) -> list[str]:
    """The words whose columns equal this word's column in the fraction."""
    return sorted((multiply(word, r) for r in relation), key=lambda w: (len(w), w))


def resolution(relation: list[str]) -> int:
    """Length of the shortest word in the defining relation."""
    return min(len(w) for w in relation)


def half_normal_quantiles(m: int) -> np.ndarray:
    """Plotting positions for m absolute effects on a half-normal plot."""
    return stats.norm.ppf(0.5 + 0.5 * (np.arange(1, m + 1) - 0.5) / m)


@dataclass
class LenthResult:
    pse: float          # pseudo standard error of one effect
    me: float           # margin of error for any one effect
    sme: float          # simultaneous margin, for all effects at once


def lenth(values, alpha: float = 0.05) -> LenthResult:
    """Lenth's (1989) method for an unreplicated factorial: estimate an effect's
    standard error from the effects themselves, trusting that most are noise.
    s0 = 1.5 median|e|; PSE = 1.5 median of the |e| below 2.5 s0; margins use a t
    with m/3 degrees of freedom for m effects."""
    a = np.abs(np.asarray(values, dtype=float))
    m = len(a)
    s0 = 1.5 * np.median(a)
    pse = float(1.5 * np.median(a[a < 2.5 * s0]))
    gamma = (1 + (1 - alpha) ** (1 / m)) / 2
    return LenthResult(pse, float(stats.t.ppf(1 - alpha / 2, m / 3) * pse),
                       float(stats.t.ppf(gamma, m / 3) * pse))


@dataclass
class CurvatureTest:
    estimate: float     # mean of the factorial runs minus mean of the center runs
    se: float
    t: float
    df: int
    p_value: float


def curvature_test(y_factorial, y_center) -> CurvatureTest:
    """Is the response at the center where the corners say a flat surface puts it?
    Pure error comes from the center replicates alone, so df = n_center - 1."""
    yf, yc = np.asarray(y_factorial, dtype=float), np.asarray(y_center, dtype=float)
    est = float(yf.mean() - yc.mean())
    s = float(yc.std(ddof=1))
    se = s * math.sqrt(1 / len(yf) + 1 / len(yc))
    t = est / se
    df = len(yc) - 1
    return CurvatureTest(est, se, t, df, float(2 * stats.t.sf(abs(t), df)))


# ------------------------------------------------- planning: noise and power

def effect_se(x, sigma: float) -> float:
    """Standard error of one effect (the change from -1 to +1) on an orthogonal design:
    2 sigma / sqrt(sum of the column's squared coded settings). For a two-level column
    that sum is the number of runs N, so the familiar 2 sigma / sqrt(N); a center run
    adds 0 to it, so center points do not sharpen an effect."""
    x = np.asarray(x, dtype=float)
    return float(2 * sigma / math.sqrt((x ** 2).sum()))


@dataclass
class SigmaInterval:
    s: float            # sample standard deviation of the replicates
    df: int
    lower: float
    upper: float


def sigma_interval(y, conf: float = 0.95) -> SigmaInterval:
    """Two-sided interval for sigma from replicates: (n-1) s^2 / sigma^2 is chi-square
    with n-1 degrees of freedom."""
    y = np.asarray(y, dtype=float)
    df = len(y) - 1
    s = float(y.std(ddof=1))
    a = 1 - conf
    return SigmaInterval(s, df, s * math.sqrt(df / stats.chi2.ppf(1 - a / 2, df)),
                         s * math.sqrt(df / stats.chi2.ppf(a / 2, df)))


def sigma_bound(y, conf: float) -> float:
    """One-sided upper confidence bound for sigma: a planning value that the true noise
    exceeds with probability 1 - conf."""
    y = np.asarray(y, dtype=float)
    df = len(y) - 1
    return float(y.std(ddof=1) * math.sqrt(df / stats.chi2.ppf(1 - conf, df)))


def power(delta: float, se: float, df: int | None = None, alpha: float = 0.05) -> float:
    """Probability that a two-sided test at level alpha declares an effect of true size
    delta, when its estimate has standard error se. With df, the test is a t test and
    the statistic is noncentral t with noncentrality delta/se; without, the normal
    approximation."""
    lam = delta / se
    if df is None:
        z = stats.norm.ppf(1 - alpha / 2)
        return float(stats.norm.sf(z - lam) + stats.norm.cdf(-z - lam))
    tc = stats.t.ppf(1 - alpha / 2, df)
    lower = stats.nct.cdf(-tc, df, lam)
    # scipy returns nan for the lower tail when lam is many standard errors past tc;
    # that tail is then smaller than any probability printed here
    return float(stats.nct.sf(tc, df, lam) + (0.0 if np.isnan(lower) else lower))


def runs_needed(delta: float, sigma: float, alpha: float = 0.05, target: float = 0.8) -> float:
    """Total two-level runs for the normal-approximation power to reach target:
    N = 4 (z_{alpha/2} + z_{1-target})^2 (sigma/delta)^2. Total runs, not replicates
    per cell: every run of a factorial informs every effect."""
    z = stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(target)
    return float(4 * z ** 2 * (sigma / delta) ** 2)


# -------------------------------------------- planning: building on runs you have

# Added to M'M before taking a log-determinant, only so that a design that cannot yet
# estimate every term (det = 0) still ranks candidates: each missing dimension costs
# log(AUGMENT_RIDGE), so a run that adds one always beats a run that does not. It is
# not a comparison tolerance and never decides an answer once M'M is full rank.
AUGMENT_RIDGE = 1e-6


def log_det(M: np.ndarray) -> float:
    """log det(M'M + AUGMENT_RIDGE I): the D-criterion. det(M'M) is inversely
    proportional to the squared volume of the joint confidence region for the
    coefficients, so a larger value is a sharper design."""
    return float(np.linalg.slogdet(M.T @ M + AUGMENT_RIDGE * np.eye(M.shape[1]))[1])


def augment(existing: np.ndarray, candidates: np.ndarray, terms: list[str], n_add: int,
            factors: str = FACTORS, block: bool = True) -> list[int]:
    """Greedy D-optimal augmentation: add n_add candidate runs one at a time, each the
    one that most increases log_det of the model matrix. Candidates are used at most
    once and the first one found wins a tie. With block, the model carries a column
    that is -1 for existing runs and +1 for new ones, so a shift between the two
    batches is estimated instead of leaking into the effects."""
    def matrix(rows, batch):
        M = model_matrix(rows, terms, factors)
        return np.column_stack([M, batch]) if block else M
    rows, batch = existing.astype(float), -np.ones(len(existing))
    chosen: list[int] = []
    for _ in range(n_add):
        best_i, best_v = None, -np.inf
        for i in range(len(candidates)):
            if i in chosen:
                continue
            v = log_det(matrix(np.vstack([rows, candidates[i]]), np.append(batch, 1.0)))
            if v > best_v:
                best_i, best_v = i, v
        chosen.append(best_i)
        rows, batch = np.vstack([rows, candidates[best_i]]), np.append(batch, 1.0)
    return chosen


def d_efficiency(M: np.ndarray) -> float:
    """det(M'M)^(1/p) / N for an N-by-p model matrix of coded columns. An orthogonal
    two-level design scores 1, the most a design of that size can."""
    n, p = M.shape
    return float(np.exp(np.linalg.slogdet(M.T @ M)[1] / p) / n)


# ---------------------------------------------------------- Latin hypercubes

def lhs(n: int, d: int, rng: np.random.Generator, centered: bool = False) -> np.ndarray:
    """An n-run Latin hypercube in [0, 1]^d: each axis cut into n equal bins, every bin
    used exactly once. Per column: a permutation picks the bins, then a uniform draw
    (or the bin's middle, if centered) places the point inside its bin."""
    P = np.empty((n, d))
    for j in range(d):
        perm = rng.permutation(n)
        offset = 0.5 if centered else rng.random(n)
        P[:, j] = (perm + offset) / n
    return P


def min_distance(P: np.ndarray) -> float:
    """Smallest Euclidean distance between any two runs: the maximin criterion."""
    diff = P[:, None, :] - P[None, :, :]
    dist = np.sqrt((diff ** 2).sum(axis=2))
    return float(dist[np.triu_indices(len(P), 1)].min())


def maximin_lhs(n: int, d: int, tries: int, seed: int) -> tuple[np.ndarray, float]:
    """The best of ``tries`` random Latin hypercubes by minimum distance; the first
    one found wins a tie."""
    rng = np.random.default_rng(seed)
    best, best_d = None, -1.0
    for _ in range(tries):
        P = lhs(n, d, rng)
        dmin = min_distance(P)
        if dmin > best_d:
            best, best_d = P, dmin
    return best, best_d


def is_latin(P: np.ndarray) -> bool:
    """True when every column uses each of the n bins exactly once."""
    n = len(P)
    bins = np.floor(P * n).astype(int)
    return all(sorted(bins[:, j]) == list(range(n)) for j in range(P.shape[1]))


def sine_sum(P: np.ndarray) -> np.ndarray:
    """Test function sum_j sin(pi x_j). Its mean over the unit cube is d * 2/pi."""
    return np.sin(np.pi * P).sum(axis=1)


def sampling_study(n: int, d: int, reps: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Estimate the mean of sine_sum from n plain random points and from an n-run
    Latin hypercube, ``reps`` times each, drawing in that order every repetition."""
    rng = np.random.default_rng(seed)
    est_random, est_lhs = np.empty(reps), np.empty(reps)
    for r in range(reps):
        est_random[r] = sine_sum(rng.random((n, d))).mean()
        est_lhs[r] = sine_sum(lhs(n, d, rng)).mean()
    return est_random, est_lhs
