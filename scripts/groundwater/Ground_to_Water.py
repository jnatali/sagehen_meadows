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
1. Unique well ids: 'well_unique_id.txt'
2. Well Dimensions: 'well_dimensions.csv'
3. RAW groundwater data (in cm) for all years: 'groundwater_biweekly_RAW.csv'
4. Well meter offsets (in cm): 'well_meter_offsets.csv'

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

# Setup directory structure and file names based on structure in github
gw_data_dir = '../../data/field_observations/groundwater/biweekly_manual/'
gw_plot_dir = '../../data/field_observations/groundwater/plots/biweekly_manual/'

# Input (source data) filenames
well_unique_id_filename = gw_data_dir + '../well_unique_id.txt'
well_dimension_filename = gw_data_dir + '../well_dimensions.csv'
meter_offset_filename = gw_data_dir + '../well_meter_offsets.csv'
gw_rawdata_filename = gw_data_dir + 'groundwater_biweekly_RAW.csv'

# Output filenames
gw_fulldata_filename = gw_data_dir + 'groundwater_biweekly_FULL.csv'
gw_plot_filename = gw_plot_dir + 'groundwater_biweekly_2018-2021.pdf'

# Fetch input (source data) files
well_unique_id = pd.read_csv(well_unique_id_filename)
well_dimension = pd.read_csv(well_dimension_filename)
gw_rawdata = pd.read_csv(gw_rawdata_filename)
meter_offset = pd.read_csv(meter_offset_filename)

# --- VALIDATE well_id's and well_dimension.welltop_to_ground ---
# 
# 1. Check that all well_id's in gw_rawdata and well_dimension are
#    found in well_unique_id; if not, print in a WARNING and save in a CSV.
#
# 2. Check that every well_id in gw_rawdata has a matching welltop_to_ground;
#    if not, print in a WARNING and save well_id and date in a CSV.

# --- DETERMINE welltop_to_ground_cm ---
#
# 1. For each well reading, subtract well_dimension.welltop_to_ground_cm 
#    from gw_rawdata.welltop_to_water_cm for the matching well_id
#
# 2. For each reading, apply the appropriate meter offset based on
#    gw_rawdata.meter_id
#
# 3. If water_binary is false (no water), estimate the welltop_to_ground
#    as "greater than the" (total_well_length_cm - welltop_to_ground_cm)
#    and set as welltop_to_ground_gt_cm.
#
# 4. Save gw_fulldata with the adjusted welltop_to_ground_cm and 
#    welltop_to_ground_gt_cm measurements along with following params 
#    from gw_rawdata: well_id, timestamp,
#    welltop_to_water_cm, water_binary, logger_binary, meter_id,
#    soil_moisture, notes



# # --- UTILITY FUNCTIONS ---
# def SAMPLE_get_poly_area(x, y) -> float:
#     """
#     Calculate area of a polygon.

#     Parameters:
#     x (array of float): series of x coordinates
#     y (array of float): series of y coordinates

#     Returns:
#     a_np (float): the area of polygon
#     """
