"""Seed for the Markov chains and queues teaching notebook. Writes the notebook without outputs; execute it afterwards (README.md here)."""
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "notebooks", "09_queueing_and_markov", "markov_and_queues.ipynb")
cells = []


def md(t):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": t.strip("\n").splitlines(keepends=True)})


def code(t):
    cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
                  "source": t.strip("\n").splitlines(keepends=True)})


md(r"""
# Markov chains and queues: where things end up, and how long they wait

Two models of systems that change at random. A **Markov chain** hops between a handful of states
with fixed probabilities that depend only on where it is now; the questions are where it will be
after a few steps, where it settles in the long run, and — if some state is a trap — how long until
it falls in. A **queue** is customers arriving at random and being served at random; the questions
are how many are waiting and for how long.

Both are matrix arithmetic and a few formulas. No solver in this notebook, no licence cell — numpy
does everything, and the last section checks the formulas by simulating the queue with a printed
seed. The course taught the chains and queues through R packages; every number those packages
printed is reproduced here by hand.
""")

md(r"""
## Setup: where the package lives

This notebook builds its models by hand and then checks them against `orteach`, the package in
`src/`. Run from a clone of the repository, `../../src` is right there. On Colab there is no clone
until this cell makes one, and no `gurobipy` until it installs it. Nothing here needs a secret.
""")
code(r'''
import os, subprocess, sys

REPO_URL = None      # the public GitHub URL, once this library is published; Colab clones from it

try:
    import google.colab                      # noqa: F401 - succeeds only on Colab
    ON_COLAB = True
except ImportError:
    ON_COLAB = False

if ON_COLAB:
    if REPO_URL is None:
        raise SystemExit("This library is not published yet: open the notebook from a clone of the repository.")
    if not os.path.isdir("/content/teaching-code"):
        subprocess.run(["git", "clone", "--quiet", REPO_URL, "/content/teaching-code"], check=True)
    os.chdir("/content/teaching-code/notebooks/09_queueing_and_markov")
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "gurobipy>=11,<14"], check=True)

sys.path.insert(0, os.path.abspath(os.path.join("..", "..", "src")))
try:
    import orteach                            # noqa: F401
except ImportError:
    raise SystemExit("orteach not found: run this notebook from its own folder inside the repository, "
                     "so that ../../src exists.")
print("package:", os.path.dirname(orteach.__file__))
''')

md(r"""
## A chain is a table

Three zones a taxi driver works. Each row is where the driver is now; each entry is the probability
of the next fare ending in that column's zone. Rows sum to one. The matrix is instance data, so it
lives in `data/raw/` and both this notebook and the package read it.
""")
code(r'''
import sys, os
import numpy as np
sys.path.insert(0, os.path.abspath(os.path.join("..", "..", "src")))
from orteach.markov import load_chain

zones = load_chain("driver_zones.csv")
P = zones.P

print("states:", zones.states)
print(f"{'from / to':10}" + "".join(f"{s:>8}" for s in zones.states))
for i, s in enumerate(zones.states):
    print(f"{s:10}" + "".join(f"{P[i, j]:8.2f}" for j in range(len(zones.states))))
print()
print("P[North -> West] =", float(P[zones.index("North"), zones.index("West")]), "   row sums:", P.sum(axis=1))

# to try a different chain, edit the loaded matrix; the change reaches the package check at the bottom:
# zones.P[0] = [0.5, 0.3, 0.2]
''')

md(r"""
## One step, two steps, three

Start in North: the distribution over zones is the row vector $\pi_0 = (1, 0, 0)$. After one fare
it is $\pi_0 P$; after two, $\pi_0 P^2$. Predict before running: does the driver's location keep
depending on where they started, or does it wash out?
""")
code(r'''
pi0 = np.array([1.0, 0.0, 0.0])          # starts in North

dist = pi0.copy()
for n in range(1, 4):
    dist = dist @ P
    print(f"after {n} fare(s): " + "  ".join(f"{s} {x:.4f}" for s, x in zip(zones.states, dist)))
''')

