"""A Python wrapper for the England & Wales Census 2021 API."""

from .interface import Interface
from .wrapper import APIWrapper

__all__ = ["APIWrapper", "Interface"]