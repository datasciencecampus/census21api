"""A Python wrapper for the England and Wales Census 2021 API."""

from . import constants
from .interface import Interface
from .wrapper import CensusAPI

__all__ = ["CensusAPI", "Interface", "constants"]
