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
        file naming convention and formatting
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
import numpy as np
import pandas as pd
import geopandas as gpd # to handle geojson file
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.colors as mcolors
import matplotlib.patches as patches
import os
import datetime
from datetime import time
import re # regexpression library to extract well id from filenames
import math
import statistics
import logging
import pprint

### SETUP FLAGS 
##  for processing, logging, debugging and data validation

# For 2025:
process_cut = True

# PRE-2025
#process_cut = False
process_baro = True #not working with false yet

save_fig = False #not working yet, throwing error

debug_cut = True
debug_baro = True
debug_gtw = True

### GLOBAL VARIABLES
gravity_sagehen = 9.800698845791 # based on gravity at 1934 meters
density_factor = 1/gravity_sagehen # to convert kPa to m of pressure
baro_standard_elevation = 1933.7 # in meters? TODO: is this Tower #1 elev?

### SETUP DIRECTORY + FILE NAMES
project_dir = '/VOLUMES/SANDISK_SSD_G40/GoogleDrive/GitHub/sagehen_meadows/'
gw_data_dir = project_dir + 'data/field_observations/groundwater/'

# Year-dependent variables
# For 2025, try to limit processing and results to 2025 only
subdaily_dir = gw_data_dir + 'subdaily_loggers/RAW/Solinst_levelogger_2025/'
gw_biweekly_file = gw_data_dir + 'manual/groundwater_manual_2025_FULL.csv' #ground_to_water in cm
gw_daily_file = gw_data_dir + 'groundwater_daily_2025_FULL_COMBINED.csv' # manual + logger data
subdaily_full_file = 'subdaily_loggers/FULL/groundwater_subdaily_2025_FULL.csv'

# PRE-2025
# subdaily_dir = gw_data_dir + 'subdaily_loggers/RAW/Solinst_levelogger_all/'
# gw_biweekly_file = gw_data_dir + 'biweekly_manual/groundwater_biweekly_FULL.csv' #ground_to_water in cm
# gw_daily_file = gw_data_dir + 'groundwater_daily_FULL_COMBINED.csv' # manual + logger data
# subdaily_full_file = 'subdaily_loggers/FULL/groundwater_subdaily_FULL.csv'

cut_dir = gw_data_dir + 'subdaily_loggers/WORKING/cut/'
solinst_baro_data_dir = gw_data_dir + 'subdaily_loggers/RAW/baro_data/'
compensated_dir = gw_data_dir + 'subdaily_loggers/WORKING/baro_compensated/'
gtw_logger_dir = gw_data_dir + 'subdaily_loggers/WORKING/relative_to_ground/'
os.makedirs(gtw_logger_dir,exist_ok=True)
os.makedirs("logs",exist_ok=True)

cut_times_file = gw_data_dir + 'subdaily_loggers/groundwater_logger_times.csv'
cut_data_file = cut_dir+'cut_all_wells.csv'
well_elevation_file = gw_data_dir + 'Sagehen_Wells_Natali_6417.geojson'

## For 2025, try with new combined WRCC and DRI weather data
station_dendra_data_dir = project_dir + 'data/station_instrumentation/climate/'
station_dendra_file = station_dendra_data_dir + 'Weather_2010_2025_10min_SagehenTower1.csv'

# PRE-2025
#station_dendra_data_dir = project_dir + 'data/station_instrumentation/climate/Dendra/'
#station_dendra_file = station_dendra_data_dir + 'RAW/Dendra_Sagehen_2007_2024.csv'
# OLDER
#station_baro_file = station_dendra_data_dir + 'Dendra_Sagehen_2007_2024.csv'

# Configure and test logging to write to a file
log_level=logging.INFO  # Can log different levels: INFO, DEBUG or ERROR
if (debug_cut or debug_baro or debug_gtw):
    log_level=logging.DEBUG
    print("LOG LEVEL IS DEBUG")

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

def remove_outliers(df, column_name, multiplier=1.5):
    """
    Remove outliers based on IQR method.
    
    Parameters:
    df : pandas DataFrame
        The dataframe containing the data.
    column_name : str
        The column in which to identify outliers.
    multiplier : float, optional
        The factor to multiply the IQR by (default is 1.5).
    
    Returns:
    pandas DataFrame
        DataFrame with outliers removed.
    """
    # Calculate the IQR
    Q1 = df[column_name].quantile(0.25)
    Q3 = df[column_name].quantile(0.75)
    IQR = Q3 - Q1
    
    # Calculate bounds
    lower_bound = Q1 - multiplier * IQR
    upper_bound = Q3 + multiplier * IQR
    
    # Remove outliers
    df_cleaned = df[(df[column_name] >= lower_bound) & (df[column_name] <= upper_bound)]
    
    return df_cleaned

## Consolidate all logger csv files into one dataframe    
def get_logger_dataframe():
    """Consolidate all logger csv filesinto one dataframe."""
    for f in os.listdir(subdaily_dir):
        log_df = pd.concat([pd.read_csv(f, header=11, encoding='ISO-8859-1')])
    log_df['DT'] = pd.to_datetime(log_df['Date'] + ' ' + log_df['Time'])
    return log_df

def get_well_elevations(gw_df):
    """
    Adds new column for elevation of the well (in meters) based on geojson data
    
    Parameters:
    gw_df : pandas dataframe
        groundwater reading data from sensor

    Returns:
        gw_df: pandas dataframe
        groundwater reading data with a new column, 'elevation_m'
    """
    # Load well elevation data from GeoJSON
    well_elevations = gpd.read_file(well_elevation_file)[['Name', 'elevation_m']]
    well_elevations = well_elevations.rename(columns={'Name': 'well_id'})
    # Merge elevation data into groundwater dataframe
    gw_df = gw_df.merge(well_elevations, on='well_id', how='left')
    
    return gw_df

