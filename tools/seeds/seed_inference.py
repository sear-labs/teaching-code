"""Seed for the inference-and-regression teaching notebook. Writes the notebook without outputs; execute it afterwards (README.md here)."""
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "notebooks", "14_probability_and_stats", "inference_and_regression.ipynb")
cells = []


def md(t):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": t.strip("\n").splitlines(keepends=True)})


def code(t):
    cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
                  "source": t.strip("\n").splitlines(keepends=True)})


md(r"""
# Tests and regressions, line by line

Every hypothesis test is the same three moves: a statistic computed from the data, a reference
distribution the statistic would follow if the null hypothesis were true, and the tail area beyond
what was observed. R's `t.test` prints those three things and a confidence interval, and hides how it
got them. This notebook computes each one by hand, then calls `scipy.stats` to confirm, on the tests
the course covered: one mean, two means, one variance, two variances, and two chi-squared tests.

The second half is least squares — the normal equations, then everything `summary(lm)` prints — on
a public dataset, so the answers can be checked against what R printed.
""")

md(r"""
## Setup: where the package lives

This notebook builds its models by hand and then checks them against `orteach`, the package in
`src/`. Run from a clone of the repository, `../../src` is right there. On Colab there is no clone
until this cell makes one, and no `gurobipy` until it installs it. Nothing here needs a secret.
""")
code(r'''
import os, subprocess, sys

REPO_URL = "https://github.com/sear-labs/teaching-code"

try:
    import google.colab                      # noqa: F401 - succeeds only on Colab
    ON_COLAB = True
except ImportError:
    ON_COLAB = False

if ON_COLAB:
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
root = os.path.abspath(os.path.join("..", ".."))
print("package:", os.path.relpath(os.path.dirname(orteach.__file__), root))
''')

md(r"""
## The scores are a table

Two exam-score vectors, 22 students each. The course's notebook typed two real class score lists;
these are synthetic ones with the same shape, generated from a printed seed by the package and
stored in `data/raw/`, so both this notebook and the package read the same file. The generating seed
and shape are printed so a reader can regenerate them.
""")
code(r'''
import math
import numpy as np
from scipy import stats
from orteach import inference as inf
from orteach.tolerance import AGREEMENT_RTOL, rel_diff

scores = inf.load_scores()
exam1, exam2 = np.array(scores["exam1"]), np.array(scores["exam2"])
print("generated from seed", inf.SCORES_SEED, "with", inf.SCORES_SHAPE)
print("exam1:", exam1)
print("exam2:", exam2)
print(f"\nexam1 mean {exam1.mean():.3f}  sd {exam1.std(ddof=1):.3f}     exam2 mean {exam2.mean():.3f}  sd {exam2.std(ddof=1):.3f}")

# to try different scores, edit the loaded vectors; the change reaches the package check at the bottom:
# exam2[0] = 95.0
''')

md(r"""
## One mean against a claimed value

Claim: the exam 2 average is 70. The statistic is how far the sample mean sits from 70, in units of
its own standard error; under the null it follows a $t$ with $n - 1$ degrees of freedom.

$$t = \frac{\bar x - \mu_0}{s/\sqrt{n}}$$

Predict before running: with the mean and standard deviation printed above, is $t$ nearer 0 or
nearer 3, and will the p-value be small?
""")
code(r'''
MU0 = 70.0
n = len(exam2)
xbar, s = exam2.mean(), exam2.std(ddof=1)
se = s / math.sqrt(n)
t_stat = (xbar - MU0) / se
df = n - 1
p_two = 2 * stats.t.sf(abs(t_stat), df)                    # both tails beyond |t|
half = stats.t.ppf(0.975, df) * se
print(f"t = {t_stat:.4f}   df = {df}   p (two-sided) = {p_two:.4f}")
print(f"95% CI for the mean: [{xbar - half:.4f}, {xbar + half:.4f}]")
ref = stats.ttest_1samp(exam2, MU0)
print(f"scipy: t = {ref.statistic:.4f}   p = {ref.pvalue:.4f}")
''')

md(r"""
The same statistic, one-sided. Same claim — the average is 70 — but now the alternative is that it
is *less*: only the lower tail counts, and the confidence interval is open on one side. Predict
whether the p-value halves, doubles, or neither.
""")
code(r'''
t_less = (xbar - MU0) / se                                 # the same t as above
p_less = stats.t.cdf(t_less, df)                           # lower tail only
upper = xbar + stats.t.ppf(0.95, df) * se
print(f"t = {t_less:.4f}   p (less) = {p_less:.6f}   two-sided was {p_two:.6f}   95% CI: (-inf, {upper:.4f}]")
ref = stats.ttest_1samp(exam2, MU0, alternative="less")
print(f"scipy: t = {ref.statistic:.4f}   p = {ref.pvalue:.6f}")
''')

