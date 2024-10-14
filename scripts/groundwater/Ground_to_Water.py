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
import pandas as pd
import os
from datetime import datetime
import numpy as np


# --- INITIALIZE FILE VARIABLES ---

# Setup directory (dir) structure and file names based on structure in github
groundwater_data_dir = '../../data/field_observations/groundwater/biweekly_manual/'
groundwater_plot_dir = '../../data/field_observations/groundwater/plots/biweekly_manual/'

# Input (source data) filenames
well_unique_id_filename = groundwater_data_dir + '../well_unique_id.txt'
well_dimension_filename = groundwater_data_dir + '../well_dimensions.csv'
meter_offset_filename = groundwater_data_dir + '../well_meter_offsets.csv'
groundwater_rawdata_filename = groundwater_data_dir + 'groundwater_biweekly_RAW.csv'

# Output filenames
groundwater_fulldata_filename = groundwater_data_dir + 'groundwater_biweekly_FULL.csv'
groundwater_plot_filename = groundwater_plot_dir + 'groundwater_biweekly_2018-2021.pdf'

# Fetch input (source data) files
well_unique_id = pd.read_csv(well_unique_id_filename)
well_dimension = pd.read_csv(well_dimension_filename)
#well_dimension = pd.read_excel(well_dimension_filename)
groundwater_data = pd.read_csv(groundwater_rawdata_filename)
meter_offset = pd.read_csv(meter_offset_filename)

# Setup dataframe for groundwater entries with no matching well height
# groundwater_no_wellheight = pd.DataFrame(columns=["well_id", "date"])

# # --- FUNCTIONS ---
# def SAMPLE_get_poly_area(x, y) -> float:
#     """
#     Calculate area of a polygon.

#     Parameters:
#     x (array of float): series of x coordinates
#     y (array of float): series of y coordinates

#     Returns:
#     a_np (float): the area of polygon
#     """
    
def validate_well_id(well_unique_id, groundwater_data) -> bool:
    """
    Check that all well_id's in gw_rawdata and well_dimension are
    found in well_unique_id; if not, print in a WARNING and save in a CSV.

    Parameters:
    well_unique_id (dataframe): a list of all the unique well identifiers
    groundwater_data (dataframe): groundwater well reading entries; each
                                  entry uniquely identified by well_id and 
                                  timestamp

    Returns:
    validated (binary): true if no issues, false if not valid
    """
    
    # TODO: code this function, for now assume OK and return True
    print('WARNING: Did not validate well id, function not yet defined.')
    return True

def validate_well_dimension(well_unique_id, well_dimension) -> bool:  
    """
    Check that every well_id in gw_rawdata has a matching welltop_to_ground;
    if not, print in a WARNING and save well_id and date in a CSV.

    Parameters:
    well_unique_id (pd.DataFrame()): a list of all the unique well identifiers
    groundwater_dimension (pd.DataFrame()): groundwater dimensional characteristics
                                       per well_id

    Returns:
    validated (binary): true if no issues, false if not valid
    """
    
    # TODO: code this function, for now assume OK and return True
    print('WARNING: Did not validate well dimension, function not yet defined.')
    return True

