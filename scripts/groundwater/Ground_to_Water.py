#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct  3 12:45:42 2024

##########  GROUNDWATER FIELD DATA PROCESSING SCRIPT  ##########  

This module processes groundwater well readings to determine the groundwater
level relative to the ground surface.

This code is under development and follows a functional programming paradigm.
It leverages Pandas DataFrames and csv files with well-defined column names.

Major Functions:
TRANSLATES 

Requires X data files:
    1. 
    2. 
    3. 

TODOs documented in github repo issue tracking.

"""

# --- DUNDERS ---
__author__ = 'Jennifer Natali'
__copyright__ = 'Copyright (C) 2024 Jennifer Natali'
__license__ = 'NOT Licensed, Private Code under Development, DO NOT DISTRIBUTE'
__maintainer__ = 'Jennifer Natali'
__email__ = 'jennifer.natali@berkeley.edu'
__status__ = 'Development'

# --- IMPORTS ---
# Basic libraries
import numpy as np
import pandas as pd
import os
from datetime import datetime

# --- INITIALIZE FILE VARIABLES ---


# --- UTILITY FUNCTIONS ---
def SAMPLE_get_poly_area(x, y) -> float:
    """
    Calculate area of a polygon.

    Parameters:
    x (array of float): series of x coordinates
    y (array of float): series of y coordinates

    Returns:
    a_np (float): the area of polygon
    """