## Plot subdaily logger dataframe
#  Assume dataframe has DT column converted to datetime
def plot_water_level(logger,water_level_column_name,well_id):
    fig, ax1 = plt.subplots(figsize=(10, 5), nrows=1, sharex=True)
    ax1.plot(logger['DateTime'], logger[water_level_column_name])
    ax1.set_ylabel('Water Level', size=12)

    for tick in ax1.yaxis.get_major_ticks():
        tick.label.set_fontsize(9)

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
        tick.label.set_fontsize(8)
    for tick in ax2.xaxis.get_major_ticks():
        tick.label.set_fontsize(8)

    fig.suptitle('Before/After cut of GW Level and Temp at Well '+ well_id, size=12)
    plt.show()
    
## Plot subdaily logger dataframe before/after cut times
#  Assume dataframe has DT column converted to datetime
def plot_water_temp_compare(before_df, manual_df, after_df, water_level_column_name, well_id):
    fig, (ax1, ax2) = plt.subplots(figsize=(10, 5), nrows=2, sharex=True)
    ax1.set_ylabel('Water Level', size=12)
    ax2.set_ylabel('Temperature', size=12)

    ax1.plot(before_df['DT'], before_df[water_level_column_name], color="b", linewidth=0.6, label="Cut due to date")
    ax2.plot(before_df['DT'], before_df['TEMPERATURE'], color="b", linewidth=0.6, label="Cut due to date")
    
    ax1.plot(manual_df['DT'], manual_df[water_level_column_name], color="g", linewidth=0.6, label="Cut due to Temp change")
    ax2.plot(manual_df['DT'], manual_df['TEMPERATURE'], color="g", linewidth=0.6, label="Cut due to Temp change")
    
    ax1.plot(after_df['DT'], after_df[water_level_column_name], color="r", linewidth=0.6, label="Remaining data")
    ax2.plot(after_df['DT'], after_df['TEMPERATURE'], color="r", linewidth=0.6, label="Remaining data")

    # Throwing error --> AttributeError: 'YTick' object has no attribute 'label'
    # for tick in ax1.yaxis.get_major_ticks():
    #     tick.label.set_fontsize(10)
    # for tick in ax2.yaxis.get_major_ticks():
    #     tick.label.set_fontsize(8)
    # for tick in ax2.xaxis.get_major_ticks():
    #     tick.label.set_fontsize(8)

    plt.legend()
    fig.suptitle(f"Cut of GW Level and Temp at Well {well_id}\n"
                 + f"{min(after_df['DT'])} to\n"
                 + f"{max(after_df['DT'])}", size=10)
    plt.xticks(rotation=45)
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

def plot_subdaily_groundwater_by_deployment(subdaily_df, biweek_df, 
                                            plot_rain=False):
    """
    Plots subdaily groundwater level (in cm) for each well_id and deployment,
    overlaying biweekly manual measurements if they are within 10 minutes.

    Parameters:
        subdaily_df (DataFrame): Logger data with columns 
                ['well_id', 'deployment', 'DateTime', 'ground_to_water_m'].
        biweek_df (DataFrame): Manual measurement data with columns 
            ['well_id', 'DateTime', 'ground_to_water_cm'].
        plot_rain: a binary, should the function plot rainfall? Y or N?

    Returns:
    None, displays the plots.
    """
    # Convert groundwater depth from meters to cm
    subdaily_df['ground_to_water_cm'] = subdaily_df['ground_to_water_m'] * 100  
    
    # Convert DateTime columns to pandas datetime format
    subdaily_df['DateTime'] = pd.to_datetime(subdaily_df['DateTime'])
    biweek_df['DateTime'] = pd.to_datetime(biweek_df['DateTime'])
    
    # Load rainfall if needed
    if plot_rain:
        rain_df = get_rainfall_dendra()
        rain_df['DateTime'] = pd.to_datetime(rain_df['DateTime'])
    
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
        
        # Setup plot
        fig, ax1 = plt.subplots(figsize=(12, 5))
    
        # Plot subdaily groundwater levels (black)
        ax1.plot(well_subdaily['DateTime'], 
                 well_subdaily['ground_to_water_cm'], 
                 linestyle='-', marker='o', markersize=0.6, 
                 color='black', linewidth=0.4, label='Logger (10-min intervals)')
    
        # Biweekly groundwater levels (red) for overlapping times
        if not well_biweek.empty:
            ax1.scatter(well_biweek['DateTime'], 
                        well_biweek['ground_to_water_cm'], 
                        color='red', s=30, 
                        label='Biweekly Manual Measurement', zorder=3)
    
        # Formatting
        ax1.set_xlabel("DateTime")
        ax1.set_ylabel("Groundwater Level (cm)")
        ax1.invert_yaxis()
        ax1.grid(True)
        plot_title = "Subdaily Groundwater Levels"
        
        
    
        # Plot rainfall
        if plot_rain:
            ax2 = ax1.twinx()
            rain_window = rain_df[
                (rain_df['DateTime'] >= well_subdaily['DateTime'].min()) &
                (rain_df['DateTime'] <= well_subdaily['DateTime'].max())]
            ax2.bar(rain_window['DateTime'], rain_window['rainfall_mm'],
                    width=0.005, color='blue', alpha=0.5, label='Rainfall (mm)')
            ax2.set_ylabel("Rainfall (mm)", color='blue')
            plot_title += " and Rainfall"

        plot_title += (f" for Well {well_id} (Deployment {deployment} from"
                      f" {min(well_subdaily['DateTime'])} to "
                      f"{max(well_subdaily['DateTime'])})")
                      
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels() if plot_rain else ([], [])
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')

        plt.title(plot_title)
        plt.tight_layout()
        plt.show()

