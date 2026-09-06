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

# The scope now: build the REE 4301 series as its own repository

Under the boundary decided in `CLAUDE.md` Part 11, REE 4301 is a **series** — its modules run over
one energy system in order — so it gets its own repository rather than folding in here.

**It is worth putting a strong model on this**, and the reason is specific rather than general. The
recurring hard problem across both reviews of this library was **non-uniqueness**: every serious
finding was an assertion that held because the solver is deterministic rather than because the answer
is unique. A1, A2, B1, B2 and B4 are all that same defect wearing different clothes. The REE models
are larger networks than anything here, so ties and degenerate duals are more likely, not less. The
package boundary and the first agreement assertions are where that judgement is spent; the prose and
the nits are not.

## Where it is, and what it is

    C:\Users\jonesec\OneDrive - UT Arlington\Documents\Classes\REE 4301 - Energy System Modeling

Checked 2026-09-06: working tree clean, **no remote**, 49 commits, last one 2026-09-05 23:35. The
parallel session that was committing to it appears to have stopped — nothing has touched it since.
A bare mirror exists at `C:\dev\mirrors\Classes-REE-4301-Energy-System-Modeling.git`, on the same
disk, which is redundancy and not backup.

**The series repository needs fresh history, not a push of that one.** Three blockers, none of them
privacy:

1. **Twenty-four exam files** are tracked there — mini-exam banks in text and QTI form, undergraduate
   and graduate variants, plus a Canvas backup holding the full question content of six quizzes.
   They are live for a course being taught now. Publishing retires them.
2. **Ninety-four files of the CARES book**, an in-progress manuscript with a versioned archive.
   Publishing it as a side effect of pushing notebooks is not a decision anybody made.
3. **It would fail Part 5 on its first commit.** Measured 2026-09-06: all thirteen notebooks are
   unexecuted, **207 code cells and zero outputs**. Five carry no assertion at all (`M0B_Model_Boundary`,
   `M3_Transport_Companion`, `SB1`, `SB2`, `SB3`) — the earlier note said four; it is five. There is
   no package for an agreement assertion to compare against.

Filtering the working tree is not enough: the exams and the book are in the 48-commit history.

## What the new repository takes, and what stays behind

The thirteen notebooks in `2026 Fall/Notebooks/`, and **the notebook builders only** from `Tools/`.
That folder has 92 files and the distinction matters, because the same directory holds the material
that must stay private:

| takes | stays in the private course folder |
|---|---|
| `build_m0.py` … `build_m5_notebook.py`, `build_sb*_notebook.py`, `build_1n_notebook.py`, `build_grad_*_notebook.py`, `build_toy_lp_notebook.py`, `build_powerflow_notebook.py`, `build_transport_notebook.py`, `build_supplychain_notebook.py`, `build_boundary_notebook.py`, `check_builders.py` | `build_exam_sections.py`, `build_rubrics.py`, `export_to_canvas_rubrics.py`, `build_canvas_instructions.py`, `canvas_*.py`, `build_book_edits.py`, `build_assignments.py`, `build_task_docs.py`, the deck tooling |

So the work is: a new repository from those notebooks and builders, with **fresh history**; the
notebooks executed and verified, which is where the defects will be, as they were in every subject
here; and a package for them to check against.

Notebook `12` in this library is that series' Module 0 and was verified by running it. **The other
twelve never have been.**

## Two things to settle before touching the folder

Both are Jones's calls, not a session's:

- **Moving it out of OneDrive.** It is 2.9 GB with no remote, so OneDrive is currently its only
  off-machine backup. A move needs a backup decided first. Verify any move by comparing
  `HEAD^{tree}`, never checked-out files — CRLF makes identical objects look different.
- **Whether the private course folder gets a remote of its own**, which is the real answer to the
  backup question but is a separate decision from publishing the notebooks.

## What was already checked, so nobody re-runs it

**No FERPA problem, and no credentials** — established by opening the files, not by pattern-matching
filenames. The twenty Canvas CSVs are rubric *definitions*. The rubric backup's `assessments` array
is empty. In the quiz backup, "student" and "submission" occur only inside Canvas API endpoint URLs
and permission strings. No rosters, gradebooks, submissions, names, IDs, logins, emails or scores.
No credential in the working tree or in any of the 48 commits; the Gurobi cells name three secrets
and contain none, and the Canvas scripts read their token from the environment.

> **A privacy question cannot be cleared against the Code Standard.** That document has zero
> occurrences of FERPA, student record, education record, PII, personally identifiable, privacy or
> data governance across its 1,615 lines — verified 2026-09-05. It governs how code is written and
> has no jurisdiction over a federal privacy statute, so its silence is not clearance: the same
> check returns "fine" on a repository that does hold a gradebook. **Open the files.** The rule this
> library actually operates under came from Jones directly — student work is fine to hold privately,
> and only publication crosses the line.

## House rules that will bite in the new repository

The same ones that bit here, and the reason the split above puts a strong model on this half:

- Tables live in `data/raw/` and both sides read them; a knob the prose names is passed to the
  package, not typed twice.
- **Where an optimum is not unique, the check compares what every optimum shares and the prose
  teaches the tie.** It never compares the solver's path. This is the one that keeps going wrong.
- The commit message carries the defect record: which source was wrong, and what the notebook does
  now. That record is the point of the work.
- Never commit a credential. The Gurobi WLS key in the older course copies **has not been rotated**,
  so do not reuse any key found there.

---

## Still open in this repository, beyond the closed queue

- Second notebooks for `05` (Gandhi cloth fixed charge, Portfolio logic) and `07` (server-farm
  two-stage LP, bakery VSS/EVPI).
- Roughly 140 files in the original migration queue were never classified or read.
- `README.md` and `notebooks/12_energy_systems_pypsa/README.md` still point at REE 4301 by its
  OneDrive path, because that repository has no remote. **Replace both with the URL once it is
  pushed** — that is the last thing the REE work should do.
- Rotate the Gurobi WLS key. Nothing here needs it, but it is still live in shared Drive copies.
- `Documents\Classes\Advanced Opt Modeling Examples` still exists — a process held it open during
  the 2026-09-05 move, so the new copy at `C:\dev\advopt-lithiumsc` is a fresh clone rather than a
  move. It is one commit stale and holds 54 ignored files including a `gurobi.lic`. Delete it once
  nothing holds it, after deciding what to keep.
- **Two repositories are still inside OneDrive, deliberately**: `Classes\REE 4301 - Energy System
  Modeling` (2.9 GB) and `Classes\Curriculum Working Folder` (6.6 GB). See the backup question above;
  it applies to both.