md(r"""
## Two means

Did the two exams have the same average? Two versions of the test, differing in one assumption. The
**pooled** test assumes both exams have the same variance and pools the two sample variances; the
**Welch** test does not, and pays for it with a fractional, smaller number of degrees of freedom.
Predict which will give the smaller p-value here, and by how much.
""")
code(r'''
n1, n2 = len(exam1), len(exam2)
v1, v2 = exam1.var(ddof=1), exam2.var(ddof=1)
diff = exam1.mean() - exam2.mean()

sp2 = ((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2)     # pooled variance
se_pooled = math.sqrt(sp2 * (1 / n1 + 1 / n2))
t_pooled, df_pooled = diff / se_pooled, n1 + n2 - 2
p_pooled = 2 * stats.t.sf(abs(t_pooled), df_pooled)

se_welch = math.sqrt(v1 / n1 + v2 / n2)
df_welch = (v1 / n1 + v2 / n2) ** 2 / ((v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1))
t_welch = diff / se_welch
p_welch = 2 * stats.t.sf(abs(t_welch), df_welch)

print(f"difference in means {diff:.4f}")
print(f"pooled: t = {t_pooled:.4f}   df = {df_pooled}       p = {p_pooled:.6f}")
print(f"Welch : t = {t_welch:.4f}   df = {df_welch:.3f}   p = {p_welch:.6f}")
print(f"scipy : pooled p = {stats.ttest_ind(exam1, exam2, equal_var=True).pvalue:.6f}   "
      f"Welch p = {stats.ttest_ind(exam1, exam2, equal_var=False).pvalue:.6f}")
''')

md(r"""
## One variance

Claim: the exam 2 standard deviation is 25. The statistic $(n-1)s^2/\sigma_0^2$ follows a
chi-squared with $n - 1$ degrees of freedom, which is not symmetric — so the two-sided p-value is
twice the smaller tail, and the confidence interval is lopsided.
""")
code(r'''
SIGMA0 = 25.0
chi2_stat = (n - 1) * v2 / SIGMA0 ** 2
p_chi2 = 2 * min(stats.chi2.cdf(chi2_stat, df), stats.chi2.sf(chi2_stat, df))
ci_var = ((n - 1) * v2 / stats.chi2.ppf(0.975, df), (n - 1) * v2 / stats.chi2.ppf(0.025, df))
print(f"chi2 = {chi2_stat:.4f}   df = {df}   p = {p_chi2:.4f}")
print(f"95% CI for the variance [{ci_var[0]:.1f}, {ci_var[1]:.1f}]   (s^2 = {v2:.1f})")
''')

md(r"""
## Two variances

The ratio of the two exams' sample variances follows an $F$ distribution with $(n_1 - 1, n_2 - 1)$
degrees of freedom when the true variances are equal. This is the test that decides which
two-sample $t$ test you should have reported.
""")
code(r'''
f_stat = v1 / v2
p_f = 2 * min(stats.f.cdf(f_stat, n1 - 1, n2 - 1), stats.f.sf(f_stat, n1 - 1, n2 - 1))
print(f"F = {f_stat:.4f}   df = ({n1 - 1}, {n2 - 1})   p = {p_f:.4f}")
''')

md(r"""
## Chi-squared: does a distribution fit?

Bin exam 1 into four grade bands and ask whether the counts match what a Normal with the generating
mean and standard deviation would put in each band — the expected counts come from the normal CDF,
which the distributions notebook derived.

$$\chi^2 = \sum \frac{(O - E)^2}{E}$$

Two conventions to state. The degrees of freedom are bands minus one *because the mean and standard
deviation are known here* (they generated the data); estimated from the sample, they would cost one
degree of freedom each. And the chi-squared approximation is usually trusted only when every
expected count is at least 5; two of these are not, and the notebook goes ahead anyway — say what
you would do about it.
""")
code(r'''
EDGES = [60, 70, 80]                                   # band boundaries; the outer bands are open
observed = np.histogram(exam1, bins=[-1e9] + EDGES + [1e9])[0]
mu, sd = inf.SCORES_SHAPE["exam1"][0], inf.SCORES_SHAPE["exam1"][1]
cdf_at_edges = [0.0] + [0.5 * (1 + math.erf((e - mu) / (sd * math.sqrt(2)))) for e in EDGES] + [1.0]
probs = np.diff(cdf_at_edges)                          # probability the Normal puts in each band
expected = probs * len(exam1)
gof_stat = float(((observed - expected) ** 2 / expected).sum())
p_gof = stats.chi2.sf(gof_stat, len(observed) - 1)
print("bands <60, 60-70, 70-80, >=80")
print(f"observed {observed}   expected {np.round(expected, 2)}")
print(f"goodness of fit: chi2 = {gof_stat:.4f}   df = {len(observed) - 1}   p = {p_gof:.4f}")
print(f"scipy: p = {stats.chisquare(observed, expected).pvalue:.4f}")
''')

