#!/usr/bin/env bash
# Build repiscope.mcpb — a one-click install bundle for Claude Desktop.
#
# Stages the repiscope package plus its dependencies (copied from .venv)
# into mcpb/server/lib, then packs the mcpb/ folder with the official
# `mcpb` CLI. Output lands in dist/repiscope-<version>.mcpb.
#
# The bundled dependencies include compiled extensions from this machine's
# interpreter, so the bundle is macOS-only and tied to the Python minor
# version it was built with.
#
# Usage: bash mcpb/build.sh [path-to-mcpb-cli]

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
LIB="$REPO/mcpb/server/lib"
SITE=("$REPO"/.venv/lib/python*/site-packages)
MCPB_BIN="${1:-mcpb}"

VERSION=$(python3 -c "import tomllib; print(tomllib.load(open('$REPO/pyproject.toml','rb'))['project']['version'])")

rm -rf "$LIB"
mkdir -p "$LIB" "$REPO/dist"

# Dependencies from the venv (skip packaging tools and editable-install artifacts)
rsync -a \
  --exclude '__pycache__' \
  --exclude 'pip' --exclude 'pip-*' \
  --exclude 'setuptools' --exclude 'setuptools-*' \
  --exclude 'wheel' --exclude 'wheel-*' \
  --exclude 'pkg_resources' --exclude '_distutils_hack' \
  --exclude '*.pth' \
  "${SITE[0]}/" "$LIB/"

# The repiscope package itself (the venv has it as an editable install)
rsync -a --exclude '__pycache__' --exclude '*.egg-info' \
  "$REPO/src/repiscope" "$LIB/"

"$MCPB_BIN" pack "$REPO/mcpb" "$REPO/dist/repiscope-$VERSION.mcpb"