def plot_dataframes(df1, df2, column_name, title, timespan=None):
    """
    Plots the given column from two DataFrames against their DateTime column.

    Parameters:
    df1 (pd.DataFrame): First dataframe with 'DateTime' column and target column.
    df2 (pd.DataFrame): Second dataframe with 'DateTime' column and target column.
    column_name (str): Name of the column to plot on the y-axis.
    title (str): Preface for the title to describe df1 vs df2
    timespan (tuple): Optional (start_date, end_date) to limit x-axis range.
                      Accepts strings or datetime-like objects.
    """
    # Ensure DateTime is sorted
    df1.sort_values('DateTime', inplace=True)
    df2.sort_values('DateTime', inplace=True)
    
    # Filter by timespan if provided
    if timespan is not None:
        start, end = pd.to_datetime(timespan[0]), pd.to_datetime(timespan[1])
        df1 = df1[(df1['DateTime'] >= start) & (df1['DateTime'] <= end)]
        df2 = df2[(df2['DateTime'] >= start) & (df2['DateTime'] <= end)]

    # Plotting
    plt.figure(figsize=(12, 6))
    plt.plot(df1['DateTime'], df1[column_name], label='DataFrame 1', linestyle='-', linewidth=0.6)
    plt.plot(df2['DateTime'], df2[column_name], label='DataFrame 2', linestyle='--', linewidth=0.6)
    
    plt.xlabel('DateTime')
    plt.ylabel(column_name)
    plt.title(f'{title}: {column_name} Over Time')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def plot_baro_compare(df1, df2):
    """
    Plots and compares barometric data from two dataframes.
    Each year's data is plotted in a separate subplot.
    Only years where both dataframes have data are included.
    
    Parameters:
    df1, df2: pandas DataFrame
        DataFrames contain 'DateTime' and 'baro_LEVEL_kPa' columns.
    """
    df3 = normalize_baro(df1, df2)

    # Extract years present in initial datasets
    years_df1 = set(df1['DateTime'].dt.year)
    years_df2 = set(df2['DateTime'].dt.year)
    common_years = sorted(years_df1.intersection(years_df2))
    
    if not common_years:
        print("No common years with data between the two datasets.")
        return
    
    fig, axes = plt.subplots(len(common_years), 1, 
                             figsize=(10, 5 * len(common_years)), sharex=True)
    if len(common_years) == 1:
        axes = [axes]  # Ensure axes is iterable
    
    for ax, year in zip(axes, common_years):
        # Filter data for the given year
        df1_year = df1[df1['DateTime'].dt.year == year].copy()
        df2_year = df2[df2['DateTime'].dt.year == year].copy()
        df3_year = df3[df3['DateTime'].dt.year == year].copy()

        # Convert DateTime to day of the year
        df1_year['DayOfYear'] = df1_year['DateTime'].dt.dayofyear
        df2_year['DayOfYear'] = df2_year['DateTime'].dt.dayofyear
        df3_year['DayOfYear'] = df3_year['DateTime'].dt.dayofyear

        
        # Plot data with smaller lines and markers
        ax.plot(df1_year['DayOfYear'], df1_year['baro_Pressure_kPa'], label='Solinst', linestyle='-', linewidth=0.9)
        ax.plot(df2_year['DayOfYear'], df2_year['baro_Pressure_kPa'], label='Dendra', linestyle='-',  linewidth=0.7)
        ax.plot(df3_year['DayOfYear'], df3_year['baro_Pressure_kPa'], label='Offset Correction', linestyle='--', linewidth=0.5)

        # Formatting
        ax.set_title(f'Barometric Pressure Comparison for {year}')
        ax.set_ylabel('Barometric Pressure (kPa)')
        ax.legend()
        ax.grid(True)
    
    plt.xlabel('Day of Year')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()
    return

