"""Seed for the distributions-and-CLT teaching notebook. Writes the notebook without outputs; execute it afterwards (README.md here)."""
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "notebooks", "14_probability_and_stats", "distributions_and_clt.ipynb")
cells = []


def md(t):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": t.strip("\n").splitlines(keepends=True)})


def code(t):
    cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
                  "source": t.strip("\n").splitlines(keepends=True)})


md(r"""
# Distributions as formulas, and the theorem that makes the mean trustworthy

The course taught its distributions through R's `d`, `p` and `q` functions — `dbinom`, `pnbinom`,
`qpois` — which return a number and hide the formula behind a name. This notebook writes each
formula out, evaluates it by hand, draws a sample from the distribution with a printed seed, and
only then calls `scipy.stats` to confirm. Each distribution gets three lines: what it counts, its
probability formula, and one number the course's notebook asked for.

The second half is the central limit theorem: averages of samples from a lopsided distribution
become bell-shaped, and their spread shrinks in a way you can predict before you see it.
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
    os.chdir("/content/teaching-code/notebooks/14_probability_and_stats")
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
## Set the seed, and print it

Every sample below is random. With the seed fixed and printed, every number in this notebook is the
same on your machine as on this one, and a reader who changes it knows they did.
""")
code(r'''
import math
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from orteach.tolerance import AGREEMENT_RTOL, rel_diff

SEED = 20260905
N_SAMPLE = 10_000            # draws per distribution, as in the course notebook
rng = np.random.default_rng(SEED)
print("seed:", SEED, "  draws per distribution:", N_SAMPLE)
''')

md(r"""
## Binomial: successes in a fixed number of trials

$n = 100$ trials, each a success with probability $p = 0.25$. $X$ is how many succeed.

$$P(X = k) = \binom{n}{k} p^k (1-p)^{n-k}$$

Predict before running: the most likely value of $X$, and roughly how wide the histogram will be.
""")
code(r'''
N_BINOM, P_BINOM = 100, 0.25
binom_pmf_25 = math.comb(N_BINOM, 25) * P_BINOM ** 25 * (1 - P_BINOM) ** (N_BINOM - 25)
binom_cdf_30 = sum(math.comb(N_BINOM, i) * P_BINOM ** i * (1 - P_BINOM) ** (N_BINOM - i) for i in range(0, 31))

sample = rng.binomial(N_BINOM, P_BINOM, N_SAMPLE)
print(f"P(X = 25) by the formula  {binom_pmf_25:.6f}    scipy {stats.binom.pmf(25, N_BINOM, P_BINOM):.6f}")
print(f"P(X <= 30) by the formula {binom_cdf_30:.6f}    scipy {stats.binom.cdf(30, N_BINOM, P_BINOM):.6f}")
print(f"sample mean {sample.mean():.3f}   n p = {N_BINOM * P_BINOM}      sample sd {sample.std(ddof=1):.3f}   "
      f"sqrt(n p (1-p)) = {math.sqrt(N_BINOM * P_BINOM * (1 - P_BINOM)):.3f}")
plt.hist(sample, bins=range(sample.min(), sample.max() + 2), color="lightblue", edgecolor="white")
plt.axvline(sample.mean(), color="red"); plt.title("Binomial(100, 0.25): 10,000 draws"); plt.show()
''')

md(r"""
## Negative binomial: failures before the $r$-th success

$r = 500$ successes wanted, $p = 0.25$ each trial; $X$ counts the failures along the way. In R's
convention (and scipy's),

$$P(X = x) = \binom{x + r - 1}{x} p^r (1-p)^x.$$

Evaluate that at $x = 1500$ exactly as written and look at what comes back. Predict first: a number,
zero, or something else?
""")
code(r'''
R_NB, P_NB = 500, 0.25
x = 1500
print(f"  C(x+r-1, x) has {len(str(math.comb(x + R_NB - 1, x)))} digits   (a float holds {len(str(int(sys.float_info.max)))})")
print(f"  p^r              = {P_NB ** R_NB:.3e}")
print(f"  (1-p)^x          = {(1 - P_NB) ** x:.3e}")
print(f"  p^r * (1-p)^x    = {P_NB ** R_NB * (1 - P_NB) ** x}")
try:
    direct = math.comb(x + R_NB - 1, x) * P_NB ** R_NB * (1 - P_NB) ** x
    print(f"the formula as written, at x = 1500: {direct}")
except OverflowError as e:
    print("the formula as written, at x = 1500:", type(e).__name__, "-", e)
''')

