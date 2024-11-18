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
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

# --- USE TRANSDUCER DATA? ---
transducer_binary = False

# --- INITIALIZE FILE VARIABLES ---

# Setup directory (dir) structure and file names based on structure in github
groundwater_data_dir = '../../data/field_observations/groundwater/biweekly_manual/'
groundwater_plot_dir = '../../data/field_observations/groundwater/plots/biweekly_manual/'

if transducer_binary:
    transducer_data_dir = '../../data/field_observations/groundwater/subdaily_loggers/relative_to_ground/'

# Input (source data) filenames
well_unique_id_filename = groundwater_data_dir + '../well_unique_id.txt'
well_dimension_filename = groundwater_data_dir + '../well_dimensions.csv'
meter_offset_filename = groundwater_data_dir + '../well_meter_offsets.csv'
groundwater_rawdata_filename = groundwater_data_dir + 'groundwater_biweekly_RAW.csv'

# Output filenames
groundwater_fulldata_filename = groundwater_data_dir + 'groundwater_biweekly_FULL.csv'
groundwater_plot_filename = groundwater_plot_dir + 'groundwater_biweekly_2018-2024.pdf'


# Fetch input (source data) files
well_unique_id = pd.read_csv(well_unique_id_filename)
well_dimension = pd.read_csv(well_dimension_filename)
#well_dimension = pd.read_excel(well_dimension_filename)
groundwater_data = pd.read_csv(groundwater_rawdata_filename)
meter_offset = pd.read_csv(meter_offset_filename)

# Setup dataframe for groundwater entries with no matching well height
# groundwater_no_wellheight = pd.DataFrame(columns=["well_id", "date"])

# # --- FUNCTIONS ---


def get_transducer_data() -> pd.DataFrame:
    """
    get groundwater levels from transducer files
    they're oragnized in one directory, 
    with one file per well per logging time period.

    Parameters: none
    
    Returns:
    transducer_data (dataframe): new entries added from the transducer directory
    """    
    
    target_time = pd.to_datetime('08:00').time()
    all_transducer_data = pd.DataFrame()
    transducer_data_path = Path(transducer_data_dir)
   
    # iterate through all .csv files in the tranducer directory
    for transducer_filename in transducer_data_path.iterdir():

        # check if valid file
        if transducer_filename.is_file() and transducer_filename.suffix == '.csv':
            
            # open the next file
            transducer_data = pd.read_csv(transducer_filename)
            
            # extract well_id from filename
            # assumes format follows this pattern: 'gtw_compensated_cut_EEF-1_2018_0727_0824.csv'
            filename_only = os.path.basename(transducer_filename)
            well_id_parts = filename_only.split('_')
            well_id = well_id_parts[3]
            
            print(filename_only)
            # convert to datetime formats
            transducer_data['timestamp'] = pd.to_datetime(transducer_data['Date'] + ' ' + transducer_data['Time'], format='mixed')
            #transducer_data['timestamp'] = pd.to_datetime(transducer_data['Date'] + ' ' + transducer_data['Time'], format='%m/%d/%Y %I:%M:%S %p')

            transducer_data['Time'] = pd.to_datetime(transducer_data['Time'], format='%I:%M:%S %p').dt.time
            
            # filter to only 8am timestamps
            transducer_data = transducer_data[transducer_data['Time'] == target_time]
            
            # flip sign of ground_to_water and rename
            # TODO: fix non-standard way of recording ground_to_water across observation types
            transducer_data = transducer_data[['timestamp', 'ground_to_water_m']]
            transducer_data['ground_to_water_cm'] = (-1) * transducer_data['ground_to_water_m']
            transducer_data.drop(columns=['ground_to_water_m'], inplace=True)
            
            # reconstruct dataframe with bi-weekly groundwater columns and values
            transducer_data['well_id'] = well_id
            transducer_data['water_binary'] = True
            transducer_data['logger?'] = True
            transducer_data['meter_id'] = 'transducer'
            transducer_data = transducer_data.reset_index(drop=True)
            
            # add to all_transducer_data
            all_transducer_data = pd.concat([all_transducer_data, transducer_data], ignore_index=True)
    
    return all_transducer_data
 


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

def calculate_from_ground(row, well_dimension):
        
    # get well_dimension row(s) for the groundwater well_id
    well_dimension_filtered = well_dimension[
        well_dimension["well_id"] == row["well_id"]]
    
    well_dimension_filtered = well_dimension_filtered[
        well_dimension_filtered["valid"] == True]
    
    # filter and sort well_dimension row(s) by matching groudwater date
    well_dimension_filtered = well_dimension_filtered[
        well_dimension_filtered["effective_timestamp"] <= row["timestamp"]].sort_values(by="effective_timestamp")
    
    if well_dimension_filtered.empty:
        print("WARNING: No well height for %s on %s" % 
            (row["well_id"],row["timestamp"]))
        return None
    else:
        if row["well_id"] in ["KEF-XE3S", "KFF-XE8S"]:
            print("CALCULATING water depth for %s on %s with %s well dimension entry" %
              (row["well_id"],row["timestamp"],well_dimension_filtered.iloc[-1].effective_timestamp) )
        
        if row["well_id"] in ["KW"]:
            print("CALCULATING water depth for %s on %s with %s well dimension entry" %
                  (row["well_id"],row["timestamp"],well_dimension_filtered.iloc[-1].effective_timestamp) )
        well_height = well_dimension_filtered.iloc[-1].welltop_to_ground_cm
        ground_to_water_cm = row["welltop_to_water_cm"] - well_height
  
        # For each reading, add the appropriate meter offset (based on
        #    gw_rawdata.meter_id) to adjust ground_to_water_cm.
        #
        # NOTE: For now, add 3cm offset for any meter except solinst or nm (no meter)
        # TODO: Examine range of meter_offset, did I consistently measure from 
        #       the top or bottom of the sensor?! Re-test the meters if possible.
        if row["meter_id"] not in ['nm','solinst']:
            ground_to_water_cm = ground_to_water_cm + 3
        
        return ground_to_water_cm

    
