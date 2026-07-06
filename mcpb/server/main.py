"""Launcher for the Repiscope MCP bundle.

Puts the bundled dependencies (server/lib) on the import path, then starts
the normal Repiscope server. The root folder arrives via REPISCOPE_ROOT,
set by the host app from the bundle's user config.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "lib"))

from repiscope.server import main

main()