md(r"""
The pieces fail in both directions. The binomial coefficient is an exact integer with more digits
than a float can hold, so Python cannot convert it to multiply it by anything — that is the error.
And the two powers, each representable on its own, multiply to a number below the smallest positive
float and round to exactly zero. The probability itself is an ordinary number; it is the *pieces*
that cannot be held. The fix is to add logarithms instead of multiplying numbers:

$$\log P = \log\Gamma(x+r) - \log\Gamma(x+1) - \log\Gamma(r) + r \log p + x \log(1-p)$$
""")
code(r'''
log_pmf = math.lgamma(x + R_NB) - math.lgamma(x + 1) - math.lgamma(R_NB) + R_NB * math.log(P_NB) + x * math.log1p(-P_NB)
pmf_1500 = math.exp(log_pmf)
cdf_1600 = sum(math.exp(math.lgamma(i + R_NB) - math.lgamma(i + 1) - math.lgamma(R_NB) + R_NB * math.log(P_NB) + i * math.log1p(-P_NB))
               for i in range(0, 1601))

sample = rng.negative_binomial(R_NB, P_NB, N_SAMPLE)
print(f"P(X = 1500) in logs    {pmf_1500:.6f}    scipy {stats.nbinom.pmf(1500, R_NB, P_NB):.6f}")
print(f"P(X <= 1600) in logs   {cdf_1600:.6f}    scipy {stats.nbinom.cdf(1600, R_NB, P_NB):.6f}   (R printed 0.901)")
print(f"sample mean {sample.mean():.1f}   r (1-p) / p = {R_NB * (1 - P_NB) / P_NB:.1f}")
''')

md(r"""
## Geometric: failures before the first success

$p = 0.05$. Two conventions exist and they differ by one: R (and this notebook) count *failures*
before the first success, scipy's `geom` counts *trials* including the success. A formula that
does not say which one it uses is wrong for half its readers.

$$P(X = x) = p(1-p)^x, \qquad P(X \le x) = 1 - (1-p)^{x+1}$$
""")
code(r'''
P_GEOM = 0.05
geom_pmf_25 = P_GEOM * (1 - P_GEOM) ** 25
geom_cdf_40 = 1 - (1 - P_GEOM) ** 41

sample = rng.geometric(P_GEOM, N_SAMPLE) - 1            # numpy counts trials; subtract one for failures
print(f"P(X = 25)  {geom_pmf_25:.6f}    scipy geom.pmf(26) {stats.geom.pmf(26, P_GEOM):.6f}   <- scipy's k is x + 1")
print(f"P(X <= 40) {geom_cdf_40:.6f}    scipy geom.cdf(41) {stats.geom.cdf(41, P_GEOM):.6f}   (R printed 0.878)")
print(f"sample mean {sample.mean():.2f}   (1-p)/p = {(1 - P_GEOM) / P_GEOM:.2f}")
''')

md(r"""
## Poisson: events in a fixed interval

Rate $\lambda = 20$ per interval.

$$P(X = k) = \frac{e^{-\lambda} \lambda^k}{k!}$$

Predict: is $P(X \le 25)$ nearer 0.5 or 0.9?
""")
code(r'''
LAM_POIS = 20.0
pois_pmf_20 = math.exp(-LAM_POIS) * LAM_POIS ** 20 / math.factorial(20)
pois_cdf_25 = sum(math.exp(-LAM_POIS) * LAM_POIS ** i / math.factorial(i) for i in range(0, 26))

sample = rng.poisson(LAM_POIS, N_SAMPLE)
print(f"P(X = 20)  {pois_pmf_20:.6f}    scipy {stats.poisson.pmf(20, LAM_POIS):.6f}")
print(f"P(X <= 25) {pois_cdf_25:.6f}    scipy {stats.poisson.cdf(25, LAM_POIS):.6f}   (R printed 0.888)")
print(f"sample mean {sample.mean():.3f}   sample variance {sample.var(ddof=1):.3f}   both should be near {LAM_POIS}")
''')

