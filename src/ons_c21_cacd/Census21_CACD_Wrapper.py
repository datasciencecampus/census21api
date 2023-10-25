import requests
import json
import pandas as pd
from typing import List, Dict, Any, Set, Optional
from requests.models import Response
import itertools
import os


class APIWrapper:
    def __init__(self, logger: bool = False) -> None:
        self._logger = logger
        self._current_data = None
        self.set_root_string('https://api.beta.ons.gov.uk/v1/population-types')
        self.set_population_types_available()
        self.set_areas_by_pop_types()
        self.set_dims_by_pop_types()
        

    def set_root_string(self, root_str: str) -> None:
        """
        set the root string for the API
        """
        self._root_string = root_str
    
    
    def get_root_string(self) -> str:
        """
        getter function for the root string
        """
        return self._root_string
    
        
    def _validate_status_code(self, response: Response) -> bool:
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
        valid_response = 200 <= response.status_code <= 299
        if self._logger and not valid_status_code:
            print(f'response status code: {response.status_code} for url: {self._current_url}')        
        return valid_response

    
    def _process_reponse(self, response: Response) -> Optional[Dict[str, Any]]:
        """
        get function with minimal validation.

        Args:
            response: Response = the response from the API call.

        Returns:
            dictionary of json format from api.       
        """
        if not self._validate_status_code(response):
            return None
        try:
            data_out: Dict[str, Any] = response.json()
        except json.JSONDecodeError as e:
            data_out = None
            if self._logger:
                print(f'{e} for url: {self._current_url} returning None')
        return data_out
    

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
    
    
    def extract_pop_type_from_item(self, item: Dict[str, str]) -> str:
        """
        helper function for splitting pop type
        """
        return item["name"].split("-")[3].upper()
    
    
    def set_population_types_available(self) -> List[str]:
        """
        Loops through the possible codes to see if returns data.
        Saves successful codes to a list

        Returns:
            list of the successful population codes.
        """        
        
        root_string: str = self.get_root_string()
        self.get(root_string)

        # list comprehension, splits out the suspected population codes from the longer call_code response
        # converts to upper case to mirror upper case shown in the github demo found here: 
            # https://github.com/GSS-Cogs/knowledge/blob/main/api/ons_local_census_api_walkthrough_python.ipynb
        # converts to set to remove duplicates and back to list for easy manipulation
        possible_codes: Set[str] = set([self.extract_pop_type_from_item(item) for item in self._current_data['items']])
        working_pop_codes: List[str] = []

        for cd in possible_codes:
            search_string = f"{root_string}/{cd}"
            self.get(search_string)

            # if the attempt returns none we know get has failed
            # sometimes the API returns a json with "errors" as a key
            # that also counts as failing so we ignore that
            if isinstance(self._current_data, dict) and "errors" not in self._current_data.keys():
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
        self.get(f"{self.get_root_string()}/{pop_type}/{parameter_type}")

        # dictionary comprehension to connect the description with the useful id code
        if isinstance(self._current_data['items'], list):
            possible_params = {item['label'] : item['id'] for item in self._current_data['items']}  
            return possible_params  
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
        """
        Returns:
            a dictionary of available area codes for the input arg pop_type
        """
        return self._area_dict[pop_type]
    
    
    def get_dims_by_pop_type(self, pop_type: str) -> Dict[str, str]:
        """
        Returns:
            a dictionary of available dimensions for the input arg pop_type
        """
        return self._dims_dict[pop_type]    
    
    
    def build_search_string(self, search_pop_type: str, search_dimensions: str = None, search_area_type: str = None) -> str:
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
        search_string: str = f"{self.get_root_string()}/{search_pop_type}/census-observations?"

        parameter_strings = (
            f"{name}={param}"
            for name, param in zip(("dimensions", "area-type"), (search_dimensions, search_area_type))
            if param is not None
        )
        search_string += "&".join(parameter_strings)

        return search_string  
    

    def query_api(self, search_pop_type: str, search_dimensions: str = None, search_area_type: str = None, create_csv: bool = True) -> pd.DataFrame:
        """
            wrapper function to query api

        Args:
            search_pop_type: str = the population code
            search_dimensions: str = the dimensions
            search_area_type: str = the area type
 
        Returns:
            Dataframe for analysis.    
        """
        self._searched_dims = search_dimensions.split(',')
        self._searched_area = search_area_type
        search_string: str = self.build_search_string(search_pop_type, search_dimensions, search_area_type) 
        self.get(search_string)
        data = self.create_observation_df()
        
        if isinstance(data, pd.DataFrame) and create_csv:
            folder_path = 'data/output/'
            if not os.path.exists(folder_path):
                os.makedirs(folder_path) 
            data.to_csv(f"data/output/{search_pop_type}_{search_dimensions.replace(',','_')}_{search_area_type}.csv")
            
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
        if (self._current_data is None) or (self._current_data['observations'] is None):
            return None
        
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
                inner_dict[f'{sub_item["dimension_id"]}_id'] = sub_item['option_id']

            # the count of observations for this dimension_id and option_id
            inner_dict['count'] = item_dict['observation'] 

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
            print('No query data available to summarise.')
            return None
        
        self._groupby_dim_dict = {}
        for dim in self._searched_dims:
            groupby_ = self._query_df.groupby(dim)[['count']].sum()
            denom = groupby_.sum()
            self._groupby_dim_dict[dim] = groupby_
            self._groupby_dim_dict[f'{dim}_normalised'] = groupby_ / denom
            
        return self._groupby_dim_dict
    
    
    def get_summary_by_area(self) -> Dict[str, pd.DataFrame]:
        """
            builds and returns summaries of the data grouped by area
         
        Returns:
            a dict of both absolute counts for each area and proportions
            normalised by the total.    
        """        
        if self._query_df is None:
            print('No query data available to summarise.')
            return None
        
        self._groupby_area_dict = {}
        groupby_ = self._query_df.groupby(self._searched_area)[['count']].sum()
        denom = groupby_.sum()
        self._groupby_area_dict[self._searched_area] = groupby_
        self._groupby_area_dict[f'{self._searched_area}_normalised'] = groupby_ / denom
            
        return self._groupby_area_dict
    
    
    def loop_through_variables(self, residence_code, region):
        '''
        Collects data for all variable combinations relating to residence/region
            
        Args:
            residence_code: str = code relating to residence, eg. 'HH', 'UR'
            region: str = regional code relating to region, eg. 'rgns'
            
        Returns:
            .csv file for all possible combinations    
        '''   
        dims = list(self.get_dims_by_pop_type(residence_code).values())
        combos = [sorted(i) for i in itertools.product(dims, dims)]
        trimmed_combos = sorted(list(map(list, set(map(frozenset, combos)))))
        no_single_searches = [i for i in trimmed_combos if len(i) == 2]
        
        for combination in no_single_searches:
            stripped_string = ','.join(combination)
            data = self.query_api(residence_code, stripped_string, region)