md(r"""
## Chi-squared: are two factors independent?

The course's 2 × 3 table of counts. Under independence the expected count in each cell is
(row total × column total) / grand total, and the degrees of freedom are (rows − 1)(columns − 1).
""")
code(r'''
table = np.array([[120, 90, 40], [110, 95, 45]], dtype=float)
exp_table = np.outer(table.sum(axis=1), table.sum(axis=0)) / table.sum()
ind_stat = float(((table - exp_table) ** 2 / exp_table).sum())
p_ind = stats.chi2.sf(ind_stat, (table.shape[0] - 1) * (table.shape[1] - 1))
print(f"independence: chi2 = {ind_stat:.4f}   df = {(table.shape[0] - 1) * (table.shape[1] - 1)}   p = {p_ind:.4f}")
print(f"scipy: p = {stats.chi2_contingency(table, correction=False)[1]:.4f}")
''')

md(r"""
---

## Least squares, by the normal equations

R's `mtcars`: 32 cars from a 1974 magazine, public data, in `data/raw/`. Fuel economy against engine
displacement. With a column of ones for the intercept, the least-squares coefficients solve
$X^\top X \beta = X^\top y$, and everything else in `summary(lm)` follows from the residuals.

Predict the sign of the slope, and whether $R^2$ will be above or below one half.
""")
code(r'''
mt = inf.load_table("mtcars.csv")
disp, mpg = np.array(mt["disp"]), np.array(mt["mpg"])
N = len(mpg)

X = np.column_stack([np.ones(N), disp])
beta = np.linalg.solve(X.T @ X, X.T @ mpg)
fitted = X @ beta
resid = mpg - fitted
df_resid = N - 2
ss_resid = float(resid @ resid)
ss_total = float(((mpg - mpg.mean()) ** 2).sum())
sigma = math.sqrt(ss_resid / df_resid)
se_beta = np.sqrt(np.diag(sigma ** 2 * np.linalg.inv(X.T @ X)))
t_beta = beta / se_beta
p_beta = 2 * stats.t.sf(np.abs(t_beta), df_resid)
r2 = 1 - ss_resid / ss_total
adj_r2 = 1 - (1 - r2) * (N - 1) / df_resid
f_reg = ((ss_total - ss_resid) / 1) / sigma ** 2

print(f"{'':12} {'estimate':>10} {'std error':>10} {'t':>8} {'p':>10}")
for name, b, se_, t_, p_ in zip(("(Intercept)", "disp"), beta, se_beta, t_beta, p_beta):
    print(f"{name:12} {b:10.6f} {se_:10.6f} {t_:8.3f} {p_:10.2e}")
print(f"\nresidual standard error {sigma:.3f} on {df_resid} df   R^2 {r2:.4f}   adjusted {adj_r2:.4f}   F {f_reg:.2f}")
''')