def plot_timeseries_gridmap(df):
    # Add DOY and year columns
    df['DayOfYear'] = df['DateTime'].dt.dayofyear
    df['Year'] = df['DateTime'].dt.year
    df['month'] = df['DateTime'].dt.month

    # Extract site and category info
    df['site'] = df['well_id'].str[0].replace({'E': 'East', 'K': 'Kiln', 'L': 'Lower'})
    df['plant'] = df['well_id'].str[1]
    df['zone'] = df['well_id'].str[2]
    df['category'] = df['plant'] + df['zone']

    categories = sorted(df['category'].unique())
    sites = ['East', 'Kiln', 'Lower']

    # Get range of DOYs
    min_doy = df['DayOfYear'].min()
    max_doy = df['DayOfYear'].max()

    # Count number of years for each site/category/DOY
    counts = df.drop_duplicates(subset=['well_id', 'DayOfYear', 'Year'])
    summary = counts.groupby(['site', 'category', 'DayOfYear'])['Year'].nunique().reset_index()
    summary = summary.rename(columns={'Year': 'year_count'})

    # Create color map
    cmap = plt.cm.magma_r # to reverse, use _r
    norm = mcolors.Normalize(vmin=0, vmax=summary['year_count'].max())
    
    # Get months in data and sort them
    months_in_data = sorted(df['month'].unique())

    # Map month numbers to month initials
    month_labels = {
        1: 'J', 2: 'F', 3: 'M', 4: 'A', 5: 'M', 6: 'J', 7: 'J', 8: 'A', 9: 'S', 10: 'O', 11: 'N', 12: 'D'
    }
    dynamic_month_labels = [month_labels[month] for month in months_in_data]

    # Mapping DOY to grid position: (row for month, column for day-in-month)
    day_to_grid = {}
    for month in months_in_data:
        for day in range(1, 32):
            try:
                doy = pd.Timestamp(f'2021-{month:02d}-{day:02d}').dayofyear
                if min_doy <= doy <= max_doy:
                    day_to_grid[doy] = (months_in_data.index(month), day - 1)
            except ValueError:
                continue

    # Start plotting
    fig, axes = plt.subplots(nrows=len(categories), ncols=len(sites), figsize=(15, 12), sharex=True, sharey=True)

    square_size = 1.0
    spacing = 0.2

    for i, cat in enumerate(categories):
        for j, site in enumerate(sites):
            ax = axes[i, j] if len(categories) > 1 else axes[j]
            ax.set_xlim(0, 32)
            ax.set_ylim(0, len(months_in_data))  # Dynamic number of rows based on months
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_aspect('equal')
            ax.set_facecolor('white')
            
            # Set gray border around each grid
            for spine in ax.spines.values():
                spine.set_edgecolor('gray')

            subset = summary[(summary['site'] == site) & (summary['category'] == cat)]
            doy_to_count = dict(zip(subset['DayOfYear'], subset['year_count']))

            for doy, (row, col) in day_to_grid.items():
                count = doy_to_count.get(doy, 0)
                color = cmap(norm(count))
                x = col * (square_size + spacing)
                y = len(months_in_data) - row - 1  # Flip to have May on top

                rect = patches.Rectangle((x, y), square_size, square_size,
                                         facecolor=color, edgecolor='white', 
                                         linewidth=0.4)
                ax.add_patch(rect)

            if j == 0:
                ax.set_ylabel(cat, rotation=0, labelpad=25, va='center', 
                              fontsize=12)
            if i == 0:
                ax.set_title(site, fontsize=12)

            # Add dynamic month labels on the left side of each row
            if j == 0 and i == 0:  # Only add once for the first site and first category
                for idx, label in enumerate(dynamic_month_labels):
                    # move the month labels
                    ax.text(-1, len(months_in_data) - idx - 0.5, label, 
                            ha='center', va='center', fontsize=9, 
                            color='gray')

    # Add colorbar
    max_years = summary['year_count'].max()

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=axes.ravel().tolist(), orientation='horizontal', 
                        fraction=0.05, pad=0.02, shrink=0.4)
    cbar.set_label('Years with data')
    # Show only integer ticks on the colorbar
    cbar.set_ticks(range(0, max_years + 1))

    fig.suptitle("Groundwater Well Data Overlap by DOY and Category", fontsize=14)
    plt.tight_layout(rect=[0, 0.15, 1, 0.96])
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
    for f in sorted(os.listdir(subdaily_dir)):
        if f.endswith('.csv'):
        
            if debug_cut: logging.debug(f)
            
            # get well_id based on filename
            well_id = re.split('_20',f)[0]
                        
            # create data frame with data from this csv file
            deployment_df = pd.read_csv(subdaily_dir+f, header=11, encoding='ISO-8859-1')
            
            # Convert 'Date' to datetime and 'Time' to timedelta
            deployment_df.insert(3, 'DT', pd.to_datetime(deployment_df['Date'] 
                                                         + ' ' + deployment_df['Time'], format='mixed'))
            
            # add well_id to dataframe
            deployment_df.insert(0, 'well_id', well_id)
    
            # save original version for comparison plot later
            orig_deployment_df = deployment_df.rename(columns={'LEVEL': 'raw_Level_m'})  
            
            ## Calculate difference between raw datetime and field notes start_time and end_time
            #  and select matching deployments, first by well_id
            #  this result may have timing for several deployments
            well_time_df = log_time_df[log_time_df['well_id'] == well_id]
            
            ## ERROR HANDLING if no time limits found for this well deployment in field notes
            if well_time_df.empty: 
                logging.info(f'ALERT: No time limits for {well_id}:' 
                      + 'check if well name is correct. Exiting cut process.')
                break
                       
            # Strip timing of deployment from the filename
            # Extract YYYY, MMDD_min, MMDD_max using regex
            match = re.search(r"_(\d{4})_(\d{4})_(\d{4})\.csv", f)
            if match:
                year, min_mmdd, max_mmdd = match.groups()
                
                # Construct timestamps
                start_time = pd.Timestamp(f"{year}-{min_mmdd[:2]}-{min_mmdd[2:]} 00:00:00")
                end_time = pd.Timestamp(f"{year}-{max_mmdd[:2]}-{max_mmdd[2:]} 00:00:00")
            else: 
                logging.debug(f'ALERT: No min/max time from {f}. Exiting cut process.')
                break
            
            time_delta = pd.Timedelta(hours=48)
            well_time_df = well_time_df[
                ((well_time_df['start'] >= (start_time - time_delta)) & 
                (well_time_df['start'] <= (start_time + time_delta))) & 
                ((well_time_df['end'] >= (end_time - time_delta)) & 
                (well_time_df['end'] <= (end_time + time_delta)))
            ]

            ## ERROR HANDLING: only continue if one matching entry of start/stop times
            if well_time_df.shape[0] != 1:
                warning_str = (f"WARNING: more/less than one row for {well_id} "
                                "in cut_logger_data(). Which one to use?"
                                " Check date range in logger csv. Exiting.")
                logging.info(warning_str)
                logging.debug(well_time_df)
                break
            
            ## Select logger data rows within start/end times from field notes
            # number of minutes to subtract or add from start/end times
            time_delta=pd.Timedelta(minutes=10) 
            
            start_time = well_time_df['start'].iloc[0] - time_delta
            end_time = well_time_df['end'].iloc[0] + time_delta
            
            # apply filtering mask
            deployment_df = deployment_df[(deployment_df['DT'] >= start_time) & (deployment_df['DT'] <= end_time)]
            
            # take snapshot of dataframe to plot and validate later
            manual_deployment_df = deployment_df.rename(columns={'LEVEL': 'raw_Level_m'})
            
            ## Calculate temperature rate of change
            # temp change threshold that controls cutoff points
            change_threshold = well_time_df['temp_threshold'].iloc[0]
            if debug_cut: logging.debug(str(change_threshold))
            deployment_df['Rate of Change'] = np.append(np.abs(
                (deployment_df['TEMPERATURE'].iloc[:-1].values - 
                 deployment_df['TEMPERATURE'].iloc[1:].values)/(10)), 0.0001)

            # Split data in half
            first = deployment_df.iloc[:int(deployment_df.shape[0]/2)]
            second = deployment_df.iloc[int(deployment_df.shape[0]/2):]
        
            # In first half, cut out all data before the last point that has a rate of change greater than the change threshold
            try:
                index = first.loc[(first['Rate of Change'] >= 
                                   change_threshold), :].index[-1]
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
            deployment_df = pd.concat((first_cut, second_cut), axis=0)
            deployment_df.rename(columns={'LEVEL': 'raw_Level_m'}, inplace=True)
            
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
            if debug_cut: plot_water_temp_compare(orig_deployment_df, manual_deployment_df, deployment_df,'raw_Level_m',well_id)
            
            # save individual csv file with cut times
            deployment_df.to_csv(cut_dir+'cut_'+f, encoding='ISO-8859-1', index=False)
            
            # cut_logger_df = cut_logger_df.append(log_df)
            cut_logger_df = pd.concat([cut_logger_df, deployment_df])
    
    # cleanup logger data to save in human-readable format
    cut_logger_df.drop(['Date', 'Time', 'ms', 'Rate of Change'], axis=1, inplace=True)
    cut_logger_df.rename(columns={'DT': 'DateTime', 'TEMPERATURE': 'Temp_c'}, inplace=True)
    cut_logger_df.to_csv(cut_data_file, index=False)
    #cut_count_df.to_csv(cut_dir+'cut_count_'+str(change_threshold)+'.csv')
    cut_count_df.to_csv(cut_dir+'cut_count.csv', index=False)
    
    return cut_logger_df
    
