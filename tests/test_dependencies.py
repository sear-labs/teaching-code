"""Every third-party import is declared in pyproject.toml (standard Part 6).

An undeclared import is invisible on the authoring machine and on Colab, which ship most
of the scientific stack, and fatal on a clean install. So the imports are SCANNED (parsed,
never executed: importing may build a model) and compared with pyproject.toml, which is
READ rather than restated here, so this guard cannot drift from the file it guards.

    src/orteach    the core dependencies, plus an extra for an import made inside a function
                   (orteach.energy reaches PyPSA only when a network is built)
    notebooks/     the core dependencies and the extras; google.colab is Colab's own
    tests/         all of the above plus dev

A distribution whose import name differs from its project name needs an entry in MODULE_OF.
An unknown distribution FAILS rather than being guessed at: loosening the check to pass would
hide exactly the change it exists to catch.
"""
import ast
import json
import re
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:                                          # declared in dev for 3.10; never skipped
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]

# project name on PyPI -> the module it installs. Every declared distribution must appear.
MODULE_OF = {"gurobipy": "gurobipy", "numpy": "numpy", "scipy": "scipy", "matplotlib": "matplotlib",
             "pytest": "pytest", "statsmodels": "statsmodels", "ruff": None, "tomli": "tomli",
             "pypsa": "pypsa", "pandas": "pandas", "ipywidgets": "ipywidgets"}
PLATFORM = {"google"}                          # google.colab: present only on Colab, guarded there


def _dists(specs):
    return {re.split(r"[<>=!~;\[ ]", s, maxsplit=1)[0].strip().lower() for s in specs}


def _modules(dists):
    unknown = sorted(d for d in dists if d not in MODULE_OF)
    assert not unknown, ("pyproject.toml declares %s, which MODULE_OF does not map to a module. "
                         "Add the mapping; do not loosen this test." % unknown)
    return {MODULE_OF[d] for d in dists if MODULE_OF[d]}


CORE = _modules(_dists(PYPROJECT["dependencies"]))
EXTRAS = {k: _modules(_dists(v)) for k, v in PYPROJECT["optional-dependencies"].items()}
STDLIB = set(sys.stdlib_module_names)


def _imports(source):
    out = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            out |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            out.add(node.module.split(".")[0])
    return out


def _undeclared(found, allowed):
    return sorted(m for m in found if m not in STDLIB | allowed | {"orteach"})


def _notebook_code(path):
    cells = json.loads(path.read_text(encoding="utf-8"))["cells"]
    code = "\n".join("".join(c["source"]) for c in cells if c["cell_type"] == "code")
    return "\n".join(ln for ln in code.splitlines() if not ln.lstrip().startswith(("!", "%")))


def test_the_package_imports_only_what_it_declares():
    files = sorted((ROOT / "src" / "orteach").glob("*.py"))
    assert files, "no package modules found"
    allowed = CORE | EXTRAS["energy"]
    bad = {f.name: _undeclared(_imports(f.read_text(encoding="utf-8")), allowed) for f in files}
    bad = {k: v for k, v in bad.items() if v}
    assert not bad, "imported but not declared in pyproject.toml: %s" % bad
    print("%d modules scanned" % len(files))


def test_every_notebook_imports_only_what_is_declared():
    nbs = sorted((ROOT / "notebooks").rglob("*.ipynb"))
    assert len(nbs) >= 17, "found only %d notebooks" % len(nbs)
    allowed = CORE | EXTRAS["energy"] | PLATFORM
    bad = {n.name: _undeclared(_imports(_notebook_code(n)), allowed) for n in nbs}
    bad = {k: v for k, v in bad.items() if v}
    assert not bad, "imported but not declared in pyproject.toml: %s" % bad
    print("%d notebooks scanned" % len(nbs))


def test_the_tests_import_only_what_is_declared():
    files = sorted((ROOT / "tests").glob("*.py"))
    allowed = CORE | EXTRAS["energy"] | EXTRAS["dev"]
    bad = {f.name: _undeclared(_imports(f.read_text(encoding="utf-8")), allowed) for f in files}
    bad = {k: v for k, v in bad.items() if v}
    assert not bad, "imported but not declared in pyproject.toml: %s" % bad
