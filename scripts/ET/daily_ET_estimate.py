#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DAILY ET CALCULATION SCRIPT
Created on  Sat 7 Feb 11:37 AM
@author: jnatali

Calculates daily ET (from groundwater, in cm) according to different methods, 
starting with simplest (White 1932 with constant Sy* with best guess 
                        from Loheide et al 2005 Fig 10).

"""
# ---- IMPORTS ---

# import basic libraries
import pandas as pd
#import os
#import datetime
import matplotlib.pyplot as plt
# import well_utils to process well_ids for Sy data

import sys
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

import scripts.groundwater.well_utils as well_utils
# ---- INITIALIZE GLOBAL VARIABLES ---

SY_STAR = 0.04 # center of sand, silt and clay in Loheide et al 2005 Fig 10

## Directory and Filenames based on structure in github
# TODO: update source file
# TODO: where is 2025-only processed logger data or filter for 2025 only or get ET for ALL years?
groundwater_data_dir = PROJECT_ROOT / 'data/field_observations/groundwater/loggers/PROCESSED/'
groundwater_subdaily_filepath = groundwater_data_dir / 'groundwater_subdaily.csv'

weather_data_dir = PROJECT_ROOT / 'data/station_instrumentation/climate/'
weather_subdaily_filepath = weather_data_dir / 'Weather_2010_2025_10min_SagehenTower1.csv'

ET_calc_data_dir = PROJECT_ROOT / 'data/ET_calculations/'
ET_calc_filepath = ET_calc_data_dir / 'ET_daily_2025_White_constantSy.csv'

sy_data_dir = PROJECT_ROOT / 'scripts/ET/'
sy_data_filepath = sy_data_dir / 'sy_lookup.csv' 

well_data_dir = PROJECT_ROOT / 'data/field_observations/soil/'
well_data_filepath = well_data_dir / 'soil_survey_PROCESSED.csv'

pet_data_dir = PROJECT_ROOT / 'data/et'
pet_data_filepath = pet_data_dir / 'pet_by_well_results.csv'

save_plots_dir = PROJECT_ROOT / 'results/plots/ET/White_avg'
save_csv_dir = PROJECT_ROOT / 'data/calculated_time_series/ET/ET_daily_2025_White_constantSy1.csv'

# TODO: add data_dir and filepath for Sy stuff

# ---- FUNCTIONS ---

## TODO: Split out as a weather_util.py for the project

def load_precip_for_years(
    precip_csv_path: str,
    years: int | list[int],
    ) -> pd.DataFrame:
    """
    Load only precipitation data for specific year(s) from a large CSV.

    Parameters
    ----------
    precip_csv_path : str
        Path to CSV file
    years : int or list[int]
        Year or list of years to load

    Returns
    -------
    pd.DataFrame
        Columns: time (datetime), precip_mm (float)
    """

    if isinstance(years, int):
        years = [years]

    # --- Read only the datetime and precipitation columns ---
    df = pd.read_csv(
        precip_csv_path,
        usecols=["time", "precipitation-geonor-mm"],
        parse_dates=["time"]
    ).rename(columns={"precipitation-geonor-mm": "precip_mm"})

    # --- Filter to the desired years ---
    df["year"] = df["time"].dt.year
    df = df[df["year"].isin(years)].copy()
    df = df.drop(columns="year")  # optional

    # --- include date in returned df
    #df["date"] = df["time"].dt.date
    return df


def daily_cumulative_precip(precip_df) -> pd.DataFrame:
    """
    Calculate daily cumulative precipitation (mm).

    Parameters
    ----------
    precip_df : DataFrame
        Columns: time, precip_mm

    Returns
    -------
    DataFrame
        Columns: date, precip_mm_day
    """

    # ensure datetime dtype
    if not pd.api.types.is_datetime64_any_dtype(precip_df["time"]):
        precip_df["time"] = pd.to_datetime(precip_df["time"])

    precip_df["date"] = precip_df["time"].dt.floor("D")

    daily = (
        precip_df
        .groupby("date", as_index=False)["precip_mm"]
        .sum()
        .rename(columns={"precip_mm": "precip_mm_day"})
    )

    return daily


def load_all_groundwater(gw_dir) -> pd.DataFrame:
    """
    Load all subdaily groundwater data

    """
    dfs = []
    
    # TODO: filter files to checkout from gw_dir
    for f in gw_dir:
        df = pd.read_csv(f, parse_dates=["DateTime"])
        dfs.append(df)
    
    gw = (
        pd.concat(dfs, ignore_index=True)
        .rename(columns={"DateTime": "datetime"})
        .sort_values(["well_id", "datetime"])
    )

    return gw
    
def get_daily_gw_levels(gw_df) -> pd.DataFrame:
    """
    Get groundwater levels at key times for calculating ET via White method
    from subdaily groundwater data
    
    
    Returns:
    a validated ataframe with daily groundwater variables 
        (needed to calculate ET)for each well_id
    """
    df = gw_df.copy()

    assert "ground_to_water_m" in gw_df.columns, 'field_observations'
    df["ground_to_water_cm"] = df["ground_to_water_m"] * 100
    
    df["date"] = df["datetime"].dt.floor("D")
    df["time"] = df["datetime"].dt.strftime("%H:%M")

    
    # get groundwater levels for the following times
    times=("00:00", "04:00")
    
    daily = (
        df[df["time"].isin(times)]
        .pivot_table(
            index = ["well_id", "date"],
            columns="time",
            values="ground_to_water_cm",
            )
        .rename(columns={"00:00":"gw_00", "04:00": "gw_04"})
        .reset_index()
        )
    
    # get the next day's gw level at 00:00
    daily["gw_24"] = (
        daily
        .sort_values("date")
        .groupby("well_id")["gw_00"]
        .shift(-1)
        )
    
    # enforce data completeness; drop  dates without needed gw levels
    daily = daily.dropna(subset=["gw_04", "gw_24"])
    # alternative enforcement
    #assert not daily[["gw_04", "gw_24"]].isna().any().any()
    
    daily["doy"] = daily["date"].dt.dayofyear
    daily["year"] = daily["date"].dt.year

    return daily

def get_daily_temperature(weather_subdaily_filepath: str) -> pd.DataFrame:
    """
    Loads massive sub-daily weather data, extracts the 25ft air temp, 
    calculates the daily average, and converts it to Fahrenheit.
    """
    # 1. Load only the necessary columns to save memory
    cols_to_load = ['time', 'air-temp-25-ft-avg-degc']
    weather_df = pd.read_csv(weather_subdaily_filepath, usecols=cols_to_load)
    
    # 2. Convert to datetime
    weather_df['time'] = pd.to_datetime(weather_df['time'])
    
    # 3. Resample to daily average
    daily_weather = weather_df.resample('D', on='time').mean().reset_index()
    
    # 4. Create merge-friendly columns 
    daily_weather['year'] = daily_weather['time'].dt.year
    daily_weather['clean_date'] = daily_weather['time'].dt.strftime('%m-%d')
    
    # 5. Rename the Celsius column for clarity
    daily_weather = daily_weather.rename(columns={'air-temp-25-ft-avg-degc': 'temp_25ft_C'})
    
    # Return the dataframe with the new Fahrenheit column included
    return daily_weather[['year', 'clean_date', 'temp_25ft_C']]

def calculate_storage_recharge(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate storage and recharge terms for ET calculations.

    Parameters:
    df: daily groundwater dataframe with gw levels at key times

    Returns:
    DataFrame with additional columns for storage and recharge
    """
    df = df.copy()
    
    # Calculate R, overnight recharge rate in cm/day
    df["R_cm"] = 24.0 * (df["gw_00"] - df["gw_04"]) / 4.0
    
    # Calculate s, daily storage change (cm)
    df["S_cm"] = df["gw_24"] - df["gw_00"] 
    
    return df