md(r"""
Twenty steps, from each starting zone. The rows of $P^{20}$ are the distributions after twenty fares
for each start.
""")
code(r'''
P20 = np.linalg.matrix_power(P, 20)
for i, s in enumerate(zones.states):
    print(f"start {s:6}: " + "  ".join(f"{x:.6f}" for x in P20[i]))
''')

md(r"""
## The steady state, solved rather than iterated

The long-run distribution $\pi$ satisfies $\pi P = \pi$ and $\sum_i \pi_i = 1$. That is a linear
system: three balance equations, one of which is redundant, plus the normalisation. Replace the
redundant one with the normalisation and solve. Write down what you expect $\pi$ to be from the
$P^{20}$ rows first.
""")
code(r'''
n = len(zones.states)
A = P.T - np.eye(n)          # rows of (P^T - I) pi = 0
A[-1, :] = 1.0               # ... with the last balance equation replaced by sum(pi) = 1
b = np.zeros(n); b[-1] = 1.0

pi_hand = np.linalg.solve(A, b)
print("steady state:", {s: round(float(x), 6) for s, x in zip(zones.states, pi_hand)})
print("as fractions of 18:", np.round(pi_hand * 18, 6))
print("check pi P - pi =", np.round(pi_hand @ P - pi_hand, 12))
''')

md(r"""
## A two-state check by hand

The course's R notebook had this arithmetic: two states, $P = \begin{pmatrix} 1/2 & 1/2 \\ 1/3 & 2/3
\end{pmatrix}$, start in state 1. Compute the probability of being in state 1 after three steps by
hand — it is a fraction with denominator 72 — then run this.
""")
code(r'''
from orteach.markov import Chain

two = Chain(["1", "2"], [[0.5, 0.5], [1 / 3, 2 / 3]])
after3 = np.array([1.0, 0.0]) @ np.linalg.matrix_power(two.P, 3)
print("after three steps:", after3, "   x 72 =", np.round(after3 * 72, 9))
''')

md(r"""
---

## A chain with a trap

Four states. Look at the row for C before running anything: what is the probability of leaving C
once you are there? A state like that is **absorbing**, and the question changes from "where does
the chain settle" to "how long until it is absorbed".
""")
code(r'''
ab = load_chain("absorbing_4state.csv")
Q_full = ab.P
print(f"{'from / to':10}" + "".join(f"{s:>6}" for s in ab.states))
for i, s in enumerate(ab.states):
    print(f"{s:10}" + "".join(f"{Q_full[i, j]:6.1f}" for j in range(len(ab.states))))
absorbing = [s for i, s in enumerate(ab.states) if Q_full[i, i] == 1.0]
transient = [s for s in ab.states if s not in absorbing]
print("\nabsorbing:", absorbing, "  transient:", transient)
''')

md(r"""
## The fundamental matrix

Split $P$ into the transient-to-transient block $Q$ and the transient-to-absorbing block $R$. Then
$N = (I - Q)^{-1}$ counts the expected number of visits to each transient state before absorption,
so each row of $N$ summed is the expected number of steps to absorption from that start, and $NR$
is the probability of ending in each absorbing state. Predict which starting state takes longest.
""")
code(r'''
ti = [ab.index(s) for s in transient]
ai = [ab.index(s) for s in absorbing]
Q = Q_full[np.ix_(ti, ti)]
R = Q_full[np.ix_(ti, ai)]

N = np.linalg.inv(np.eye(len(ti)) - Q)
steps_hand = {s: float(N[k].sum()) for k, s in enumerate(transient)}
land = N @ R
print("expected steps to absorption:", {s: round(x, 4) for s, x in steps_hand.items()})
print("probability of absorption in", absorbing, "from each start:", np.round(land.ravel(), 6))
''')

md(r"""
D is the fastest start, and half of the time D's first step is to A, the slowest. Trace the paths
and say how that can be.

---

## A queue: M/M/1

Customers arrive as a Poisson process at rate $\lambda$ and one server works at rate $\mu$, both
exponential. Two knobs. The course's example: $\lambda = 2$ per hour, $\mu = 3$ per hour.

Utilisation $\rho = \lambda/\mu$ is the fraction of time the server is busy, and every other measure
is a one-liner in $\rho$. Predict $L$, the average number in the system, before running: below 1,
between 1 and 2, or above 2?
""")
code(r'''
LAM = 2.0     # arrivals per hour
MU  = 3.0     # services per hour, one server

rho = LAM / MU
P0  = 1 - rho
L   = rho / (1 - rho)
Lq  = rho ** 2 / (1 - rho)
W   = L / LAM
Wq  = Lq / LAM
print(f"rho {rho:.4f}   P0 {P0:.4f}   L {L:.4f}   Lq {Lq:.4f}   W {W:.4f} h   Wq {Wq:.4f} h")
''')