md(r"""
R printed, for this same regression: intercept 29.599855 with standard error 1.229720, slope
−0.041215 with standard error 0.004712, residual standard error 3.251 on 30 degrees of freedom,
$R^2$ 0.7183, adjusted 0.709, $F$ 76.51. Compare line by line.

## Three regressors at once

The same equations with more columns. Nothing changes but the shape of $X$ — which is the point of
writing it as matrices. Predict: does displacement keep its significance once horsepower and weight
are in the model?
""")
code(r'''
hp, wt = np.array(mt["hp"]), np.array(mt["wt"])
X3 = np.column_stack([np.ones(N), disp, hp, wt])
beta3 = np.linalg.solve(X3.T @ X3, X3.T @ mpg)
resid3 = mpg - X3 @ beta3
df3 = N - 4
sigma3 = math.sqrt(float(resid3 @ resid3) / df3)
se3 = np.sqrt(np.diag(sigma3 ** 2 * np.linalg.inv(X3.T @ X3)))
t3 = beta3 / se3
p3 = 2 * stats.t.sf(np.abs(t3), df3)
ss_resid3 = float(resid3 @ resid3)
r2_3 = 1 - ss_resid3 / ss_total
adj_r2_3 = 1 - (1 - r2_3) * (N - 1) / df3
f_reg3 = ((ss_total - ss_resid3) / 3) / sigma3 ** 2

print(f"{'':12} {'estimate':>10} {'std error':>10} {'t':>8} {'p':>10}")
for name, b, se_, t_, p_ in zip(("(Intercept)", "disp", "hp", "wt"), beta3, se3, t3, p3):
    print(f"{name:12} {b:10.6f} {se_:10.6f} {t_:8.3f} {p_:10.4f}")
print(f"\nresidual standard error {sigma3:.3f} on {df3} df   R^2 {r2_3:.4f}   adjusted {adj_r2_3:.4f}   F {f_reg3:.2f}")
''')

md(r"""
Displacement's coefficient collapsed toward zero and lost its significance the moment weight and
horsepower entered. Did displacement stop mattering? How would you check?

## Fit on some cars, predict the rest

R's `cars`: 50 stopping distances against speed. Hold out a fifth of them, fit on the rest, and score
the fit on what it never saw — the root-mean-square error and the mean absolute percentage error on
the ten held-out cars. The split is a seeded permutation, printed so it can be reproduced. Predict
the RMSE before running, from the residual spread of the mtcars fits above.

The course's notebook scored the fit by the correlation between actual and predicted distances.
That number is printed too. Would a different slope change it?
""")
code(r'''
cars = inf.load_table("cars.csv")
speed, dist = np.array(cars["speed"]), np.array(cars["dist"])
SPLIT_SEED = 100
TRAIN_FRAC = 0.8
print("split seed:", SPLIT_SEED)

perm = np.random.default_rng(SPLIT_SEED).permutation(len(speed))
n_train = int(round(TRAIN_FRAC * len(speed)))
train, test = np.sort(perm[:n_train]), np.sort(perm[n_train:])

Xtr = np.column_stack([np.ones(len(train)), speed[train]])
b_tr = np.linalg.solve(Xtr.T @ Xtr, Xtr.T @ dist[train])
pred = b_tr[0] + b_tr[1] * speed[test]
rmse = math.sqrt(np.mean((pred - dist[test]) ** 2))
mape = np.mean(np.abs(pred - dist[test]) / dist[test])
corr = np.corrcoef(dist[test], pred)[0, 1]
print(f"fit on {len(train)} cars: dist = {b_tr[0]:.3f} + {b_tr[1]:.3f} speed")
print(f"held-out {len(test)} cars: RMSE {rmse:.2f} ft   mean absolute % error {mape:.1%}   correlation(actual, predicted) {corr:.4f}")
''')

md(r"""
---

# Now the streamlined version

Eight tests and two regressions have been written out by hand, and every one of them will be needed
again on the next dataset; that is the moment to keep them in one place. `orteach.inference` holds
each one once, in the conventions R reports: `t_one_sample`, `t_two_sample`, `chi2_variance`,
`f_variance_ratio`, `chi2_goodness_of_fit`, `chi2_independence`, `ols` and `split_indices`.
""")
code(r'''
pkg_t = inf.t_one_sample(exam2, MU0)
pkg_less = inf.t_one_sample(exam2, MU0, "less")
pkg_pooled = inf.t_two_sample(exam1, exam2, equal_var=True)
pkg_welch = inf.t_two_sample(exam1, exam2, equal_var=False)
pkg_var = inf.chi2_variance(exam2, SIGMA0 ** 2)
pkg_f = inf.f_variance_ratio(exam1, exam2)
pkg_gof = inf.chi2_goodness_of_fit(observed, expected)
pkg_ind = inf.chi2_independence(table)
pkg_ols = inf.ols(disp, mpg, ["disp"])
pkg_ols3 = inf.ols(np.column_stack([disp, hp, wt]), mpg, ["disp", "hp", "wt"])
pkg_train, pkg_test = inf.split_indices(len(speed), TRAIN_FRAC, SPLIT_SEED)

for r in (pkg_t, pkg_less, pkg_pooled, pkg_welch, pkg_var, pkg_f, pkg_gof, pkg_ind):
    print(f"{r.method:36} statistic {r.statistic:9.4f}   p {r.p_value:.4f}")
print(f"{'ols mpg ~ disp':36} R^2 {pkg_ols.r2:.4f}   F {pkg_ols.f_stat:.2f}")
print(f"{'ols mpg ~ disp + hp + wt':36} R^2 {pkg_ols3.r2:.4f}   adj R^2 {pkg_ols3.adj_r2:.4f}   F {pkg_ols3.f_stat:.2f}")
''')

