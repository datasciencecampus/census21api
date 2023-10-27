"""Module for the API wrapper."""

import itertools
import json
import warnings
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from requests.models import Response

from census21api.constants import API_ROOT, DIMENSIONS_BY_POPULATION_TYPE

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
        except json.JSONDecodeError as e:
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
            Population type to query. See `census21api.POPULATION_TYPES`.
        area_type : str
            Area type to query.
            See `census21api.AREA_TYPES_BY_POPULATION_TYPE`.
        dimensions : list of str
            Dimensions to query.
            See `census21api.DIMENSIONS_BY_POPULATION_TYPE`.

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

        Parameters
        ----------
        population_type : str
            Population type to query. See `census21api.POPULATION_TYPES`.
        area_type : str
            Area type to query.
            See `census21api.AREA_TYPES_BY_POPULATION_TYPE`.
        dimensions : list of str
            Dimensions to query.
            See `census21api.DIMENSIONS_BY_POPULATION_TYPE`.
        use_id : bool, default True
            If `True` (the default) use the ID for each dimension and
            area type. Otherwise, use the full label.

        Returns
        -------
        data : pandas.DataFrame or None
            Data frame containing the data from the API call if it is
            successful, and `None` otherwise.
        """

        data = self._query_table_json(population_type, area_type, dimensions)

        if isinstance(data, dict) and "observations" in data:
            records = _extract_records_from_observations(
                data["observations"], use_id
            )

            columns = (area_type, *dimensions, "count")
            data = pd.DataFrame(records, columns=columns)
            data["population_type"] = population_type

            return data

    def get_summary_by_dimensions(self) -> Dict[str, pd.DataFrame]:
        """
            builds and returns summaries of the data grouped by dimension

        Returns:
            a dict of both absolute counts for each dimension and proportions
            normalised by the total.
        """
        if self._query_df is None:
            print("No query data available to summarise.")
            return None

        self._groupby_dim_dict = {}
        for dim in self._searched_dims:
            groupby_ = self._query_df.groupby(dim)[["count"]].sum()
            denom = groupby_.sum()
            self._groupby_dim_dict[dim] = groupby_
            self._groupby_dim_dict[f"{dim}_normalised"] = groupby_ / denom

        return self._groupby_dim_dict

    def get_summary_by_area(self) -> Dict[str, pd.DataFrame]:
        """
            builds and returns summaries of the data grouped by area

        Returns:
            a dict of both absolute counts for each area and proportions
            normalised by the total.
        """
        if self._query_df is None:
            print("No query data available to summarise.")
            return None

        self._groupby_area_dict = {}
        groupby_ = self._query_df.groupby(self._searched_area)[["count"]].sum()
        denom = groupby_.sum()
        self._groupby_area_dict[self._searched_area] = groupby_
        self._groupby_area_dict[f"{self._searched_area}_normalised"] = (
            groupby_ / denom
        )

        return self._groupby_area_dict

    def loop_through_variables(self, residence_code, region):
        """
        Collects data for all variable combinations relating to residence/region

        Args:
            residence_code: str = code relating to residence, eg. 'HH', 'UR'
            region: str = regional code relating to region, eg. 'rgns'

        Returns:
            .csv file for all possible combinations
        """
        dims = list(DIMENSIONS_BY_POPULATION_TYPE[residence_code].values())
        combos = [sorted(i) for i in itertools.product(dims, dims)]
        trimmed_combos = sorted(list(map(list, set(map(frozenset, combos)))))
        no_single_searches = [i for i in trimmed_combos if len(i) == 2]

        for combination in no_single_searches:
            stripped_string = ",".join(combination)
            _ = self.query_api(residence_code, stripped_string, region)


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
