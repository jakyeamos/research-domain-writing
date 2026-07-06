"""Research Domain Writing package."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("research-domain-writing")
except PackageNotFoundError:  # source tree without an installed dist
    __version__ = "0.0.0+local"