## Consolidate all solinst barometer CSV files into one dataframe
## Rename columns with units and filter based on start/end time of gw data
def get_baro_solinst(start_time, end_time):
    """Consolidate all barometer CSV files into one dataframe, then convert LEVEL (kPa) to LEVEL (m); add a column for LEVEL (m); rename columns with units."""
    all_baro_data = pd.DataFrame()
    
    # Get elevations for well_ids from geojson file
    well_elevations = gpd.read_file(well_elevation_file)[['Name', 'elevation_m']]
    well_elevations = well_elevations.rename(columns={'Name': 'well_id'})
    
    # Set index for fast lookups in the for loop
    well_elevations = well_elevations.set_index('well_id')

    for f in os.listdir(solinst_baro_data_dir):
        if f.endswith('.csv'):
            if debug_baro: 
                logging.debug(f"Fetching baro data from {f}")
            
            ## Get data from csv and format date
            new_baro = pd.read_csv(solinst_baro_data_dir + f, header=10, encoding='ISO-8859-1')
            new_baro['DateTime'] = pd.to_datetime(
                new_baro['Date'] + ' ' + new_baro['Time'],
                format='%m/%d/%Y %I:%M:%S %p')
            
            # Extract well_id from filename using regex and add column
            match = re.search(r'Baro_([A-Za-z0-9-]{4,8})_', f)
            well_id = match.group(1) if match else None  # Extract matched group
            
            if well_id in well_elevations.index:
                elevation_m = well_elevations.at[well_id, 'elevation_m'] 
            else:
                elevation_m = None

            if debug_baro and elevation_m == None:
                logging.debug(f"No elevation found for well_id {well_id}")
            
            # Assign the elevation to the DataFrame
            new_baro['elevation_m'] = elevation_m
            
            # Cleanup data so column names clear, not carrying unneeded data
            new_baro.drop(['Date', 'Time', 'ms'], axis=1, inplace=True)
            new_baro.rename(columns={'LEVEL': 'baro_Pressure_kPa', 
                                     'TEMPERATURE': 'baro_Temp_C'}, 
                            inplace=True)
            
            if debug_baro: 
                logging.debug(f"Length of bara dataframe: {str(len(new_baro))}")
                str_b_range = 'min/max of new baro file time:' + str(min(new_baro['DateTime'])) + ' to ' + str(max(new_baro['DateTime']))
                logging.debug(str_b_range)
                
            all_baro_data = pd.concat([all_baro_data, new_baro],
                                      ignore_index=True, sort=True)
    
    # Filter baro data so only store those relevant to gw data
    all_baro_data = all_baro_data[(all_baro_data['DateTime'] >= start_time) 
                                  & (all_baro_data['DateTime'] <= end_time)]
    
    if debug_baro: 
        logging.debug(str(len(all_baro_data))+ '\n')
        
    return all_baro_data

def get_rainfall_dendra(start_time, end_time):
    """Retrieve 10-min frequency rainfall data from Dendra CSV files
       for requested dates"""       
    # Get needed data from the csv
    rainfall = pd.read_csv(station_dendra_file)
    rainfall = rainfall[['time', 'precipitation-geonor-mm-mm']]
    rainfall = rainfall.rename(columns={'precipitation-geonor-mm-mm': 'rainfall_mm'})
    
    # Filter for start and end times
    rainfall['DateTime'] = pd.to_datetime(rainfall['time'])
    rainfall = rainfall[(rainfall['DateTime'] >= start_time) & (rainfall['DateTime'] <= end_time)]
        
    column_order = ['DateTime', 'rainfall_mm']
    rainfall = rainfall.reindex(columns=column_order)

    return rainfall

