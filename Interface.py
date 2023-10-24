from tkinter import *
from functools import partial
from Census21_CACD_Wrapper import APIWrapper
FONT = ("arial",10)

class Interface():
    def __init__(self, api):
        self.configure_window()
        self.start_selections()
        
        # Define variables
        self.dimension_drop_1 = None
        self.dimension_drop_2 = None
        self.regional_drop = None
        self.api = api


    def configure_window(self):
        '''
        Configure window for interface usage
        '''
        self.window = Tk()
        self.window.title('Census API')
        self.window.configure(padx=50, pady=50)


    def drop_config_button(self, text, selection, row, column, command):
        '''
        Create a dropdown with a button

        Args:
            text: str = The label for dropdown
            selection: iterable object =  The options for the dropdown
            row: int = The row to place the dropdown
            colum: int = The column to place the dropdown
            command: function = The command to execute when the button is clicked

        Returns:
            dropdown list as object
        '''
        label = Label(text=text, font=FONT)
        label.grid(row=row, column=column)

        variable = StringVar(self.window)
        drop_list = OptionMenu(self.window, variable, *selection)
        variable.set(text)
        drop_list.grid(row=row+1, column=column)

        residence_select = Button(text="Select", command=command)
        residence_select.grid(row=row+2, column=column)

        return drop_list


    def drop_config(self, text, selection, row, column):
        '''
        Create a dropdown without a button

        Args:
            text: str = The label for dropdown
            selection: iterable object =  The options for the dropdown
            row: int = The row to place the dropdown
            colum: int = The column to place the dropdown

        Returns:
             dropdown list as object
        '''
        label = Label(text=text, font=FONT)
        label.grid(row=row, column=column)

        variable = StringVar(self.window)
        drop_list = OptionMenu(self.window, variable, *selection)
        variable.set(text)
        drop_list.grid(row=row+1, column=column)

        return drop_list


    def retrieve_res_input(self):
        '''
        Retrieve the selection of 'residence dropdown list' and returns abbreviation (abbreviation used in API call)
        '''
        output = self.residence_drop.cget('text')
        if output == 'Usual Residence':
            self.residence_code = 'UR'
        elif output == 'Household':
            self.residence_code = 'HH'
        else:
            self.residence_code = 'HRP'

        self.dimension_list = self.list_dimensions()
        self.create_dimension_selection()


    def execute_api_call(self):
        '''
        Query API and save data to csv file in '/data/output/'

        Returns:
             Saves Data to .csv
        '''
        dim_1 = self.dimension_drop_1.cget('text')
        dim_2 = self.dimension_drop_2.cget('text')
        self.get_region()
        
        data = self.api.query_api(self.residence_code, f'{dim_1},{dim_2}', self.region)


    def create_dimension_selection(self):
        '''
        Creates the remaining three selection dropdown lists & 'Save Data' button after residence selected
        '''
        # Retrieve list of dimensions 
        self.dimension_drop_1 = self.drop_config('Variable 1', self.dimension_list, 
                                 row=2, column=2) 
        self.dimension_drop_2 = self.drop_config('Variable 2', self.dimension_list, 
                                 row=2, column=3)
        self.area_codes = self.list_areas()
        self.regional_drop = self.drop_config('Regional Divisions', 
                                                self.area_codes, row=2, column=4)
        but = Button( text = 'Save Data', command=self.execute_api_call)
        but.grid(column=4, row=4)
        but = Button(text='Reset', command=self.reset)
        but.grid(column=5, row=3)
        but = Button(text='Loop', command=self.loop)
        but.grid(column=4, row=5)
        
                 
    def list_dimensions(self):
        '''
        Returns the list of demensions relating to that residence code (HH, HRP, UR) & add option for None
        '''
        self.dimension_list = list(self.api.get_dims_by_pop_type(self.residence_code).values())
        return self.dimension_list


    def list_areas(self):
        '''
        returns a list of areas relating to the selected residence code
        '''
        area_list = list(self.api.get_areas_by_pop_type(self.residence_code).keys())
        return area_list


    def start_selections(self):
        '''
        Creates Selection drop down
        '''
        self.residence_drop = self.drop_config_button('Residence Selection', ('Usual Residence', 'Household',
                                'Household Reference Person'),row=2, column=1, command=self.retrieve_res_input)
        return self.residence_drop
    
    def reset(self):
        '''
        Reset Interface to allow for next combination of variables to be inpt
        '''
        self.window.destroy()
        self.__init__(self.api)
        
        
    def loop(self):
        '''
        Loops through all combinations of variables relating to that region & residence code
        
        *** Requires both the residence drop down list & regional drop down list to be filled***
        
        Returns:
            .csv files containing all the data combinations
        '''
        self.get_region()
        self.api.loop_through_variables(self.residence_code, self.region)
        
    def get_region(self):
        region_dict = self.api.get_areas_by_pop_type(self.residence_code)
        region_value = self.regional_drop.cget('text')
        self.region = region_dict[region_value]