def subcalculate_groundwater_level(row, well_dimension):
        
    # get well_dimension row(s) for the groundwater well_id
    well_dimension_filtered = well_dimension[
        well_dimension["well_id"] == row["well_id"]]
    
    # filter and sort well_dimension row(s) by matching groudwater date
    well_dimension_filtered = well_dimension_filtered[
        well_dimension_filtered["effective_timestamp"] <= row["timestamp"]].sort_values(by="effective_timestamp")
    
    if well_dimension_filtered.empty:
        print("WARNING: No well height for %s on %s" % 
            (row["well_id"],row["timestamp"]))
        return None
    else:
        if row["well_id"] == ("KEF-XE3S" or "KFF-XE8S"):
            print("CALCULATING water depth for %s on %s with %s well dimension entry" %
              (row["well_id"],row["timestamp"],well_dimension_filtered.iloc[0].effective_timestamp) )
        
        well_height = well_dimension_filtered.iloc[0].welltop_to_ground_cm
        
        ground_to_water_cm = row["welltop_to_water_cm"] - well_height
  
        # For each reading, add the appropriate meter offset (based on
        #    gw_rawdata.meter_id) to adjust ground_to_water_cm.
        #
        # NOTE: For now, add 3cm offset for any meter except solinst or nm (no meter)
        # TODO: Examine range of meter_offset, did I consistently measure from 
        #       the top or bottom of the sensor?! Re-test the meters if possible.
        if row["meter_id"] != ('nm' or 'solinst'):
            ground_to_water_cm = ground_to_water_cm + 3
        
        return ground_to_water_cm

    
def calculate_groundwater_level(groundwater_data, well_dimension) -> pd.DataFrame():
    """
    For each well reading, determine ground_to_water_cm. 

    Parameters:
    groundwater_data (pd.DataFrame()): groundwater well reading; each entry
                                  uniquely identified by well_id and timestamp
    groundwater_dimension (pd.DataFrame()): groundwater dimensional characteristics
                                       per well_id

    Returns:
    updated groundwater_data (pd.DataFrame())
    """

    # 0. If multiple well readings for a single timestamp, average them.
    
    groundwater_groups = groundwater_data.groupby(['well_id','timestamp'])
    groundwater_groups = groundwater_groups['welltop_to_water_cm'].mean().reset_index()
    groundwater_data = pd.merge(groundwater_groups, groundwater_data[[
        'well_id','timestamp', 'water_binary','logger?',
        'meter_id','soil moisture', 'notes' ]].drop_duplicates(), 
         on=['well_id','timestamp'], how='left')
    
    # 1. For each well reading, subtract well_dimension.welltop_to_ground_cm 
    #    from groundwater_data.welltop_to_water_cm for the matching well_id to
    #    calculate ground_to_water_cm
    
    # Setup groundwater_data for new column value
    groundwater_data["ground_to_water_cm"] = np.NaN
    
    # Setup groundwater_data with date and timestamp
    #groundwater_data["timestamp"] = pd.Timestamp(groundwater_data["timestamp"])
    #groundwater_data["timestamp"] = pd.to_datetime(groundwater_data["timestamp"], format="%m/%d/%y %I:%M %p")
    groundwater_data["timestamp"] = pd.to_datetime(groundwater_data["timestamp"])

    #groundwater_data["date"] = [d.date() for d in groundwater_data["timestamp"]]

    
    # Setup well_dimension for selection by date
    #well_dimension["effective_timestamp"] = pd.Timestamp(well_dimension["effective_timestamp"])
    #well_dimension["effective_timestamp"] = pd.to_datetime(well_dimension["effective_timestamp"], format="%m/%d/%y %I:%M %p")
    well_dimension["effective_timestamp"] = pd.to_datetime(well_dimension["effective_timestamp"])
    #well_dimension["date"] = [d.date() for d in well_dimension["effective_timestamp"]]
    
    
    # 2. Logic for determining appropriate well height:
    #   A. Try to match well_dimension from the same day of the reading
    #      or the most recent well_dimension in the past.
    
        # NOTE: This might not be right!
        # TODO: Need to determine and consider dates of well replacement and 
        #       make sure this logic will work.
    
    
    # for i, row in groundwater_data.iterrows():
        
    #     # get well_dimension row(s) for the groundwater well_id
    #     well_dimension_filtered = well_dimension[
    #         well_dimension["well_id"] == row["well_id"]]
        
    #     # filter and sort well_dimension row(s) by matching groudwater date
    #     well_dimension_filtered = well_dimension_filtered[
    #         well_dimension_filtered["effective_timestamp"] <= row["timestamp"]].sort_values(by="effective_timestamp")
        
    #     if well_dimension_filtered.empty:
    #         print("WARNING: No well height for %s on %s" % 
    #             (row["well_id"],row["timestamp"]))
            
    #         # Add well_id and date to groundwater_no_wellheight 
    #         # dict = {"well_id": row["well_id"],
    #         #         "date": row["date"]}
    #         # groundwater_no_wellheight.loc[len(groundwater_no_wellheight)] = pd.Series(dict)

    #     else:
    #         if row["well_id"] == ("KEF-XE3S" or "KFF-XE8S"):
    #             print("CALCULATING water depth for %s on %s with %s well dimension entry" %
    #               (row["well_id"],row["timestamp"],well_dimension_filtered.iloc[0].effective_timestamp) )
    #         well_height = well_dimension_filtered.iloc[0].welltop_to_ground_cm
    #         row["ground_to_water_cm"] = row["welltop_to_water_cm"] - well_height
      
    #         # For each reading, add the appropriate meter offset (based on
    #         #    gw_rawdata.meter_id) to adjust ground_to_water_cm.
    #         #
    #         # NOTE: For now, add 3cm offset for any meter except solinst or nm (no meter)
    #         # TODO: Examine range of meter_offset, did I consistently measure from 
    #         #       the top or bottom of the sensor?! Re-test the meters if possible.
    #         if row["meter_id"] != ('nm' or 'solinst'):
    #             row["ground_to_water_cm"] = row["ground_to_water_cm"] + 3
                
    #         # Add this column to new_groundwater_data
    #         new_groundwater_data = pd.concat([new_groundwater_data, row])
        
    # 3. If water_binary is false (no water), estimate the ground_to_water
    #    as "greater than the" (total_well_length_cm - welltop_to_ground_cm)
    #    and set as ground_to_water_greater_than_cm.
    # NOTE: Skip for now
    # TODO: Add ground_to_water_greater_than_cm attribute to groundater_data
    
    #groundwater_data['ground_to_water_cm'] = new_groundwater_data['ground_to_water_cm']
    
    groundwater_data['ground_to_water_cm'] = groundwater_data.apply(lambda row: 
        subcalculate_groundwater_level(row, well_dimension), axis=1)
    
    return groundwater_data