md(r"""
## The agreement assertion

Every statistic, p-value, interval bound, coefficient and standard error computed by hand above,
against the package. All of it is deterministic arithmetic on the same tables, so agreement to
`AGREEMENT_RTOL` is what must hold.
""")
code(r'''
checks = [("one-sample t", t_stat, pkg_t.statistic), ("one-sample p", p_two, pkg_t.p_value),
          ("one-sample CI low", xbar - half, pkg_t.conf_int[0]), ("one-sample CI high", xbar + half, pkg_t.conf_int[1]),
          ("one-sided t", t_less, pkg_less.statistic), ("one-sided p", p_less, pkg_less.p_value),
          ("one-sided CI high", upper, pkg_less.conf_int[1]),
          ("pooled t", t_pooled, pkg_pooled.statistic), ("pooled p", p_pooled, pkg_pooled.p_value),
          ("Welch t", t_welch, pkg_welch.statistic), ("Welch df", df_welch, pkg_welch.df), ("Welch p", p_welch, pkg_welch.p_value),
          ("variance chi2", chi2_stat, pkg_var.statistic), ("variance p", p_chi2, pkg_var.p_value),
          ("variance CI low", ci_var[0], pkg_var.conf_int[0]), ("variance CI high", ci_var[1], pkg_var.conf_int[1]),
          ("F ratio", f_stat, pkg_f.statistic), ("F p", p_f, pkg_f.p_value),
          ("GOF chi2", gof_stat, pkg_gof.statistic), ("GOF p", p_gof, pkg_gof.p_value),
          ("independence chi2", ind_stat, pkg_ind.statistic), ("independence p", p_ind, pkg_ind.p_value),
          ("simple R^2", r2, pkg_ols.r2), ("simple adj R^2", adj_r2, pkg_ols.adj_r2),
          ("simple F", f_reg, pkg_ols.f_stat), ("simple sigma", sigma, pkg_ols.resid_se),
          ("multiple R^2", r2_3, pkg_ols3.r2), ("multiple adj R^2", adj_r2_3, pkg_ols3.adj_r2),
          ("multiple F", f_reg3, pkg_ols3.f_stat), ("multiple sigma", sigma3, pkg_ols3.resid_se)]
for j in range(2):
    checks.append((f"simple coef {j}", beta[j], pkg_ols.coef[j]))
    checks.append((f"simple se {j}", se_beta[j], pkg_ols.se[j]))
for j in range(4):
    checks.append((f"multiple coef {j}", beta3[j], pkg_ols3.coef[j]))
    checks.append((f"multiple se {j}", se3[j], pkg_ols3.se[j]))
    checks.append((f"multiple p {j}", p3[j], pkg_ols3.p[j]))
assert list(train) == list(pkg_train) and list(test) == list(pkg_test), "the seeded split differs"

worst = max(rel_diff(h, k) for _, h, k in checks)
print(f"{len(checks)} comparisons, plus the split")
for name, hand, packaged in checks[:4]:
    print(f"  {name:20} hand {hand:12.6f}   package {packaged:12.6f}   rel {rel_diff(hand, packaged):.2e}")
print("  ...")
assert worst < AGREEMENT_RTOL, f"notebook and package disagree by {worst:.2e}"
print(f"\nnotebook and package agree to {worst:.1e}")
''')

md(r"""
---

## Where to take this next

- The pooled and Welch tests gave nearly the same answer here. Multiply every exam 2 score by 3 and
  run both again. Now which test would you report, and what did the ratio-of-variances test say
  about it before you looked?
- Add `qsec` to the three-regressor model. Does $R^2$ go up? Does adjusted $R^2$? What is the
  adjustment protecting you from?
- The cars split used one seed. Run it with twenty seeds and look at the spread of the held-out
  RMSE. How much of it is the model, and how much is the draw? Then compute the correlation for a
  deliberately wrong line — `100 + 0.5 * speed` — on the same ten cars, and explain what you see.
""")

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                   "language_info": {"name": "python", "version": "3.13"}}, "nbformat": 4, "nbformat_minor": 5}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    f.write("\n")
print("wrote %s  (%d cells)" % (OUT, len(cells)))
