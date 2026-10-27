"""orteach.paths.table(): the one place every module finds an instance table.

Standard Part 4: local must win, a NAMED location is honoured or refused and never skipped,
and the URL fallback names a tag. Each of those is a test below, by name. No test here touches
the network: the URL case fakes the download.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

from orteach import assignment, paths  # noqa: E402

NAME = "assignment_4x4.csv"


@pytest.fixture
def no_env(monkeypatch):
    monkeypatch.delenv(paths.ENV, raising=False)


def test_in_a_clone_the_table_comes_from_the_repository(no_env):
    assert paths.table(NAME) == os.path.join(paths.SOURCE_DIR, NAME)
    assert os.path.isfile(paths.table(NAME))


def test_a_readers_edited_copy_reaches_the_loader(tmp_path, no_env):
    """The case the ordering exists for: a reader edits a table in their own folder and the
    package must read THAT file, not the published one."""
    (tmp_path / NAME).write_text("machine,job,cost\n1,1,99\n", encoding="utf-8")
    assert paths.table(NAME, data_dir=str(tmp_path)) == str(tmp_path / NAME)
    assert assignment.load_costs(paths.table(NAME, data_dir=str(tmp_path))) == {("1", "1"): 99.0}


def test_a_named_directory_without_the_file_is_refused_not_skipped(tmp_path, no_env):
    with pytest.raises(FileNotFoundError, match="never skipped"):
        paths.table(NAME, data_dir=str(tmp_path))


def test_the_environment_variable_is_honoured_and_refused_the_same_way(tmp_path, monkeypatch):
    monkeypatch.setenv(paths.ENV, str(tmp_path))
    with pytest.raises(FileNotFoundError, match=paths.ENV):
        paths.table(NAME)                      # set, but empty: refused, not the repo's copy
    (tmp_path / NAME).write_text("machine,job,cost\n", encoding="utf-8")
    assert paths.table(NAME) == str(tmp_path / NAME)


def test_without_a_local_copy_it_fetches_the_tagged_file_once(tmp_path, monkeypatch, no_env):
    """The pip-installed case: no data/raw beside the code or under the cwd."""
    monkeypatch.setattr(paths, "SOURCE_DIR", str(tmp_path / "absent"))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    fetched = []

    def fake_retrieve(url, dest):
        fetched.append(url)
        with open(dest, "w", encoding="utf-8") as f:
            f.write("machine,job,cost\n")

    monkeypatch.setattr(paths.urllib.request, "urlretrieve", fake_retrieve)
    first = paths.table(NAME)
    second = paths.table(NAME)
    assert first == second and os.path.isfile(first)
    assert fetched == [paths.RAW_URL + NAME], fetched          # once, then from the cache
    assert first.startswith(str(tmp_path / "cache"))


def test_the_url_names_the_release_tag_not_a_branch():
    assert "/%s/data/raw/" % paths.TAG in paths.RAW_URL
    assert "/main/" not in paths.RAW_URL and paths.TAG.startswith("v")
