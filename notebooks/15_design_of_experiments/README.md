# 15 — Design of experiments

Three notebooks on one synthetic instance, a five-factor reactor (`doe_reactor_runs.csv`, generated
by `orteach.doe` from a printed seed and a stated true model). Package: `orteach.doe`.

**Read them in this order, and stop when you have what you need.**

1. `planning_an_experiment.ipynb` — **the basics, for anyone planning a study.** Six steps in the
   order you take them: the noise and the effect worth detecting; how many runs and how many
   replicates, and why; the reduction ladder (two levels plus center points, then replicate only the
   center, then a fraction) with the power each rung keeps; randomizing and blocking; what the runs
   you already have can estimate; and which runs to add (D-optimal augmentation, fold-over, axial
   points). Each step carries one piece of theory: the chi-square interval for sigma, the power
   formula and its noncentral-t check, hidden replication, drift as a fake effect, rank and the
   D-criterion.
2. `factorial_designs.ipynb` — **the deep dive behind steps 2, 3 and 6.** Effects and interactions
   by hand, the half-normal plot and Lenth's margins, the half and quarter fractions with their alias
   algebra, and the center-point curvature test.
3. `space_filling_designs.ipynb` — **only for computer experiments**, where a simulation replaces the
   lab and the goal is a surrogate. Latin hypercubes, maximin, and why the run count does not grow
   with the number of factors. Skip it for a physical experiment.

The three share the reactor so that a number in one can be found in another: the 36-run design that
planning recommends is the table `factorial_designs` analyses, and the eight-run quarter fraction
that misreads stirring there is the one planning's fold-over repairs.

Not here yet: response surface designs and steepest ascent (the central composite design that step
6 names), and a degradation-study notebook.