def estimate_ET_White_constant_Sy(daily_df) -> pd.DataFrame:
    """
    Calculate ET in cm/day for each well in subdaily groundwater logger data.

    Parameters: daily groundwater dataframe with gw levels at key times
    
    Returns:
    populated "ET estimate" dataframe
    """
    METHOD_ID = "White_constantSy"
    
    df = daily_df.copy()
    
    df = calculate_storage_recharge(df)
    
    # Set constants for this method
    df["Sy_star"] = SY_STAR
    df["method_id"] = METHOD_ID
    
    # Calculate daily ET
    df["ET_gw_cm"] = df["Sy_star"] * (df["R_cm"] + df["S_cm"])
    
    return df[
        [
            "date",
            "doy",
            "year",
            "well_id",
            "ET_gw_cm",
            "R_cm",
            "S_cm",
            "Sy_star",
            "method_id",
        ]
    ].dropna()

def estimate_ET_White_wavg_Sy(daily_df: pd.DataFrame, sy_df: pd.DataFrame,) -> pd.DataFrame:
    """
    Calculate ET in cm/day for each well in subdaily groundwater logger data
    using White (1932) method and a specific yield for each well that's a weighted
    average based on soil profile field data and Sy* estimates from 
    Loheide et al (2008) <to verify> and <who else?>

    Parameters:
    daily_df: daily groundwater dataframe with gw levels at key times
    sy_df: A dataframe with specific yield information for each soil texture
    
    Returns:
    populated "ET estimate" dataframe
    """
    METHOD_ID = "White_wavg"
    
    df = daily_df.copy()

    #   ---- ET CALCULATIONS ----
    df = calculate_storage_recharge(df)
    # Set constants for this method
    df["method_id"] = METHOD_ID

    # Create the dictionary from the corrected dataframe
    sy_lookup = sy_df.set_index('well_id')['average_Sy'].to_dict()

    # Map the dictionary to the main daily dataframe
    df["Sy_star"] = df['well_id'].map(sy_lookup)

    # Calculate daily ET
    df["ET_gw_cm"] = df["Sy_star"] * (df["R_cm"] + df["S_cm"])

    return df[
        [
            "date",
            "doy",
            "year",
            "well_id",
            "ET_gw_cm",
            "R_cm",
            "S_cm",
            "Sy_star",
            "method_id"
        ]
    ].dropna()

