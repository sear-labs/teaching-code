# Review queue

Two fresh-context reviewers read notebooks `09`, `10`, `12` and `06`, `13` cell by cell on
2026-09-05, reproduced every number by running the package, and ranked what they found. Their
reports are below, verbatim. The status table says what was done about each item; the commit it
names is the record of what changed and why. Earlier reviews (of `01`, `03`, `04`, `05`, `07`,
`08`, `11`, `14`) were applied in full and are recorded only in `git log`.

## Status

The first review's fifteen findings are fixed and the three notebooks re-executed; the second
review's nine are open. `git log` carries what each fix changed and why.

| # | item | where | status |
|---|---|---|---|
| A1 | charging-hour list compared though not unique; standing-loss "tie" story wrong | 12 cells 29-31, 42; `tests/test_energy.py` | fixed |
| A2 | four `row dual` comparisons on a non-unique dual | 10 cells 21-22 | fixed |
| A3 | row LP hardcodes payoffs instead of reading the table | 10 cell 10 | fixed |
| A4 | leave-room: peaker and battery conclusions announced | 12 cell 21 | fixed |
| A5 | leave-room: "Two things to notice" | 10 cell 13 | fixed |
| A6 | exercise 2 promises an event that does not happen | 10 cell 23 | fixed |
| A7 | `DAYS_PER_YEAR` typed on both sides, never passed | 12 cell 32; `energy.py` | fixed |
| A8 | build-cap rule differs between hand and package | 12 cell 32 | fixed |
| A9 | draw-order contract pinned by no test; "exactly" asserted as a tolerance | 09 cell 27; `tests/test_markov_queueing.py` | fixed |
| A10 | "closer to 1 or 3" when L = 2 | 09 cell 17 | fixed |
| A11 | "even though" inverted | 09 cell 17 | fixed |
| A12 | SOC row written additively | 12 cell 25 | fixed |
| A13 | hour 18 also above gas's cost | 12 cell 27 | fixed |
| A14 | first day network loops where Part C wrote generators out | 12 cell 22 | fixed |
| A15 | cosmetics: `np.float64` reprs, `n.buses` dump, literal tolerances in tests, defect story in prose | 09, 10, 12, tests | fixed |
| B1 | "no processor rows" check compares the wrong objective | 13 cell 26 | open |
| B2 | "shadow price is zero" asserts a non-unique dual | 13 cells 14-15; `sourcing.py` | open |
| B3 | box story mis-attributed; exercise premise false (the lower bound is what matters) | 06 curve_fit cells 7, 19, exercise | open |
| B4 | `smallest_feasible_share` wrong in general | `sourcing.py`; `tests/test_sourcing.py` | open |
| B5 | exercise points at an advopt notebook that does not contain the problem | 13 cell 27 | open |
| B6 | leave-room quotes | 06 curve_fit 23; pooling 0, 9, 21, 23; 13 cells 0, 23; `06/README.md` | open |
| B7 | tests: literal tolerances, "exactly one dollar" comment, unpinned local optimum, model built outside the silent env | `tests/test_nonconvex.py`, `tests/test_sourcing.py` | open |
| B8 | Part 3 nits: inline lambda, three-idea heading, silent trailing solves | 06 curve_fit 20; 13 cell 12; pooling 22, 13 cell 22 | open |
| B9 | Part 4 nits: `B1_MIN` derived twice, `ub=200.0`, scipy call not compared, X quality printed, `FLOW_CAP` comment | 06 both; 13 | open |

## Before the first push

Not from the reviews; from reading what the public repository would contain. **Done**, on
2026-09-05:

- `REPO_URL` is `https://github.com/sear-labs/teaching-code` in all seventeen setup cells, and the
  "not published yet" exit is gone.
- The licence cell no longer exits when no Colab Secret is set: it falls back to the size-limited
  licence `pip install gurobipy` ships. Model sizes were measured rather than assumed - the largest
  in the library is 3,001 variables and 3,000 constraints, both in `07`, and everything else is
  under five hundred. So `07` is the one notebook that still needs a licence of its own, and its
  licence cell says so.
- The setup cell prints the package path relative to the repository root, so no committed output
  carries an author's user name or OneDrive path any more.
- The Gurobi licence number is out of the output history. The list above said four commits; scanning
  every commit found six. Redacted with `git filter-repo`, so every hash in this repository changed
  and the ones quoted in `README.md` were remapped.