md(r"""
## Exponential: the wait for the next event

Rate $\lambda = 20$ per unit time, so a mean wait of $1/\lambda = 0.05$.

$$P(X \le x) = 1 - e^{-\lambda x}, \qquad x_q = -\frac{\ln(1-q)}{\lambda}$$
""")
code(r'''
RATE_EXP = 20.0
exp_cdf_02 = 1 - math.exp(-RATE_EXP * 0.2)
exp_q95 = -math.log(1 - 0.95) / RATE_EXP

sample = rng.exponential(1 / RATE_EXP, N_SAMPLE)
print(f"P(X <= 0.2) {exp_cdf_02:.6f}    scipy {stats.expon.cdf(0.2, scale=1 / RATE_EXP):.6f}   (R printed 0.982)")
print(f"95th percentile {exp_q95:.6f}    scipy {stats.expon.ppf(0.95, scale=1 / RATE_EXP):.6f}")
print(f"sample mean {sample.mean():.4f}   1/lambda = {1 / RATE_EXP}")
''')

md(r"""
## Gamma with an integer shape: the wait for the $k$-th event

$k = 3$ events at rate $\lambda = 20$. When the shape is a whole number this is the Erlang
distribution, and its CDF has a formula with no special function in it: the third event has arrived
by time $x$ exactly when a Poisson count over $[0, x]$ is at least 3.

$$P(X \le x) = 1 - \sum_{i=0}^{k-1} \frac{e^{-\lambda x} (\lambda x)^i}{i!}$$
""")
code(r'''
K_ERL, RATE_ERL = 3, 20.0
lx = RATE_ERL * 0.2
erl_cdf_02 = 1 - sum(math.exp(-lx) * lx ** i / math.factorial(i) for i in range(K_ERL))

sample = rng.gamma(K_ERL, 1 / RATE_ERL, N_SAMPLE)
print(f"P(X <= 0.2) {erl_cdf_02:.6f}    scipy {stats.gamma.cdf(0.2, K_ERL, scale=1 / RATE_ERL):.6f}   (R printed 0.762)")
print(f"sample mean {sample.mean():.4f}   k/lambda = {K_ERL / RATE_ERL}")
''')

md(r"""
## Normal

Mean 50, standard deviation 10. The CDF has no elementary formula; it is written with the error
function, which every language ships:

$$P(X \le x) = \tfrac12\left[1 + \operatorname{erf}\!\left(\frac{x-\mu}{\sigma\sqrt2}\right)\right]$$
""")
code(r'''
MU_N, SD_N = 50.0, 10.0
norm_cdf_40 = 0.5 * (1 + math.erf((40 - MU_N) / (SD_N * math.sqrt(2))))

sample = rng.normal(MU_N, SD_N, N_SAMPLE)
print(f"P(X <= 40) {norm_cdf_40:.6f}    scipy {stats.norm.cdf(40, MU_N, SD_N):.6f}   (R printed 0.159)")
print(f"sample mean {sample.mean():.3f}   sd {sample.std(ddof=1):.3f}")
''')

md(r"""
## Log-normal

A log-normal is a variable whose *logarithm* is normal, so its CDF is the normal CDF of $\ln x$.
The two parameters are the mean and standard deviation of that logarithm, not of the variable.
""")
code(r'''
MEANLOG, SDLOG = 0.8, 0.3
lnorm_cdf_3 = 0.5 * (1 + math.erf((math.log(3.0) - MEANLOG) / (SDLOG * math.sqrt(2))))

sample = rng.lognormal(MEANLOG, SDLOG, N_SAMPLE)
print(f"P(X <= 3) {lnorm_cdf_3:.6f}    scipy {stats.lognorm.cdf(3.0, SDLOG, scale=math.exp(MEANLOG)):.6f}   (R printed 0.84)")
print(f"sample mean {sample.mean():.3f}   exp(meanlog + sdlog^2/2) = {math.exp(MEANLOG + SDLOG ** 2 / 2):.3f}")
''')

md(r"""
## Three the formulas do not cover

Chi-squared, $F$ and Student's $t$ have no elementary CDF; the course's notebook read them from R
and this one reads them from scipy. What they *are* is worth holding on to: a chi-squared with $d$
degrees of freedom is a sum of $d$ squared standard normals; an $F$ is a ratio of two chi-squareds
each divided by its degrees of freedom; a $t$ is a standard normal divided by the square root of a
chi-squared over its degrees of freedom. Check the first of those by construction.
""")
code(r'''
dof = 20
by_construction = (rng.standard_normal((N_SAMPLE, dof)) ** 2).sum(axis=1)
print(f"chi-squared(20): P(X <= 25) scipy {stats.chi2.cdf(25, dof):.6f}   (R printed 0.799)   "
      f"fraction of constructed draws <= 25: {(by_construction <= 25).mean():.4f}")
print(f"F(20, 30):       P(X <= 1.5) scipy {stats.f.cdf(1.5, 20, 30):.6f}   (R printed 0.846)")
print(f"t(10):           P(X <= 2)   scipy {stats.t.cdf(2.0, 10):.6f}")
''')