def filter_ET_by_precip(et_df: pd.DataFrame, precip_df: pd.DataFrame, threshold_mm: float = 8.0, recovery_days: int = 3) -> pd.DataFrame:
    """
    Filters out storage and recharge terms on days with heavy precipitation and subsequent recovery days.

    Parameters:
    et_df: populated ET estimate dataframe to filter
    precip_df: dataframe with columns: date, precip_mm_day
    threshold_mm: precipitation threshold to filter by in mm
    recovery_days: number of days to exclude after a heavy precipitation event
    
    Returns:
    filtered ET estimate dataframe
    """
    # ---- 1. CREATE THE MASK ----
    
    # Make a copy to protect the original data, sort chronologically so the rolling window 
    # looks backward in time correctly, and reset the index to prevent alignment errors.
    p_df = precip_df.copy().sort_values("date").reset_index(drop=True)
    
    # Create a boolean series (True/False) flagging days where rain met or exceeded the threshold.
    high_precip = p_df["precip_mm_day"] >= threshold_mm
    
    # Calculate the total window size (the rain event day itself + the number of recovery days).
    window_size = recovery_days + 1
    
    # Apply a rolling window that looks backward. If any day in that window was a 
    # "high_precip" day (True), .max() evaluates to True for the current day, 
    # effectively dragging the exclusion flag forward through the recovery period.
    p_df["exclude_ET"] = high_precip.rolling(window=window_size, min_periods=1).max().astype(bool)
    
    
    # ---- 2. APPLY THE MASK ----
    
    # Merge the True/False mask into the calculated ET dataframe, matching exactly by date.
    # A 'left' merge ensures we don't accidentally drop ET dates just because they are missing from weather data.
    filtered_df = et_df.merge(p_df[["date", "exclude_ET"]], on="date", how="left")
    
    # If any dates in the ET data didn't have weather data, assume it didn't rain (False).
    filtered_df["exclude_ET"] = filtered_df["exclude_ET"].fillna(False)
    
    # ----  PRINT DROPPED DAYS SUMMARY ----
    # Isolate the records that are flagged for exclusion
    dropped_records = filtered_df[filtered_df["exclude_ET"]]
    
    if not dropped_records.empty:
        print(f"\n--- Dropping {len(dropped_records)} ET records due to precip >= {threshold_mm} mm + {recovery_days} recovery days ---")
        
        # Use .unique() before .tolist() to get only the unique dates
        dates = dropped_records["date"].dt.strftime("%Y-%m-%d").unique().tolist()
        
        print(f"Zeroing records for {len(dates)} days -> {dates} \n"
        "--------------------------------------------------------------------------------------------------\n")
    else:
        print(f"\n--- No ET records dropped due to precipitation (threshold = {threshold_mm} mm) ---\n")
    
    # Set 'ET_gw_cm' to 0 for the flagged rows using .loc
    filtered_df.loc[filtered_df["exclude_ET"], ["ET_gw_cm"]] = 0.0
    
    # Drop the temporary "exclude_ET" column to keep the dataframe clean.
    filtered_df = filtered_df.drop(columns=["exclude_ET"])
    
    return filtered_df

