# -*- coding: utf-8 -*-
"""
Created on Mon Oct 23 09:48:04 2023

@author: agbenm
"""

from Census21_CACD_Wrapper import APIWrapper
import pytest


api = APIWrapper()

# Test checks that the test can accurately complete a simple request
def test_can_retrieve_usual_residents_sex_EW():
    res = api.query_api('UR','sex','nat').iloc[0]['count']
    assert res == 30420202 # The number of female respondents in England & Wales

#Testing a batch of possible https response codes.
#This should ensure that the API wrapper only processes sucessful responses (200-299)    
class Response:
    def __init__(self, status_code):
        self.status_code = status_code
        
test_response1 = Response(120)
test_response2 = Response(200)
test_response3 = Response(298)
test_response4 = Response(301)
test_response5 = Response(445)
test_response6 = Response(586)

response_value_test_cases = [
    (test_response1, False), 
    (test_response2, True),
    (test_response3, True),
    (test_response4, False),
    (test_response5, False),
    (test_response6, False)
    ]

@pytest.mark.parametrize("response_value, expected_outcome", response_value_test_cases)
def test_valid_status_code(response_value, expected_outcome):
    assert api._valid_status_code(response_value) == expected_outcome
    
# Trying to ensure that no errors are sneaking in the pop codes list. 
def test_no_errors_in_pop_codes():
    api.set_population_types_available()
    assert 'errors' not in api._valid_pop_types

