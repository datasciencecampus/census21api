"""Unit tests for the `census21api.wrapper` module."""

import json
from unittest import mock

import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from census21api import CensusAPI
from census21api.constants import (
    API_ROOT,
    POPULATION_TYPES,
)
from census21api.wrapper import _extract_records_from_observations

from .strategies import (
    st_category_queries,
    st_feature_queries,
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


@given(st.sampled_from(POPULATION_TYPES))
def test_query_population_type_valid(population_type):
    """Test the population querist returns a valid series."""

    api = CensusAPI()

    with mock.patch("census21api.wrapper.CensusAPI.get") as get:
        get.return_value = {
            "population_type": {
                "name": population_type,
                "label": None,
                "description": None,
                "type": None,
            }
        }
        metadata = api.query_population_type(population_type)

    assert isinstance(metadata, pd.Series)
    assert metadata.index.to_list() == ["name", "label", "description", "type"]
    assert metadata["name"] == population_type
    assert metadata.to_list() == [population_type, None, None, None]

    get.assert_called_once_with(f"{API_ROOT}/{population_type}")


@given(
    st.sampled_from(POPULATION_TYPES),
    st.one_of((st.just(None), st.dictionaries(st.integers(), st.integers()))),
)
def test_query_population_type_invalid(population_type, result):
    """Test the population querist returns nothing on a failed call."""

    api = CensusAPI()

    with mock.patch("census21api.wrapper.CensusAPI.get") as get:
        get.return_value = result

        metadata = api.query_population_type(population_type)

    assert metadata is None

    get.assert_called_once_with(f"{API_ROOT}/{population_type}")


@given(st_feature_queries())
def test_query_feature(query):
    """Test the feature querist can return something valid."""

    population_type, endpoint, items, result = query

    api = CensusAPI()

    with mock.patch("census21api.wrapper.CensusAPI.get") as get:
        get.return_value = result
        metadata = api.query_feature(population_type, endpoint, *items)

    assert isinstance(metadata, pd.DataFrame)
    assert metadata.columns.to_list() == ["id", "population_type"]
    assert (metadata["population_type"] == population_type).all()
    if items:
        assert len(metadata) == len(items)
        assert set(metadata["id"]) == set(items)

    get.assert_called_once_with(
        "/".join((API_ROOT, population_type, f"{endpoint}?limit=500"))
    )


@given(
    st_feature_queries(),
    st.one_of((st.just(None), st.dictionaries(st.integers(), st.integers()))),
)
def test_query_feature_invalid(query, result):
    """Test the feature querist returns nothing if the call fails."""

    population_type, endpoint, items, _ = query

    api = CensusAPI()

    with mock.patch("census21api.wrapper.CensusAPI.get") as get:
        get.return_value = result
        metadata = api.query_feature(population_type, endpoint, *items)

    assert metadata is None

    get.assert_called_once_with(
        "/".join((API_ROOT, population_type, f"{endpoint}?limit=500"))
    )


@given(st_category_queries())
def test_query_categories_single_call(query):
    """Test the category querist works on a single call."""

    population_type, feature, item, endpoint, items = query

    api = CensusAPI()

    with mock.patch("census21api.wrapper.CensusAPI.get") as get:
        get.return_value = {"count": 1, "total_count": 1, "items": items}
        categories = api.query_categories(population_type, feature, item)

    assert isinstance(categories, pd.DataFrame)
    assert len(categories) == len(items)
    assert set(categories["item"]) == set(i["item"] for i in items)
    assert (categories["population_type"] == population_type).all()

    expected_columns = ["item", "population_type"]
    assert categories.columns.to_list() == expected_columns

    get.assert_called_once_with(
        "/".join(
            (API_ROOT, population_type, feature, item, f"{endpoint}?limit=500")
        )
    )


@given(st_category_queries())
def test_query_categories_multiple_calls(query):
    """Test the category querist works with multiple calls."""

    population_type, feature, item, endpoint, items = query

    api = CensusAPI()

    with mock.patch("census21api.wrapper.CensusAPI.get") as get:
        get.return_value = {
            "count": 1,
            "total_count": 2,
            "items": items.copy(),
        }
        categories = api.query_categories(population_type, feature, item)

    assert isinstance(categories, pd.DataFrame)
    assert categories.columns.to_list() == ["item", "population_type"]
    assert len(categories) == len(items) * 2
    assert set(categories["item"]) == set(i["item"] for i in items)
    assert (categories["population_type"] == population_type).all()

    assert get.call_count == 2
    get.assert_called_with(
        "/".join(
            (
                API_ROOT,
                population_type,
                feature,
                item,
                f"{endpoint}?limit=500&offset=1",
            )
        )
    )


@given(
    st_category_queries(),
    st.one_of((st.just(None), st.dictionaries(st.integers(), st.integers()))),
)
def test_query_categories_invalid(query, result):
    """Test the category querist returns nothing on a failed call."""

    population_type, feature, item, endpoint, _ = query

    api = CensusAPI()

    with mock.patch("census21api.wrapper.CensusAPI.get") as get:
        get.return_value = result
        categories = api.query_categories(population_type, feature, item)

    assert categories is None

    get.assert_called_once_with(
        f"{API_ROOT}/{population_type}/{feature}/{item}/{endpoint}?limit=500"
    )
