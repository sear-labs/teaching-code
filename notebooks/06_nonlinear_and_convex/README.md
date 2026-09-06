# 06 — Nonlinear and convex

`curve_fit_lifting.ipynb` — a congestion curve with a division in it, lifted for a global QCQP
solver, and what one bound on the residual variables did to three terms of a graduate course.
`pooling.ipynb` — Haverly's pooling problem and its bilinear quality balances. Package:
`orteach.nonconvex`.

## Cournot, Stackelberg and the exact MIQP are in the advopt repository

The equilibrium models — Cournot best response and iterated best response, the exact MIQP that
checks it, and Stackelberg as a single-level MPEC — belong to the lithium supply-chain library and
stay there, with the package (`lithium.games`, `lithium.mpec`) that holds them:

    https://github.com/sear-labs/advopt-lithiumsc   → 04c_cournot, 04c_exact_miqp, 04d_stackelberg