def save_groundwater(groundwater_data) -> None:
    """
    Save a subset of groundwater_data to pre-defined csv (global var)

    Parameters:
    groundwater_data (dataframe): groundwater well reading; each entry
                                  uniquely identified by well_id and timestamp

    Returns: None
    """
    groundwater_data[['well_id','timestamp','ground_to_water_cm']].to_csv(groundwater_fulldata_filename, index=False)
    
# --- VALIDATE well_id's and well_dimension.welltop_to_ground ---
# 
# 1. Check that all well_id's in gw_rawdata and well_dimension are
#    found in well_unique_id; if not, print in a WARNING and save in a CSV.
#
# 2. Check that every well_id in gw_rawdata has a matching welltop_to_ground;
#    if not, print in a WARNING and save well_id and date in a CSV.

if (validate_well_id(well_unique_id, groundwater_data) and
    validate_well_dimension(well_unique_id, well_dimension)):
    
#   print('OK to calculate! Well ID and Dimensions Validated.')
       
# --- DETERMINE welltop_to_ground_cm ---
#
# 4. Save groundwater_data with adjusted measurements along 
#    with following params from groundwater_rawdata: well_id, timestamp,
#    welltop_to_water_cm, water_binary, logger_binary, meter_id,
#    soil_moisture, notes (but not the original three measurements).

    groundwater_data = calculate_groundwater_level(groundwater_data, 
                                                   well_dimension)
    # Re-order columns
    #groundwater_data.insert(3,'ground_to_water_cm', groundwater_data.pop('ground_to_water_cm'))
    save_groundwater(groundwater_data)
    
else:
    print('WARNING: Unable to manipulate or save groundwater data.')
