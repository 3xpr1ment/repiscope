"""The sensitive-file filter: one gate, used by every tool.

Anything matched here is invisible to ALL of Repiscope — it never appears
in overviews, structure trees, search results or read_file. We prefer
false positives (hiding a harmless file) over ever leaking a secret to
an LLM context.
"""

from pathlib import Path

# Private keys, certificates, keystores, encrypted vaults.
SENSITIVE_EXTENSIONS = {
    ".pfx", ".p12", ".pem", ".key", ".der", ".jks", ".keystore",
    ".ppk", ".gpg", ".asc", ".kdbx",
}

# Exact (lowercased) filenames that are credentials by convention.
SENSITIVE_NAMES = {
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
    ".netrc", ".npmrc", ".pypirc", ".htpasswd",
    "credentials", "credentials.json", "service-account.json",
    "secrets.json", "secrets.yml", "secrets.yaml", "secrets.toml",
}

# Any file whose name starts with these is hidden (.env, .env.local, …).
SENSITIVE_PREFIXES = (".env",)

# Words in a filename that make it too risky to expose.
SENSITIVE_KEYWORDS = ("secret", "password", "private_key", "credential", "apikey", "api_key")


def is_sensitive(path: Path) -> bool:
    """True if this file must be invisible to every Repiscope tool."""
    name = path.name.lower()
    if path.suffix.lower() in SENSITIVE_EXTENSIONS:
        return True
    if name in SENSITIVE_NAMES:
        return True
    if name.startswith(SENSITIVE_PREFIXES):
        return True
    return any(word in name for word in SENSITIVE_KEYWORDS)


def is_off_limits(path: Path, project: Path) -> bool:
    """The full visibility gate: sensitive by name, escaping the project
    via a symlink, or sensitive at the symlink's real target.

    A cloned repo is untrusted content — it may contain a symlink like
    `notes.txt -> ~/.ssh/id_rsa`. Anything whose real location falls
    outside the project folder is invisible, and the sensitive-name check
    runs on the real target too, so a harmless-looking link cannot smuggle
    a secret past the filter.
    """
    if is_sensitive(path):
        return True
    try:
        real = path.resolve()
    except OSError:
        return True
    if not real.is_relative_to(project.resolve()):
        return True
    return real != path and is_sensitive(real)