md(r"""
Four measures, two relationships. $L = \lambda W$ and $L_q = \lambda W_q$ — **Little's law** — hold
for any stable queue, not just this one, and $W = W_q + 1/\mu$ because the time in the system is the
wait plus the service. The R package printed the probability of $n$ customers in the system for
$n = 0..5$; here is the geometric formula behind it.
""")
code(r'''
print("Little's law: L - lambda W =", round(L - LAM * W, 12), "   Lq - lambda Wq =", round(Lq - LAM * Wq, 12))
print("W - (Wq + 1/mu) =", round(W - (Wq + 1 / MU), 12))
print()
print("P(n in system):", "  ".join(f"n={n} {(1 - rho) * rho ** n:.4f}" for n in range(6)))
''')

md(r"""
## Two servers: M/M/2

Add a server. The offered load $a = \lambda/\mu$ is now shared by $c = 2$ servers, so utilisation is
$a/c$. $P_0$ needs the Erlang C sum — the one formula in this notebook that is not a one-liner — and
$L_q$ follows from it; the rest is Little's law again. Predict: does $W_q$ halve, or fall by more?
""")
code(r'''
from math import factorial

C = 2                                   # servers
a = LAM / MU                            # offered load, in servers
rho2 = a / C

P0_2 = 1 / (sum(a ** k / factorial(k) for k in range(C)) + a ** C / (factorial(C) * (1 - rho2)))
Lq_2 = P0_2 * a ** C * rho2 / (factorial(C) * (1 - rho2) ** 2)
Wq_2 = Lq_2 / LAM
W_2  = Wq_2 + 1 / MU
L_2  = LAM * W_2
print(f"M/M/{C}: rho {rho2:.4f}   P0 {P0_2:.4f}   Lq {Lq_2:.4f}   Wq {Wq_2:.4f} h   W {W_2:.4f} h   L {L_2:.4f}")
print(f"M/M/1: Wq {Wq:.4f} h  ->  M/M/2: Wq {Wq_2:.4f} h   ratio {Wq_2 / Wq:.3f}")
''')

md(r"""
---

## Simulate the M/M/1 queue

Formulas are claims. Check one by running the queue: draw every interarrival time and every service
time up front from a seeded generator, then apply **Lindley's recursion** — a customer's wait is the
previous customer's wait plus their service, minus the gap before this arrival, floored at zero.

The seed is printed. The package's `simulate_mm1` draws the same numbers in the same order from the
same seed, which is why the agreement check at the bottom can demand an exact match from a random
simulation.
""")
code(r'''
SEED = 20260905
N_CUSTOMERS = 200_000
print("seed:", SEED, "  customers:", N_CUSTOMERS)

rng = np.random.default_rng(SEED)
interarrival = rng.exponential(1 / LAM, N_CUSTOMERS)     # gaps between arrivals
service = rng.exponential(1 / MU, N_CUSTOMERS)           # service times, in arrival order

wait = np.zeros(N_CUSTOMERS)
for k in range(1, N_CUSTOMERS):
    wait[k] = max(0.0, wait[k - 1] + service[k - 1] - interarrival[k])

Wq_sim = wait.mean()
W_sim = (wait + service).mean()
lam_obs = N_CUSTOMERS / interarrival.sum()
print(f"simulated  Wq {Wq_sim:.4f} h   W {W_sim:.4f} h   observed lambda {lam_obs:.4f}")
print(f"formula    Wq {Wq:.4f} h   W {W:.4f} h")
''')

