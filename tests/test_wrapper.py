"""Unit tests for the `census21api.wrapper` module."""

from hypothesis import given
from hypothesis import strategies as st

from census21api import CensusAPI


@given(st.booleans())
def test_init(logger):
    """Test that the `CensusAPI` class can be instantiated correctly."""

    api = CensusAPI(logger)

    assert api._logger is logger
    assert api._current_data is None
    assert api._current_url is None
