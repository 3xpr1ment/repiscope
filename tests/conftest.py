"""Shared fixture: a fake --root folder with one normal project, one
malicious project (symlink attacks), and secrets lying outside the root.

Every security test runs against this little world.
"""

import pytest

import repiscope.server as server


@pytest.fixture
def world(tmp_path, monkeypatch):
    """Build root/{alpha,evil}, plus an 'outside' area that must stay invisible."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "id_rsa_real").write_text("OUTSIDE-PRIVATE-KEY")
    (outside / "diary.txt").write_text("OUTSIDE-DIARY hunter2")
    ssh_like = outside / "dot-ssh"
    ssh_like.mkdir()
    (ssh_like / "id_ed25519").write_text("OUTSIDE-SSH-KEY")
    (ssh_like / "known_hosts").write_text("OUTSIDE-HOSTS")

    root = tmp_path / "root"
    root.mkdir()

    # A well-behaved project with both normal files and secrets.
    alpha = root / "alpha"
    (alpha / "src").mkdir(parents=True)
    (alpha / "README.md").write_text("# alpha\nA perfectly normal project\n")
    (alpha / "src" / "app.py").write_text("print('alpha application code')\n")
    (alpha / ".env").write_text("ALPHA_TOKEN=super-secret-token")
    (alpha / "secrets.json").write_text('{"password": "in-repo-secret"}')
    (alpha / "server.key").write_text("IN-REPO-PRIVATE-KEY")
    (alpha / "my_password_notes.md").write_text("password stash")

    # A hostile project: a cloned repo is untrusted content.
    evil = root / "evil"
    evil.mkdir()
    (evil / "README_real.md").write_text("# evil\nlooks like a normal repo\n")
    (evil / "innocent.py").write_text("print('evil but harmless code')\n")
    # symlinks escaping the root entirely
    (evil / "notes.txt").symlink_to(outside / "id_rsa_real")
    (evil / "README.md").symlink_to(outside / "diary.txt")
    (evil / "docs").symlink_to(ssh_like)
    # an innocently named symlink to a sensitive file inside the repo
    (evil / ".env").write_text("EVIL_TOKEN=evil-secret")
    (evil / "config.txt").symlink_to(evil / ".env")

    monkeypatch.setattr(server, "ROOT", root)
    monkeypatch.setattr(server, "EXCLUDE", set())
    return root
