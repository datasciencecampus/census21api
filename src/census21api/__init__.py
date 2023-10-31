"""A Python wrapper for the England and Wales Census 2021 API."""

from . import constants
from .wrapper import CensusAPI

__all__ = ["CensusAPI", "constants"]
