"""Importing the toolkit must leave logging configuration to the application."""

import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "module",
    ["sim_atlas_toolkit", "sim_atlas_toolkit.parsers", "sim_atlas_toolkit.cli"],
)
def test_import_does_not_configure_root_logger(module: str) -> None:
    # A fresh interpreter: in this process the modules are already imported.
    code = (
        "import logging\n"
        "root = logging.getLogger()\n"
        "before = (list(root.handlers), root.level)\n"
        f"import {module}\n"
        "assert (list(root.handlers), root.level) == before, "
        "(root.handlers, root.level)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
