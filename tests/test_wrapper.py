"""Unit tests for the `census21api.wrapper` module."""

import json
from unittest import mock

import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from census21api import CensusAPI
from census21api.constants import API_ROOT
from census21api.wrapper import _extract_records_from_observations

from .strategies import (
    st_observations,
    st_records_and_queries,
    st_table_queries,
)

MOCK_URL = "mock://test.com/"


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


@given(st.dictionaries(st.text(), st.text()))
def test_get(json):
    """Test that the API only gives data from successful responses."""

    api = CensusAPI()

    with mock.patch("census21api.wrapper.requests.get") as get, mock.patch(
        "census21api.wrapper.CensusAPI._process_response"
    ) as process:
        response = mock.MagicMock()
        get.return_value = response
        process.return_value = json

        data = api.get(MOCK_URL)

    assert api._current_url == MOCK_URL
    assert api._current_data == data
    assert data == json

    get.assert_called_once_with(MOCK_URL, verify=True)
    process.assert_called_once_with(response)


@given(st_table_queries(), st.dictionaries(st.text(), st.text()))
def test_query_table_json(query, json):
    """Test that the table querist makes URLs and returns correctly."""

    population_type, area_type, dimensions = query
    url = (
        f"{API_ROOT}/{population_type}/census-observations"
        f"?area-type={area_type}&dimensions={','.join(dimensions)}"
    )

    api = CensusAPI()

    with mock.patch("census21api.wrapper.CensusAPI.get") as get:
        get.return_value = json

        data = api._query_table_json(population_type, area_type, dimensions)

    assert data == json

    get.assert_called_once_with(url)


@given(st_observations(), st.booleans())
def test_extract_records_from_observations(observations, use_id):
    """Test the record extractor extracts correctly."""

    records = _extract_records_from_observations(observations, use_id)

    assert isinstance(records, list)

    option = "option_id" if use_id else "option"
    for record, observation in zip(records, observations):
        assert isinstance(record, tuple)
        assert len(record) == len(observation["dimensions"]) + 1

        *dimensions, count = record
        assert count == observation["observation"]
        for i, dimension in enumerate(dimensions):
            assert dimension == observation["dimensions"][i][option]


@given(st_records_and_queries(), st.booleans())
def test_query_table_valid(records_and_query, use_id):
    """Test that the querist can create a data frame."""

    records, population_type, area_type, dimensions = records_and_query

    api = CensusAPI()

    with mock.patch(
        "census21api.wrapper.CensusAPI._query_table_json"
    ) as querist, mock.patch(
        "census21api.wrapper._extract_records_from_observations"
    ) as extract:
        querist.return_value = {"observations": "foo"}
        extract.return_value = records

        data = api.query_table(population_type, area_type, dimensions, use_id)

    assert isinstance(data, pd.DataFrame)
    assert len(data) == len(records)

    expected_columns = [area_type, *dimensions, "count", "population_type"]
    assert data.columns.to_list() == expected_columns
    assert (data["population_type"] == population_type).all()

    for i, row in data.drop("population_type", axis=1).iterrows():
        assert tuple(row) == records[i]

    querist.assert_called_once_with(population_type, area_type, dimensions)
    extract.assert_called_once_with("foo", use_id)


@given(
    st_table_queries(),
    st.one_of((st.just(None), st.dictionaries(st.integers(), st.text()))),
)
def test_query_table_invalid(query, result):
    """Test the querist returns nothing if the call is unsuccessful."""

    api = CensusAPI()

    with mock.patch(
        "census21api.wrapper.CensusAPI._query_table_json"
    ) as builder:
        builder.return_value = result

        data = api.query_table(*query)

    assert data is None

    builder.assert_called_once_with(*query)
