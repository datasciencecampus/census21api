import requests
import json
import pandas as pd
from typing import List, Dict, Any
from requests.models import Response

class APIWrapper:
    def __init__(self, logger: bool = False) -> None:
        self._logger = logger
        self._current_data = None
        self.set_population_types_available()
        self.set_areas_by_pop_types()
        self.set_dims_by_pop_types()

        
    def _valid_status_code(self, response: Response) -> bool:
        """
        Checks response codes for https requests
            Informational responses (100 – 199)
            Successful responses (200 – 299)
            Redirection messages (300 – 399)
            Client error responses (400 – 499)
            Server error responses (500 – 599)

        Args:
            response: requests HTTP response object.

        Returns:
            Boolean.
        """
        if response.status_code >= 200 and response.status_code <= 299:
            return True
        return False


    def get(self, url: str) -> Dict[str, Any]:
        """
        get function with minimal validation.

        Args:
            url: str = the url for the API call.

        Returns:
            dictionary of json format from api.

        Raises:
            Doesn't raise an error but prints the url and the response code on failure.
        """
        response: Response = requests.get(url=url, verify=True)
        data_out = response.json()

        # checks if the response code was valid
        if self._valid_status_code(response):
            self._current_data = data_out
        else:
            if self._logger:
                print(f'response status code: {response.status_code} for url: {url}')
            self._current_data = None    
        
        
    def set_population_types_available(self) -> List[str]:
        """
        Loops through the possible codes to see if returns data.
        Saves successful codes to a list

        Returns:
            list of the successful population codes.
        """        
        root_string: str = 'https://api.beta.ons.gov.uk/v1/population-types'
        self.get(root_string)

        # list comprehension, splits out the suspected population codes from the longer call_code response
        # converts to upper case to mirror upper case shown in the github demo found here: 
            # https://github.com/GSS-Cogs/knowledge/blob/main/api/ons_local_census_api_walkthrough_python.ipynb
        # converts to set to remove duplicates and back to list for easy manipulation
        possible_codes: List[str] = list(set([item['name'].split('-')[3].upper() for item in self._current_data['items']]))
        working_pop_codes: List[str] = []

        for cd in possible_codes:
            search_string = f'https://api.beta.ons.gov.uk/v1/population-types/{cd}'
            self.get(search_string)

            # if the attempt returns none we know get has failed
            if self._current_data is not None:
                # sometimes the API returns a json with "errors" as a key
                # that also counts as failing so we ignore that
                if 'errors' not in self._current_data.keys():
                    working_pop_codes.append(cd)

        self._valid_pop_types = working_pop_codes 
    
    
    def get_population_types_available(self) -> List[str]:
        
        return self._valid_pop_types
    
    
    def get_parameters_available(self, pop_type: str, parameter_type: str) -> Dict[str, str]:
        """
        get the available parameters for either area-type or dimensions

        Args:
            pop_type: str = UR, HRP, HH
            parameter_type: str = area-types, dimensions

        Returns:
            dictionary of descriptive name and relevant id.
        """
        # the API structure of parameter_type coming after population type means we can use the same \
        # function for two calls, if this changes at some point this function will break
        # TODO add some error checking for the pop and parameter type inputs
        self.get(f"https://api.beta.ons.gov.uk/v1/population-types/{pop_type}/{parameter_type}")

        # dictionary comprehension to connect the description with the useful id code
        if self._current_data['items'] is not None:
            possible_params = {item['label'] : item['id'] for item in self._current_data['items']}  
            return possible_params  
        else:
            if self._logger:
                print(f"Unable to iterate over NoneType for {pop_type = } and {parameter_type = }")
    
    def set_areas_by_pop_types(self) -> None:
        """
        Loops over the valid pop types and creates a dict of valid area types for each of them
        """
        self._area_dict: Dict[str, str] = {}
        
        for pt in self._valid_pop_types:
            self._area_dict[pt] = self.get_parameters_available(pt, 'area-types')
    
    
    def set_dims_by_pop_types(self) -> None:
        """
        Loops over the valid pop types and creates a dict of valid dimensions for each of them
        """        
        self._dims_dict: Dict[str, str] = {}
        
        for pt in self._valid_pop_types:
            self._dims_dict[pt] = self.get_parameters_available(pt, 'dimensions')
      
    
    def get_areas_by_pop_type(self, pop_type: str) -> Dict[str, str]:
        return self._area_dict[pop_type]
    
    
    def get_dims_by_pop_type(self, pop_type: str) -> Dict[str, str]:
        return self._dims_dict[pop_type]    
    
    
    def build_search_string(self, search_pop_type: str = None, search_dimensions: str = None, search_area_type: str = None) -> str:
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
        search_string: str = f"https://api.beta.ons.gov.uk/v1/population-types/{search_pop_type}/census-observations?"


        # if not searching for dimensions we don't want to add this because we don't know what the API would return
        if search_dimensions is not None:
            search_string += f'dimensions={search_dimensions}'

            # checking to see if anything else is being searched for because then we'll need this "&"
            # don't worry that this results in the print out including "&amp;" it still works
            if search_area_type is not None:
                search_string += '&'

        # same reasoning as search_dimensions above
        if search_area_type is not None:
            search_string += f'area-type={search_area_type}'

        return search_string  
    
    
    def query_api(self, search_pop_type: str = None, search_dimensions: str = None, search_area_type: str = None) -> pd.DataFrame:
        """
            wrapper function to query api

        Args:
            search_pop_type: str = the population code
            search_dimensions: str = the dimensions
            search_area_type: str = the area type            

        Returns:
            Dataframe for analysis.    
        """
        search_string: str = self.build_search_string(search_pop_type, search_dimensions, search_area_type) 
        self.get(search_string)
        return self.create_observation_df()
    
    
    def create_observation_df(self) -> pd.DataFrame:
        """
        builds the df for the data from the API

        Args:
            returned_data_json: dict = the data returned by the search_string

        Returns:
            Dataframe for analysis.    
        """
        # we only want the observations data
        data: Dict[str, Any] = self._current_data['observations']

        data_list: List[Dict[str, Any]] = []

        for item_dict in data:
            # this temp dict will make each row of our dataframe
            inner_dict = {}

            for sub_item in item_dict['dimensions']:
                # dimension_id holds the name of the dimension, option_id is the response
                # option = the word description of the value
                # option_id = the ONS encoding for that item
                inner_dict[sub_item['dimension_id']] = sub_item['option']

            # the count of observations for this dimension_id and option_id
            inner_dict['count'] = item_dict['observation'] 

            # add row of data to list
            data_list.append(inner_dict)

        output_df = pd.DataFrame(data_list)
        return output_df
    