md(r"""
Close, not equal. Change the seed and run again; then make `N_CUSTOMERS` a hundred times smaller, and
then ten times larger.
How does the gap between simulated and formula move with each, and what does that tell you about
which one to trust when they disagree?

---

# Now the streamlined version

Every computation above is a few lines of numpy, and the package holds each of them once:
`markov.steady_state`, `markov.distribution_after`, `markov.absorption`, `queueing.mm1`,
`queueing.mmc` and `queueing.simulate_mm1`.
""")
code(r'''
from orteach import markov, queueing
from orteach.tolerance import AGREEMENT_RTOL, rel_diff

pkg_pi = markov.steady_state(zones)
pkg_after3 = markov.distribution_after(two, "1", 3)
pkg_ab = markov.absorption(ab)
pkg_mm1 = queueing.mm1(LAM, MU)
pkg_mm2 = queueing.mmc(LAM, MU, C)
pkg_sim = queueing.simulate_mm1(LAM, MU, N_CUSTOMERS, SEED)

print("steady state       ", np.round(pkg_pi, 6))
print("absorption steps   ", {s: round(float(x), 4) for s, x in pkg_ab.expected_steps.items()})
print(f"M/M/1 L {pkg_mm1.L:.4f}  Wq {pkg_mm1.Wq:.4f}    M/M/2 L {pkg_mm2.L:.4f}  Wq {pkg_mm2.Wq:.4f}")
print(f"simulation (seed {pkg_sim.seed}) Wq {pkg_sim.Wq:.4f}  W {pkg_sim.W:.4f}")
''')

md(r"""
## The agreement assertion

Every hand-built number against the package: the steady state, the three-step distribution, the
absorption times, all six M/M/1 and M/M/2 measures, and the simulated waits — which are asserted
equal to the last bit, not merely close, because the seed and the draw order are the same on both
sides.
""")
code(r'''
checks = [("two-state after 3 steps", after3[0], pkg_after3[0]),
          ("M/M/1 L", L, pkg_mm1.L), ("M/M/1 Lq", Lq, pkg_mm1.Lq), ("M/M/1 W", W, pkg_mm1.W),
          ("M/M/1 Wq", Wq, pkg_mm1.Wq), ("M/M/1 P0", P0, pkg_mm1.P0),
          ("M/M/2 P0", P0_2, pkg_mm2.P0), ("M/M/2 Lq", Lq_2, pkg_mm2.Lq), ("M/M/2 Wq", Wq_2, pkg_mm2.Wq),
          ("M/M/2 W", W_2, pkg_mm2.W), ("M/M/2 L", L_2, pkg_mm2.L),
          ("simulated Wq", Wq_sim, pkg_sim.Wq), ("simulated W", W_sim, pkg_sim.W)]
for k, s in enumerate(zones.states):
    checks.append((f"steady state {s}", pi_hand[k], pkg_pi[k]))
for s in transient:
    checks.append((f"steps from {s}", steps_hand[s], pkg_ab.expected_steps[s]))
assert Wq_sim == pkg_sim.Wq and W_sim == pkg_sim.W, "the simulation's draw order differs from the package's"

worst = max(rel_diff(h, k) for _, h, k in checks)
print(f"{len(checks)} comparisons")
for name, hand, packaged in checks[:4]:
    print(f"  {name:24} hand {hand:10.6f}   package {packaged:10.6f}   rel {rel_diff(hand, packaged):.2e}")
print("  ...")
assert worst < AGREEMENT_RTOL, f"notebook and package disagree by {worst:.2e}"
print(f"\nnotebook and package agree to {worst:.1e}")
''')

md(r"""
---

## Where to take this next

- Push $\lambda$ toward $\mu$ — try 2.5, 2.9, 2.99. Plot $L$ against $\rho$. Where does the curve go,
  and what does that say about running a server at 95% utilisation?
- Give the four-state chain a second absorbing state by making D absorbing too. Now $NR$ has two
  columns. From B, which trap is more likely, and does that match your reading of the matrix?
- The simulation assumes an infinite waiting room. Cap it at $K = 4$ customers and turn away
  arrivals that find it full. Which of the six measures still obey Little's law, and with which
  $\lambda$?
""")

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                   "language_info": {"name": "python", "version": "3.13"}}, "nbformat": 4, "nbformat_minor": 5}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    f.write("\n")
print("wrote %s  (%d cells)" % (OUT, len(cells)))