md(r"""
## The empirical CDF against the formula

Sort a sample and plot the fraction below each value: that is the empirical CDF, and with 10,000
draws it should sit on top of the formula. Where would you expect it to deviate most?
""")
code(r'''
sample = np.sort(rng.normal(50, 10, N_SAMPLE))
ecdf = np.arange(1, N_SAMPLE + 1) / N_SAMPLE
grid = np.linspace(10, 90, 200)
plt.plot(sample, ecdf, ".", ms=2, label="empirical")
plt.plot(grid, [0.5 * (1 + math.erf((g - 50) / (10 * math.sqrt(2)))) for g in grid], "k-", lw=1, label="formula")
plt.legend(); plt.title("Normal(50, 10): empirical CDF of 10,000 draws"); plt.show()
print(f"largest gap between the two: {np.max(np.abs(ecdf - stats.norm.cdf(sample, 50, 10))):.4f}")
''')

md(r"""
---

## The central limit theorem

Take a population that is nothing like a bell: exponential with mean 4, skewed hard to the right.
Draw samples of size 30, 100 and 1000 from it, a thousand times each, and average every sample.

Predict before running: the mean of the sample means (all three sizes), and the standard deviation of
the sample means for each size. The population's standard deviation is also 4.

This section gets its own generator, seeded and printed, so the check at the bottom can reproduce
the table exactly.
""")
code(r'''
POP_MEAN = 4.0
CLT_SEED = SEED + 1
rng_clt = np.random.default_rng(CLT_SEED)
print("CLT seed:", CLT_SEED)
population = rng_clt.exponential(POP_MEAN, N_SAMPLE)
print(f"population: mean {population.mean():.3f}   sd {population.std(ddof=1):.3f}   (theory: {POP_MEAN} and {POP_MEAN})")

SIZES = (30, 100, 1000)
K = 1000                      # samples of each size
means = {}
for size in SIZES:
    draws = rng_clt.choice(population, size=(K, size), replace=True)
    means[size] = draws.mean(axis=1)

print(f"\n{'n':>5} {'mean of means':>14} {'sd of means':>12} {'sigma/sqrt(n)':>14}")
for size in SIZES:
    print(f"{size:5} {means[size].mean():14.4f} {means[size].std(ddof=1):12.4f} {population.std(ddof=1) / math.sqrt(size):14.4f}")
''')

md(r"""
Ten times the sample bought how much of the spread — and why $\sqrt{n}$ rather than $n$? Now look at
the shapes.
""")
code(r'''
fig, axes = plt.subplots(1, 4, figsize=(14, 3))
axes[0].hist(population, bins=40, color="lightblue"); axes[0].set_title("population: exponential")
for ax, size in zip(axes[1:], SIZES):
    ax.hist(means[size], bins=30, color="lightgreen"); ax.set_title(f"means of samples of {size}")
plt.tight_layout(); plt.show()
''')

md(r"""
The population is skewed; the averages of thirty are already nearly symmetric; the averages of a
thousand are a spike. What would you have to know about a population for this *not* to happen?

---

# Now the streamlined version

Thirteen formulas have been typed by hand above, and a course's worth of homework would type them
again; that is the moment to keep them in one place. `orteach.distributions` holds each of them once,
in the R convention, with the log form where the direct form overflows or underflows. `sample_means`
draws the CLT samples from a seeded generator in the same order this notebook did.
""")
code(r'''
from orteach import distributions as dist

print(f"nbinom cdf(1600; {R_NB}, {P_NB}) {dist.nbinom_cdf(1600, R_NB, P_NB):.6f}   geom cdf(40; {P_GEOM}) {dist.geom_cdf(40, P_GEOM):.6f}")
print(f"poisson cdf(25; {LAM_POIS:.0f}) {dist.poisson_cdf(25, LAM_POIS):.6f}   exponential cdf(0.2; {RATE_EXP:.0f}) {dist.exponential_cdf(0.2, RATE_EXP):.6f}")
print(f"erlang cdf(0.2; {K_ERL}, {RATE_ERL:.0f}) {dist.erlang_cdf(0.2, K_ERL, RATE_ERL):.6f}   normal cdf(40; {MU_N:.0f}, {SD_N:.0f}) {dist.normal_cdf(40, MU_N, SD_N):.6f}")
''')

