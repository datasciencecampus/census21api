"""Module for the API wrapper."""

import warnings
from json import JSONDecodeError
from typing import Any, Dict, List, Literal, Optional, Set, Union

import pandas as pd
import requests
from requests.models import Response

from census21api.constants import API_ROOT

JSONLike = Optional[Union[List[dict], Dict[str, Any]]]
DataLike = Optional[pd.DataFrame]


class CensusAPI:
    """A wrapper for the 2021 England and Wales Census API."""

    def _process_response(self, response: Response) -> JSONLike:
        """
        Validate and extract data from a response.

        Valid responses can be decoded from JSON and have a "successful"
        status code (200-299).

        Parameters
        ----------
        response : requests.Response
            Response to be processed.

        Returns
        -------
        data : dict or None
            Data dictionary if the response is valid and `None` if not.
        """

        if not 200 <= response.status_code <= 299:
            warnings.warn(
                "\n".join(
                    (
                        f"Unsuccessful GET from {response.url}",
                        f"Status code: {response.status_code}",
                        response.text,
                    )
                ),
                UserWarning,
            )
            return None

        try:
            return response.json()
        except JSONDecodeError as e:
            warnings.warn(
                "\n".join(
                    (f"Error decoding data from {response.url}:", str(e))
                ),
                UserWarning,
            )

    def get(self, url: str) -> JSONLike:
        """
        Make a call to, and retrieve some data from, the API.

        Parameters
        ----------
        url : str
            URL from which to retrieve data.

        Returns
        -------
        data : dict or None
            JSON data from the response of this API call if it is
            successful, and `None` otherwise.
        """

        response = requests.get(url, verify=True)

        return self._process_response(response)

    def _query_table_json(
        self, population_type: str, area_type: str, dimensions: List[str]
    ) -> JSONLike:
        """
        Retrieve the JSON for a table query from the API.

        Parameters
        ----------
        population_type : str
            Population type to query.
            See `census21api.constants.POPULATION_TYPES`.
        area_type : str
            Area type to query.
            See `census21api.constants.AREA_TYPES_BY_POPULATION_TYPE`.
        dimensions : list of str
            Dimensions to query.
            See `census21api.constants.DIMENSIONS_BY_POPULATION_TYPE`.

        Returns
        -------
        data : dict or None
            JSON data from the API call if it is successful, and `None`
            otherwise.
        """

        base = "/".join((API_ROOT, population_type, "census-observations"))
        parameters = f"area-type={area_type}&dimensions={','.join(dimensions)}"
        url = "?".join((base, parameters))

        data = self.get(url)

        return data

    def query_table(
        self,
        population_type: str,
        area_type: str,
        dimensions: List[str],
        use_id: bool = True,
    ) -> DataLike:
        """
        Query a custom table from the API.

        This method connects to the `census-observations` endpoint
        `/{population_type}/census-observations` with query parameters
        `?area-type={area_type}&dimensions={','.join(dimensions)}`.

        Parameters
        ----------
        population_type : str
            Population type to query.
            See `census21api.constants.POPULATION_TYPES`.
        area_type : str
            Area type to query.
            See `census21api.constants.AREA_TYPES_BY_POPULATION_TYPE`.
        dimensions : list of str
            Dimensions to query.
            See `census21api.constants.DIMENSIONS_BY_POPULATION_TYPE`.
        use_id : bool, default True
            If `True` (the default) use the ID for each dimension and
            area type. Otherwise, use the full label.

        Returns
        -------
        data : pandas.DataFrame or None
            Data frame containing the data from the API call if it is
            successful and without blocked pairs, and `None` otherwise.
        """

        table_json = self._query_table_json(
            population_type, area_type, dimensions
        )

        if isinstance(table_json, dict) and "observations" in table_json:
            if table_json.get("blocked_areas"):
                warnings.warn(
                    "Dimensions include a blocked pair - no table available.",
                    UserWarning,
                )
                return None

            records = _extract_records_from_observations(
                table_json["observations"], use_id
            )
            columns = (area_type, *dimensions, "count")
            table = pd.DataFrame(records, columns=columns)
            table["population_type"] = population_type

            if use_id:
                table = table.astype({dim: int for dim in dimensions})

            return table

    def _get_population_types(self) -> Set[str]:
        """
        Retrieve the set of available population types from the API.

        Returns
        -------
        available_types : set of str
            Set of codes for the available population types.
        """

        json = self.get(f"{API_ROOT}?limit=100")
        available_types = set(
            item["name"]
            for item in json["items"]
            if item["type"] == "microdata"
        )

        return available_types

    def _query_population_type_json(self, population_type: str) -> JSONLike:
        """
        Query the metadata for a population type in JSON format.

        Parameters
        ----------
        population_type : str
            Population type to be queried.

        Returns
        -------
        metadata : dict or None
            Dictionary of population type metadata if the call succeeds,
            and `None` if not.
        """

        url = "/".join((API_ROOT, population_type))
        json = self.get(url)

        if isinstance(json, dict):
            return json.get("population_type")

    def query_population_types(self, *population_types: str) -> DataLike:
        """
        Query the metadata for a set of population types.

        This method finds all available population types and retrieves
        their metadata from the `population-types` endpoint, returning
        the combined information as a data frame.

        Parameters
        ----------
        population_types : str
            Population types to be queried. If not specified, metadata
            on all the population types are returned. See
            `census21api.constants.POPULATION_TYPES`.

        Returns
        -------
        metadata : pandas.DataFrame or None
            Data frame with all the population type metadata. If none of
            the API calls are successful, returns `None`.
        """

        available_types = self._get_population_types()

        metas = []
        for population_type in available_types:
            meta = self._query_population_type_json(population_type)
            if isinstance(meta, dict) and "name" in meta:
                metas.append(meta)

        if metas:
            metadata = pd.DataFrame(metas)
            if population_types:
                metadata = metadata[metadata["name"].isin(population_types)]

            return metadata.sort_values("name", ignore_index=True)

    def query_feature(
        self,
        population_type: str,
        feature: Literal["area-types", "dimensions"],
        *items: str,
    ) -> DataLike:
        """
        Query metadata on a feature for a population type.

        This method connects to the `area-types` and `dimensions`
        endpoints (ie. `/{population_type}/{endpoint}`) and returns a
        data frame format of the metadata there.

        Parameters
        ----------
        population_type : str
            Population type to query.
        feature : {"area-types", "dimensions"}
            Endpoint of the feature to query.
        *items : str
            Items to query from the endpoint. If not specified,
            return all items at the endpoint. For dimensions, see
            `census21api.constants.DIMENSIONS_BY_POPULATION_TYPE`, and
            `census21api.constants.AREA_TYPES_BY_POPULATION_TYPE` for
            area types.

        Returns
        -------
        metadata : pd.DataFrame or None
            Data frame with the metadata if the call succeeds, and
            `None` if not.
        """

        url = "/".join((API_ROOT, population_type, f"{feature}?limit=500"))
        json = self.get(url)

        if isinstance(json, dict) and "items" in json:
            metadata = pd.json_normalize(json["items"])
            metadata["population_type"] = population_type
            if items:
                metadata = metadata[metadata["id"].isin(items)]

            return metadata.reset_index(drop=True)

    def _query_area_type_categories_json(
        self, population_type: str, area_type: str
    ) -> JSONLike:
        """
        Query metadata for an area type's categories in JSON format.

        Parameters
        ----------
        population_type : str
            Population type to query.
        area_type : str
            Area type to query.

        Returns
        -------
        areas : dict or None
            Dictionary with the area type categories if the calls
            succeed, and `None` if any fail.
        """

        url = "/".join(
            (
                API_ROOT,
                population_type,
                "area-types",
                area_type,
                "areas?limit=500",
            )
        )
        json = self.get(url)

        if isinstance(json, dict) and "items" in json:
            areas = json["items"]
            total_counted = json["count"]
            while total_counted < json["total_count"]:
                json = self.get(url + f"&offset={total_counted}")
                if not (isinstance(json, dict) and "items" in json):
                    return None

                areas.extend(json["items"])
                total_counted += json["count"]

            return areas

    def _query_dimension_categories_json(
        self, population_type: str, dimension: str
    ) -> JSONLike:
        """
        Query metadata for a dimension's categories in JSON format.

        Parameters
        ----------
        population_type : str
            Population type to query.
        dimension : str
            Dimension to query.

        Returns
        -------
        categorisations : list or None
            List with the dimension category metadata if the call
            succeeds, and `None` if not.
        """

        url = "/".join(
            (
                API_ROOT,
                population_type,
                "dimensions",
                dimension,
                "categorisations?limit=500",
            )
        )
        json = self.get(url)

        if isinstance(json, dict) and "items" in json:
            item = next(
                item for item in json["items"] if item["id"] == dimension
            )
            categorisations = [
                {**cat, "dimension": dimension} for cat in item["categories"]
            ]

            return categorisations

    def query_categories(
        self,
        population_type: str,
        feature: Literal["area-types", "dimensions"],
        item: str,
    ) -> DataLike:
        """
        Query metadata on the categories of a particular feature item.

        This method connects to different endpoints depending on
        `feature`:

        - `/{population_type}/area-types/{item}/areas`
        - `/{population_type}/dimensions/{item}/categorisations`

        Parameters
        ----------
        population_type : str
            Population type to query.
        feature : {"area-types", "dimensions"}
            Endpoint of the feature to query.
        item : str
            ID of the item in the feature to query.

        Returns
        -------
        categories : pd.DataFrame or None
            Metadata on the categories for the feature item if the call
            succeeds, and `None` if not.
        """

        if feature == "area-types":
            categories = self._query_area_type_categories_json(
                population_type, item
            )
        if feature == "dimensions":
            categories = self._query_dimension_categories_json(
                population_type, item
            )

        if isinstance(categories, (dict, list)):
            categories = pd.json_normalize(categories)
            categories["population_type"] = population_type

            return categories


def _extract_records_from_observations(
    observations: List[Dict[str, Any]], use_id: bool
) -> List[tuple]:
    """
    Extract record information from a set of JSON observations.

    Parameters
    ----------
    observations : dict
        Dictionary of dimension options and count for the observation.
    use_id : bool
        If `True`, use the ID for each dimension option and area type.
        Otherwise, use the full label.

    Returns
    -------
    records : list of tuple
        List of records to be formed into a data frame.
    """

    option = f"option{'_id' * use_id}"

    records = []
    for observation in observations:
        record = (
            *(dimension[option] for dimension in observation["dimensions"]),
            observation["observation"],
        )
        records.append(record)

    return records
