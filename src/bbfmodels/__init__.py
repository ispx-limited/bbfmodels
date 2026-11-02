"""Typed models and schema tooling for Broadband Forum data models.

The Broadband Forum publishes its device data models (TR-181, TR-098, TR-104
and the rest) as XML in the TR-106 schema. This package reads that XML once
into a normalised intermediate representation, works with the models at
runtime from that representation, and generates typed bindings from it.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("bbfmodels")
except PackageNotFoundError:  # running from a source tree that is not installed
    __version__ = "0.4.0"

__all__ = ["__version__"]
