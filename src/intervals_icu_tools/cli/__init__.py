"""CLI package. Importing commands registers them with the Click group via decorators."""

from .main import cli
from . import commands  # noqa: F401 — side-effect: registers @cli.command() decorators

__all__ = ["cli"]