## Retrieve baro data from Dendra field station 
## Convert pressure reading from mb to kPa
def get_baro_dendra(start_time, end_time):
    """Consolidate all barometer CSV files into one dataframe, then convert LEVEL (kPa) to LEVEL (m); add a column for LEVEL (m); rename columns with units."""
    
    # Get needed data from the csv
    new_baro = pd.read_csv(station_dendra_file)
    new_baro = new_baro[['time', 'barometric-pressure-avg-mb', 'air-temp-avg-degc']]
    new_baro = new_baro.rename(columns={'air-temp-avg-degc': 'baro_Temp_C'})
    
    # Filter for start and end times
    new_baro['DateTime'] = pd.to_datetime(new_baro['time'])
    new_baro = new_baro[(new_baro['DateTime'] >= start_time) & (new_baro['DateTime'] <= end_time)]
    
    if debug_baro: 
        print(str(len(new_baro)))
        str_b_range = 'min/max of new baro file time:' + str(min(new_baro['DateTime'])) + ' to ' + str(max(new_baro['DateTime']))
        print(str_b_range)
        
    # Convert measurement from mb to kPa
    new_baro['baro_Pressure_kPa'] = new_baro['barometric-pressure-avg-mb']*0.1
    new_baro.drop(['barometric-pressure-avg-mb'], axis=1, inplace=True)
    
    column_order = ['DateTime', 'baro_Pressure_kPa', 'baro_Temp_C']
    new_baro = new_baro.reindex(columns=column_order)

    return new_baro

def normalize_baro(df1, df2):
    """
    Computes the mean offset correction for barometric pressure data in df2 
    based on df1. 
    
    Also adjusts time interval between readings from 10 to 5 minuts.
    
    Returns df2 with corrected values.

    Parameters:
        df1, df2: pandas DataFrame
        DataFrames containing 'DateTime' and 'baro_Pressure_kPa' columns.

    Returns:
        df2_offset: pandas DataFrame
    """

    # initialize df2_offset
    df2_offset = df2.copy()

    # determine and apply unique offset for each year
    years_df1 = set(df1['DateTime'].dt.year)
    years_df2 = set(df2['DateTime'].dt.year)
    common_years = sorted(years_df1.intersection(years_df2))

    if not common_years:
        print("No common years with data between the two datasets.")
        return df2_offset

    for year in common_years:
        df1_year_raw = df1[df1['DateTime'].dt.year == year].copy()
        df2_year_raw = df2[df2['DateTime'].dt.year == year].copy()
        
        # Remove outliers for the year
        # - need multiplier of 5 based on plots for 2018-2024
        df1_year = remove_outliers(df1_year_raw, 'baro_Pressure_kPa', 5.0)
        df2_year = remove_outliers(df2_year_raw, 'baro_Pressure_kPa', 5.0)
        
        if debug_baro:
            # Compare plots before/after outlier removal
            plot_dataframes(df1_year_raw, df1_year, 'baro_Pressure_kPa', 
                            'Solinst Baro raw vs clean')
            plot_dataframes(df2_year_raw, df2_year, 'baro_Pressure_kPa', 
                        'Dendra Baro raw vs clean')
            if (year==2021): 
                plot_dataframes(df2_year_raw, df2_year, 'baro_Pressure_kPa', 
                            'Dendra Baro raw vs clean',
                            ('2021-11-15', '2021-11-16'))
            if (year==2024): 
                plot_dataframes(df2_year_raw, df2_year, 'baro_Pressure_kPa', 
                            'Dendra Baro raw vs clean',
                            ('2024-08-16', '2024-08-18'))
            if (year==2025):
                plot_dataframes(df2_year_raw, df2_year, 'baro_Pressure_kPa', 
                        'Dendra Baro raw vs clean',
                        ('2025-08-20', '2024-09-30'))
                
        merged = df1_year[['DateTime','baro_Pressure_kPa', 'baro_Temp_C']].merge(
            df2_year[['DateTime', 'baro_Pressure_kPa', 'baro_Temp_C']], 
            on='DateTime', 
            suffixes=('_df1', '_df2')
            )
    
        if not merged.empty:
            mean_offset = (merged['baro_Pressure_kPa_df1'] - 
                           merged['baro_Pressure_kPa_df2']).mean()
        else:
            mean_offset = 0  # No common data points
        
        # Select rows where the 'DateTime' column matches the current year
        mask = df2_offset['DateTime'].dt.year == year

        # Apply the offset only to those rows
        df2_offset.loc[mask, 'baro_Pressure_kPa'] = ( 
            df2_offset.loc[mask, 'baro_Pressure_kPa'] + mean_offset)
        
    # Sort values and ensure DateTime is a proper index
    df2_offset = df2_offset.sort_values('DateTime').set_index('DateTime')
        
    # Resample to 5-minute intervals to match the finest gw_df interval
    df2_offset = df2_offset.resample("5min").interpolate(method="linear").reset_index()

    # Reset index and return the offset data with increased interval
    return df2_offset


## Converts barometric pressure reading
## from kPa of pressure to meters (m) of pressure head
def convert_baro_kPa_meters(pressure_kPa):
    """
    Converts kPa of pressure to meters (m).
    Param is a pandas Series
    Returns a pandas Series
    """
    return pressure_kPa * density_factor 
      

def adjust_pressure_elevation(df, to_elevation=baro_standard_elevation, from_elevation=None):
    """
    Adjusts barometric pressure readings in df based on elevation change.
    Uses the barometric formula.
    
    Parameters:
    df : pandas DataFrame
        DataFrame containing:
        - 'baro_Pressure_kPa' (barometric pressure in kPa)
        - 'DateTime' (timestamp of the reading)
        - 'baro_Temp_C' (air temperature in Celsius)
        - 'elevation_m' (current elevation of the reading in meters)
    to_elevation : float, optional
        The target elevation to adjust pressure readings to. Default is baro_standard_elevation.
    from_elevation : float, optional
        The source elevation. If None, it uses 'elevation_m' from the DataFrame.
    
    Returns:
    pandas DataFrame
        The input DataFrame with 'baro_Level_kPa' adjusted and 'elevation_m' set to to_elevation.
    """
    
    # Physical constants
    R = 8.3144598  # Universal gas constant (J/(mol*K))
    M = 0.0289644  # Molar mass of Earth's air (kg/mol)
    L = 0.0065  # Standard temperature lapse rate (K/m)
    
    # Ensure from_elevation is set
    if from_elevation is None:
        from_elevation = df['elevation_m']
    
    # Convert temperature to Kelvin
    df['baro_Temp_K'] = df['baro_Temp_C'] + 273.15
    
    # Compute pressure adjustment using the barometric formula
    exponent = (gravity_sagehen * M) / (R * L)
    df['baro_Pressure_kPa'] = df['baro_Pressure_kPa'] * (
        (1 - L * (to_elevation - from_elevation) 
         / df['baro_Temp_K']) ** exponent
    )
    
    # Update elevation column
    df['elevation_m'] = to_elevation
    
    return df


