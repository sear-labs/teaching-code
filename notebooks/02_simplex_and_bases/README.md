# 02 — Simplex and bases

Both notebooks solve IE 3315's tableau example (deck 05): maximise 40x1 + 50x2 subject to
x1 + 2x2 <= 40 and 4x1 + 3x2 <= 120, table `lp_simplex_40_50.csv`. Package: `orteach.simplex`.

`simplex_by_hand.ipynb` — every basis (six, four of them feasible corners), then the tableau
pivoted by hand from (0, 0) through (0, 20) to (24, 8), as the slides do it. Row 0's final
entries under the slacks are the duals, which the notebook asks the reader to notice.

`interior_point.ipynb` — a log-barrier method on the same LP: one equality-constrained Newton step
written out, the line search, centering, then the central path as t grows. It replaces
`barrierShort.ipynb` (IE 5301 folder), which ran on a random instance redrawn every run, so no
number in it could be quoted; here the instance is fixed and the path can be drawn against the
simplex's corners.

The slides' exercise, Wyndor (max 3x1 + 5x2, three plants), is `lp_wyndor.csv`; the tests pin its
simplex path, (0, 0) to (0, 6) to (2, 6).
