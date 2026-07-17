"""SmartPip Trader modular platform.

Because this package shares its name with the stdlib ``platform`` module,
we load the real stdlib module from its file path and proxy its most-used
attributes so that downstream libraries (joblib, sklearn, etc.) continue
to work when they ``import platform``.
"""
from __future__ import annotations

import importlib.util as _util
import os as _os
import sys as _sys

# ---------------------------------------------------------------------------
# Load the *real* stdlib platform module from its file on disk, bypassing
# sys.modules (which would just resolve back to us).
# ---------------------------------------------------------------------------
_stdlib_plat = None
try:
    _stdlib_path = _os.path.join(
        _os.path.dirname(_os.__file__), "platform.py"
    )
    _spec = _util.spec_from_file_location("_stdlib_platform", _stdlib_path)
    _stdlib_plat = _util.module_from_spec(_spec)
    _spec.loader.exec_module(_stdlib_plat)
except Exception:  # pragma: no cover
    pass

if _stdlib_plat is not None:
    python_implementation = _stdlib_plat.python_implementation
    system = _stdlib_plat.system
    machine = _stdlib_plat.machine
    node = _stdlib_plat.node
    platform = _stdlib_plat.platform
    processor = _stdlib_plat.processor
    release = _stdlib_plat.release
    version = _stdlib_plat.version
    uname = _stdlib_plat.uname
    architecture = _stdlib_plat.architecture

__all__ = [
    "python_implementation", "system", "machine", "node",
    "platform", "processor", "release", "version", "uname",
    "architecture",
]
