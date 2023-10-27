"""Unit tests for the `census21api.wrapper` module."""

import json
from unittest import mock

import pytest
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


@given(st.dictionaries(st.text(), st.text()))
def test_process_response_valid(json):
    """Test a valid response can be processed correctly."""

    api = CensusAPI()

    response = mock.MagicMock()
    response.status_code = 200
    response.json.return_value = json

    data = api._process_response(response)

    assert data == json

    response.json.assert_called_once()


@given(st.one_of((st.integers(max_value=199), st.integers(300))))
def test_process_response_invalid_status_code(status):
    """Test an invalid status code returns no data and a warning."""

    api = CensusAPI(logger=True)

    response = mock.MagicMock()
    response.status_code = status
    response.body = "foo"

    with pytest.warns(UserWarning, match="Unsuccessful GET from"):
        data = api._process_response(response)

    assert data is None


def test_process_response_invalid_json():
    """Test for valid coded, invalid JSON responses.

    We expect the processor to return no data and a warning.
    """

    api = CensusAPI(logger=True)

    response = mock.MagicMock()
    response.status_code = 200
    response.json.side_effect = json.JSONDecodeError("foo", "bar", 42)

    with pytest.warns(UserWarning, match="Error decoding data from"):
        data = api._process_response(response)

    assert data is None