def filter_ET_by_well_depth(et_df: pd.DataFrame, gw_df: pd.DataFrame, well_df: pd.DataFrame, buffer_cm: float = 5.0) -> pd.DataFrame:
    """
    Filters out storage and recharge terms for days when the groundwater level drops 
    below the total depth of the well, minus a safety buffer.

    Parameters:
    et_df: populated ET estimate dataframe to filter
    gw_df: daily groundwater dataframe with start-of-day gw levels (gw_00)
    well_df: dataframe with soil survey data including stop_depth_cm to calculate total well depth
    buffer_cm: safety buffer in cm to exclude data before the well goes completely dry (default is 5.0)
    
    Returns:
    filtered ET estimate dataframe
    """
    # ---- FIND TOTAL WELL DEPTHS 
    # Group the soil survey by well_id and find the maximum stop_depth_cm 
    max_depths = well_df.groupby("well_id")["stop_depth_cm"].max().reset_index()
    max_depths = max_depths.rename(columns={"stop_depth_cm": "total_well_depth_cm"})
    
    # ---- GET DAILY GROUNDWATER LEVELS -
    # Extract just the identifiers and the start-of-day groundwater depth (gw_00)
    gw_levels = gw_df[["well_id", "date", "gw_00"]].copy()
    
    # ---- CREATE THE EXCLUSION MASK 
    mask_df = gw_levels.merge(max_depths, on="well_id", how="left")
    
    # Flag days where the water depth (gw_00) is deeper than the well bottom minus the buffer.
    # Example: If well is 100cm deep and buffer is 5cm, flag if gw_00 >= 95cm.
    mask_df["is_dry"] = mask_df["gw_00"] >= (mask_df["total_well_depth_cm"] - buffer_cm)
    
    # ----  PRINT DROPPED DAYS SUMMARY 
    dry_records = mask_df[mask_df["is_dry"]]
    if not dry_records.empty:
        print(f"\n--- Zeroing {len(dry_records)} records due to dry well conditions (buffer = {buffer_cm} cm) ---")
        for well, group in dry_records.groupby("well_id"):
            dates = group["date"].dt.strftime("%Y-%m-%d").tolist()
            # This prints the well ID, the total count of dropped days, and the exact dates
            print(f"{well}: Dropped {len(dates)} days -> {dates}")
        print("----------------------------------------------------------------------------------\n")
    else:
        print(f"\n--- No ET records dropped due to dry well conditions (buffer = {buffer_cm} cm) ---\n") 

    # ---- APPLY THE MASK TO ET DATA 
    # Merge the mask into your ET dataframe using both well_id and date
    filtered_et = et_df.merge(mask_df[["well_id", "date", "is_dry"]], on=["well_id", "date"], how="left")
    
    # Set 'ET_gw_cm' to 0 for the flagged rows using .loc
    filtered_et.loc[filtered_et["is_dry"], ["ET_gw_cm"]] = 0.0
    
    # Drop the temporary column
    filtered_et = filtered_et.drop(columns=["is_dry"]) 

    return filtered_et

