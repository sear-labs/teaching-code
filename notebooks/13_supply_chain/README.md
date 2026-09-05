# 13 — Supply chain

`sourcing_and_resilience.ipynb` is REE 4301's Module 4 model: three mines, two processors, two
plants, and the price curve of capping any one mine's share. Package: `orteach.sourcing`.

## The lithium supply-chain models live in their own repository

The Advanced Optimization Modeling course's notebooks — a six-site network MILP, its stochastic
extension with progressive hedging and Benders cuts, CVaR, the planner-and-game sequence, the exact
MIQP, the Stackelberg MPEC, policy instruments and interdiction — are a complete library of their
own, written to the same standard, with their package `lithium` and their own agreement assertions:

    https://github.com/sear-labs/advopt-lithiumsc

They are **not copied here**. A copy would be a second definitive source, and the standard's Part 4
is about why that fails. The course-folder copies on Drive (`Advanced Supply Chain Modeling/Part1_…`
through `Part4f_…`) are earlier drafts of the same notebooks; the repository is the current one.

| topic | advopt notebook |
|---|---|
| the deterministic network MILP | `01_deterministic.ipynb`, `03_network_core.ipynb` |
| two-stage stochastic, progressive hedging | `02_stochastic.ipynb` |
| Benders / L-shaped by hand | `02b_benders.ipynb` |
| CVaR | `02c_cvar.ipynb` |
| production learning curves | `03b_production_learning.ipynb` |
| planner and game, Cournot, Stackelberg, policy, interdiction | `04ab_…` through `04f_…` |
| the closed loop | `05_integrated_core.ipynb` |