def get_groundwater_level(groundwater_data, well_dimension) -> pd.DataFrame():
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
             'meter_id','soil moisture', 'notes' ]].drop_duplicates(
                 subset=['well_id','timestamp'], keep='first'), 
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
          
    groundwater_data['ground_to_water_cm'] = groundwater_data.apply(lambda row: 
        calculate_from_ground(row, well_dimension), axis=1)
        
    # 3. If water_binary is false (no water), estimate the ground_to_water
    #    as "greater than the" (total_well_length_cm - welltop_to_ground_cm)
    #    and set as ground_to_water_greater_than_cm.
    # NOTE: Skip for now
    # TODO: Add ground_to_water_greater_than_cm attribute to groundater_data
    
    return groundwater_data

def save_groundwater(groundwater_data) -> None:
    """
    Save a subset of groundwater_data to pre-defined csv

    Parameters:
    groundwater_data (dataframe): groundwater well reading; each entry
                                  uniquely identified by well_id and timestamp

    Returns: None
    """
    groundwater_data['ground_to_water_cm'] = groundwater_data['ground_to_water_cm'].astype('float').round(4)
    groundwater_data = groundwater_data.sort_values(['well_id', 'timestamp'])
    groundwater_data[['well_id','timestamp','ground_to_water_cm']].to_csv(groundwater_fulldata_filename, index=False)
    return

def plot_groundwater_per_well(groundwater_data) -> None:
    """
    Plot groundwater level for each well with each year plotted as a different color
    Save as a single pdf

    Parameters:
    groundwater_data (dataframe): groundwater well reading; each entry
                                  uniquely identified by well_id and timestamp

    Returns: None (creates a pdf)
    """
    
    # Convert date to extra 'year' and 'isoweek'
    groundwater_data['timestamp'] = pd.to_datetime(groundwater_data['timestamp'])
    groundwater_data['year'] = groundwater_data['timestamp'].dt.year
    groundwater_data['isoweek'] = groundwater_data['timestamp'].dt.isocalendar().week
    
    # Define isoweek range
    isoweek_range = groundwater_data['isoweek'].unique()
    
    # Group by well_id, year and isoweek
    well_ids = groundwater_data['well_id'].unique()
    years = sorted(groundwater_data['year'].unique())  # Extract unique years in sorted order
    plot_data = pd.MultiIndex.from_product([well_ids, years, isoweek_range], names=['well_id', 'year', 'isoweek'])
    plot_data = pd.DataFrame(index=plot_data).reset_index()
    
    # Merge plot_data with original data to fill in missing weeks with NaN
    groundwater_data = plot_data.merge(groundwater_data, on=['well_id', 'year', 'isoweek'], how='left')
    
    # Sort values
    groundwater_data = groundwater_data.sort_values(by=['well_id', 'timestamp'])

    
    # Define color map for years    
    # TODO P3: consider coding flexibility if more years?             
    plot_colors = ['blue', 'green', 'orange', 'yellow']  # Define colors for each year
    plot_color_map = dict(zip(years, plot_colors)) # Define dict for legend
    
    # Setup plots within a single PDF output
    with PdfPages(groundwater_plot_filename) as pdf:
        for well_id in well_ids:
            plt.figure(figsize=(10, 6))
        
            # Filter data for the current well_id
            well_data = groundwater_data[groundwater_data['well_id'] == well_id]
        
            # Plot data for each year in a different color
            for year in years:
                year_data = well_data[well_data['year'] == year]
                plt.plot(
                    year_data['isoweek'], 
                    year_data['ground_to_water_cm'], 
                    marker='o', linestyle='-',  # Use dots for data points
                    markersize=5,
                    color=plot_color_map[year], 
                    label=str(year)
                    )
        
            # plot layout
            plt.gca().invert_yaxis() #Invert the y-axis so gw level is intuitive
            plt.xticks(isoweek_range)
            plt.grid(color='0.95', linestyle='-', linewidth=0.5)
            plt.grid(True, which='both', axis='x')

            # plot labeling
            plt.title(f"Ground to Water Level for Well ID {well_id}")
            plt.xlabel("Isoweek")
            plt.ylabel("Ground to Water Level (cm)")
            plt.legend(title="Year")
        
        
            # Save the current plot to the PDF
            pdf.savefig()
            plt.close()
    return

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

    groundwater_data = get_groundwater_level(groundwater_data, 
                                                   well_dimension)    
    # Re-order columns
    #groundwater_data.insert(3,'ground_to_water_cm', groundwater_data.pop('ground_to_water_cm'))
    save_groundwater(groundwater_data)
    
else:
    print('WARNING: Unable to manipulate or save biweekly groundwater data.')
    
# --- ADD transducer data ---

print('# OF UNIQUE WELLS: %s' % len(groundwater_data['well_id'].unique()))
if transducer_binary:
    transducer_data = get_transducer_data()
    print('# of TRANSDUCER ENTRIES: %s' % len(transducer_data))
    print('# of BI-WEEKLY ENTRIES: %s' % len(groundwater_data))
    groundwater_data = pd.concat([groundwater_data, transducer_data], ignore_index=True)
    print('# of BI-WEEKLY ENTRIES AFTER MERGE: %s' % len(groundwater_data))
    save_groundwater(groundwater_data)

plot_groundwater_per_well(groundwater_data)