def compensate_baro(gw_df):
    """
    Compensates groundwater sensor readings by removing barometric pressure.
    Removes the barometric pressure (in meters) from the sensor water level.
    
    Parameters:
        gw_df : pandas DataFrame
        Contains groundwater level readings with 'well_id', 'DateTime', and 'raw_LEVEL_m'.
    
    Returns:
        pandas DataFrame
        The groundwater data with corrected water level (in meters)

    
    """
    
    ## 1. Get the barometric data for the date ranges of the gw_df
    
    # Get date ranges of gw_df
    start_time = min(gw_df['DateTime'])
    end_time = max(gw_df['DateTime'])
    
    # Get barometric data for the given date range
    baro_df_solinst = get_baro_solinst(start_time, end_time)
    baro_df_dendra = get_baro_dendra(start_time, end_time)
    
    # Standardize solinst baro data for elevation; set to weather station elev
    baro_df_solinst = adjust_pressure_elevation(baro_df_solinst,
                                                baro_standard_elevation, None)
        
    # If helpful, plot and compare the baro data sources
    # if debug_baro:
    #     plot_baro_compare(baro_df_solinst, baro_df_dendra)
    
    # Normalize the baro data based on both sources using an offset
    baro_df = normalize_baro(baro_df_solinst, baro_df_dendra)
    
    # # If helpful, plot and compare the baro data sources after normalized
    if debug_baro:
         plot_baro_compare(baro_df_solinst, baro_df_dendra)
    
    ## 2. Offset the baro pressure (convered to m) from the gw level
    
    # 2a. Adjust baro pressure for the well elevation
       
    # Merge baro and gw data
    gw_df = gw_df.merge(baro_df, on="DateTime", how="left")  # Merge baro data
    
    # Adjust pressure based on elevation difference
    gw_df = adjust_pressure_elevation(gw_df, gw_df['elevation_m'], baro_standard_elevation)
    
    # 2b. Convert baro pressure to meters and compensate the raw groundwater level reading
    gw_df['baro_Level_m'] = convert_baro_kPa_meters(gw_df['baro_Pressure_kPa']) #TODO: why does this return NaNs when gw_df has none when passing in?
    
    # Compensate by subtracting air pressure from the raw groundwater reading
    gw_df['compensated_Level_m'] = gw_df["raw_Level_m"] - gw_df["baro_Level_m"] 
        
    # Return the gw data with compensated water level
    return gw_df

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
                pressure_head = exact_match['compensated_Level_m'].values[0]
            
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
                    v1 = before['compensated_Level_m'].values[0]
                    v2 = after['compensated_Level_m'].values[0]
                
                    # Linear interpolation
                    pressure_head = v1 + (
                        manual_time - t1) / (t2 - t1) * (v2 - v1)
                
                elif not before.empty and len(before) > 1:
                    logging.debug(f"CASE not before.empty for {well} and {deploy}")
                    # Use rate of change to extrapolate
                    before_sorted = before.sort_values('DateTime_subdaily')
                    t1, t2 = before_sorted['DateTime_subdaily'].iloc[-2:].values
                    v1, v2 = before_sorted['compensated_Level_m'].iloc[-2:].values
                    time_diff = (t2 - t1) / np.timedelta64(1, 'm')  # Convert to minutes
                    rate = (v2 - v1) / time_diff  # Rate of change per minute
                    pressure_head = v2 + rate * ((manual_time - t2).total_seconds()/60)

                elif not after.empty and len(after) > 1:
                    logging.debug(f"CASE not after.empty for {well} and {deploy}")
                    # Use rate of change from two after readings
                    after_sorted = after.sort_values('DateTime_subdaily')
                    t1, t2 = after_sorted['DateTime_subdaily'].iloc[:2].values
                    v1, v2 = after_sorted['compensated_Level_m'].iloc[:2].values
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
                        v1, v2 = before_sorted['compensated_Level_m'].iloc[-2:].values
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
                  + " elements:\n" + 
                  pprint.pformat(sensor_levels, indent=4))
    logging.debug(f"Drift error dictionary has {len(drift_errors)}"
                  + " elements:\n" + pprint.pformat(drift_errors, indent=4))

    for (well, deploy), this_sensor_level in sensor_levels.items():
        if isinstance(this_sensor_level, float) and math.isnan(this_sensor_level):
            logging.info(f"Offset is NaN for {well} and {deploy}")
    
    return sensor_levels

