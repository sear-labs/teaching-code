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

Checked 2026-09-06: working tree clean, **no remote**, 49 commits. A bare mirror sits at
`<dev-root>\store\mirrors\Classes-REE-4301-Energy-System-Modeling.git`, on the same disk, which is
redundancy and not backup.

**The synced-`.git` hazard is already solved for this folder** and needs no decision. Its `.git` is a
one-line pointer file reading `gitdir: <dev-root>/gitdirs/ree4301.git`, so the worktree keeps syncing
and staying backed up while the history sits on local disk where two writers cannot reach it. The
standard documents the arrangement, including that exactly one machine owns the gitdir and the others
are *expected* to fail with `fatal: not a git repository`. `Curriculum Working Folder` is set up the
same way. **Do not "fix" either by moving the worktree.**

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

## Read Part 2c before creating the repository

The standard grew from 1,615 to 2,216 lines between 2026-09-05 and 09-06, and **Part 2c — the life
of a project** is new and governs exactly this task: how a repository is started, named, licensed and
given provenance, and what must never be published. It opens on the thing that makes this go wrong —
opening a session in a folder creates one path-keyed directory and nothing else, so git, the remote,
the `CLAUDE.md` and the `.claude/` exist only because somebody made them. Read it before running
`gh repo create`, not after.

Two other additions land on this work: **accessibility for teaching material**, and the **licensing
and provenance** rules. Neither existed when the plan below was written.

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

## One thing to settle before touching the folder

Jones's call, not a session's: **whether the private course folder gets a remote of its own.** It is
2.9 GB with no remote, so OneDrive is its only off-machine backup and the local mirror is redundancy
rather than backup. That is a separate decision from publishing the notebooks, and the separated
gitdir does not address it — it fixed corruption risk, not durability.

*(The old second item, moving the folder out of OneDrive, is moot: the separated gitdir gets both
properties at once, and moving the worktree would lose the sync backup for nothing.)*

## What was already checked, so nobody re-runs it

**No FERPA problem, and no credentials** — established by opening the files, not by pattern-matching
filenames. The twenty Canvas CSVs are rubric *definitions*. The rubric backup's `assessments` array
is empty. In the quiz backup, "student" and "submission" occur only inside Canvas API endpoint URLs
and permission strings. No rosters, gradebooks, submissions, names, IDs, logins, emails or scores.
No credential in the working tree or in any of the 48 commits; the Gurobi cells name three secrets
and contain none, and the Canvas scripts read their token from the environment.

> **A privacy question cannot be cleared against the Code Standard.** Re-checked 2026-09-06 against
> its current 2,216 lines: FERPA, student record, PII, personally identifiable, privacy and data
> governance still appear zero times. *Education record* now appears once — in Part 2c's **never
> publish** list, which forbids publishing anything adjacent to one and says consolidated
> observations about students qualify even with no name attached.
>
> That is a prohibition, not a test. It tells you what not to publish; it cannot tell you whether a
> given file *is* one, which is the question that actually needed answering here. So the method is
> unchanged: **open the files.** Silence is not clearance, and neither is a prohibition you have not
> checked your files against. The operating rule came from Jones directly — student work is fine to
> hold privately, and only publication crosses the line.

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
- Rotate nothing on account of the two course folders in OneDrive: their `.git` trees were moved to
  separated gitdirs on 2026-09-06 and the worktrees stay synced on purpose. What remains open for
  both is durability, not corruption — see the backup question above.

*(Closed since the last edit: the stale `Documents\Classes\Advanced Opt Modeling Examples` copy is
gone, and the two OneDrive repositories no longer carry a synced `.git`.)*
