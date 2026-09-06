# Prompt for the next session

Everything a cold session needs is on disk: `REVIEW_QUEUE.md` holds the open findings verbatim,
`CLAUDE.md` Part 11 holds this library's conventions, and `git log` holds the defect record. This
file is just the starting message, kept here so it survives a moved folder or a lost chat.

**The short version**, if you would rather not paste the whole block — any session opened in this
folder can be started with one line:

```
Read NEXT_SESSION_PROMPT.md in this repository and do what it says.
```

Paste the longer block below instead when you want the session to start with the scope already in
front of it rather than after a file read.

---

```
Work in Classes\Teaching Code. Read REVIEW_QUEUE.md first, then CLAUDE.md Part 11.
The queue holds two fresh-context reviews verbatim with a status line per finding.

Fix the nine open findings, B1 through B9, on notebooks 06 (curve_fit_lifting,
pooling) and 13 (sourcing_and_resilience). The fifteen A rows are already done.
B1 and B4 are real defects rather than presentation: an agreement check that
compares the wrong objective and turns red against a correct package once a
reader edits the table, and smallest_feasible_share in src/orteach/sourcing.py
giving the wrong answer on any instance but the shipped one. B2 and B3 are
teaching judgement calls, so use your own read of them.

Those three notebooks are generated from tools/seeds/. Edit the seed, run it,
then re-execute the notebook in place so it ships with outputs. Before any
commit run pytest, tools/check_notebooks.py and tools/check_seeds.py; all three
must be clean.

House rules that bite here: tables live in data/raw and both sides read them; a
knob the prose names is passed to the package, not typed twice; where an optimum
is not unique the check compares what every optimum shares and the prose teaches
the tie; and the commit message carries the defect record, which source was
wrong and what the notebook does now. That record is the point of this work.

Never commit a credential. This repo is going public and the Gurobi WLS key in
the older course copies has not been rotated, so do not reuse any key you find.

Don't inherit a one-notebook-at-a-time rhythm from the git log; that was mine,
not a house style. Verify as you go rather than at the end, however you like.
Update the status lines in REVIEW_QUEUE.md as you close findings.
```

---

## What is already done, so nobody redoes it

- The fifteen findings on `09`, `10` and `12` are fixed and those notebooks re-executed.
- **The library is public**, at `https://github.com/sear-labs/teaching-code`, pushed 2026-09-05.
  `REPO_URL` points there, the setup cell prints a repository-relative path so no output carries an
  author's machine, the licence cell falls back to the size-limited licence pip ships (so no key is
  needed anywhere except `07`, which says so itself), and the Gurobi licence number was removed from
  the output history before the push. A fresh clone was checked: the checker passes on all
  seventeen, and `../../src` resolves from a notebook folder the way the setup cell expects.
- Because it is public now, `git push` after committing, and remember that anything committed here
  is immediately visible.

## Second scope item: build the REE 4301 series as its own repository

Under the boundary decided in `CLAUDE.md` Part 11, REE 4301 is a **series** and gets its own
repository rather than folding in here. It was scanned on 2026-09-05 and **not** pushed. Three
blockers, none of them privacy:

1. **Twenty-four exam files** are tracked in that folder — mini-exam banks in text and QTI form,
   undergraduate and graduate variants, plus a Canvas backup holding the full question content of
   six quizzes. They are live for a course being taught now. Publishing retires them.
2. **Ninety-four files of the CARES book**, an in-progress manuscript with a versioned archive.
   Publishing it as a side effect of pushing notebooks is not a decision anybody made.
3. **The series would fail Part 5 on its first commit.** All thirteen notebooks are unexecuted —
   207 code cells, zero outputs. Four carry no assertion at all, and there is no package for an
   agreement assertion to compare against.

Filtering the working tree is not enough: the exams and the book are in the 48-commit history, so
the series repository needs **fresh history**, not a push of that one.

So the work is: a new repository from the thirteen notebooks in `2026 Fall/Notebooks/` and their
builders in `Tools/`; the notebooks executed and verified, which is where the defects will be, as
they were in every subject here; and a package for them to check against. Course administration —
exams, rubrics, Canvas tooling, the book — stays in the private folder repository. Notebook `12`
here is that series' Module 0 and was verified by running it; the other twelve never have been.

### What was already checked, so nobody re-runs it

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

## Still open beyond the queue

- Second notebooks for `05` (Gandhi cloth fixed charge, Portfolio logic) and `07` (server-farm
  two-stage LP, bakery VSS/EVPI).
- Roughly 140 files in the original migration queue were never classified or read.
- The REE 4301 modules beyond M0 have not been verified by running them.
- `REE 4301` is still pointed at by OneDrive path from this README and from `12`, because that
  repository has no remote yet.
