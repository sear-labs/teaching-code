"""Where the instance tables are: one function, so every module finds data/raw the same way.

Standard Part 4, "the table has to be reachable from wherever the notebook runs".
`pip install git+https://github.com/sear-labs/teaching-code` ships this package and NOT
`data/raw/`, which sits at the repository root and never enters the wheel. Until 2026-10-27
every module found its tables by walking up from `__file__`, which is right in a clone and
an editable install and lands on site-packages' parent anywhere else, so the error read like
a corrupt download.

The order, local copy first:

    1. an explicit `data_dir=`      a test, or a reader's own copy        NAMED: honoured or refused
    2. $ORTEACH_DATA                an override needing no code change     NAMED: honoured or refused
    3. data/raw beside the code     a clone, or `pip install -e .`
    4. data/raw under the cwd       a script run from the repository root
    5. the published raw URL        everything else, at the release TAG, cached locally

A named location that lacks the file raises; it never falls through to the next candidate,
because handing someone who pointed at their own edited copy the published numbers instead
is the silent failure this ordering exists to prevent. Local must win over the URL for the
same reason: the notebooks tell the reader to edit a table and re-run, and the agreement
assertion stays green only if both halves read the edited file.

The URL names a tag, not `main`: a notebook handed to students must not change its answer
when someone edits a table on the default branch.
"""
from __future__ import annotations

import os
import urllib.request

TAG = "v1.0.0"
REPO = "sear-labs/teaching-code"
RAW_URL = "https://raw.githubusercontent.com/%s/%s/data/raw/" % (REPO, TAG)
ENV = "ORTEACH_DATA"

_HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.normpath(os.path.join(_HERE, "..", "..", "data", "raw"))   # in a clone


def _cache_dir() -> str:
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "orteach", TAG)


def table(name: str, data_dir: str | None = None) -> str:
    """Absolute path of instance table `name` (e.g. "diet_macros_foods.csv")."""
    for label, where in (("data_dir argument", data_dir), ("$" + ENV, os.environ.get(ENV))):
        if where:
            path = os.path.join(where, name)
            if not os.path.isfile(path):
                raise FileNotFoundError("%s points at %s, which has no %s. A named location is "
                                        "used or refused, never skipped." % (label, where, name))
            return path
    for where in (SOURCE_DIR, os.path.join(os.getcwd(), "data", "raw")):
        path = os.path.join(where, name)
        if os.path.isfile(path):
            return path
    cached = os.path.join(_cache_dir(), name)
    if not os.path.isfile(cached):
        os.makedirs(os.path.dirname(cached), exist_ok=True)
        url = RAW_URL + name
        try:
            urllib.request.urlretrieve(url, cached + ".part")
        except OSError as e:
            raise FileNotFoundError("%s is not in a local data/raw and could not be fetched from "
                                    "%s (%s). Clone the repository, or set $%s." % (name, url, e, ENV)) from e
        os.replace(cached + ".part", cached)
    return cached