md(r"""
## The agreement assertion

Every value computed by hand above — the variables themselves, not retyped — against the package's
formula called with the same knobs, so an edit to any parameter above reaches both sides. Then the
CLT table's sample means against `sample_means` driven by a generator seeded to `CLT_SEED` and drawn
in the same order. The formulas are deterministic and the generator is seeded, so agreement to
`AGREEMENT_RTOL` — in practice, to the last bit — is what must hold.
""")
code(r'''
checks = [("binomial pmf(25)", binom_pmf_25, dist.binom_pmf(25, N_BINOM, P_BINOM)),
          ("binomial cdf(30)", binom_cdf_30, dist.binom_cdf(30, N_BINOM, P_BINOM)),
          ("nbinom pmf(1500)", pmf_1500, dist.nbinom_pmf(1500, R_NB, P_NB)),
          ("nbinom cdf(1600)", cdf_1600, dist.nbinom_cdf(1600, R_NB, P_NB)),
          ("geom pmf(25)", geom_pmf_25, dist.geom_pmf(25, P_GEOM)),
          ("geom cdf(40)", geom_cdf_40, dist.geom_cdf(40, P_GEOM)),
          ("poisson pmf(20)", pois_pmf_20, dist.poisson_pmf(20, LAM_POIS)),
          ("poisson cdf(25)", pois_cdf_25, dist.poisson_cdf(25, LAM_POIS)),
          ("exponential cdf(0.2)", exp_cdf_02, dist.exponential_cdf(0.2, RATE_EXP)),
          ("exponential q95", exp_q95, dist.exponential_quantile(0.95, RATE_EXP)),
          ("erlang cdf(0.2)", erl_cdf_02, dist.erlang_cdf(0.2, K_ERL, RATE_ERL)),
          ("normal cdf(40)", norm_cdf_40, dist.normal_cdf(40, MU_N, SD_N)),
          ("lognormal cdf(3)", lnorm_cdf_3, dist.lognormal_cdf(3.0, MEANLOG, SDLOG))]

rng_pkg = np.random.default_rng(CLT_SEED)                 # the CLT section's generator, from the same seed
pop_pkg = rng_pkg.exponential(POP_MEAN, N_SAMPLE)
for size in SIZES:
    packaged = dist.sample_means(pop_pkg, size, K, rng_pkg)
    checks.append((f"CLT sd of means, n={size}", means[size].std(ddof=1), packaged.std(ddof=1)))
    checks.append((f"CLT first mean, n={size}", means[size][0], packaged[0]))

worst = max(rel_diff(h, k) for _, h, k in checks)
print(f"{len(checks)} comparisons")
for name, hand, packaged in checks[:5]:
    print(f"  {name:22} hand {hand:12.6f}   package {packaged:12.6f}   rel {rel_diff(hand, packaged):.2e}")
print("  ...")
assert worst < AGREEMENT_RTOL, f"notebook and package disagree by {worst:.2e}"
print(f"\nnotebook and package agree to {worst:.1e}")
''')

md(r"""
---

## Where to take this next

- The negative binomial with $r = 500$ failed in two ways at once. Find the smallest $r$ at which
  the direct formula first *raises* at its own mean, and separately the smallest $r$ at which
  $p^r(1-p)^x$ alone first rounds to zero there. Which arrives first, and why are they different
  kinds of failure?
- Replace the exponential population in the CLT section with a Bernoulli($0.02$) population — mostly
  zeros. How large does $n$ have to be before the averages look normal? Why does skew matter?
- The empirical CDF's largest gap from the formula shrinks with the sample. Plot that gap against
  $n$ for $n = 100, 1000, 10000, 100000$, on log axes, and read off the exponent.
""")

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                   "language_info": {"name": "python", "version": "3.13"}}, "nbformat": 4, "nbformat_minor": 5}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    f.write("\n")
print("wrote %s  (%d cells)" % (OUT, len(cells)))