## Convert baro-compensated water level from sensor 
## so that it's relative to the ground surface, not the sensor level
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
    biweek_df = pd.read_csv(gw_biweekly_file, index_col=0)
    biweek_df['DateTime'] = biweek_df['timestamp'].astype('datetime64[ns]')
    biweek_df = biweek_df.drop(columns=['timestamp'])
    biweek_df.reset_index(inplace=True)
    
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
                     + f"Removing {row['well_id']}-{row['deployment']}"
                     + " from subdaily dataframe.\n")
    
    # Remove NaN deployments from subdaily_df
    # with an inner join (tags subdaily_df rows that match nan_deployment)
    subdaily_df = subdaily_df.merge(nan_deployments, on=['well_id', 
                                                         'deployment'], 
                                    how='left', 
                                    indicator=True)

    # Keep only rows that do NOT match the NaN deployments
    # by filtering out rows with _merge, created by innerjoin with indicator=T
    subdaily_df = subdaily_df[subdaily_df['_merge'] == 'left_only'].drop(
                                                            columns=['_merge'])
    
    # Identify rows to drop from merged_df
    nan_rows = merged_df[merged_df['ground_to_water_cm'].isna()]
    # Count total rows to be removed
    num_dropped_rows = len(nan_rows)
    # Get unique well_id + deployment groups affected
    affected_deployments = nan_rows[['well_id', 
                                     'deployment']].drop_duplicates()

    # Log the results
    logging.info(f"Removing {num_dropped_rows} rows where 'ground_to_water_cm' is NaN.")
    logging.info(f"Affected well_id + deployment groups:\n{affected_deployments.to_string(index=False)}")

    # Drop NaN rows from merged_df
    merged_df = merged_df.dropna(subset=['ground_to_water_cm'])
    
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
        single_biweek_details = merged_df.merge(
            single_biweek_deployments[['well_id', 'deployment']], 
                                        on=['well_id', 'deployment'])
        
        # Log the affected deployments
        if not single_biweek_details.empty:
            logging.info("Deployments with only ONE unique manual measure:\n" + 
                single_biweek_details[['well_id', 
                'deployment']].drop_duplicates().to_string(index=False))
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
        return sensor_levels_m.get(key, np.nan) - row['compensated_Level_m']
    
    subdaily_df['ground_to_water_m'] = subdaily_df.apply(
                                        calculate_subdaily_water_level, axis=1)

    # Plot to validate
    if debug_gtw:
        plot_weekly_groundwater_data_by_well(subdaily_df, biweek_df)
        plot_subdaily_groundwater_by_deployment(subdaily_df, biweek_df)
    return subdaily_df
    
    ## SAVE subdaily logger data in single file
    # Re-order columns
    column_order = ['well_id', 'DateTime', 'deployment', 'ground_to_water_m', 
                    'raw_Level_m', 'baro_Level_m', 
                    'compensated_Level_m', 'Temp_c']
    subdaily_df = subdaily_df.reindex(columns=column_order)  
    
    # Save subdaily data
    subdaily_df.to_csv(gw_data_dir + subdaily_full_file, 
                       encoding='ISO-8859-1', index=False)
    
    # COMBINE manual and subdaily logger data in single file
    # Filter subdaily_df, only select rows between 7a to 10a
    subdaily_df['DateTime'] = pd.to_datetime(subdaily_df['DateTime'])
    subdaily_df['date'] = subdaily_df['DateTime'].dt.date
    subdaily_df['time'] = subdaily_df['DateTime'].dt.time
   
    mask = subdaily_df['time'].between(time(7, 0), time(10, 0))
    subdaily_am_df = subdaily_df[mask].copy()
    
    # Target the measurement closest to 8am
    subdaily_am_df['target_time'] = pd.to_datetime(
            subdaily_am_df['date'].astype(str) + ' 08:00')
    subdaily_am_df['time_diff'] = (subdaily_am_df['DateTime'] - subdaily_am_df['target_time']).abs()
    
    subdaily_am_df = subdaily_am_df.sort_values(['well_id', 'date', 'time_diff', 'DateTime'])
    subdaily_8am_df = subdaily_am_df.groupby(['well_id', 'date']).first().reset_index()

    # Convert to cm and prepare data for merge
    subdaily_8am_df['ground_to_water_cm'] = subdaily_8am_df['ground_to_water_m'] * 100
    subdaily_8am_df = subdaily_8am_df.drop(columns='ground_to_water_m')
    subdaily_8am_df = subdaily_8am_df.rename(columns={'DateTime': 'timestamp'})
    biweek_df = biweek_df.rename(columns={'DateTime': 'timestamp'})
    
    # Append and save
    daily_df = pd.concat([biweek_df, subdaily_8am_df], ignore_index=True)
    daily_df = daily_df[['well_id', 'timestamp', 'ground_to_water_cm']]
    daily_df = daily_df.sort_values(['well_id', 'timestamp'])
    daily_df.to_csv(gw_daily_file, index=False)

    # Validated combined dataset
    if debug_gtw:
        #Compare count of original versus combined dataset
        print(f"biweek_df rows: {len(biweek_df)}, "
              f"daily_df rows: {len(daily_df)}" 
              f" ({(len(daily_df) - len(biweek_df)) / len(biweek_df) * 100:.1f}% change)")
        missing_count = daily_df['ground_to_water_cm'].isna().sum()
        total_count = len(daily_df)
        missing_percent = (missing_count / total_count) * 100
        print(f"Missing ground_to_water_cm values in daily_df: {missing_count}"
              f"( {missing_percent:.1f}%)")


### EXECUTE FUNCTIONS TO PROCESS LOGGER DATA

## Starts with individual raw Solinst logger files 
##   in the 'subdaily_dir' directory
    
## 1. Cut logger entries when sensor not in the well, 
##     as indicated by drastic water level or temperature change
if process_cut:
    waterLevel_df = cut_logger_data()
    print("CUT COMPLETE")
else: 
    waterLevel_df = pd.read_csv(cut_data_file).dropna(axis=1, how="all")
    waterLevel_df['DateTime'] = waterLevel_df.DateTime.astype('datetime64[ns]')

## 2. Get elevation data for each well
waterLevel_df = get_well_elevations(waterLevel_df)
print("GOT WELL ELEVATIONS")

## 3. Compensate logger water level (m) based on barometer data (kPa)
if process_baro: 
    waterLevel_df = compensate_baro(waterLevel_df)
    print("COMPENSATION COMPLETE")

## 4. Convert water level from 'relative to sensor' to 
###    'relative to ground surface elevation' (in meters)
###   Also save combined manual and sensor-based gw readings as .csv
waterLevel_df = convert_relativeToGround(waterLevel_df)
print("RELATIVE TO GROUND CALCULATED")

## 5. Plot a visualization of the subdaily groundwater time series
#plot_timeseries_gridmap(waterLevel_df)


print(waterLevel_df)
    