# Prompt for the next session

Everything a cold session needs is on disk: `REVIEW_QUEUE.md` holds both reviews verbatim with a
status line per finding, `CLAUDE.md` Part 11 holds this library's conventions, and `git log` holds
the defect record. This file is just the starting message, kept here so it survives a moved folder
or a lost chat.

**The short version**, if you would rather not paste the whole block — any session opened in this
folder can be started with one line:

```
Read NEXT_SESSION_PROMPT.md in this repository and do what it says.
```

---

## This repository's review queue is closed

**All twenty-four findings are fixed** and all five reviewed notebooks re-executed and pushed.
`REVIEW_QUEUE.md` has the status table and the verbatim reports; `git log` has the defect record.

The last nine (B1–B9, on `06` and `13`) were closed on 2026-09-06. Two were wrong answers rather
than presentation: `smallest_feasible_share` returned a share at which no plan exists on any instance
but the shipped one, and `13`'s agreement cell compared the wrong objective and would turn red
against a correct package as soon as a reader edited the table. One finding, **B3, was fixed on a
different diagnosis than the reviewer gave** — their mechanism did not reproduce, and the section in
`REVIEW_QUEUE.md` above the verbatim reports says what actually does.

State as of that commit: 175 tests pass, `tools/check_notebooks.py` is clean on all seventeen
notebooks, `tools/check_seeds.py` on all eleven seeds.

---

# The energy-system series has its own repository, and it is public

**Updated 2026-09-24. The twelve notebooks are finished; the seven new ones are not.**

    sear-labs/energy-system-modeling     PUBLIC since 2026-09-13, at 0f5f2c7
    dev/repo/teaching/energy-system-modeling

    13 notebooks, all executing clean       11 modules in src/esm/       232 tests
    agreement-assert   13/13                tolerance-named   13/13

Twelve notebooks and thirteen tools came out of the private course folder with **fresh history**,
and nothing else did. The exams, the Canvas quiz backup and the CARES manuscript stayed where they
are. It was a copy, not a move — that folder is unchanged.

The thirteenth notebook is new: `notebooks/p0_start/00_start_here.ipynb`, a front door that
teaches nothing. It runs every model from the package on fixed data with no student-facing blank,
which is why it was the one notebook publishable without any assignment-exposure question.

## Read the plan, not this file, for what happens next

**`ENERGY_SERIES_PLAN.md` has moved into that repository, and it is the specification.** It carries
the chapter mapping checked against the manuscript, the layout, the seven notebooks still to write,
the vendored-data licence table, and the prompts for sessions 2 through 6 with session 1 marked
done and its three departures recorded.

> **This file failed to name the plan for a day, and it cost a session's opening.** The plan was
> committed here at 06:49 on 2026-09-06, an hour after this handoff was first written. This handoff
> was then edited again at 22:35 — and still did not mention it. So a session told to read only
> this file set out to derive a repository name and a layout that the plan had already settled, and
> got as far as asking Jones to choose a name before he said *check the github, didn't I already do
> this*. He had. The plan was the thing he remembered.
>
> **A handoff that does not name its specification is worse than no handoff, because it reads as
> complete and stops the search.** If you add a scope to this file, name the document that governs
> it in the same edit.

**Sessions 2 through 5 are done.** All twelve execute clean, each ends with an agreement
assertion against an independent implementation in `src/esm/`, and the data-licence questions the
plan listed are settled (see the plan and `data/vendor/README.md`). **What remains of the plan is
the seven notebooks it names as NEW** — `screening_curves`, `cost_of_transit_by_mode`,
`storage_duration_sizing`, `depot_charging`, `feeder_hosting_capacity`, `pipeline_pressure_and_n1`,
`process_heat_electrification`. None exists. That is the largest open item in the series by a wide
margin, and the plan, not this file, specifies them.

## Settled on the way, so nobody reopens it

