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
    st_population_types,
    st_records_and_queries,
    st_table_queries,
)

MOCK_URL = "mock://test.com/"


def test_init():
    """Test that the `CensusAPI` class can be instantiated correctly."""

    api = CensusAPI()

    assert isinstance(api, CensusAPI)
    assert vars(api) == {}


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

    api = CensusAPI()

    response = mock.MagicMock()
    response.status_code = status
    response.url = MOCK_URL
    response.text = "foo"

    with pytest.warns(UserWarning, match=f"Unsuccessful GET from {MOCK_URL}"):
        data = api._process_response(response)

    assert data is None


def test_process_response_invalid_json():
    """Test for valid coded, invalid JSON responses.

    We expect the processor to return no data and a warning.
    """

    api = CensusAPI()

    response = mock.MagicMock()
    response.status_code = 200
    response.url = MOCK_URL
    response.json.side_effect = json.JSONDecodeError("foo", "bar", 42)

    with pytest.warns(
        UserWarning, match=f"Error decoding data from {MOCK_URL}"
    ):
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
    assert all(data.columns == expected_columns)
    assert (data["population_type"] == population_type).all()

    if use_id:
        assert all(data.select_dtypes("int").columns == [*dimensions, "count"])
        assert all(
            data.select_dtypes("object").columns
            == [area_type, "population_type"]
        )
    else:
        assert all(data.select_dtypes("int").columns == ["count"])
        assert all(
            data.select_dtypes("object").columns
            == [area_type, *dimensions, "population_type"]
        )

    for i, row in data.drop("population_type", axis=1).iterrows():
        assert (*map(str, row[:-1]), row[-1]) == records[i]

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


@given(
    st.lists(
        st.tuples(st.text(), st.sampled_from(("microdata", "tabular"))),
        min_size=1,
        unique=True,
    )
)
def test_get_population_types(population_types):
    """Test population metadata can be filtered correctly."""

    api = CensusAPI()

    with mock.patch("census21api.wrapper.CensusAPI.get") as get:
        get.return_value = {
            "items": [
                {"name": name, "type": dtype}
                for name, dtype in population_types
            ]
        }

        available_types = api._get_population_types()

    assert isinstance(available_types, set)
    assert all(isinstance(pop_type, str) for pop_type in available_types)
    assert available_types == {
        name for name, dtype in population_types if dtype == "microdata"
    }

    get.assert_called_once_with(f"{API_ROOT}?limit=100")


@given(st.sampled_from(POPULATION_TYPES))
def test_query_population_type_json_valid(population_type):
    """Test the population querist can process valid JSON."""

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
        metadata = api._query_population_type_json(population_type)

    assert metadata == get.return_value["population_type"]

    get.assert_called_once_with(f"{API_ROOT}/{population_type}")


@given(
    st.sampled_from(POPULATION_TYPES),
    st.one_of((st.just(None), st.dictionaries(st.integers(), st.integers()))),
)
def test_query_population_type_json_invalid(population_type, result):
    """Test the population querist returns nothing on a failed call."""

    api = CensusAPI()

    with mock.patch("census21api.wrapper.CensusAPI.get") as get:
        get.return_value = result

        metadata = api._query_population_type_json(population_type)

    assert metadata is None

    get.assert_called_once_with(f"{API_ROOT}/{population_type}")


@given(st_population_types())
def test_query_population_types_valid_all_types(params):
    """Test the population querist works in the base scenario."""

    population_types, json_metadata = params

    api = CensusAPI()

    with mock.patch(
        "census21api.wrapper.CensusAPI._get_population_types"
    ) as get_pop_types, mock.patch(
        "census21api.wrapper.CensusAPI._query_population_type_json"
    ) as query_json:
        get_pop_types.return_value = population_types
        query_json.side_effect = json_metadata

        metadata = api.query_population_types()

    assert isinstance(metadata, pd.DataFrame)
    assert len(metadata) == len(population_types)
    assert metadata.columns.to_list() == [
        "name",
        "label",
        "description",
        "type",
    ]

    sorted_json_metadata = sorted(json_metadata, key=lambda x: x["name"])
    for (_, row), meta in zip(metadata.iterrows(), sorted_json_metadata):
        assert dict(row) == meta

    get_pop_types.assert_called_once_with()
    assert query_json.call_count == len(population_types)
    assert [call.args for call in query_json.call_args_list] == [
        (pop_type,) for pop_type in population_types
    ]


