"""The agreement tolerance and the solver settings that make it honest — in one place.

Standard Part 4, two amendments adopted 2026-09-04:

**A threshold used in two places is a parameter.** Before this module, ``1e-9``
was written into three notebooks and ``1e-9`` / ``1e-6`` into three test files.
Nothing compared those copies, so a tolerance corrected in one place would not
reach the others. Notebooks and tests now import from here and write no literal.

**Solve at least as tightly as you assert.** Gurobi's defaults are
``OptimalityTol 1e-6``, ``FeasibilityTol 1e-6``, ``MIPGap 1e-4``. A notebook that
solves at those defaults and then asserts agreement to ``1e-9`` is demanding a
thousand times more precision than it asked the solver for. It passes only because
both sides take the identical path on the same machine — it is testing
determinism, not equivalence, and it fails the first time it runs somewhere else.
Every solver in this package applies ``GUROBI_PARAMS`` so the assertion is a
claim the computation can actually support.

A tolerance must sit between the noise and the effect. ``1e-9`` relative is
tighter than any modelling difference these notebooks exist to catch, and looser
than what a solve at ``1e-9`` tolerances leaves behind.
"""

# What the agreement assertion claims. Relative, on objective values and on the
# decision quantities the notebook compares.
AGREEMENT_RTOL = 1e-9

# Absolute slack allowed when a test checks that a solution RESPECTS something -
# a budget, a bound, a floor. Constraint rows come back satisfied to
# FeasibilityTol (1e-9), so 1e-6 sits three orders above the solver's noise and
# far below any violation a test exists to catch. It was written into five
# asserts across two test files before it had a name.
FEASIBILITY_ATOL = 1e-6

# How far from 0 or 1 a value may sit and still count as integral. Gurobi's
# IntFeasTol is set to 1e-9 below, so this is the solver's own promise. It was
# typed as a literal in three package modules and two notebooks before it had
# a name (review of 2026-09-05).
INTEGRALITY_ATOL = 1e-9

# What a SECOND METHOD's answer may differ from the solver's by, relative. A local
# optimiser, a closed-form formula or a hand recursion is not running Gurobi's
# stopping rule, so it cannot be held to AGREEMENT_RTOL: the traffic fit's scipy
# check lands 2.7e-8 away in relative terms, which is far above 1e-9 and far below
# any modelling difference. Distinct from AGREEMENT_RTOL, which is the notebook and
# the package running the SAME method and having no excuse to differ.
CROSS_METHOD_RTOL = 1e-6

# Absolute tolerance on a quantity computed in closed form - a share, a ratio, a
# formula evaluated by hand - with no solver and no iteration anywhere in it.
# Floating point on numbers this size leaves error near 1e-16, so this sits four
# orders above the noise and far below any modelling error worth catching.
CLOSED_FORM_ATOL = 1e-12

# Absolute tolerance on numpy linear-algebra results - a solved steady state,
# a matrix power, a fundamental matrix - on the small, well-conditioned
# systems the teaching notebooks use. Not a solver tolerance; numpy has none to
# set, so this is the noise floor a test allows for.
LINALG_ATOL = 1e-9

# What makes that claim honest. Gurobi's documented minimum for the three
# tolerances is 1e-9; MIPGap 0 solves to proven optimality, which is instant on
# instances this size and is the only setting under which a 1e-9 objective
# comparison between two MIP solves means anything.
GUROBI_PARAMS = {
    "OutputFlag": 0,
    "OptimalityTol": 1e-9,
    "FeasibilityTol": 1e-9,
    "IntFeasTol": 1e-9,
    "MIPGap": 0.0,
    "MIPGapAbs": 0.0,
}


def apply(model):
    """Set the package's solver parameters on a Gurobi model and return it."""
    for name, value in GUROBI_PARAMS.items():
        model.setParam(name, value)
    return model


def rel_diff(a, b):
    """Relative difference with a floor, so a zero-valued quantity does not
    divide by itself. Used identically by every notebook's agreement cell."""
    return abs(a - b) / max(abs(a), abs(b), 1.0)