- **Name and visibility — settled and acted on.** `energy-system-modeling`, public since
  2026-09-13 on Jones's explicit instruction. Colab badges ship and resolve. Two things were
  decided to get there and should not be reopened from this file alone: the four worked-example
  assignments (SB3, SB6, GRAD-M, GRAD-N) were ruled publishable, and `case_ACTIVSg2000.m` is
  vendored and redistributed — its sidecar carries the full licence position and a two-step
  reversal.
- **Twelve notebooks crossed, not the thirteen the plan's own session-1 prompt asked for.**
  `M0_Toy_LP_to_PyPSA` stayed behind because `notebooks/12_energy_systems_pypsa` here **is** it,
  executed and verified. The new repository's `p1_foundations/README.md` points at it rather than
  keeping a second copy with nothing comparing them.
- **`build_m0.py` through `build_m4.py` and `build_m5_deck.py` are PowerPoint builders** and must
  never be brought over; they pull in six local helpers. `check_builders.py` globs
  `build_*notebook*.py`, which is the reliable test and selects exactly the right twelve.
- **No FERPA problem and no credentials**, re-verified on the copied tree rather than on the source.
  Every Gurobi mention is the same empty `WLS = {}` placeholder.
- **Everything is executed, and the package exists.** That bullet used to read "still nothing is
  executed, and no package yet"; it was session 2's starting line and is now three weeks out of
  date. `tools/check_notebooks.py` reports the current state at any time and is the thing to run
  rather than a number written here.

## Still Jones's call

**Whether the private course folder gets a remote of its own.** It is 2.9 GB with no remote, so
OneDrive is its only off-machine backup and the local mirror is redundancy rather than backup. The
separated gitdir fixed corruption risk, not durability — and this session changed nothing about it.

---

## Harvest note — 2026-09-24

The session that finished the energy-system notebooks was harvested and archived on this date.
**Nothing of it lives only in a chat.** Where its state went:

| what | where it lives now |
|---|---|
| what each change did, and the defect it fixed | the twelve commit messages in `energy-system-modeling`; this repo's convention is that the commit carries the defect record |
| why each package module solves a second way | the module docstrings in `src/esm/` |
| the current audit state | run `tools/check_notebooks.py`; no file records it, on purpose |
| what is still to build | `ENERGY_SERIES_PLAN.md` in that repository — the seven NEW notebooks |
| the licence position on vendored data | `data/vendor/README.md` and the per-file sidecars |
| repository status and visibility | the block above |

**Parked deliberately, not forgotten:** alt text for `06_end_use_disaggregation`,
`15_real_network_import` and `17_pipeline_transport` — eight descriptions. The CARES book's
figure manifest covers none of those three, so it is new work rather than reuse; Jones assigned
it to a figures session.

**One inference went to the carry-forward queue** (`yamierick/claude-notes`, c7dc10b) rather than
here, because it is a candidate rule and not a fact about this repository: *a check that cannot
fail is worse than no check, because it reads as coverage.* Four instances in one session, each
caught by a printed number rather than by review or by the suite.

---

## Still open in this repository, beyond the closed queue

- Second notebooks for `05` (Gandhi cloth fixed charge, Portfolio logic) and `07` (bakery
  VSS/EVPI). The server farm and VaR/CVaR landed in `07` on 2026-10-27.
- Roughly 140 files in the original migration queue were never classified or read.
- ~~`README.md` and `notebooks/12_energy_systems_pypsa/README.md` point at REE 4301 by its
  OneDrive path.~~ **Done.** Both carry the GitHub URL, and since 2026-09-13 it resolves for
  anyone rather than 404ing.
- Rotate the Gurobi WLS key. Nothing here needs it, but it is still live in shared Drive copies.
- Rotate nothing on account of the two course folders in OneDrive: their `.git` trees were moved to
  separated gitdirs on 2026-09-06 and the worktrees stay synced on purpose. What remains open for
  both is durability, not corruption — see the backup question above.

*(Closed since the last edit: the stale `Documents\Classes\Advanced Opt Modeling Examples` copy is
gone, the two OneDrive repositories no longer carry a synced `.git`, and the REE series scope that
filled this file is now a repository with a plan of its own.)*