def average_sy(df_sy: pd.DataFrame, df_wells: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the average specific yield for each well based on soil texture and thickness.

    Parameters:
    df_sy: a dataframe with specific yield information for each soil texture
    df_wells: a data frame with well information including soil texture and depth
    
    Returns:
    a dataframe with the average specific yield for each well
    """

    # Set the key column as the index, select the value column, and convert to dict
    soil_sy_dict = df_sy.set_index('soil_texture')['Sy'].to_dict()

    #  Data Cleaning
    df_wells = df_wells.dropna(subset=['well_id']).copy()

    #  Math and Calculations
    df_wells['Sy'] = df_wells['soil_texture_code'].map(soil_sy_dict)
    df_wells['thickness'] = df_wells['stop_depth_cm'] - df_wells['start_depth_cm']
    df_wells['Sy_weighted'] = df_wells['Sy'] * df_wells['thickness']

    #  Grouping and Averagingpass
    well_summary = df_wells.groupby('well_id')[['Sy_weighted', 'thickness']].sum()
    well_summary['average_Sy'] = well_summary['Sy_weighted'] / well_summary['thickness']


    return well_summary[['average_Sy']].reset_index()
  
def plot_ET_line(
        ET_df,
        method_id,
        years=None,
        precip_df: pd.DataFrame | None = None,
        save_dir=None):
    """
    
    Plot ET in cm/day for each well as a line; one plot per well.

    Parameters
    ----------
    ET_df : pandas.DataFrame
        Daily ET estimates.
    method_id : str
        ET estimation method to plot.
    years : int or list[int], optional
        Year(s) to include (e.g., 2025).
    precip_df: optional
    save_dir : pathlib.Path or str, optional
        If provided, save one figure per well.
    """
    
    # get ET for the prescribed method
    df = ET_df[ET_df["method_id"] == method_id].copy()
    
    if years is not None:
        if isinstance(years, int):
            years = [years]
        df = df[df["year"].isin(years)]
    
    if df.empty:
        raise ValueError("No ET data after filtering by method/year.")

    # --- Loop over well_ids with groupby ---
    for well_id, well_df in df.groupby("well_id"):
        
        well_df = well_df.sort_values("date")

        fig, ax1 = plt.subplots(figsize=(8, 4))
        fig.suptitle(f"Daily ET via {method_id} for {well_id}")
        
# ---- ET line (Dominant Foreground) ----
        l1 = ax1.plot(
            well_df["date"],
            well_df["ET_gw_cm"],
            linewidth=1.5,        # Thicker line makes it dominant
            color="black",        # High contrast color
            zorder=3,             # Forces ET to be drawn on top of everything
            label="ET"
        )
        
        # Set primary axis labels
        ax1.set_ylabel("ET (cm/day)")
        ax1.set_xlabel("Date")
        
        # ---- Create Secondary Y-Axis ----
        ax2 = ax1.twinx()
# ---- Storage line (Secondary Y-Axis) ----
        l2 = ax2.plot(
            well_df["date"],
            well_df["S_cm"],
            linewidth=0.8,
            color="lightgreen",   # Lighter green
            zorder=2,             # Draws this line above Recharge
            label="Storage (S)"
        )
        
    
# ---- Recharge line  ----
        l3 = ax2.plot(
            well_df["date"],
            well_df["R_cm"],
            linewidth=0.8,
            color="lightcoral",   # Lighter red, bypasses the need for alpha
            zorder=1,             # Draws this line first (at the bottom)
            label="Recharge (R)"
        )
        """
        # ---- Optional precipitation ----
        if precip_df is not None:
            merged = well_df.merge(
                precip_df,
                on="date",
                how="left"
            )

            ax2 = ax1.twinx()
            ax2.bar(
                merged["date"],
                merged["precip_mm_day"],
                width=1.0,
                alpha=0.3
            )
            ax2.set_ylabel("Precipitation (mm)")
        """

        # Set secondary axis label
        ax2.set_ylabel("Recharge & Storage (cm/day)")

        # ---- Force Primary Axis on Top ----
        # twinx() draws ax2 on top of ax1 by default. This forces ax1 back to the top
        # and makes its background transparent so ax2 is visible underneath.
        ax1.set_zorder(ax2.get_zorder() + 1)
        ax1.patch.set_visible(False)

        # ---- Combine Legends ----
        # Because we have two axes, calling .legend() normally creates two separate boxes.
        # This combines the labels from both axes into a single legend.
        lines = l1 + l2 + l3
        labels = [l.get_label() for l in lines]
        # Move legend below the plot, centered, with items in 3 columns
        ax1.legend(lines, labels, loc="upper center", bbox_to_anchor=(0.5, -0.35), ncol=3)
        
        fig.autofmt_xdate()
        
        if save_dir is not None:
            fname = f"ET_{method_id}_{well_id}_{'_'.join(map(str, years))}_filtered.eps"
            fig.savefig(save_dir / fname, format="eps", bbox_inches="tight")
            plt.close(fig)
        else:
            plt.show()

def plot_Storage_Recharge_bar(ET_df, method_id, year, save_dir=None):
    index = ['method_id','S_cm','R_cm','year','well_id','date']
    df = ET_df[index]
    filtered_df = df[(df['year'] == year) & (df['method_id'] == method_id)]

    for well_id, well_df in filtered_df.groupby('well_id'):
        fig, ax1 = plt.subplots(figsize=(6, 6))
        well_df['clean_date'] = pd.to_datetime(well_df['date']).dt.strftime('%m-%d')
        plot_df = well_df.set_index('clean_date')[['S_cm_proportion', 'R_cm_proportion']]
        plot_df.plot(
            kind='bar',
            stacked=True, 
            color=['teal','cornflowerblue'],
            ax = ax1,
            width = 1.0)
        ax1.set(xlabel='Date', 
                ylabel='GW Levels (cm)', 
                title=f'{method_id}_{well_id}')
        ax1.legend(['Storage', 'Recharge'], bbox_to_anchor=(1.05, 1), loc='upper left')

        # 1. Grab all the current tick locations and their text labels
        ticks = ax1.get_xticks()
        labels = [item.get_text() for item in ax1.get_xticklabels()]
        
        # 2. Overwrite the axis to ONLY include every 14th tick and label
        # The [::14] tells Python to slice the list, taking every 14th item
        ax1.set_xticks(ticks[::15])
        ax1.set_xticklabels(labels[::15])

        # Optional: rotate the ones that are visible so they read perfectly flat
        ax1.tick_params(axis='x', rotation=0)
        if save_dir is not None:
            fname = f"Storage_and_Recharge_{method_id}_{well_id}_{year}_BAR.eps"
            fig.savefig(save_dir / fname, format="eps", bbox_inches="tight")
            plt.close(fig)
        else:
            plt.show()

def plot_ET_prop_bar(ET_df: pd.DataFrame, PET_df: pd.DataFrame, weather_df: pd.DataFrame, method_id: str, year: int, save_dir=None):
    """
    Plots proportional Net ET bars and PET line on the left axis, 
    and daily average temperature (Fahrenheit) on a secondary right axis.
    Saves the figures as .eps files or displays them.
    """
    # 1. Filter down to the specific year and method safely
    ET_df = ET_df[(ET_df['year'] == year) & (ET_df['method_id'] == method_id)].copy()
    ET_df['clean_date'] = pd.to_datetime(ET_df['date']).dt.strftime('%m-%d')

    ET_df['S_cm_proportion'] = ET_df['Sy_star']*ET_df['S_cm'] 
    ET_df['R_cm_proportion'] = ET_df['Sy_star']*ET_df['R_cm']
    
    PET_df = PET_df.copy()
    PET_df['clean_date'] = pd.to_datetime(PET_df['Date']).dt.strftime('%m-%d')

    # 2.Filter weather data by the target year to avoid multi-year duplication cross-joins
    if 'year' in weather_df.columns:
        weather_filtered = weather_df[weather_df['year'] == year].copy()
    else:
        weather_filtered = weather_df.copy()

    # Combine dataframes using left joins
    filtered_df = ET_df.merge(PET_df, how='left', on=['well_id', 'clean_date'])
    filtered_df = filtered_df.merge(weather_filtered, how='left', on='clean_date')

    for well_id, well_df in filtered_df.groupby('well_id'):
        fig, ax1 = plt.subplots(figsize=(6, 6))
        
        dates = well_df['clean_date'].tolist()

        # Calculate Net ET and absolute totals
        ET_net = well_df['S_cm_proportion'] + well_df['R_cm_proportion']
        total_abs = well_df['S_cm_proportion'].abs() + well_df['R_cm_proportion'].abs()

        # Calculate proportions safely (avoiding zero-division)
        s_prop = np.where(total_abs == 0, 0, well_df['S_cm_proportion'].abs() / total_abs)
        r_prop = np.where(total_abs == 0, 0, well_df['R_cm_proportion'].abs() / total_abs)

        # Scale proportions to the Net ET bar height
        s_bar_heights = ET_net * s_prop
        r_bar_heights = ET_net * r_prop

        # ---- PLOTTING 
        # 1. Left Axis (ax1): Stacking Bars
        ax1.bar(dates, s_bar_heights, width=1.0, color='teal', label='Storage')
        ax1.bar(dates, r_bar_heights, bottom=s_bar_heights, width=1.0, color='cornflowerblue', label='Recharge')

        # 2. Overlay PET Line
        if 'PET_mm_day' in well_df.columns:
            pet_cm = well_df['PET_mm_day'] / 10.0
            ax1.plot(dates, pet_cm, color='crimson', linewidth=2, label='PET (cm)')
            
        # Add zero-line to clearly anchor positive/negative days
        ax1.axhline(0, color='black', linewidth=0.5)

        # Formatting Left Axis
        ax1.set(xlabel='Date', ylabel='Net ET / PET (cm)')
        
        # 3. Right Axis (ax2): Temperature context (Celsius)
        ax2 = ax1.twinx() 
        if 'temp_25ft_C' in well_df.columns:
            ax2.plot(dates, well_df['temp_25ft_C'], color='darkorange', linestyle='--', linewidth=1.25, alpha=0.5, label='Temp 25ft (°C)')
        
        ax2.set_ylabel('Air Temperature (°C)')
        
        # ---- NEW: CALCULATE PERFECT ZERO ALIGNMENT ----
        ax1_min, ax1_max = ax1.get_ylim()
        ax2_max = 40.0
        
        # Scale the lower temp bound exactly proportional to the left axis lower bound
        ax2_min = ax1_min * (ax2_max / ax1_max)
        
        # Apply the balanced limits
        ax2.set_ylim(ax2_min, ax2_max)

        # Using string array indices avoids the empty string layout engine bug
        ax1.set_xticks(range(0, len(dates), 20))
        ax1.set_xticklabels(dates[::20])
        ax1.tick_params(axis='x', rotation=0)

        # ---- COMBINED LEGEND ----
        lines_1, labels_1 = ax1.get_legend_handles_labels()
        lines_2, labels_2 = ax2.get_legend_handles_labels()
        ax1.legend(lines_1 + lines_2, labels_1 + labels_2, bbox_to_anchor=(1.15, 1), loc='upper left')

        # Unified single title assignment
        ax1.set_title(f'{method_id}_temperature_and_pet_{well_id}', fontsize=12, fontweight='bold')


        # ---- SAVING LOGIC ----
        if save_dir is not None:
            save_path = Path(save_dir)
            fname = f"ET_proportional_{method_id}_{well_id}_{year}_BAR.eps"
            fig.savefig(save_path / fname, format="eps", bbox_inches="tight")
            plt.close(fig)
        else:
            plt.show()

def plot_gw_ET_overlay(gw_df, et_df, year):
    # See DRAFT in chatgpt here: https://chatgpt.com/s/t_6988e9118c34819181d813da8c21634b
    
    return

def update_wells(filepath: str) -> pd.DataFrame:
    """
    Validates files with well_ids
    Returns a valided dataframe with corrected well_ids.

    Parameters
    ----------
    filepath : str
        Path to CSV file with well_ids 
    """
    # Validate the well_ids to ensure no bad data slipped through
    #Load Sy data
    sy_df = pd.read_csv(filepath)

    # Correct the well_ids using the STATIC function 
    sy_df = well_utils.correct_well_ids_static(sy_df)
    
    # Validate the well_ids to ensure no bad data slipped through
    sy_df = well_utils.validate_well_ids(sy_df, id_col="well_id")
    return  sy_df 


    # ---- MAIN PROCEDURES ---

def main():
   

    # I/O: load subdaily groundwater input (source data) file
    subdaily_gw_df = pd.read_csv(groundwater_subdaily_filepath,
                                 parse_dates=["DateTime"]
                                 ).rename(columns={"DateTime": "datetime"})   
    # Plot daily ET with precip
    precip_df = load_precip_for_years(weather_subdaily_filepath, 2025)
    daily_precip_df = daily_cumulative_precip(precip_df)
    
    # pre-process gw from subdaily into key daily values
    daily_gw_df = get_daily_gw_levels(subdaily_gw_df)
    print("got gw levels")
  
    #calculate average Sy for each well
    df_soil_sy = pd.read_csv(sy_data_filepath)
    df_well_logs = pd.read_csv(well_data_filepath)
    calculated_sy_df = average_sy(df_soil_sy, df_well_logs)

    # 1. Calculate raw ET for ALL days
    raw_ET_df = estimate_ET_White_constant_Sy(daily_gw_df)

    # 2. Filter out the storm events
    ET_no_rain = filter_ET_by_precip(raw_ET_df, daily_precip_df, threshold_mm=8.0, recovery_days=3)

    # 3. Filter out days where the well went dry (dropping data when water is within 5cm of bottom)
    daily_ET_df = filter_ET_by_well_depth(ET_no_rain, daily_gw_df, df_well_logs, buffer_cm=5.0)

    daily_ET_df.to_csv(save_csv_dir, index=False)

    PET_df = update_wells(pet_data_filepath)
    weather_df = get_daily_temperature(weather_subdaily_filepath)

    plot_ET_prop_bar(daily_ET_df, 
            PET_df,
            weather_df,
            "White_constantSy", 
            2025,  
            save_dir=save_plots_dir)
    print("ET plotted for White average Sy")

   
    # Save to csv? Do we want a new one or write over the one from above?
    # Then plot this new estimate, use an appropriate name, check if the 2nd param affects filename and not just the title
    print("COMPLETE!!")
   

# --- END FUNCTIONS

if __name__ == "__main__":
    main()
