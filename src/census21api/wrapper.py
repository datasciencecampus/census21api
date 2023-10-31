"""Module for the API wrapper."""

import warnings
from json import JSONDecodeError
from typing import Any, Dict, List, Literal, Optional

import pandas as pd
import requests
from requests.models import Response

from census21api.constants import API_ROOT

DataLike = Optional[Dict[str, Any]]


class CensusAPI:
    """
    A wrapper for the 2021 England and Wales Census API.

    Parameters
    ----------
    logger : bool, default False
        Whether to be verbose about issues when connecting to the API.

    Attributes
    ----------
    _current_data : dict or None
        Data dictionary from the most recent API call. If no call has
        been made or the last call failed, this is `None`.
    _current_url : str or None
        URL of the most recent API call. If no call has been made, this
        is `None`.
    """

    def __init__(self, logger: bool = False) -> None:
        self._logger: bool = logger
        self._current_url: str = None
        self._current_data: dict = None

    def _process_response(self, response: Response) -> DataLike:
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

        data = None
        if not 200 <= response.status_code <= 299:
            if self._logger:
                warnings.warn(
                    "\n".join(
                        (
                            f"Unsuccessful GET from {self._current_url}",
                            f"Status code: {response.status_code}",
                            response.body,
                        )
                    ),
                    UserWarning,
                )
            return data

        try:
            data = response.json()
        except JSONDecodeError as e:
            if self._logger:
                warnings.warn(
                    "\n".join(
                        (
                            f"Error decoding data from {self._current_url}:",
                            str(e),
                        )
                    ),
                    UserWarning,
                )

        return data

    def get(self, url: str) -> DataLike:
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

        self._current_url = url
        response = requests.get(url, verify=True)

        data = self._process_response(response)
        self._current_data = data

        return self._current_data

    def _query_table_json(
        self, population_type: str, area_type: str, dimensions: List[str]
    ) -> DataLike:
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
    ) -> Optional[pd.DataFrame]:
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
            successful, and `None` otherwise.
        """

        table_json = self._query_table_json(
            population_type, area_type, dimensions
        )
        data = None

        if isinstance(table_json, dict) and "observations" in table_json:
            records = _extract_records_from_observations(
                table_json["observations"], use_id
            )
            columns = (area_type, *dimensions, "count")
            data = pd.DataFrame(records, columns=columns)
            data["population_type"] = population_type

            return data

    def query_population_type(
        self, population_type: str
    ) -> Optional[pd.Series]:
        """
        Query the metadata for a population type.

        This method connects to the `population-types` endpoint for a
        population type (ie. `/{population_type}`) and returns a series
        format of the metadata there.

        Parameters
        ----------
        population_type : str
            Population type to be queried.
            See `census21api.constants.POPULATION_TYPES`.

        Returns
        -------
        metadata : pd.Series or None
            Series with the population type metadata if the call
            succeeds, and `None` if not.
        """

        url = "/".join((API_ROOT, population_type))
        json = self.get(url)
        metadata = None

        if isinstance(json, dict) and "population_type" in json:
            metadata = pd.Series(json["population_type"])

        return metadata

    def query_feature(
        self,
        population_type: str,
        feature: Literal["area-types", "dimensions"],
        *items: str,
    ) -> Optional[pd.DataFrame]:
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
        metadata = None

        if isinstance(json, dict) and "items" in json:
            metadata = pd.json_normalize(json["items"])
            metadata["population_type"] = population_type
            if items:
                metadata = metadata[metadata["id"].isin(items)]

        return metadata

    def query_categories(
        self,
        population_type: str,
        feature: Literal["area-types", "dimensions"],
        item: str,
    ) -> Optional[pd.DataFrame]:
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

        endpoint = "areas" if feature == "area-types" else "categorisations"
        url = "/".join(
            (API_ROOT, population_type, feature, item, f"{endpoint}?limit=500")
        )
        json = self.get(url)
        categories = None

        if isinstance(json, dict) and "items" in json:
            items = json["items"]

            total_counted = json["count"]
            while total_counted < json["total_count"]:
                json = self.get(url + f"&offset={total_counted}")
                items.extend(json["items"])
                total_counted += json["count"]

            categories = pd.json_normalize(items)
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
