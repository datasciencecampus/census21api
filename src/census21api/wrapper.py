"""Module for the API wrapper."""

import itertools
import json
import os
import warnings
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from requests.models import Response

from census21api.constants import API_ROOT, DIMENSIONS_BY_POPULATION_TYPE


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

    def _process_response(
        self, response: Response
    ) -> Optional[Dict[str, Any]]:
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

    def get(self, url: str) -> Optional[Dict[str, Any]]:
        """
        get function with minimal validation.

        Args:
            url: str = the url for the API call.

        Returns:
            dictionary of json format from api.

        Raises:
            Doesn't raise an error but prints the url and the response code on failure.
        """
        self._current_url: str = url
        response: Response = requests.get(url=self._current_url, verify=True)
        # checks if the response code was valid
        self._current_data = self._process_reponse(response)
        return self._current_data

    def build_search_string(
        self,
        search_pop_type: str,
        search_dimensions: str = None,
        search_area_type: str = None,
    ) -> str:
        """
        builds the url based on the search parameters

        Args:
            search_pop_type: str = the population code
            search_dimensions: str = the dimensions
            search_area_type: str = the area type

        Returns:
            the url for the API call
        """
        # base string to build search off
        search_string = f"{API_ROOT}/{search_pop_type}/census-observations?"

        parameter_strings = (
            f"{name}={param}"
            for name, param in zip(
                ("dimensions", "area-type"),
                (search_dimensions, search_area_type),
            )
            if param is not None
        )
        search_string += "&".join(parameter_strings)

        return search_string

    def query_api(
        self,
        search_pop_type: str,
        search_dimensions: str = None,
        search_area_type: str = None,
        create_csv: bool = True,
    ) -> pd.DataFrame:
        """
            wrapper function to query api

        Args:
            search_pop_type: str = the population code
            search_dimensions: str = the dimensions
            search_area_type: str = the area type

        Returns:
            Dataframe for analysis.
        """
        self._searched_dims = search_dimensions.split(",")
        self._searched_area = search_area_type
        search_string: str = self.build_search_string(
            search_pop_type, search_dimensions, search_area_type
        )
        self.get(search_string)
        data = self.create_observation_df()

        if isinstance(data, pd.DataFrame) and create_csv:
            folder_path = "data/output/"
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            data.to_csv(
                f"data/output/{search_pop_type}_{search_dimensions.replace(',','_')}_{search_area_type}.csv"
            )

        return data

    def create_observation_df(self) -> pd.DataFrame:
        """
        builds the df for the data from the API

        Args:
            returned_data_json: dict = the data returned by the search_string

        Returns:
            Dataframe for analysis.
        """
        # to make the program flow continue for mass testing
        if (self._current_data is None) or (
            self._current_data["observations"] is None
        ):
            return None

        # we only want the observations data
        data: Dict[str, Any] = self._current_data["observations"]

        data_list: List[Dict[str, Any]] = []

        for item_dict in data:
            # this temp dict will make each row of our dataframe
            inner_dict = {}

            for sub_item in item_dict["dimensions"]:
                # dimension_id holds the name of the dimension, option_id is the response
                # option = the word description of the value
                # option_id = the ONS encoding for that item
                inner_dict[sub_item["dimension_id"]] = sub_item["option"]
                inner_dict[f'{sub_item["dimension_id"]}_id'] = sub_item[
                    "option_id"
                ]

            # the count of observations for this dimension_id and option_id
            inner_dict["count"] = item_dict["observation"]

            # add row of data to list
            data_list.append(inner_dict)

        self._query_df = pd.DataFrame(data_list)
        return self._query_df

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
