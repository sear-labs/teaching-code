# Teaching Code — one library, organised by subject

> **The rules are not in this file.** Everything portable — archetypes, naming, the teaching
> standard, the engineering/teaching boundary, verification, working alongside other sessions —
> lives in one document and is deliberately **not restated** here:
>
>     Documents\Classes\Code Standard\CLAUDE.md      local working copy on this machine
>     https://github.com/sear-labs/code-standard     the source, canonical
>
> **Read it first and last.** First because it decides how the work is done; last because a change
> you are about to make may be one it already settles.
>
> This file used to hold an 814-line *copy* of that standard. It was 23 lines behind the source and
> nothing said so — which is why copies were abandoned on 2026-09-04 in favour of pointing. Do not
> paste it back.

---

# Part 11 — This project specifically

**Archetype A + T.** `src/orteach/` is Parts 1–2 territory; `notebooks/` is Part 3 territory; Part 4
governs the boundary between them.

## The organising decision, and why it is not obvious

**One library, not one repo per course.** The subjects are shared — LP formulation, duality,
networks and stochastic programming each serve more than one of IE 3315, IE 5301 and REE 4301 — so
splitting by course would duplicate every shared subject and guarantee the copies drift.

This is written down rather than left implicit because it is the decision somebody will reasonably
want to undo the first time a course needs something the library does not have. **The answer is to
add the subject here, not to fork a course-shaped copy.**

## Layout

```
src/orteach/        the package
notebooks/NN_subject/   01_lp_formulation ... 14_probability_and_stats
data/raw/  tests/
```

**`notebooks/NN_subject` is the sort-key rule from Part 1 applied.** Zero-padded, so `01`–`14` order
correctly and a fifteenth would too. Keep the padding when adding one.

## Status, measured 2026-09-04

**This is scaffolding. No content has landed yet.** One commit (`726618f`), 14 `.gitkeep` files, an
empty `src/orteach/__init__.py`, and placeholders in `tests/` and `data/`.

So there is nothing here to audit against Part 7 and nothing to break. The first real notebook sets
the pattern for the other thirteen — build it to Part 3, and to the shape Part 0 of
`Advanced Opt Modeling Examples` uses as its template, rather than inventing a second house style.
