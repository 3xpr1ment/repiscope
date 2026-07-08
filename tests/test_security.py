"""The security claims, as executable proof.

README promises: read-only by architecture, path traversal refused,
sensitive files invisible to every tool, symlinks can't smuggle
anything in or out. Each promise gets a test.
"""

from pathlib import Path

import repiscope.server as server
from repiscope.overview import _iter_files, _readme_excerpt, _tree
from repiscope.privacy import is_off_limits, is_sensitive
from repiscope.scanner import one_line_description
from repiscope.textsearch import search_project


# ---------------------------------------------------------------- traversal

def test_read_file_refuses_dotdot(world):
    out = server.read_file("alpha", "../evil/innocent.py")
    assert "Refused" in out or "points outside" in out
    assert "harmless" not in out


def test_read_file_refuses_absolute_path(world):
    out = server.read_file("alpha", "/etc/passwd")
    assert "points outside" in out


def test_project_names_cannot_traverse(world):
    for name in ("../outside", "..", "outside", "alpha/../../outside"):
        assert "Unknown project" in server.read_file(name, "diary.txt")


# ----------------------------------------------------------------- symlinks

def test_search_ignores_symlink_escaping_root(world):
    hits = search_project(world / "evil", "OUTSIDE", 50)
    assert hits == []


def test_search_still_sees_normal_files_in_hostile_repo(world):
    hits = search_project(world / "evil", "harmless", 50)
    assert len(hits) == 1 and "innocent.py" in hits[0]


def test_read_file_refuses_symlink_escaping_root(world):
    out = server.read_file("evil", "notes.txt")
    assert "points outside" in out
    assert "PRIVATE-KEY" not in out


def test_readme_readers_ignore_symlinked_readme(world):
    assert "OUTSIDE" not in _readme_excerpt(world / "evil")
    assert "OUTSIDE" not in one_line_description(world / "evil")


def test_tree_hides_symlinked_outside_dir(world):
    tree = _tree(world / "evil")
    assert "docs" not in tree
    assert "id_ed25519" not in tree and "known_hosts" not in tree
    assert "innocent.py" in tree


def test_innocent_name_cannot_disguise_sensitive_target(world):
    # config.txt -> .env: the link's own name passes the filter, its target must not
    assert "Refused" in server.read_file("evil", "config.txt")
    assert search_project(world / "evil", "evil-secret", 50) == []


def test_symlinked_project_folder_still_works(world, tmp_path):
    real = tmp_path / "elsewhere" / "real-repo"
    real.mkdir(parents=True)
    (real / "main.py").write_text("print('hello from linked repo')\n")
    (world / "linked").symlink_to(real)
    hits = search_project(world / "linked", "hello from linked", 50)
    assert len(hits) == 1


# -------------------------------------------------------------- secret filter

def test_sensitive_names_and_extensions_flagged():
    for name in (".env", ".env.local", "id_rsa", "secrets.json", "server.key",
                 "cert.pem", "my_password_notes.md", "apikey.txt", ".npmrc"):
        assert is_sensitive(Path(name)), name
    for name in ("README.md", "app.py", "package.json", "environment.yml"):
        assert not is_sensitive(Path(name)), name


def test_search_never_returns_secret_content(world):
    for needle in ("super-secret-token", "in-repo-secret",
                   "IN-REPO-PRIVATE-KEY", "password stash"):
        assert search_project(world / "alpha", needle, 50) == []


def test_read_file_refuses_sensitive_files(world):
    for path in (".env", "secrets.json", "server.key", "my_password_notes.md"):
        assert "sensitive-file filter" in server.read_file("alpha", path)


def test_tree_and_language_stats_hide_sensitive_files(world):
    tree = _tree(world / "alpha")
    assert "secrets.json" not in tree and "server.key" not in tree
    listed = {p.name for p in _iter_files(world / "alpha")}
    assert "secrets.json" not in listed and ".env" not in listed
    assert "app.py" in listed


def test_normal_files_remain_fully_visible(world):
    assert "normal project" in server.read_file("alpha", "README.md")
    hits = search_project(world / "alpha", "alpha application", 50)
    assert len(hits) == 1


# ---------------------------------------------------------- the gate itself

def test_is_off_limits_unreadable_path_is_hidden(world):
    dangling = world / "evil" / "dangling"
    dangling.symlink_to(world / "evil" / "does-not-exist")
    # a dangling symlink resolves but is not a file; must never blow up
    assert not dangling.is_file()
    assert search_project(world / "evil", "does-not-exist", 50) == []


def test_excluded_projects_are_invisible(world, monkeypatch):
    monkeypatch.setattr(server, "EXCLUDE", {"alpha"})
    assert "Unknown project" in server.read_file("alpha", "README.md")
    assert "alpha" not in server.list_projects()
