# -*- coding: utf-8 -*-
"""
Created on Mon Oct 23 09:48:04 2023

@author: agbenm
"""

from Census21_CACD_Wrapper import APIWrapper

def test_can_retrieve_usual_residents_sex_EW():
    api = APIWrapper(logger=False)
    res = api.query_api('UR',f'sex',f'nat').iloc[0]['count']
    assert res == 30420202 # The number of female respondents in England & Wales