#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SUB-DAILY GROUNDWATER DATA TRANSFORM SCRIPT
Created on Fri Jun 11 13:18:44 2021
@author: jnatali, alopez, zdamico

Takes RAW subdaily logger data and compensates for barometric pressure
Once compensated, translates water level above the pressure sensor to water level below ground
Uses manual readings to generate the needed offset, 
    then applies to all subdaily readings for the appropriate time period.

Requires data files:
    1. RAW logger data as .csv files in subdaily_dir with strict 
        naming convention and formatting
    2. cut_times_file = groundwater_logger_times.csv (based on field notes)
    3. barometric pressure data as .csv

TODO: 
* 2021_0624 FIX cut times for 1-2 wells, see cut_times_file for notes
* 2021_0628 FIX save_fig flag and plot_water_level(), 
    throwing a "view limit minimum" valueError
* Look at barometric compensation script, why are 6 files empty?
* Look at several files with zero overlapping manual readings 
    (note: if +/- 30 mins, capture 5 more valid files)
* EWR-1 2018-10-01 count: 0, KET-1 2019-09-04 count: 0, KWR-1 2018-10-01 count: 0
"""
# import libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import datetime
import re # regexpression library to extract well id from filenames
import math
import statistics
import logging
import pprint
#from glob import glob

### SETUP FLAGS 
##  for processing, logging, debugging and data validation
process_cut = True
process_baro = True

save_fig = False #not working yet, throwing error

debug_cut = False
debug_baro = False
debug_gtw = True

### GLOBAL VARIABLES
gravity_sagehen = 9.800698845791 # based on gravity at 1934 meters
density_factor = 1/gravity_sagehen

### SETUP DIRECTORY + FILE NAMES
project_dir = '/VOLUMES/SANDISK_SSD_G40/GoogleDrive/GitHub/sagehen_meadows/'
gw_data_dir = project_dir + 'data/field_observations/groundwater/'

# As of 02/12/2025, Solinst_levelogger_all contains 2018 and 2019 data
subdaily_dir = gw_data_dir + 'subdaily_loggers/RAW/Solinst_levelogger_all/'
cut_dir = gw_data_dir + 'subdaily_loggers/WORKING/cut/'
solinst_baro_data_dir = gw_data_dir + 'subdaily_loggers/RAW/baro_data/'
station_baro_data_dir = project_dir + 'data/station_instrumentation/climate/Dendra/'
compensated_dir = gw_data_dir + 'subdaily_loggers/WORKING/baro_compensated/'
gtw_logger_dir = gw_data_dir + 'subdaily_loggers/WORKING/relative_to_ground/'
os.makedirs(gtw_logger_dir,exist_ok=True)
os.makedirs("logs",exist_ok=True)

cut_times_file = gw_data_dir + 'subdaily_loggers/groundwater_logger_times.csv'
cut_data_file = cut_dir+'cut_all_wells.csv'
station_baro_file = station_baro_data_dir + 'Dendra_baro_2018_0701_2019_1201.csv'
gw_biweekly_file = 'biweekly_manual/groundwater_biweekly_FULL.csv' #ground_to_water in cm
subdaily_full_file = 'subdaily_loggers/FULL/groundwater_subdaily_full.csv'

# Configure and test logging to write to a file
log_level=logging.INFO  # Can log different levels: INFO, DEBUG or ERROR
if (debug_cut or debug_baro or debug_gtw):
    log_level=logging.DEBUG

# Remove any existing log handlers, force reconfiguration
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
    
logging.basicConfig(filename="logs/subdaily_processing_log.txt", 
                        level=log_level, 
                        format='%(asctime)s - %(message)s')
logging.info("----------\n\nLogging ON for subdaily_processing_RawToGround.py")

### DEFINE FUNCTIONS 

## Helper function to filter a subset dataframe based on well_id and time range
def filter_subset_dataframe(df, well, start, stop):
    subset_df = df[
        (df['well_id'] == well) &
        (df['DateTime'] >= start) &
        (df['DateTime'] <= stop)]
    return subset_df

def filter_subset_dataframe(df, well, deploy):
    subset_df = df[
        (df['well_id'] == well) &
        (df['deployment'] >= deploy)]
    return subset_df

## Consolidate all logger csv files into one dataframe    
def get_logger_dataframe():
    """Consolidate all logger csv filesinto one dataframe."""
    for f in os.listdir(subdaily_dir):
        log_df = pd.concat([pd.read_csv(f, header=11, encoding='ISO-8859-1')])
    log_df['DT'] = pd.to_datetime(log_df['Date'] + ' ' + log_df['Time'])
    return log_df

## Plot subdaily logger dataframe
#  Assume dataframe has DT column converted to datetime
def plot_water_level(logger,water_level_column_name,well_id):
    fig, ax1 = plt.subplots(figsize=(10, 5), nrows=1, sharex=True)
    ax1.plot(logger['DT'], logger[water_level_column_name])
    ax1.set_ylabel('Water Level', size=12)
    #ax2.plot(logger['DT'], logger['TEMPERATURE'])
    #ax2.set_ylabel('Temperature', size=12)

    for tick in ax1.yaxis.get_major_ticks():
        tick.label.set_fontsize(9)
#    for tick in ax2.yaxis.get_major_ticks():
#        tick.label.set_fontsize(10)
#    for tick in ax2.xaxis.get_major_ticks():
#        tick.label.set_fontsize(10)

    fig.suptitle('Groundwater Level at Well '+ well_id, size=12)
    
    if save_fig: 
        ax1.set_xticklabels(ax1.get_xticks(), rotation=90)
        plot_file = gw_data_dir +'plots/gw_level_' + well_id + '.eps'
        plt.savefig(plot_file, format='eps')
    plt.show()
    

## Plot subdaily logger dataframe
#  Assume dataframe has DT column converted to datetime
def plot_water_temp(logger,water_level_column_name,well_id):
    fig, (ax1, ax2) = plt.subplots(figsize=(10, 5), nrows=2, sharex=True)
    ax1.plot(logger['DT'], logger[water_level_column_name])
    ax1.set_ylabel('Water Level', size=12)
    ax2.plot(logger['DT'], logger['TEMPERATURE'])
    ax2.set_ylabel('Temperature', size=12)

    for tick in ax1.yaxis.get_major_ticks():
        tick.label.set_fontsize(10)
    for tick in ax2.yaxis.get_major_ticks():
        tick.label.set_fontsize(10)
    for tick in ax2.xaxis.get_major_ticks():
        tick.label.set_fontsize(10)

    fig.suptitle('Groundwater Level and Temperature at Well '+ well_id, size=12)
    plt.show()
    
## Plot subdaily logger dataframe before/after cut times
#  Assume dataframe has DT column converted to datetime
def plot_water_temp_compare(before_df, after_df, water_level_column_name, well_id):
    fig, (ax1, ax2) = plt.subplots(figsize=(10, 5), nrows=2, sharex=True)
    ax1.set_ylabel('Water Level', size=12)
    ax2.set_ylabel('Temperature', size=12)

    
    ax1.plot(before_df['DT'], before_df[water_level_column_name])
    ax2.plot(before_df['DT'], before_df['TEMPERATURE'])
    
    ax1.plot(after_df['DT'], after_df[water_level_column_name],'r')
    ax2.plot(after_df['DT'], after_df['TEMPERATURE'], 'r')
    
    for tick in ax1.yaxis.get_major_ticks():
        tick.label.set_fontsize(10)
    for tick in ax2.yaxis.get_major_ticks():
        tick.label.set_fontsize(10)
    for tick in ax2.xaxis.get_major_ticks():
        tick.label.set_fontsize(10)

    fig.suptitle('Before/After cut of GW Level and Temp at Well '+ well_id, size=12)
    plt.show()
    
## Plot subdaily logger dataframe before/after cut times
#  Assume dataframe has DT column converted to datetime
def plot_water_temp_compare(before_df, manual_df, after_df, water_level_column_name, well_id):
    fig, (ax1, ax2) = plt.subplots(figsize=(10, 5), nrows=2, sharex=True)
    ax1.set_ylabel('Water Level', size=12)
    ax2.set_ylabel('Temperature', size=12)

    ax1.plot(before_df['DT'], before_df[water_level_column_name], color="b", label="Cut due to date")
    ax2.plot(before_df['DT'], before_df['TEMPERATURE'], color="b", label="Cut due to date")
    
    ax1.plot(manual_df['DT'], manual_df[water_level_column_name], color="g", label="Cut due to Temp change")
    ax2.plot(manual_df['DT'], manual_df['TEMPERATURE'], color="g", label="Cut due to Temp change")
    
    ax1.plot(after_df['DT'], after_df[water_level_column_name], color="r", label="Remaining data")
    ax2.plot(after_df['DT'], after_df['TEMPERATURE'], color="r", label="Remaining data")

    # Throwing error --> AttributeError: 'YTick' object has no attribute 'label'
    # for tick in ax1.yaxis.get_major_ticks():
    #     tick.label.set_fontsize(10)
    # for tick in ax2.yaxis.get_major_ticks():
    #     tick.label.set_fontsize(10)
    # for tick in ax2.xaxis.get_major_ticks():
    #     tick.label.set_fontsize(10)

    plt.legend()
    fig.suptitle('Before/After cut of GW Level and Temp at Well '+ well_id, size=12)
    plt.show()

def plot_weekly_groundwater_data_by_well(subdaily_df, manual_df, plot_subdaily_only=True):
    """
    Combine weekly manual and subdaily logger data to 
    plot all groundwater level measurements (in cm) 
    for each well on a weekly basis.
    
    Parameters:
    subdaily_df (DataFrame): Logger data with columns ['well_id', 'DateTime', 'ground_to_water_cm'].
    manual_df (DataFrame): Manual measurement data with columns ['well_id', 'DateTime', 'ground_to_water_cm'].

    Returns:
        None, displays the plot.
    """
    # Define time for extracting subdaily measurement 
    #  i.e time that represents equivalent of manual readings
    manual_reading_start_time = 6
    manual_reading_stop_time = 10
    
    # Extract unique well_ids from both datasets
    well_ids = set(subdaily_df['well_id']) if plot_subdaily_only else set(subdaily_df['well_id']).union(set(manual_df['well_id']))
    
    # Convert groundwater depth from meters to cm
    subdaily_df['ground_to_water_cm'] = subdaily_df['ground_to_water_m'] * 100
    
    for well_id in well_ids:
        # Filter data for the current well_id
        well_subdaily = subdaily_df[subdaily_df['well_id'] == well_id].copy()
        well_manual = manual_df[manual_df['well_id'] == well_id].copy()

        # Convert DateTime to datetime format
        well_subdaily['DateTime'] = pd.to_datetime(well_subdaily['DateTime'])
        well_manual['DateTime'] = pd.to_datetime(well_manual['DateTime'])

        # Extract Year and Isoweek
        well_subdaily['Year'] = well_subdaily['DateTime'].dt.year
        well_subdaily['Isoweek'] = well_subdaily['DateTime'].dt.isocalendar().week
        well_manual['Year'] = well_manual['DateTime'].dt.year
        well_manual['Isoweek'] = well_manual['DateTime'].dt.isocalendar().week

        # Filter only May-November (Isoweeks ~18 to ~47)
        well_subdaily = well_subdaily[(well_subdaily['Isoweek'] >= 18)
                                      & (well_subdaily['Isoweek'] <= 47)]
        well_manual = well_manual[(well_manual['Isoweek'] >= 18)
                                  & (well_manual['Isoweek'] <= 47)]
        
        # Filter subdaily wells to appropriate AM reading times
        well_subdaily = well_subdaily[(well_subdaily['DateTime'].dt.hour >= manual_reading_start_time)
                                  & (well_subdaily['DateTime'].dt.hour < manual_reading_stop_time)]

        # Average subdaily data per isoweek
        # JN 03/04/2025 updated to plot each deployment independently
        well_subdaily_avg = well_subdaily.groupby(['Year', 'Isoweek'], as_index=False)['ground_to_water_cm'].mean()
        # Group by well_id, deployment, Year, and Isoweek, then compute mean
        #well_subdaily = well_subdaily.groupby(['deployment','Isoweek'], 
        #                                      as_index=False)['ground_to_water_cm'].mean()
        
        # Merge to restore 'Deployment'
        well_subdaily = well_subdaily_avg.merge(well_subdaily[['Year', 'Isoweek', 'deployment']].drop_duplicates(), 
                                        on=['Year', 'Isoweek'], how='left')
        # Identify years where data is present for this well
        available_years = sorted(set(well_subdaily['Year']).union(set(well_manual['Year'])))
        
        # Create combined Year-Isoweek labels
        well_subdaily['Year-Isoweek'] = well_subdaily['Year'].astype(str) + "-" + well_subdaily['Isoweek'].astype(str).str.zfill(2)
        well_manual['Year-Isoweek'] = well_manual['Year'].astype(str) + "-" + well_manual['Isoweek'].astype(str).str.zfill(2)

        # Get unique x-axis values in order (avoids unnecessary gaps)
        unique_x_labels = sorted(set(well_subdaily['Year-Isoweek']).union(set(well_manual['Year-Isoweek'])))
        x_ticks = {label: i for i, label in enumerate(unique_x_labels)}

        # Map the categorical labels to integer positions
        well_subdaily['x_pos'] = well_subdaily['Year-Isoweek'].map(x_ticks)
        well_manual['x_pos'] = well_manual['Year-Isoweek'].map(x_ticks)

        # Ensure data is sorted by x-axis position
        well_subdaily = well_subdaily.sort_values(by=['deployment','x_pos'])
        well_manual = well_manual.sort_values(by='x_pos')

        # Plot
        plt.figure(figsize=(12, 5))

        # Scatter plot for subdaily data (ENSURES circular markers)
        # plt.scatter(
        #     well_subdaily['x_pos'], well_subdaily['ground_to_water_cm'], 
        #     marker='o', s=50, color='blue', label='Logger Data', zorder=3
        # )
        # # Line plot to connect subdaily points (ENSURES correct sorting)
        # plt.plot(
        #     well_subdaily['x_pos'], well_subdaily['ground_to_water_cm'], 
        #     linestyle='-', color='blue', alpha=0.7)
        
        # Plot each subdaily deployment separately within the well
        for deployment, dep_data in well_subdaily.groupby('deployment'):
            plt.scatter(dep_data['x_pos'], dep_data['ground_to_water_cm'], 
                marker='o', s=50, color='blue', label=None, zorder=3)

            plt.plot(dep_data['x_pos'], dep_data['ground_to_water_cm'], 
                     linestyle='-', color='blue', alpha=0.7, label=None)

        # Scatter plot for manual data (ENSURES circular markers)
        plt.scatter(
            well_manual['x_pos'], well_manual['ground_to_water_cm'], 
            marker='o', s=30, color='red', label='Manual Measurements', zorder=3
        )

        # Formatting
        plt.xlabel("Time (Year-Isoweek)")
        plt.ylabel("Groundwater Level (cm)")
        plt.title(f"Weekly Groundwater Levels for Well {well_id}")
        plt.xticks(ticks=list(x_ticks.values())[::3], labels=list(x_ticks.keys())[::3], rotation=45)  # Show every 3rd label
        plt.legend()
        plt.grid(True)

        # Reverse the y-axis so positive values appear below zero
        plt.gca().invert_yaxis()

        # Add vertical lines between years
        for year in available_years[1:]:  # Skip first year
            year_marker = [x_ticks[label] for label in unique_x_labels if label.startswith(str(year))]
            if year_marker:
                plt.axvline(x=year_marker[0], color='black', linewidth=2)  # Thick vertical line

        plt.tight_layout()
        plt.show()

def plot_subdaily_groundwater_by_deployment(subdaily_df, biweek_df):
    """
    Plots subdaily groundwater level (in cm) for each well_id and deployment,
    overlaying biweekly manual measurements if they are within 10 minutes.

    Parameters:
        subdaily_df (DataFrame): Logger data with columns ['well_id', 'deployment', 'DateTime', 'ground_to_water_m'].
        biweek_df (DataFrame): Manual measurement data with columns ['well_id', 'DateTime', 'ground_to_water_cm'].

    Returns:
    None, displays the plots.
    """
    # Convert groundwater depth from meters to cm
    subdaily_df['ground_to_water_cm'] = subdaily_df['ground_to_water_m'] * 100  
    
    # Convert DateTime columns to pandas datetime format
    subdaily_df['DateTime'] = pd.to_datetime(subdaily_df['DateTime'])
    biweek_df['DateTime'] = pd.to_datetime(biweek_df['DateTime'])
    
    # Iterate through unique (well_id, deployment) combinations
    for (well_id, deployment), well_subdaily in subdaily_df.groupby(
                                                    ['well_id', 'deployment']):
        #if debug_gtw: logging.debug(f"Plotting {well_id} {deployment}")
        
        # Filter manual data for the current well
        well_biweek = biweek_df[biweek_df['well_id'] == well_id].copy()
    
        # ERROR HANDLING: Check if have biweekly measurements for deployment    
        if well_biweek.empty:
            logging.info(f"PLOTTING MANUAL BI-WEEKLY GW: {well_id} "
                         + f"{deployment} has no manual biweekly records")
            continue # Skip loop iteration for this deployment
    
        # Merge biweekly data with subdaily data, 
        # keep only biweekly points within ±10 minutes
        well_biweek['closest_subdaily'] = well_biweek['DateTime'].apply(
            lambda x: (well_subdaily['DateTime'] - x).abs().min() 
              if not well_subdaily.empty else pd.Timedelta('1D'))
        
        well_biweek = well_biweek[well_biweek['closest_subdaily'] 
                                  <= pd.Timedelta(minutes=10)]
    
        # Sort subdaily data by DateTime
        well_subdaily = well_subdaily.sort_values(by='DateTime')
        
        # Plot
        plt.figure(figsize=(12, 5))
    
        # Subdaily groundwater levels (blue)
        plt.plot(well_subdaily['DateTime'], 
                 well_subdaily['ground_to_water_cm'], 
                 linestyle='-', marker='o', markersize=2, 
                 color='blue', label='Logger (10-min intervals)')
    
        # Biweekly groundwater levels (red) for overlapping times
        if not well_biweek.empty:
            plt.scatter(well_biweek['DateTime'], 
                        well_biweek['ground_to_water_cm'], 
                        color='red', s=50, 
                        label='Biweekly Manual Measurement', zorder=3)
    
        # Formatting
        plt.xlabel("DateTime")
        plt.ylabel("Groundwater Level (cm)")
        plt.title("Subdaily Groundwater Levels for" 
                  + f" Well {well_id} (Deployment {deployment})")
        plt.legend()
        plt.grid(True)
    
        # Reverse the y-axis so positive values appear below zero
        plt.gca().invert_yaxis()
    
        plt.tight_layout()
        plt.show()

        
## Cut or trim logger data at front/back end of data
## to account for when logger not in the well.
## 
## for each logger file, cut times based on three factors:
## 1. the defined start/stop times in groundwater_logger_times file
## 2. based on an extreme temp change, signaling sensor out of water
## 3. (next step) the manual well measurement
def cut_logger_data():
    """Cut logger data at front/back 
       to account for when logger not in the well."""

    ## new dataframes
    # to hold all well logger data
    cut_logger_df = pd.DataFrame()
    
    ## to track # of rows cutoff for each logger file
    cut_count_df = pd.DataFrame()
    
    ## from csv with start + end times for each logger deployment
    log_time_df = pd.read_csv(cut_times_file)
    log_time_df['start'] = pd.to_datetime(log_time_df['start'])
    log_time_df['end'] = pd.to_datetime(log_time_df['end'])
    
    ## process each logger deployment file
    for f in os.listdir(subdaily_dir):
        if f.endswith('.csv'):
        
            if debug_cut: logging.debug(f)
            
            # get well_id based on filename
            well_id = re.split('_20',f)[0]
                        
            log_df = pd.concat([pd.read_csv(subdaily_dir+f, header=11, encoding='ISO-8859-1')])
            log_df.insert(3, 'DT', pd.to_datetime(log_df['Date'] + ' ' + log_df['Time'], format='mixed'))
            #log_df['DT'] = pd.to_datetime(log_df['Date'] + ' ' + log_df['Time'])
            
            # save log_df original version for comparison plot later
            orig_log_df = log_df.rename(columns={'LEVEL': 'raw_LEVEL_m'})
            
            # plot raw data for well deployment
            # plot_water_temp(log_df,'LEVEL',' RAW '+ well_id)
            
            
            ## Calculate difference between raw datetime and field notes start_time and end_time
            #  select matching deployments from the field notes timing dataframe
            #  first by well_id, but this result may have timing for several deployments
            well_time_df = log_time_df[log_time_df['well_id'] == well_id]
            
            ## ERROR HANDLING if no time limits found for this well deployment in field notes
            if well_time_df.empty: 
                logging.info(f'WARNING: No time limits for {well_id}:' 
                      + 'check if well name is correct. Exiting cut process.')
                break
            
            #  select timing dataframe row from the range of times in the deployment logger file
            min_DT = log_df['DT'].min()
            max_DT = log_df['DT'].max()
            buffer = pd.Timedelta(hours=8)
            
            time_mask = ((well_time_df['start'] >= (min_DT - buffer)) & (well_time_df['end'] <= (max_DT + buffer)))
            well_time_df = well_time_df.loc[time_mask]
            
            ## ERROR HANDLING: only continue if one matching entry of start/stop times
            if well_time_df.shape[0] != 1:
                warning_str = 'WARNING: More/less than one row in well_time_df for ' + well_id + ', not clear which one to use. Check date range in logger csv. Exiting cut process. '
                logging.info(warning_str)
                # break
            
            
            # select logger data rows within start/end times from field notes
            time_delta=10 # number of minutes to subtract or add from start/end times
            time_mask = (log_df['DT'] >= (well_time_df['start'].iloc[0] - pd.Timedelta(minutes=time_delta))) & (log_df['DT'] <= well_time_df['end'].iloc[0] + pd.Timedelta(minutes=time_delta))
            log_df = log_df.loc[time_mask]
            
            # take snapshot of dataframe to plot and validate later
            manual_log_df = log_df.rename(columns={'LEVEL': 'raw_LEVEL_m'})
            
            ## Calculate temperature rate of change
            # temp change threshold that controls cutoff points
            change_threshold = well_time_df['temp_threshold'].iloc[0]
            if debug_cut: logging.debug(str(change_threshold))
            log_df['Rate of Change'] = np.append(np.abs((log_df['TEMPERATURE'].iloc[:-1].values - log_df['TEMPERATURE'].iloc[1:].values)/(10)), 0.0001)

            # Split data in half
            first = log_df.iloc[:int(log_df.shape[0]/2)]
            second = log_df.iloc[int(log_df.shape[0]/2):]
        
            # In first half, cut out all data before the last point that has a rate of change greater than the change threshold
            try:
                index = first.loc[(first['Rate of Change'] >= change_threshold), :].index[-1]
                first_cut = first.iloc[index:]
                if debug_cut: logging.debug('cutoff front end.')
            except IndexError as err:
                first_cut = first
                if debug_cut: logging.debug('Nothing to cut off front end.')
            
    
            # In second half, cut out all data after the first point that has a rate of change greater than the change threshold
            try:
                index = second.loc[(second['Rate of Change'] >= change_threshold), :].index[0]
                #second_cut = second.loc[(second.index < index)]
                second_cut = second.loc[(second.index <= index)]
                if debug_cut: logging.debug('Cutoff backend.')
            except IndexError as err:
                second_cut = second
                if debug_cut: logging.debug('Nothing to cut off back end.')
        
            # Snip both halfs back together
            log_df = pd.concat((first_cut, second_cut), axis=0)
            log_df.rename(columns={'LEVEL': 'raw_LEVEL_m'}, inplace=True)
            
            # track cut info for each well
            track_df = pd.DataFrame(
                    {
                           'well_id':  well_id,
                           'front_cutoff': first.shape[0] - first_cut.shape[0],
                           'back_cutoff': second.shape[0] - second_cut.shape[0]
                    }, index=[0]
            )
            
            # append 
            # cut_count_df = cut_count_df.append(track_df)
            cut_count_df = pd.concat([cut_count_df, track_df])
      
            # plot water level and temp for this well
            if debug_cut: plot_water_temp_compare(orig_log_df, manual_log_df, log_df,'raw_LEVEL_m',well_id)
            
            # save individual csv file with cut times
            log_df.to_csv(cut_dir+'cut_'+f, encoding='ISO-8859-1')
            
            # identify well_id and add to complete data frame for all, and save as csv
            log_df.insert(0, 'well_id', well_id)
            # cut_logger_df = cut_logger_df.append(log_df)
            cut_logger_df = pd.concat([cut_logger_df, log_df])
    
    # cleanup logger data to save in human-readable format
    cut_logger_df.drop(['Date', 'Time', 'ms', 'Rate of Change'], axis=1, inplace=True)
    cut_logger_df.rename(columns={'DT': 'DateTime', 'TEMPERATURE': 'Temp_c'}, inplace=True)
    cut_logger_df.to_csv(cut_data_file, index=False)
    #cut_count_df.to_csv(cut_dir+'cut_count_'+str(change_threshold)+'.csv')
    cut_count_df.to_csv(cut_dir+'cut_count.csv')
    
    return cut_logger_df
    
## Consolidate all barometer CSV files into one dataframe
## Convert LEVEL (kPa) to LEVEL (m); add a column for LEVEL (m); rename columns with units
def get_baro_dataframe_solinst():
    """Consolidate all barometer CSV files into one dataframe, then convert LEVEL (kPa) to LEVEL (m); add a column for LEVEL (m); rename columns with units."""
    all_baro_data = pd.DataFrame()
    
    for f in os.listdir(solinst_baro_data_dir):
        if f.endswith('.csv'):
            if debug_baro: 
                logging.debug(f"Fetching baro data from {f}")
            ## TODO: consider adding barometer well_id to dataframe
            new_baro = pd.read_csv(solinst_baro_data_dir + f, header=10, encoding='ISO-8859-1')
            
            if debug_baro: 
                logging.debug(f"Length of bara dataframe: {str(len(new_baro))}")
                test_b = new_baro
                
                # format DateTime using explicit 12-hour format with AM/PM
                test_b['DateTime'] = pd.to_datetime(
                    test_b['Date'] + ' ' + test_b['Time'],
                    format='%m/%d/%Y %I:%M:%S %p')
                str_b_range = 'min/max of new baro file time:' + str(min(test_b['DateTime'])) + ' to ' + str(max(test_b['DateTime']))
                logging.debug(str_b_range)
                
            all_baro_data = pd.concat([all_baro_data, new_baro],
                                      ignore_index=True, sort=True)
            
            if debug_baro: 
                logging.debug(str(len(all_baro_data))+ '\n')

    return all_baro_data

## Consolidate all barometer CSV files into one dataframe
## Convert LEVEL (kPa) to LEVEL (m); add a column for LEVEL (m); rename columns with units
def get_baro_dataframe():
    """Consolidate all barometer CSV files into one dataframe, then convert LEVEL (kPa) to LEVEL (m); add a column for LEVEL (m); rename columns with units."""
    
    new_baro = pd.read_csv(station_baro_file)
    new_baro['DateTime'] = pd.to_datetime(new_baro['Time'])
    
    if debug_baro: 
        print(str(len(new_baro)))
        str_b_range = 'min/max of new baro file time:' + str(min(new_baro['DateTime'])) + ' to ' + str(max(new_baro['DateTime']))
        print(str_b_range)
        
    new_baro.drop(['Barometric Pressure Avg (mb)'], axis=1, inplace=True)
    new_baro.rename(columns={'Barometric Pressure Avg (kPa)': 'baro_LEVEL_kPa'}, inplace=True)
    #column_order = ['DateTime', 'baro_LEVEL_kPa']
    #new_baro = new_baro.reindex(columns=column_order)

    return new_baro

## Takes barometric pressure reading from the raw Solinst barologger
## and converts it from kPa of pressure to meters (m) of pressure
def convert_baro(baro_df):
    """Takes water level reading from the Dendra data, 
    converts it from kPa of pressure to meters (m) above the sensor."""
    
    baro_df['baro_LEVEL_m'] = baro_df['baro_LEVEL_kPa'] * density_factor    
   
#    if debug_baro: 
#        str_b_range = 'min/max of baro time:' + str(min(baro_df['DateTime'])) + ' to ' + str(max(baro_df['DateTime']))
#        print(str_b_range)
    
    # cleanup baro data so column names clear, not carrying unneeded data
#    baro_df.drop(['Date', 'Time', 'ms'], axis=1, inplace=True)
#    baro_df.rename(columns={'LEVEL': 'baro_LEVEL_kPa', 'TEMPERATURE': 'baro_Temp_C'}, inplace=True)
    
    return baro_df

## Takes barometric pressure reading from the raw Solinst barologger
## and converts it from kPa of pressure to meters (m) of pressure
def convert_baro_solinst(baro_df):
    """Takes water level reading from the raw Solinst levelogger data, converts it from kPa of pressure to meters (m) above the sensor."""
    
    #baro_df['baro_LEVEL_m'] = baro_df['LEVEL'] * 0.101972
    baro_df['baro_LEVEL_m'] = baro_df['LEVEL'] * density_factor 
    baro_df['DateTime'] = pd.to_datetime(baro_df['Date'] + ' ' + baro_df['Time'])
    
#    if debug_baro: 
#        str_b_range = 'min/max of baro time:' + str(min(baro_df['DateTime'])) + ' to ' + str(max(baro_df['DateTime']))
#        print(str_b_range)
    
    # cleanup baro data so column names clear, not carrying unneeded data
    baro_df.drop(['Date', 'Time', 'ms'], axis=1, inplace=True)
    baro_df.rename(columns={'LEVEL': 'baro_LEVEL_kPa', 'TEMPERATURE': 'baro_Temp_C'}, inplace=True)
    
    return baro_df

## Removes the barometric pressure (in meters) from the sensor water level
#  Assumes baro_df and gw_df are ('datetime64[ns]') type
def compensate_baro(baro_df, gw_df):
    """
    Removes the barometric pressure (in meters)
    from the sensor water level.
    """
    
    # merge baro and gw dataframes, only keeping relevant rows
    merge_df = baro_df.merge(gw_df, how='inner',on='DateTime')
    
#    if debug_baro: 
#        str_b_range = 'min/max of baro time:' + str(min(baro_df['DateTime'])) + ' to ' + str(max(baro_df['DateTime']))
#        str_g_range = 'min/max of gw time:' + str(min(gw_df['DateTime'])) + ' to ' + str(max(gw_df['DateTime']))
#        print(str_b_range)
#        print(str_g_range)
#        print('lost gw records after merge with baro: ' + str(len(gw_df) - len(merge_df)))
    
    # subtract baro data from gw data
    merge_df['compensated_LEVEL_m'] = merge_df['raw_LEVEL_m'] - merge_df['baro_LEVEL_m']
    
    # cleanup column names + order so human readable and save as csv
    #merge_df.drop(['baro_LEVEL_kPa', 'baro_Temp_C'], axis=1, inplace=True)
    merge_df.drop(['baro_LEVEL_kPa'], axis=1, inplace=True)
    column_order = ['well_id', 'DateTime', 'raw_LEVEL_m',
                    'baro_LEVEL_m', 'compensated_LEVEL_m', 'Temp_c']
    merge_df = merge_df.reindex(columns=column_order)
    merge_df.to_csv(compensated_dir+'compensated_all_wells.csv', 
                    encoding='ISO-8859-1', index=False)

    return merge_df



def calculate_sensor_level(merged_df):
    """
    Determines the depth of the sensor relative to the ground surface
    based on the manual gw measurement and water pressure head from the sensor
    """
    # Dictionary of sensor_levels per well_id and deployment
    sensor_levels = {}
    
    # Dictionary of errors 
    #  (based on "drift" between multiple manual measurements 
    #   within a logger deployment)
    drift_errors = {}
    
    for (well, deploy), group in merged_df.groupby(['well_id', 'deployment']):
        subdaily_group = merged_df[(merged_df['well_id'] == well) & 
                                     (merged_df['deployment'] == deploy)]
        
        # # Select the manual measurements with the smallest absolute time difference
        # group['abs_time_diff'] = group['DateTime_biweek'].apply(
        #     lambda t: subdaily_group['DateTime_subdaily'].sub(t).abs().min())
        # closest_measurements = group.sort_values('abs_time_diff').groupby(
        #         ['well_id', 'deployment']).first().reset_index()
        
        # Create a subgroup with the smallest absolute time diff
        # for each unique manual measurement time
        closest_measurements = subdaily_group.loc[
            subdaily_group['time_diff'].abs().groupby(
                subdaily_group['DateTime_biweek']).idxmin()]

        # Store all offsets for drift error calculation
        sensor_level_list = []
        
        for i, row in closest_measurements.iterrows():
            manual_time = row['DateTime_biweek']
            manual_groundwater_m = row['ground_to_water_m']
            
            # Check if there's an exact match in subdaily_df
            exact_match = subdaily_group[subdaily_group['DateTime_subdaily'] 
                                         == manual_time]
            
            # If there's an exact match, use it directly!
            if not exact_match.empty:
                pressure_head = exact_match['compensated_LEVEL_m'].values[0]
            
            else:
                # Find the closest two logger records before and after
                # JN 2025/02/28 changed tail(1) to tail(2), same for head()
                before = subdaily_group[subdaily_group['DateTime_subdaily'] <= 
                                        manual_time].tail(2)
                after = subdaily_group[subdaily_group['DateTime_subdaily'] > 
                                       manual_time].head(2)
                
                if not before.empty and not after.empty:
                    if len(before) > 1: 
                        before = before.loc[[before['time_diff'].abs().idxmin()]]
                    if len(after) > 1:
                        after = after.loc[[after['time_diff'].abs().idxmin()]]
                    # Interpolate compensated_LEVEL_m at manual measurement time
                    t1 = before['DateTime_subdaily'].values[0]
                    t2 = after['DateTime_subdaily'].values[0]
                    v1 = before['compensated_LEVEL_m'].values[0]
                    v2 = after['compensated_LEVEL_m'].values[0]
                
                    # Linear interpolation
                    pressure_head = v1 + (
                        manual_time - t1) / (t2 - t1) * (v2 - v1)
                
                elif not before.empty and len(before) > 1:
                    logging.debug(f"CASE not before.empty for {well} and {deploy}")
                    # Use rate of change to extrapolate
                    before_sorted = before.sort_values('DateTime_subdaily')
                    t1, t2 = before_sorted['DateTime_subdaily'].iloc[-2:].values
                    v1, v2 = before_sorted['compensated_LEVEL_m'].iloc[-2:].values
                    time_diff = (t2 - t1) / np.timedelta64(1, 'm')  # Convert to minutes
                    rate = (v2 - v1) / time_diff  # Rate of change per minute
                    pressure_head = v2 + rate * ((manual_time - t2).total_seconds()/60)

                elif not after.empty and len(after) > 1:
                    logging.debug(f"CASE not after.empty for {well} and {deploy}")
                    # Use rate of change from two after readings
                    after_sorted = after.sort_values('DateTime_subdaily')
                    t1, t2 = after_sorted['DateTime_subdaily'].iloc[:2].values
                    v1, v2 = after_sorted['compensated_LEVEL_m'].iloc[:2].values
                    time_diff = (t2 - t1) / np.timedelta64(1, 'm')  # Convert to minutes
                    rate = (v2 - v1) / time_diff  # Rate of change per minute
                    pressure_head = v1 - rate * ((t1 - manual_time).total_seconds()/60)

                # New case: Manual measurement occurs after the last subdaily record
                # TODO: see if there's a second before
                elif after.empty and not before.empty and len(before) >= 1:
                    logging.debug(f"CASE manual_time AFTER last DateTime_subdaily for {well} and {deploy}")
                    # Use last two before readings to estimate rate of change
                    before = subdaily_group[subdaily_group['DateTime_subdaily'] <= 
                                            manual_time].tail(2)
                    if len(before) > 1:
                        before_sorted = before.sort_values('DateTime_subdaily')
                        t1, t2 = before_sorted['DateTime_subdaily'].iloc[-2:].values
                        v1, v2 = before_sorted['compensated_LEVEL_m'].iloc[-2:].values
                        time_diff = (t2 - t1) / np.timedelta64(1, 'm')  # Convert to minutes
                        rate = (v2 - v1) / time_diff  # Rate of change per minute
                    
                        # Extrapolate forward
                        time_diff = (manual_time - t2).total_seconds() / 60  # Convert to minutes
                        pressure_head = v2 + rate * time_diff

                else:
                    # Skip if we don't have enough data
                    if before.empty:
                        logging.debug(f"No BEFORE manual entry for {well} and {deploy}")
                    if after.empty:
                        logging.debug(f"No AFTER manual entry for {well} and {deploy}")
                    else:
                        logging.debug(f"Skipping ahead, no exact manual entry for {well} and {deploy}")
                    continue
                
            # TODO: Compute the sensor level
            this_sensor_level = pressure_head + manual_groundwater_m

            sensor_level_list.append(this_sensor_level)
            
            if sensor_level_list:
                # Store the average of all sensor levels
                avg_sensor_level = statistics.mean(sensor_level_list)
                sensor_levels[(well, deploy)] = avg_sensor_level
                
                if len(sensor_level_list) > 1:
                    # Compute drift error as standard error of the mean
                    drift_errors[(well, deploy)] = (
                        statistics.stdev(sensor_level_list) / 
                        math.sqrt(len(sensor_level_list)))
                
    # Log information about offsets
    logging.debug(f"Sensor level dictionary has {len(sensor_levels)}" 
                  + "elements:\n" + 
                  pprint.pformat(sensor_levels, indent=4))
    logging.debug(f"Drift error dictionary has {len(drift_errors)}"
                  + "elements:\n" + pprint.pformat(drift_errors, indent=4))

    for (well, deploy), this_sensor_level in sensor_levels.items():
        if isinstance(this_sensor_level, float) and math.isnan(this_sensor_level):
            logging.info(f"Offset is NaN for {well} and {deploy}")
    
    return sensor_levels

## Convert baro-compensated water level from sensor 
## so that it's relative to the ground surface
## not the sensor level
## Use gw_df argument
def convert_relativeToGround(subdaily_df):
    """
    With groundwater dataframe as argument, 
    convert baro-compensated water level 
    so that it's relative to the ground surface, not the sensor level.
    """
    # set measurement frequency interval (in minutes),
    #   use to detect deployment breaks
    measurement_frequency_interval=10
    
    # Import manual groundwater data + setup for analysis
    biweek_df = pd.read_csv(gw_data_dir + gw_biweekly_file)
    biweek_df['DateTime'] = biweek_df['timestamp'].astype('datetime64[ns]')
    biweek_df = biweek_df.drop(columns=['timestamp'])
    
    # Sort and group dataframes
    subdaily_df = subdaily_df.sort_values(by=['well_id', 'DateTime'])
    biweek_df = biweek_df.sort_values(by=['well_id','DateTime'])
    well_group_df = subdaily_df.groupby('well_id')
    
    # In subdaily_df, detect breaks in the 10-minute interval
    # and convert to minutes as a numeric value
    subdaily_df['time_diff'] = (
        well_group_df['DateTime'].diff().dt.total_seconds().
        div(60).fillna(0) # replace NAN with 0
    )
    
    # Assign deployment number per well by detecting time_diff > 10 min
    subdaily_df['deployment'] = well_group_df['time_diff'].transform(lambda x: (
            x != measurement_frequency_interval).cumsum())
    
    # Log number of deployments
    unique_deployments = subdaily_df[['well_id', 'deployment']].drop_duplicates()
    logging.info("ALERT: Number of deployments in convert_relativeToGround is:"
                 + f" {len(unique_deployments)}\n")
    
    # Drop helper column
    subdaily_df = subdaily_df.drop(columns=['time_diff'])
    
    ## Find manual measurements for each deployment
    
    # Merge the biweekly and subdaily datafarmes
    merged_df = pd.merge(
        subdaily_df,
        biweek_df[['well_id', 'DateTime', 'ground_to_water_cm']],
        on='well_id',
        suffixes=('_subdaily', '_biweek')
        )
    
    # Calculate the time difference in minutes
    merged_df['time_diff'] = ((merged_df['DateTime_subdaily'] - 
                              merged_df['DateTime_biweek']).dt.
                              total_seconds() / 60)
    
    # Filter out rows where time diff exceeds the subdaily measuremnt frequency
    merged_df = merged_df[abs(merged_df['time_diff']) 
                          <= (3*measurement_frequency_interval)]

    # Remove and log where ground_to_water_cm for a deployment is nan
    deploy_group = merged_df.groupby(['well_id', 'deployment'])
    
    # Remove any deployment where all NaNs for the deployment
    nan_group_all = deploy_group['ground_to_water_cm'].transform(
         lambda x: x.isna().all())
    
    nan_deployments = merged_df.loc[nan_group_all,['well_id',
                                               'deployment']].drop_duplicates()
    
    for _, row in nan_deployments.iterrows():
        logging.info("WARNING: Assume well was dry for *full* deployment.\n" 
                     + f"Removing {row['well_id']} and {row['deployment']}"
                     + "from subdaily dataframe.\n")
    
    # Remove NaN deployments from subdaily_df
    # with an inner join (tags subdaily_df rows that match nan_deployment)
    subdaily_df = subdaily_df.merge(nan_deployments, on=['well_id', 
                                                         'deployment'], 
                                    how='left', 
                                    indicator=True)

    # Keep only rows that do NOT match the NaN deployments
    # by filtering out rows with _merge, created by innerjoin with indicator=T
    subdaily_df = subdaily_df[subdaily_df['_merge'] == 'left_only'].drop(columns=['_merge'])
    
    # Identify rows to drop from merged_df
    nan_rows = merged_df[merged_df['ground_to_water_cm'].isna()]
    # Count total rows to be removed
    num_dropped_rows = len(nan_rows)
    # Get unique well_id + deployment groups affected
    affected_deployments = nan_rows[['well_id', 'deployment']].drop_duplicates()

    # Log the results
    logging.info(f"Removing {num_dropped_rows} rows where 'ground_to_water_cm' is NaN.")
    logging.info(f"Affected well_id + deployment groups:\n{affected_deployments.to_string(index=False)}")

    # Drop NaN rows from merged_df
    merged_df = merged_df.dropna(subset=['ground_to_water_cm'])
    
    # # JN 2025/02/28 replaced the following lines with isna().any()
    # # nan_group = deploy_group['ground_to_water_cm'].transform(
    # #     lambda x: x.isna().all())
    # nan_group_any = deploy_group['ground_to_water_cm'].transform(
    #     lambda x: x.isna().any())
    
    # nan_measurements = merged_df.loc[nan_group_any,['well_id',
    #                                            'deployment']].drop_duplicates()
    # # Log where NaNs removed   
    # logging.info(
    #     f"WARNING: {len(nan_measurements)} of {len(deploy_group)} deployments "
    #     + f"removed from merged dataframe.\n"
    #     + f"Ground_to_water_cm = NaN for *some* of \n {nan_measurements}\n\n")
    
    # Remove NaNs, assume it occurs because well was dry during measurement
    #merged_df = merged_df[~nan_group_any]
    
    # Validate results 
    # if (debug_gtw):
    #         # Check if at least 2 rows of manual measurements per well_id and deployment
    #         row_counts = merged_df.groupby(['well_id', 'deployment']).size()
    #         groups_with_less_than_two = row_counts[row_counts < 2].index
    #         rows_with_less_than_two = merged_df[merged_df.set_index(
    #             ['well_id', 'deployment']).index.isin(
    #                 groups_with_less_than_two)]
    #         logging.debug("Deployments with <2 manual measurements:\n %s" %
    #               rows_with_less_than_two[['well_id','deployment',
    #                                        'DateTime_subdaily',
    #                                        'DateTime_biweek']])

    # Validate results
    if (debug_gtw):
        # Identify deployments with only one unique 'DateTime_biweek'
        single_biweek_deployments = (
            merged_df.groupby(['well_id', 'deployment'])['DateTime_biweek']
            .nunique()
            .reset_index()
        )
        
        # Filter to deployments with exactly one unique 'DateTime_biweek'
        single_biweek_deployments = single_biweek_deployments[single_biweek_deployments['DateTime_biweek'] == 1]
        
        # Merge to get relevant details
        single_biweek_details = merged_df.merge(single_biweek_deployments[['well_id', 'deployment']], 
                                                on=['well_id', 'deployment'])
        
        # Log the affected deployments
        if not single_biweek_details.empty:
            logging.info("Deployments with only ONE unique manual measurement:\n" + 
                         single_biweek_details[['well_id', 'deployment']].drop_duplicates().to_string(index=False))
        else:
            logging.info("No deployments found where 'DateTime_biweek' has only one unique value.")
        

    # Convert 'ground_to_water_cm' to meters
    merged_df = merged_df.copy()
    merged_df['ground_to_water_m'] = merged_df['ground_to_water_cm'] / 100    

    # Calculate sensor level below the ground surface (in meters)
    sensor_levels_m = calculate_sensor_level(merged_df)
    
    # Apply manual measurement offsets to subdaily_df
    def calculate_subdaily_water_level(row):
        key = (row['well_id'], row['deployment'])
        return sensor_levels_m.get(key, np.nan) - row['compensated_LEVEL_m']
    
    subdaily_df['ground_to_water_m'] = subdaily_df.apply(
                                        calculate_subdaily_water_level, axis=1)

    # Finished processing all logger files
    # Now save singular file of all logger data
    
    # Re-order columns
    column_order = ['well_id', 'DateTime', 'deployment', 'ground_to_water_m', 
                    'raw_LEVEL_m', 'baro_LEVEL_m', 
                    'compensated_LEVEL_m', 'Temp_c']
    subdaily_df = subdaily_df.reindex(columns=column_order)  
    
    # Save
    subdaily_df.to_csv(gw_data_dir + subdaily_full_file, encoding='ISO-8859-1', index=False)
    
    # Plot to validate if debugging
    if debug_gtw:
        plot_weekly_groundwater_data_by_well(subdaily_df, biweek_df)
        plot_subdaily_groundwater_by_deployment(subdaily_df, biweek_df)
    return subdaily_df


### EXECUTE FUNCTIONS TO PROCESS LOGGER DATA

## Starts with individual raw Solinst logger files 
##   in the 'subdaily_dir' directory
    
## 1. Cut logger entries when sensor not in the well, 
##     as indicated by drastic water level or temperature change
if process_cut:
    waterLevel_df = cut_logger_data()
else: 
    waterLevel_df = pd.read_csv(cut_data_file)
    waterLevel_df['DateTime'] = waterLevel_df.DateTime.astype('datetime64[ns]')

## 2. Compensate logger water level (m) based on barometer data (kPa)
if process_baro: 
    waterLevel_df = compensate_baro(convert_baro_solinst(get_baro_dataframe_solinst()), 
                                    waterLevel_df)

## 3. Convert water level from 'relative to sensor' to 
###    'relative to ground surface elevation' (in meters)
waterLevel_df = convert_relativeToGround(waterLevel_df)

print(waterLevel_df)
    