**Still open:**

- `README.md` and `notebooks/12_energy_systems_pypsa/README.md` point at REE 4301 by its OneDrive
  path, because that repository has no remote. Replace with the URL once it is pushed.
- Rotate the Gurobi WLS key. Nothing here needs it, but it is still live in shared Drive copies.
- **The push itself.** No remote is configured; creating the repository is the owner's to do.

---

## Review of 09, 10, 12 (verbatim)

All the evidence is in. Findings below, ranked; every number and every "not unique" claim was verified by running the package (base env, Gurobi 13.0.2; energy env, Gurobi 13.0.3 / PyPSA 1.3.0 / linopy 0.9.1), not taken from the notebooks.

# Findings, most serious first

**1. `12_energy_systems_pypsa/dispatch_to_pypsa.ipynb` / cells 29–31 and 42 (and `tests/test_energy.py:101`) — the charging-hour list is not unique, and the "tie the standing loss breaks" story is wrong as stated.**
The assertion `assert charging == pkg_day.charging_hours` and the test pin `r.charging_hours == [11, 12, 13, 14, 15, 16]` compare a solver path. With standing loss 0.01, Gurobi Method=2 returns charging hours `[9, 10, 11, 13, 14, 16]` at the identical objective 18132.628875 (Method 0/1 give `[11..16]`). Mechanism: PyPSA charges the StorageUnit `marginal_cost` on discharge only ("Marginal cost of production (discharge) of 1 MWh"), so the energy the loss leaks is replaced by solar that would otherwise be curtailed — stored 176.67 vs 180.33 MWh, curtailment 293.1 vs 289.5 MWh, dispatch 143.02 MWh and SOC at 16 = 160 in both. The standing loss changes the *objective* (by $117.21) but does not make the *schedule* unique. Cell 31's sentence "When a result changes and the objective does not, that is a tie, not a bug." is contradicted by the screen above it ($18,132.63 → $18,015.42). Passes today only because both sides use the same default Method on the same machine — the determinism-not-equivalence failure `tolerance.py` names.
Fix, either: (a) compare what every optimum shares — objective, discharging hours, peaker hours, the 24 prices, SOC at 16 — and rewrite 29–31 to teach that a leak covered by free curtailed solar costs nothing (cell 31's closing question "is the standing loss one?" then honestly answers "no"); or (b) break the tie with a real effect: `marginal_cost_storage` (a holding cost; 0.001 $/MWh/h makes `[11..16]` unique across Methods 0/1/2 with objective 18133.58), added to `energy.Battery` as a fifth knob. Update the test line to match. Discharging hours, peaker hour, prices, builds and the sweep *are* unique across methods, so those comparisons are sound.

**2. `10_game_theory/zero_sum_game.ipynb` / cell 22 (prose in cell 21) — the four `row dual c` comparisons compare a non-unique quantity, contradicting the notebook's own principle.**
Minus the row LP's duals is a column-optimal strategy, which cell 21 and `test_row_lp_duals_are_a_column_strategy` both say is a segment. Verified: Method=0, or Presolve=0 with Method 1 or 2, returns duals `(0, 0, -0.875, -0.125)` (the d = 1/8 endpoint) instead of the notebook's `(0, -0.5, -0.5, 0)`. It passes because hand and package build identical rows in identical order under identical defaults. Fix: drop the four entries (the "hand duals guarantee" check already covers what every optimum shares), or replace them with the shared invariants — duals sum to -1, probability-row dual equals the value — and amend cell 21's "the row LP's duals against the package's".

**3. `10` / cell 10 — the row LP hardcodes the payoff coefficients instead of reading `game.payoff`.**
Contradicts cell 5 ("The model will look entries up by `(row, col)`") and the override comment in cell 6. Verified: `game.payoff["r1","c2"] = 1.0` gives hand 2.5 vs package 2.3333 — the assertion fails pointing at the model. The override the notebook advertises (`["r1","c4"] = 1.0`) and the exercise (`= 4`) happen not to trip it because c4 is non-binding either way, so the divergence is silent for exactly the edits suggested, while the printed constraint table still shows `-1.0 p[r1]` after the reader edited the table. Fix: `game.payoff["r1","c1"] * p["r1"] + game.payoff["r2","c1"] * p["r2"] >= v` per line — still one line per column; the `getRow` print (the lesson cell 11 draws) is unchanged.

**4. `12` / cell 21 — leave-room violation, quoted:** "The cheap thermal unit is too small to cover the evening on its own, so the expensive one has to start." and "that mismatch is the whole reason a battery exists here." Cell 25 then asks the reader to predict "in how many hours will the expensive unit run at all?" — already answered. Fix: pose it as arithmetic: gas 66 MW plus battery 40 MW against a 110 MW peak — decide before solving whether the peaker can stay off.

**5. `10` / cell 13 — leave-room violation, quoted:** "Two things to notice: more columns are tight than the two the mix seems to be balancing between, and the duals are negative numbers that sum to minus one." This is cell 14's output, announced. Fix: "How many columns are tight? What sign do the duals have, and what do they sum to?"

**6. `10` / cell 23, exercise 2 — "Change `payoff["r1","c4"]` to 4 … What happened" — nothing happens.** Verified: maximin 2, minimax 3, v = 2.5, p = (0.5, 0.5); c4 merely stops being tight. If a saddle point was intended, `payoff["r2","c3"] = 3` produces one (value 3 at (r2, c2)). If "a non-binding entry changes nothing" is the intended lesson, the wording should not promise an event. (With #3 unfixed the edit does not even reach the row LP.)

**7. `12` / cell 32 vs `src/orteach/energy.py` — `DAYS_PER_YEAR` is a knob typed in both places and never passed.** Cell 31 explains it ("divided by 365"), which makes it a knob under Part 4, but `day_network`, `solar_built` and `envelope_breakeven` all read the module constant; a reader who changes it sees the assertion fail. Fix: `days_per_year=365.0` argument on those three; notebook passes `DAYS_PER_YEAR`.

**8. `12` / cell 32 vs `energy.day_network` — build-cap rule differs.** Hand: `p_nom_max` only when `t.varies`; package: whenever `p_nom_max > 0`. Same result for this table; diverges silently if a reader gives gas a cap in the CSV. Mirror the package's rule.

**9. `09_queueing_and_markov/markov_and_queues.ipynb` — the exact-agreement claim rests on a draw-order contract no test pins.** `test_simulation_is_reproducible_and_near_the_formula` compares the package with itself. Interleave the draws in `simulate_mm1` and the suite stays green; only re-executing the notebook fails. Add a test that draws interarrivals then services from `default_rng(seed)`, runs the recursion, and asserts `==` against `simulate_mm1`. Also the notebook says "must match exactly" (cell 27) but asserts `< AGREEMENT_RTOL`; asserting `Wq_sim == pkg_sim.Wq` would make the claim what is asserted.

**10. `09` / cell 17 — "Predict L … is it closer to 1 or to 3?"** L = 2 exactly, equidistant: an accidental trick question. Ask "below 1, between 1 and 2, or above 2?".

**11. `09` / cell 17 — "The chain starting in A takes longer than one starting in D even though A cannot reach C directly and D can."** The "even though" is inverted: A not reaching C directly *explains* A taking longer. The tension worth pointing at is that D goes to A (the slowest start) half the time and is still the fastest start.

**12. `12` / cell 25 — the SOC row is written additively:** "E(t) = E(t-1) + η_c P_charge − P_discharge/η_d, minus the standing loss". PyPSA's row is E(t) = (1−ℓ)E(t−1) + …; the loss multiplies the carried-over energy (the printed table confirms it: hour 17 = 0.99×160 − 18.8/0.927 = 138.1). Write it multiplicatively.

**13. `12` / cell 27 — "evening prices from hour 20 on … above gas's $22.14"** — hour 18 (22.36) is also above. Say "hours 18 and 20–22". For the instructor's benefit: the prices are 22.14/0.99^k for k hours after 17 (22.36, 22.82, 23.05, 23.28, verified to the cent) — the standing loss compounding on a MWh that could have been discharged at 17 instead.

**14. `12` / cell 22 — Part 3's named don't:** "Looping over technologies whose parameters each have different reasoning is not [fine] — write them out." The first day network loops over `techs` with an `if t.varies` branch, after Part C wrote the two generators out by hand. Write the three `n2.add` lines out here; cells 32/38 may loop. Low, because the loop reads a loaded table.

**15. Low / cosmetic:** `10` cell 11 carries the four-term-folder defect story in student-facing prose (the repo says the defect record is the git log; keep "look at the coefficients before you solve"). `10` cell 14 prints `slack -0.500` for a non-binding ≥ row without explaining Gurobi's rhs−activity sign. `09` cells 10/16 print `np.float64(...)` reprs. `12` cell 10 dumps all 14 default columns of `n.buses`. `09` cell 1 says Colab installs gurobipy while cell 0 says no solver is used (`orteach/__init__.py` is empty, so nothing needs it; harmless given the uniform-setup-cell convention). Tolerance literals in tests (`1e-12` at `tests/test_markov_queueing.py:60,67`; `1e-6` at `tests/test_energy.py:104-105`, which is `FEASIBILITY_ATOL` by another name) against the repo's "named in `orteach.tolerance` and nowhere else"; the checker audits only notebooks.

# Right, and should not be changed

- Every number in the three notebooks checks by hand: `09` — P², P³, the 7/18–6/18–5/18 steady state, 29/72, absorption times 4.566/3.3208/3.283 (three linear equations), all six M/M/1 measures, M/M/2 (P0 = 1/2, Lq = 1/12, Wq = 1/24, W = 3/8, L = 3/4, ratio 1/16), the geometric P(n); `10` — maximin 2, minimax 3, v = 2.5, p = (½, ½) is the unique row optimum (the lower envelope has one maximum), the segment formula, c1 dominated, and the segment is the *whole* column-optimal set (summing the two row constraints forces q1 = 0); `12` — $1,328.40 and $22.14, the SOC column reproduces PyPSA's row hour by hour, nodal balance holds every hour, the day cost matches a hand tally to rounding, the envelope (8.24 MWh, $182.34, $66,553), builds and sweep values are unique across Methods 0/1/2 (gas 74.373; solar 3.535/29.285/78.17/92.94), and the model's break-even lying between 83k and 90k against the envelope's 66.6k is real and pinned.
- `09` seeds: the draw order is genuinely identical to `simulate_mm1` (N interarrivals, then N services, one `default_rng(SEED)`, same recursion, same means), the seed is printed in cell 24 and echoed from the package in cell 26, and agreement is 0.0.
- `12` tolerances: verified by spying on `gurobipy.Model.setParam` that linopy 0.9.1 sets all six `GUROBI_PARAMS` and uses the notebook's `env` for both `read` and `Model`; the notebook's `SOLVE` is the same dict as `energy.solve_options(env)`. The PyPSA solves are at the same tightened tolerances as the gurobipy one.
- Tables loaded by both sides in all three, with override comments; knobs (LAM, MU, C, SEED, N_CUSTOMERS, the battery's four plus cycle cost, AVAILABLE/COST/DEMAND, CAPEX_SWEEP) are passed to the package; `AGREEMENT_RTOL`/`rel_diff` imported, no literal thresholds.
- No licence banner or number in any output; both solving notebooks start the env silent.
- Predict prompts precede every solve and the first random draw; no def/class/lambda before the heading; markdown above every code cell; longest cell 29 lines; 168 tests pass (5 PyPSA skips in base) and `tools/check_notebooks.py` is clean on all 17.
- `10` cells 17–19 teach the column-side degeneracy and compare guarantees rather than vectors — keep, and extend the same treatment to the duals (#2). `09` cell 25, `12` cells 27, 37 and 39 build to a question and stop, as Part 3 asks.

Nothing here is a wrong answer shipped to a student; the two serious items are agreement assertions that hold by solver determinism rather than by uniqueness, which is precisely what the library's own conventions say they must not do.

---

## Review of 06, 13 (verbatim)

Everything I need is in hand. Summary of the evidence, then the ranked list.

**Verification run:** `pytest` 168 passed / 5 skipped; `tools/check_notebooks.py` 17/17 ok. The `�` glyphs in my dump are U+2014 em dashes mangled by the console, not a file defect. No licence number, banner or secret appears in any output (the only 6-digit strings are `4.807586`). Every number quoted in prose matches an output in the same notebook. Gurobi here is 13.0.2.

## Ranked findings

**1. `13_supply_chain/sourcing_and_resilience.ipynb`, cell 26 — the "no processor rows" comparison compares the wrong number, and a reader's table edit turns it red against a correct package.**
`checks` contains `("no processor rows", m.ObjVal, pkg_loose.objective)`, but by cell 26 `m` has the processor rows back (re-added in cell 22, demand restored, re-solved). I traced the cell sequence in-process: at cell 26 the constraint list includes `processor[China]`, `processor[Domestic]`, and `m.ObjVal` is the *with-rows* 600. It passes only because of the coincidence the notebook exists to teach. With the reader edit the notebook invites (`inst.plants["Cell Plant A"] = 71.0` before cell 8) the assertion fails with "disagree by 1.64e-03" — hand 608 (with rows) vs `pkg_loose` 607 (no rows) — pointing at the model when the package is right. That is Part 4's "a check that punishes experimenting". Fix: in cell 20 store `loose_base = m.ObjVal` and compare that; optionally add `loose`/`tight` from cell 22 against `sourcing.solve(bigger, processor_caps=False/True)`.

**2. Same notebook, cells 14–15 — "its shadow price is zero" asserts a non-unique dual.**
The base LP is degenerate: solving the dual over the optimal face gives `Pi[processor[China]]` anywhere in **[−3, 0]**. Cost with China's capacity at 119 is 603, at 121 is 600 — the left derivative is −3, the right is 0. Gurobi returns 0 under Methods 0/1/2/3/5, so it is stable *on Gurobi*, but the sentence "The processor is at capacity and its shadow price is zero. Both of those are true at once" teaches, in a module about the price of depending on one supplier, that losing a kilotonne of China's refining costs nothing. The standard's prompt block says: where the degeneracy is structural, teach it. Fix: two extra solves (capacity 119 and 121) printed beside the dual, then ask which one the 0 describes; or drop the `Pi` print. `Plan.processor_price` in `src/orteach/sourcing.py` should carry the same caveat.

**3. `06_nonlinear_and_convex/curve_fit_lifting.ipynb`, cells 7, 19 and the first closing exercise — the box story is mis-attributed and one exercise has a false premise.**
Measured on this machine: with `B1_MAX`, `B0_MAX` and the `o_i` upper bounds all set to infinity the proof still closes in 0.07–0.13 s. The one change that reproduces the source's failure is dropping the *lower* bound `B1_MIN = max(volume)+1` to Gurobi's default 0: status SUBOPTIMAL, 100% gap, 80–99k nodes, for both residual signs. So cell 19's "the boxes above are what make the proof take a fraction of a second" is right in aggregate but points the reader at the wrong bound, and cell 7's "the tighter they are the faster the proof" is contradicted here (B1_MAX 5e4: 3828 nodes; 1e6: 1737; 1e8: 2897). The exercise "Set B1_MAX to one million… why does a box the solver never touches at the optimum still cost time?" — it does not (0.08 s, fewer nodes); a student who does it finds nothing. Fix: make it a cell (`b1.LB = 0`, `TimeLimit` a few seconds, print the gap) and rewrite the exercise as "which of the five bounds does the proof actually need? Remove them one at a time."

**4. `src/orteach/sourcing.py`, `smallest_feasible_share` — wrong in general, printed by cell 24 as if it were the answer.**
It only accounts for the largest mine's residual. Mines 120/60/20: function says 0.3333; the package's own `solve` is infeasible at 0.41 and feasible at 0.4167 (exact value 5/12). `test_smallest_feasible_share_is_one_third` pins only the shipped instance, where it happens to be right. Fix: smallest `c` with `Σ min(cap_i, c·D) ≥ D` (sort-and-scan or bisection), plus a test on a perturbed instance.

**5. Sourcing cell 27, third exercise — "Open its `01_deterministic` notebook and find this problem inside it."**
The advopt `01_deterministic` is a six-site network (two mines, two processors, two fabricators), two regions, twenty years, lumpy capacity. This three-mine instance is not in it; only the mine→processor→plant conservation structure is. "The lithium supply-chain models this module grew from" is unverifiable from the repo. Fix: say the structure (the processor balance row) is there, point at `03_network_core` ("built a block at a time"), and drop "grew from" unless known.

**6. Leave-room violations (quotes, by cell).**
- curve_fit 23: "because its stopping rule is not Gurobi's and the parameters sit on a flat ridge" — answers the discussion question cell 21 just posed ("What does that say about the shape of the objective near its minimum").
- pooling 0: "gives it more than one local optimum" — pre-empts cell 21's "one hump, or two?"; pooling 21 heading "Why a local method can get this wrong" and cell 23 "A method that starts on the wrong side climbs to the wrong hump and stops" state the finding.
- pooling 9: "Say why it cannot be written any other way" — false premise (the proportion/Q-formulation is another way; what is true is that every way is a product of two unknowns).
- sourcing 0: "the cheapest plan buys everything from one mine" pre-empts cell 7's prediction; "which is the more useful argument" tells the reader how to feel. Sourcing 23: "agreed on the course's data because total demand happened to equal one processor's capacity exactly" — the explanation, not the question.
- `06/README.md`: "the fit that only over-predicted" spoils cell 17's prediction for anyone who reads the folder README first.

**7. Tests versus the notebooks' claims.**
- `tests/test_nonconvex.py` has seven literal tolerances in asserts (`1e-6` ×4, `1e-4`, `1e-3`, plus `0.1`/`5.0`), `tests/test_sourcing.py` five (`1e-9` ×3, `1e-12`, `1e-3`); repo CLAUDE.md Part 11 says tolerances are named in `orteach.tolerance` and nowhere else, and `tolerance.py`'s own docstring says the `1e-6` literals were what `FEASIBILITY_ATOL` was created to replace. The notebook's cell 24 reuses `FEASIBILITY_ATOL` (a "respects a bound" tolerance) as the scipy-vs-Gurobi objective tolerance; observed gap 1.28e-7 from every start and method, so the 1e-6 margin is 8× — fine, but it wants its own name.
- `test_the_missing_processor_cap_is_only_silent_by_accident` comment says the models "differ by exactly one dollar" but asserts `> 0.5`; the capacity side of the coincidence (China 119 at demand 120 → 603) is not pinned.
- The local optimum at 100 (landscape at q=0.03) is pinned by nothing; the sweep exists only in the notebook. The free-residual SSE is pinned only as `< 5.0`.
- The 14.44 test pins SSE ±1e-3 and b1 ±0.5 — genuinely reproduces what shipped. It builds `gp.Model()` without the silent env, so `pytest -s` prints the licence banner.

**8. Part 3 nits.** curve_fit 20: inline `lambda` before the streamlined heading (the checker only catches named lambdas). sourcing 12: heading lists three ideas, one cell. pooling 22 and sourcing 22 end in a silent `m.optimize()`; the pooling assertion then compares the post-sweep re-solve's values without saying so (harmless only because the optimum is unique).

**9. Part 4 nits.** `B1_MIN` is derived independently in notebook and package rather than passed, so a reader's edit silently doesn't reach the package (assertion stays green). `ub=200.0` on `pr` is an unnamed knob. The hand-built scipy call (cell 20) is never compared to `fit_congestion_scipy`. pooling 24 prints `delivered sulfur : {'X': 0.0, ...}` right after cell 19 said an unmade product's quality means nothing. pooling 7 "a box above the largest demand costs nothing" — a source's pool inflow can legitimately reach the *sum* of demands (300); `FLOW_CAP = 250` is inert only at the shipped prices, and the first exercise changes them.

Nothing here is a wrong answer in a shipped output; items 1–4 are the ones I would fix before students see them.

## Right, and should stay

- Pooling's uniqueness claim (cell 25) is true: pinning profit ≥ 400 − 1e-6 and pushing every flow and `q_pool` to its extremes gives zero-width ranges; three seeds land on the same point. Leaving X's quality out of the comparison is exactly right.
- Sourcing's base plan is unique in every ore and metal flow (and the 75% plan in mine shares); comparing `by_mine` is legitimate.
- The curve-fit parameter comparison is not testing luck: seed, Method, Threads and variable order all reproduce b0, b1 and residuals to ≤1.6e-14; holding scipy to SSE only is the right split. Prose numbers 4.8076, 14.44, second-decimal b1 difference, ratio slack 71,545.3 all check.
- All landscape values (400/300/0/50/100) and the 660/696/720/768/796.8 curve verify by hand; 34% feasible, 33% not.
- Both folder READMEs' advopt pointers resolve: every named notebook and `lithium.games`/`lithium.mpec` exist in the clone.
- Setup and licence cells are identical across the three and correct for the `REPO_URL is None` design; tables load once and are passed as arguments; commented-out override examples, predict prompts, markdown-above-every-cell, no defs, and cells under 40 lines all hold.
