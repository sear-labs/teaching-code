# Prompt for the next session

Everything a cold session needs is on disk: `REVIEW_QUEUE.md` holds the open findings verbatim,
`CLAUDE.md` Part 11 holds this library's conventions, and `git log` holds the defect record. This
file is just the starting message, kept here so it survives a moved folder or a lost chat.

Paste the block below into a new chat opened in this folder.

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

## Still open beyond the queue

- Second notebooks for `05` (Gandhi cloth fixed charge, Portfolio logic) and `07` (server-farm
  two-stage LP, bakery VSS/EVPI).
- Roughly 140 files in the original migration queue were never classified or read.
- The REE 4301 modules beyond M0 have not been verified by running them.
- `REE 4301` is still pointed at by OneDrive path from this README and from `12`, because that
  repository has no remote yet.
