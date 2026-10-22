"""One probe for the Gurobi licence, shared by the whole suite.

`pip install gurobipy` ships a size-limited licence: 2,000 variables and 2,000
constraints. Every model in this library fits inside it except the newsvendor's
scenario model (3,002 variables), which is why 07's notebook says so in its own
licence cell. CI runs on that licence and has no key, by design.

A test that builds a model past the limit is marked `needs_full_licence`. Here
it runs; on the size-limited licence it SKIPS, with a reason `pytest -rs`
prints. It does not fail, because nothing is wrong with the code; and it does
not silently pass, because nothing was tested.

The probe asks the solver rather than guessing from the environment: it builds
a model one variable past the limit and sees whether Gurobi refuses it
(error 10010). Measured 2026-10-22 with the licence file hidden: the probe
reports size-limited, and exactly the seven newsvendor tests skip.
"""
from __future__ import annotations

import pytest

SIZE_LIMIT = 2000
SIZE_LIMITED_ERRNO = 10010      # "Model too large for size-limited license"


def _licence_is_size_limited() -> bool:
    import gurobipy as gp
    with gp.Env(empty=True) as env:
        env.setParam("OutputFlag", 0)        # keep the licence banner out of the test log
        env.start()
        with gp.Model(env=env) as m:
            x = m.addVars(SIZE_LIMIT + 1)
            m.addConstr(x.sum() >= 1)
            m.setObjective(x.sum())
            try:
                m.optimize()
            except gp.GurobiError as e:
                if e.errno == SIZE_LIMITED_ERRNO:
                    return True
                raise
    return False


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "needs_full_licence: builds a model past the 2,000-variable limit of the licence "
        "`pip install gurobipy` ships; skipped, with a reason, when that is the licence present",
    )


def pytest_collection_modifyitems(config, items):
    marked = [item for item in items if item.get_closest_marker("needs_full_licence")]
    if not marked or not _licence_is_size_limited():
        return
    skip = pytest.mark.skip(reason="needs a full Gurobi licence: the model is past the "
                                   "2,000-variable limit of the one `pip install gurobipy` ships")
    for item in marked:
        item.add_marker(skip)