@given(st.lists(st.text(), min_size=1, unique=True))
def test_query_population_types_invalid(population_types):
    """Test the population querist returns None on all failed calls."""

    api = CensusAPI()

    with mock.patch(
        "census21api.wrapper.CensusAPI._get_population_types"
    ) as get_pop_types, mock.patch(
        "census21api.wrapper.CensusAPI._query_population_type_json"
    ) as query_json:
        get_pop_types.return_value = population_types
        query_json.return_value = None

        metadata = api.query_population_types()

    assert metadata is None

    get_pop_types.assert_called_once_with()
    assert query_json.call_count == len(population_types)
    assert [call.args for call in query_json.call_args_list] == [
        (pop_type,) for pop_type in population_types
    ]


@given(st_population_types(include_interested=True))
def test_query_population_types_valid_some_types(params):
    """Test the population querist can filter out some types."""

    population_types, json_metadata, interested = params

    api = CensusAPI()

    with mock.patch(
        "census21api.wrapper.CensusAPI._get_population_types"
    ) as get_pop_types, mock.patch(
        "census21api.wrapper.CensusAPI._query_population_type_json"
    ) as query_json:
        get_pop_types.return_value = population_types
        query_json.side_effect = json_metadata

        metadata = api.query_population_types(*interested)

    assert isinstance(metadata, pd.DataFrame)
    assert len(metadata) == len(interested)
    assert metadata.columns.to_list() == [
        "name",
        "label",
        "description",
        "type",
    ]
    for _, row in metadata.iterrows():
        name = row["name"]
        assert dict(row) == next(
            meta for meta in json_metadata if meta["name"] == name
        )

    get_pop_types.assert_called_once_with()
    assert query_json.call_count == len(population_types)
    assert [call.args for call in query_json.call_args_list] == [
        (pop_type,) for pop_type in population_types
    ]


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


@given(st_category_queries(feature="area-types"))
def test_query_area_type_categories_json_single_call(params):
    """Test the category querist works for area types."""

    population_type, area_type, categories = params

    api = CensusAPI()

    with mock.patch("census21api.wrapper.CensusAPI.get") as get:
        get.return_value = {"count": 1, "total_count": 1, "items": categories}
        areas = api._query_area_type_categories_json(
            population_type, area_type
        )

    assert isinstance(areas, list)
    assert len(areas) == len(categories)
    assert all(isinstance(area, dict) for area in areas)
    assert areas == categories

    get.assert_called_once_with(
        "/".join(
            (
                API_ROOT,
                population_type,
                "area-types",
                area_type,
                "areas?limit=500",
            )
        )
    )


@given(st_category_queries(feature="area-types"))
def test_query_area_type_categories_json_multiple_calls(params):
    """Test the area type category querist works for multiple calls."""

    population_type, area_type, categories = params

    api = CensusAPI()

    with mock.patch("census21api.wrapper.CensusAPI.get") as get:
        get.return_value = {
            "count": 1,
            "total_count": 2,
            "items": categories.copy(),
        }
        areas = api._query_area_type_categories_json(
            population_type, area_type
        )

    assert isinstance(areas, list)
    assert len(areas) == 2 * len(categories)
    assert all(isinstance(area, dict) for area in areas)
    assert areas == 2 * categories

    assert get.call_count == 2
    get.assert_called_with(
        "/".join(
            (
                API_ROOT,
                population_type,
                "area-types",
                area_type,
                "areas?limit=500&offset=1",
            )
        )
    )


@given(
    st_category_queries(feature="area-types"),
    st.one_of((st.just(None), st.dictionaries(st.integers(), st.integers()))),
)
def test_query_area_type_categories_json_single_call_invalid(params, result):
    """Test the category querist gives None if the first call fails."""

    population_type, area_type, _ = params

    api = CensusAPI()

    with mock.patch("census21api.wrapper.CensusAPI.get") as get:
        get.return_value = result
        areas = api._query_area_type_categories_json(
            population_type, area_type
        )

    assert areas is None

    get.assert_called_once_with(
        "/".join(
            (
                API_ROOT,
                population_type,
                "area-types",
                area_type,
                "areas?limit=500",
            )
        )
    )


