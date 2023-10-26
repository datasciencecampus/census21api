from tkinter import *
from src.census21api.wrapper import APIWrapper
FONT = ("arial",10)

class Interface():
    def __init__(self, api):
        self.configure_window()
        self.start_selections()
        
        # Define variables
        self.variable_drop_1 = None
        self.variable_drop_2 = None
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
        variable.set(selection[0])
        drop_list.grid(row=row+1, column=column)
        
        self.create_button('Select', command, row+2, column)

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
        variable.set(selection[0])
        drop_list.grid(row=row+1, column=column)

        return drop_list


    def retrieve_res_input(self):
        '''
        Retrieve the selection of 'residence dropdown list' and returns abbreviation (abbreviation used in API call)
        '''
        output = self.residence_drop.cget('text')
        
        residence_mapping = {
        'Usual Residence': 'UR',
        'Household': 'HH',
        'Household Reference Person' : 'HRP'
        }
        
        self.residence_code = residence_mapping.get(output)

        self.variable_list = self.list_variables()
        self.create_variable_selection()


    def execute_api_call(self):
        '''
        Query API and save data to csv file in '/data/output/'

        Returns:
             Saves Data to .csv
        '''
        var_1 = self.variable_drop_1.cget('text')
        var_2 = self.variable_drop_2.cget('text')
        self.get_region()
        
        if var_1 != 'None' and var_2 != 'None':
            data = self.api.query_api(self.residence_code, f'{var_1},{var_2}', self.region)
        elif var_1 == 'None':
            data = self.api.query_api(self.residence_code, f'{var_2}', self.region)
        else:
            data = self.api.query_api(self.residence_code, f'{var_1}', self.region)


    def create_variable_selection(self):
        '''
        Creates the remaining three selection dropdown lists & 'Save Data' button after residence selected
        '''
        # Retrieve list of variables 
        self.variable_drop_1 = self.drop_config('Variable 1', self.variable_list, 
                                 row=2, column=2) 
        self.variable_drop_2 = self.drop_config('Variable 2', self.variable_list, 
                                 row=2, column=3)
        self.area_codes = self.list_areas()
        self.regional_drop = self.drop_config('Regional Divisions', 
                                                self.area_codes, row=2, column=4)
        
        self.create_button('Save Data', self.execute_api_call, 4, 4)
        self.create_button('Reset', self.reset, 3, 5)
        self.create_button('Loop', self.loop, 5, 4)

        
    def create_button(self, text, command, row, column):
        '''
        Create Button function
        
        Args:
            text: str = The label for button
            command: function = function to call upon button press
            row: int = The row to place the button
            colum: int = The column to place the button
        '''
        but = Button(text=text, command=command)
        but.grid(column=column, row=row)
                 
            
    def list_variables(self):
        '''
        Returns the list of variabless relating to that residence code (HH, HRP, UR) & add option for None
        '''
        self.variable_list = list(self.api.get_dims_by_pop_type(self.residence_code).values())
        self.variable_list.append('None')
        return self.variable_list


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
        '''
        Retrieves region possibilities for selection residence code
        '''
        region_dict = self.api.get_areas_by_pop_type(self.residence_code)
        self.region = region_dict[self.regional_drop.cget('text')]
