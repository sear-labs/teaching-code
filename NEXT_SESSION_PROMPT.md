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

# The energy-system series now has its own repository

**Session 1 of six is done, 2026-09-07.**

    sear-labs/energy-system-modeling     private, 40 files, first commit 78660d0
    dev/repo/teaching/energy-system-modeling

Twelve notebooks and thirteen tools came out of the private course folder with **fresh history**,
and nothing else did. The exams, the Canvas quiz backup and the CARES manuscript stayed where they
are. It was a copy, not a move — that folder is unchanged.

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

**Session 2 is next**, run in the new repository. Build a durable named kernel — the working
`orteach-energy` one lives under `AppData/Local/Temp` and must not be depended on — then execute all
twelve notebooks as they are and record what breaks, one row each. It is a **diagnostic**: do not
fix content, do not restructure, do not add assertions. Two notebooks fetch over the network and are
expected among the failures.

## Settled on the way, so nobody reopens it

- **Name and visibility.** `energy-system-modeling`, private for now; public once the notebooks are
  executed. Colab badges wait for that, and the README says why rather than shipping badges that
  404 for every student.
- **Twelve notebooks crossed, not the thirteen the plan's own session-1 prompt asked for.**
  `M0_Toy_LP_to_PyPSA` stayed behind because `notebooks/12_energy_systems_pypsa` here **is** it,
  executed and verified. The new repository's `p1_foundations/README.md` points at it rather than
  keeping a second copy with nothing comparing them.
- **`build_m0.py` through `build_m4.py` and `build_m5_deck.py` are PowerPoint builders** and must
  never be brought over; they pull in six local helpers. `check_builders.py` globs
  `build_*notebook*.py`, which is the reliable test and selects exactly the right twelve.
- **No FERPA problem and no credentials**, re-verified on the copied tree rather than on the source.
  Every Gurobi mention is the same empty `WLS = {}` placeholder.
- **Still nothing is executed.** 190 code cells, zero outputs, five notebooks with no assertion at
  all, and no package yet. That is session 2's starting line, and the new README states it up front.

## Still Jones's call

**Whether the private course folder gets a remote of its own.** It is 2.9 GB with no remote, so
OneDrive is its only off-machine backup and the local mirror is redundancy rather than backup. The
separated gitdir fixed corruption risk, not durability — and this session changed nothing about it.

---

## Still open in this repository, beyond the closed queue

- Second notebooks for `05` (Gandhi cloth fixed charge, Portfolio logic) and `07` (server-farm
  two-stage LP, bakery VSS/EVPI).
- Roughly 140 files in the original migration queue were never classified or read.
- `README.md` and `notebooks/12_energy_systems_pypsa/README.md` still point at REE 4301 by its
  OneDrive path. The repository now exists, but it is **private**, so swapping in the URL today
  would hand a public reader a 404 instead of a useless path. **Replace both when it goes public** —
  session 6 of the plan does this, and it is the last thing the energy-series work should do.
- Rotate the Gurobi WLS key. Nothing here needs it, but it is still live in shared Drive copies.
- Rotate nothing on account of the two course folders in OneDrive: their `.git` trees were moved to
  separated gitdirs on 2026-09-06 and the worktrees stay synced on purpose. What remains open for
  both is durability, not corruption — see the backup question above.

*(Closed since the last edit: the stale `Documents\Classes\Advanced Opt Modeling Examples` copy is
gone, the two OneDrive repositories no longer carry a synced `.git`, and the REE series scope that
filled this file is now a repository with a plan of its own.)*