@given(
    st_category_queries(feature="area-types"),
    st.one_of((st.just(None), st.dictionaries(st.integers(), st.integers()))),
)
def test_query_area_type_categories_json_multiple_call_invalid(
    params, second_response
):
    """Test the category querist gives None if the first call fails."""

    population_type, area_type, categories = params

    api = CensusAPI()

    with mock.patch("census21api.wrapper.CensusAPI.get") as get:
        first_response = {
            "count": 1,
            "total_count": 2,
            "items": categories.copy(),
        }
        get.side_effect = [first_response, second_response]
        areas = api._query_area_type_categories_json(
            population_type, area_type
        )

    assert areas is None

    assert get.call_count == 2
    get.assert_called_with(
        "/".join(
            (
                API_ROOT,
                population_type,
                "area-types",
                area_type,
                "areas?limit=500&offset=1",
            )
        )
    )


@given(st_category_queries(feature="dimensions"))
def test_query_dimension_categories_json_valid(params):
    """Test the dimension category querist works for a valid call."""

    population_type, dimension, categories = params

    api = CensusAPI()

    with mock.patch("census21api.wrapper.CensusAPI.get") as get:
        get.return_value = {
            "count": 0,
            "total_count": 1,
            "items": [
                {"id": dimension, "label": dimension, "categories": categories}
            ],
        }
        categorisations = api._query_dimension_categories_json(
            population_type, dimension
        )

    assert isinstance(categorisations, list)
    assert len(categorisations) == len(categories)
    assert all(
        isinstance(categorisation, dict) for categorisation in categorisations
    )
    assert categorisations == [
        {**cat, "dimension": dimension} for cat in categories
    ]

    get.assert_called_once_with(
        "/".join(
            (
                API_ROOT,
                population_type,
                "dimensions",
                dimension,
                "categorisations?limit=500",
            )
        )
    )


@given(
    st_category_queries(feature="dimensions"),
    st.one_of((st.just(None), st.dictionaries(st.integers(), st.integers()))),
)
def test_query_dimension_categories_json_invalid(params, result):
    """Test the dimension category querist works on a failed call."""

    population_type, dimension, _ = params

    api = CensusAPI()

    with mock.patch("census21api.wrapper.CensusAPI.get") as get:
        get.return_value = result
        categorisations = api._query_dimension_categories_json(
            population_type, dimension
        )

    assert categorisations is None

    get.assert_called_once_with(
        "/".join(
            (
                API_ROOT,
                population_type,
                "dimensions",
                dimension,
                "categorisations?limit=500",
            )
        )
    )


@given(st_category_queries())
def test_query_categories_valid(params):
    """Test the category querist works for a valid call."""

    population_type, item, categories = params

    api = CensusAPI()

    feature = "area-types" if "area_type" in categories[0] else "dimensions"
    querist_to_patch = (
        "census21api.wrapper.CensusAPI."
        f"_query_{feature.replace('-', '_')[:-1]}_categories_json"
    )

    with mock.patch(querist_to_patch) as query:
        query.return_value = categories
        result = api.query_categories(population_type, feature, item)

    assert isinstance(result, pd.DataFrame)
    assert (result["population_type"] == population_type).all()
    assert pd.DataFrame(categories).equals(
        result.drop("population_type", axis=1)
    )

    query.assert_called_once_with(population_type, item)


@given(st_category_queries())
def test_query_categories_invalid(params):
    """Test the category querist returns none on a failed call."""

    population_type, item, categories = params

    api = CensusAPI()

    feature = "area-types" if "area_type" in categories[0] else "dimensions"
    querist_to_patch = (
        "census21api.wrapper.CensusAPI."
        f"_query_{feature.replace('-', '_')[:-1]}_categories_json"
    )

    with mock.patch(querist_to_patch) as query, mock.patch(
        "census21api.wrapper.pd.json_normalize"
    ) as json:
        query.return_value = None
        result = api.query_categories(population_type, feature, item)

    assert result is None

    query.assert_called_once_with(population_type, item)
    json.assert_not_called()
