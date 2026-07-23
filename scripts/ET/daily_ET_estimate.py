#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DAILY ET CALCULATION SCRIPT
Created on  Sat 7 Feb 11:37 AM
@author: jnatali

Calculates daily ET (from groundwater, in mm) according to different methods, 
starting with simplest (White 1932 with constant Sy* with best guess 
                        from Loheide et al 2005 Fig 10).

"""
# ---- IMPORTS ---

# import basic libraries
import pandas as pd
#import os
#import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
# import well_utils to process well_ids for Sy data

import sys
from pathlib import Path
import numpy as np
import matplotlib.dates as mdates


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

sy_data_dir = PROJECT_ROOT / 'data/et/'
sy_data_filepath = sy_data_dir / 'sy_lookup.csv' 

sy_save_filepath = sy_data_dir / 'sy_by_well.csv'

well_data_dir = PROJECT_ROOT / 'data/field_observations/soil/'
well_data_filepath = well_data_dir / 'soil_survey_PROCESSED.csv'

pet_well_data_dir = PROJECT_ROOT / 'data/et'
pet_well_data_filepath = pet_well_data_dir / 'pet_by_well_results.csv'

pet_station_data_dir = PROJECT_ROOT / 'data/et'
pet_station_data_filepath = pet_station_data_dir / 'pet_station_results.csv'

save_plots_dir = PROJECT_ROOT / 'results/plots/ET/White_Avg/'
save_csv_dir = PROJECT_ROOT / 'data/calculated_time_series/ET/ET_daily_2025_White_constantSy.csv'

duky_sy_data_dir = PROJECT_ROOT / 'data/et/duke_lookup.csv'
# TODO: add data_dir and filepath for Sy stuff

lai_data_dir = PROJECT_ROOT / 'data/field_observations/vegetation/LAI/'
lai_data_filepath = lai_data_dir / 'LAI_2025_Corrected.csv'

extinction_data_dir = PROJECT_ROOT / 'data/et/'
extinction_data_filepath = extinction_data_dir / 'Shah_extinction_depth.csv'
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
    df["ground_to_water_mm"] = df["ground_to_water_m"] * 1000
    
    df["date"] = df["datetime"].dt.floor("D")
    df["time"] = df["datetime"].dt.strftime("%H:%M")

    
    # get groundwater levels for the following times
    times=("00:00", "04:00")
    
    daily = (
        df[df["time"].isin(times)]
        .pivot_table(
            index = ["well_id", "date"],
            columns="time",
            values="ground_to_water_mm",
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
    
    daily = update_wells(daily)

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
    # (Deleted clean_date since we no longer use it)
    
    # 5. Rename the columns for clarity, turning 'time' into 'date'
    daily_weather = daily_weather.rename(columns={
        'air-temp-25-ft-avg-degc': 'temp_25ft_C',
        'time': 'date'
    })
    
    # Return the dataframe 
    return daily_weather[['year', 'date', 'temp_25ft_C']]

def calculate_storage_recharge(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate storage and recharge terms for ET calculations.

    Parameters:
    df: daily groundwater dataframe with gw levels at key times

    Returns:
    DataFrame with additional columns for storage and recharge
    """
    df = df.copy()
    
    # Calculate R, overnight recharge rate in mm/day
    df["R_mm"] = 24.0 * (df["gw_00"] - df["gw_04"]) / 4.0
    
    # Calculate s, daily storage change (mm)
    df["S_mm"] = df["gw_24"] - df["gw_00"] 
    
    return df

def estimate_ET_White_constant_Sy(daily_df) -> pd.DataFrame:
    """
    Calculate ET in mm/day for each well in subdaily groundwater logger data.

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
    df["ET_gw_mm"] = df["Sy_star"] * (df["R_mm"] + df["S_mm"])
    
    df = update_wells(df)

    return df[
        [
            "date",
            "doy",
            "year",
            "well_id",
            "ET_gw_mm",
            "R_mm",
            "S_mm",
            "Sy_star",
            "method_id",
            "gw_00"
        ]
    ].dropna()

def estimate_ET_White_wavg_Sy(daily_df: pd.DataFrame, sy_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate ET in mm/day for each well in subdaily groundwater logger data
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
    df["ET_gw_mm"] = df["Sy_star"] * (df["R_mm"] + df["S_mm"])
    
    df = update_wells(df)

    return df[
        [
            "date",
            "doy",
            "year",
            "well_id",
            "ET_gw_mm",
            "R_mm",
            "S_mm",
            "Sy_star",
            "method_id",
            "gw_00"
        ]
    ].dropna()

def estimate_ET_White_Duke_Sy(
    daily_df: pd.DataFrame, 
    soil_df: pd.DataFrame, 
    rawls_df: pd.DataFrame,   
) -> pd.DataFrame:
    """
    Calculates ET using Duke's equation for Specific Yield (Sy), based strictly on 
    the soil parameters of the single horizon where the water table is currently fluctuating.
    If the water table is inside the capillary fringe, the White method is bypassed and
    ET is set to equal atmospheric PET.
    """
    METHOD_ID = "White_Duke"
    
    # Create clean copies
    df = daily_df.copy()
    soil_clean = soil_df.copy()
    
    
    df = calculate_storage_recharge(df)
    
    # Create dictionary lookup for Rawls parameters
    rawls_lookup = rawls_df.set_index('soil_texture_code').to_dict(orient='index')

    calculated_sy_list = []
    shallow_wt_flag_list = []      

    # LOOP THROUGH EACH DAILY GROUNDWATER RECORD
    for _, row in df.iterrows():
        current_well = row['well_id']
        
        # Groundwater depth is stored in mm in 'gw_00'. Convert it to cm to match soil depths.
        wt_depth_cm = row['gw_00'] / 10.0

        # Filter the soil survey to find horizons belonging to ONLY this well
        well_horizons = soil_clean[soil_clean['well_id'] == current_well].copy()

        if well_horizons.empty:
            calculated_sy_list.append(np.nan)
            shallow_wt_flag_list.append(False) 
            continue

        # FIND THE SINGLE HORIZON CONTAINING THE WATER TABLE
        active_horizon = well_horizons[
            (well_horizons['start_depth_cm'] <= wt_depth_cm) & 
            (well_horizons['stop_depth_cm'] > wt_depth_cm)
        ]

        # Fallback: If the water table dropped deeper than the lowest recorded log,
        # use the very bottom horizon so the script doesn't break.
        if active_horizon.empty:
            active_horizon = well_horizons.sort_values('stop_depth_cm').tail(1)

        # Extract the single row as a Series
        horizon = active_horizon.iloc[0]

        # Extract soil texture code 
        texture_code = str(horizon['soil_texture_code']).strip()

        # Calculate Specific Yield using Duke
        
        # Special Case 1: Pure Gravel (Code 'GR')
        if texture_code == 'GR' or texture_code == 'HO':
            # Average Specific Yield for Medium Gravel = 23% (0.23)
            layer_sy = 0.23
            shallow_wt_flag_list.append(False) 

        # Special Case 2: Standard Soil Matrix 
        else:
            params = rawls_lookup.get(texture_code, rawls_lookup.get('C', {}))
            phi = params.get('phi', 0.475)
            sr = params.get('Sr', 0.090)
            ha_cm = params.get('ha_cm', 37.3)
            lam = params.get('lambda', 0.131)

            max_sy = phi - sr

            # Apply Duke's Depth-Scaling Equation
            if wt_depth_cm <= ha_cm:
                # Water table is entirely inside capillary fringe -> No yield release
                layer_sy = 0.0
                shallow_wt_flag_list.append(True) 
            else:
                # Scale down maximum yield based on depth and air-entry pressure
                depth_factor = 1.0 - ((ha_cm / wt_depth_cm) ** lam)
                layer_sy = max_sy * depth_factor
                shallow_wt_flag_list.append(False) 

        # Append the calculated Sy to our daily list
        calculated_sy_list.append(layer_sy)

    # Attach the array of calculated values as a new column 
    df['Sy_star'] = calculated_sy_list 
    df['method_id'] = METHOD_ID
    
    # Calculate daily ET (Standard White Method)
    df["ET_gw_mm"] = df["Sy_star"] * (df["R_mm"] + df["S_mm"])

    df = update_wells(df)
    
    return df[
        [
            "date",
            "doy",
            "year",
            "well_id",
            "ET_gw_mm",
            "R_mm",
            "S_mm",
            "Sy_star",
            "method_id",
            "gw_00"
        ]
    ].dropna()

def filter_ET_by_precip(et_df: pd.DataFrame, precip_df: pd.DataFrame, threshold_mm: float = 8.0, recovery_days: int = 3) -> pd.DataFrame:
    """
    Filters out storage and recharge terms on days with heavy precipitation and subsequent recovery days
    by setting target columns to NaN.

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
        print(f"\n--- Masking {len(dropped_records)} ET records to NaN due to precip >= {threshold_mm} mm + {recovery_days} recovery days ---")
        
        # Use .unique() before .tolist() to get only the unique dates
        dates = dropped_records["date"].dt.strftime("%Y-%m-%d").unique().tolist()
        
        print(f"Setting records to NaN for {len(dates)} days -> {dates} \n"
        "--------------------------------------------------------------------------------------------------\n")
    else:
        print(f"\n--- No ET records masked due to precipitation (threshold = {threshold_mm} mm) ---\n")
    
    # Set target columns to NaN for the flagged rows using .loc
    filtered_df.loc[filtered_df["exclude_ET"], ["ET_gw_mm", "R_mm", "S_mm"]] = np.nan
    
    # Drop the temporary "exclude_ET" column to keep the dataframe clean.
    filtered_df = filtered_df.drop(columns=["exclude_ET"])
    
    return filtered_df

def filter_ET_by_well_depth(et_df: pd.DataFrame, gw_df: pd.DataFrame, well_df: pd.DataFrame, buffer_mm: float = 50.0) -> pd.DataFrame:
    """
    Filters out storage and recharge terms for days when the groundwater level drops 
    below the total depth of the well, minus a safety buffer by setting columns to NaN.

    Parameters:
    et_df: populated ET estimate dataframe to filter
    gw_df: daily groundwater dataframe with start-of-day gw levels (gw_00, now in mm)
    well_df: dataframe with soil survey data including stop_depth_cm to calculate total well depth
    buffer_mm: safety buffer in mm to exclude data before the well goes completely dry (default is 50.0 mm / 5 cm)
    
    Returns:
    filtered ET estimate dataframe
    """
    # ---- 1. FIND TOTAL WELL DEPTHS (Convert cm to mm) ----
    max_depths = well_df.groupby("well_id")["stop_depth_cm"].max().reset_index()
    max_depths["total_well_depth_mm"] = max_depths["stop_depth_cm"] * 10.0
    
    # ---- 2. GET DAILY GROUNDWATER LEVELS ----
    # Extract just the identifiers and the start-of-day groundwater depth (gw_00 is in mm)
    gw_levels = gw_df[["well_id", "date", "gw_00"]].copy()
    
    # ---- 3. CREATE THE EXCLUSION MASK ----
    mask_df = gw_levels.merge(max_depths[["well_id", "total_well_depth_mm"]], on="well_id", how="left")
    
    # Flag days where the water depth is deeper than the well bottom minus the buffer (all units in mm)
    mask_df["is_dry"] = mask_df["gw_00"] >= (mask_df["total_well_depth_mm"] - buffer_mm)
    
    # ---- 4. PRINT DROPPED DAYS SUMMARY ----
    dry_records = mask_df[mask_df["is_dry"]]
    if not dry_records.empty:
        print(f"\n--- Setting {len(dry_records)} records to NaN due to dry well conditions (buffer = {buffer_mm} mm) ---")
        for well, group in dry_records.groupby("well_id"):
            dates = group["date"].dt.strftime("%Y-%m-%d").tolist()
            print(f"{well}: Masked {len(dates)} days -> {dates}")
        print("----------------------------------------------------------------------------------\n")
    else:
        print(f"\n--- No ET records masked due to dry well conditions (buffer = {buffer_mm} mm) ---\n") 

    # ---- 5. APPLY THE MASK TO ET DATA ----
    filtered_et = et_df.merge(mask_df[["well_id", "date", "is_dry"]], on=["well_id", "date"], how="left")
    
    # Set target columns to NaN for flagged rows
    filtered_et.loc[filtered_et["is_dry"], ["ET_gw_mm", "R_mm", "S_mm"]] = np.nan
    
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
    
    df_wells = update_wells(df_wells)

    #  Math and Calculations
    df_wells['Sy'] = df_wells['soil_texture_code'].map(soil_sy_dict)
    df_wells['thickness'] = df_wells['stop_depth_cm'] - df_wells['start_depth_cm']
    df_wells['Sy_weighted'] = df_wells['Sy'] * df_wells['thickness']


    #  Grouping and Averaging
    well_summary = df_wells.groupby('well_id')[['Sy_weighted', 'thickness']].sum()
    well_summary['average_Sy'] = well_summary['Sy_weighted'] / well_summary['thickness']

    return well_summary[['average_Sy']].reset_index()
  
def plot_ET_bywell(
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
            well_df["ET_gw_mm"],
            linewidth=1.5,        # Thicker line makes it dominant
            color="black",        # High contrast color
            zorder=3,             # Forces ET to be drawn on top of everything
            label="ET"
        )
        
        # Set primary axis labels
        ax1.set_ylabel("ET (mm/day)")
        ax1.set_xlabel("Date")
        
        # ---- Create Secondary Y-Axis ----
        ax2 = ax1.twinx()
# ---- Storage line (Secondary Y-Axis) ----
        l2 = ax2.plot(
            well_df["date"],
            well_df["S_mm"],
            linewidth=0.8,
            color="lightgreen",   # Lighter green
            zorder=2,             # Draws this line above Recharge
            label="Storage (S)"
        )
        
    
# ---- Recharge line  ----
        l3 = ax2.plot(
            well_df["date"],
            well_df["R_mm"],
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
        ax2.set_ylabel("Recharge & Storage (mm/day)")

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
    index = ['method_id','S_mm','R_mm','year','well_id','date']
    df = ET_df[index]
    filtered_df = df[(df['year'] == year) & (df['method_id'] == method_id)]

    for well_id, well_df in filtered_df.groupby('well_id'):
        fig, ax1 = plt.subplots(figsize=(6, 6))
        well_df['clean_date'] = pd.to_datetime(well_df['date']).dt.strftime('%m-%d')
        plot_df = well_df.set_index('clean_date')[['S_mm_proportion', 'R_mm_proportion']]
        plot_df.plot(
            kind='bar',
            stacked=True, 
            color=['teal','cornflowerblue'],
            ax = ax1,
            width = 1.0)
        ax1.set(xlabel='Date', 
                ylabel='GW Levels (mm)', 
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

def process_date_and_year(df, raw_date_col, year):
        df_clean = df.copy()
        df_clean['date_dt'] = pd.to_datetime(df_clean[raw_date_col])
        return df_clean[df_clean['date_dt'].dt.year == year]

def plot_ET_prop_bar(ET_df: pd.DataFrame, 
                     PET_well_df: pd.DataFrame, 
                     pet_station_df: pd.DataFrame, 
                     gw_df: pd.DataFrame, 
                     method_id: str, 
                     year: int, 
                     soil_df: pd.DataFrame = None,
                     weather_df: pd.DataFrame = None, 
                     save_dir=None):
    """
    Plots proportional Net ET bars and PET line on the left axis, 
    and daily average temperature (Fahrenheit) on a secondary right axis.
    Saves the figures as .eps files or displays them.
    """
    # Process ET_df and apply its unique method_id filter
    ET_df = process_date_and_year(ET_df, 'date', year)
    ET_df = ET_df[ET_df['method_id'] == method_id]

    #filter the other dataframes to the same year for consistency
    gw_df = process_date_and_year(gw_df, 'datetime', year)
    PET_well_df = process_date_and_year(PET_well_df, 'Date', year)
    pet_station_df = process_date_and_year(pet_station_df, 'Date', year)

    #calculate proportion storage and recharge
    ET_df['S_mm_proportion'] = ET_df['Sy_star']*ET_df['S_mm'] 
    ET_df['R_mm_proportion'] = ET_df['Sy_star']*ET_df['R_mm']

    # Combine dataframes using left joins on the true datetime
    filtered_df = ET_df.merge(PET_well_df, how='left', on=['well_id', 'date_dt'])
    
    if weather_df is None or weather_df.empty:
        print(f"Weather data for year {year} is empty. Temperature data will not be plotted.")
    else:
        weather_df = process_date_and_year(weather_df, 'date', year)
        filtered_df = filtered_df.merge(weather_df, how='left', on='date_dt')
    
    # Merge Station PET safely by date only 
    station_subset = pet_station_df[['date_dt', 'PET_mm_day']].rename(columns={'PET_mm_day': 'PET_station_mm_day'})
    filtered_df = filtered_df.merge(station_subset, how='left', on='date_dt')

    for well_id, well_df in filtered_df.groupby('well_id'):
        fig, (ax1, ax3) = plt.subplots(2, 1, figsize=(8, 10), sharex=True)

        #isolate the groundwater data for the current well_id
        well_gw = gw_df[gw_df['well_id'] == well_id].sort_values('date_dt')
        
        dates = well_df['date_dt'].tolist()

        # Calculate Net ET and absolute totals
        ET_net = well_df['ET_gw_mm']
        total_abs = well_df['S_mm_proportion'].abs() + well_df['R_mm_proportion'].abs()

        # Calculate proportions safely (avoiding zero-division)
        s_prop = np.where(total_abs == 0, 0, well_df['S_mm_proportion'].abs() / total_abs)
        r_prop = np.where(total_abs == 0, 0, well_df['R_mm_proportion'].abs() / total_abs)

        # Scale proportions to the Net ET bar height
        s_bar_heights = ET_net * s_prop
        r_bar_heights = ET_net * r_prop

        # ---- PLOTTING ----
        # 1. Left Axis (ax1): Stacking Bars
        ax1.bar(dates, s_bar_heights, width=1.0, color='teal', label='Storage')
        ax1.bar(dates, r_bar_heights, bottom=s_bar_heights, width=1.0, color='cornflowerblue', label='Recharge')

        # 2. Overlay PET Line
        if 'PET_mm_day' in well_df.columns:
            pet_mm = well_df['PET_mm_day'] 
            ax1.plot(dates, pet_mm, color='crimson', linewidth=2, label='PET (mm)')

        # -Overlay Station PET Line (Dotted)  
        if 'PET_station_mm_day' in well_df.columns:
            pet_station_mm = well_df['PET_station_mm_day']
            ax1.plot(dates, pet_station_mm, color='darkred', linestyle=':', linewidth=2, label='Station PET (mm)')   

        # Add zero-line to clearly anchor positive/negative days
        ax1.axhline(0, color='black', linewidth=0.5)

        # Formatting Left Axis
        ax1.set(ylabel='Net ET / PET (mm)')
        
        # 3. Right Axis (ax2): Temperature context (Celsius)
        ax2 = ax1.twinx() 
        if 'temp_25ft_C' in well_df.columns:
            ax2.plot(dates, well_df['temp_25ft_C'], color='darkorange', linestyle='--', linewidth=1.25, alpha=0.5, label='Temp 25ft (°C)')
        
        ax2.set_ylabel('Air Temperature (°C)')
        
        # CALCULATE PERFECT ZERO ALIGNMENT
        ax1_min, ax1_max = ax1.get_ylim()
        ax2_max = 40.0
        
        # Scale the lower temp bound exactly proportional to the left axis lower bound
        ax2_min = ax1_min * (ax2_max / ax1_max)
        
        # Apply the balanced limits
        ax2.set_ylim(ax2_min, ax2_max)

# ---- PLOTTING GROUNDWATER (ax3) ----
        if not well_gw.empty:
            ax3.plot(well_gw['date_dt'], well_gw['ground_to_water_m'], color='navy', linewidth=1.2, label='10-Min Water Level', zorder=2)
            
            # --- NEW: Plot Soil Horizon Boundaries & Staggered Labels ---
            if soil_df is not None:
                well_soil = soil_df[soil_df['well_id'] == well_id].copy()
                
                if not well_soil.empty:
                    # Sort by depth just in case the CSV is out of order
                    well_soil = well_soil.sort_values('stop_depth_cm')
                    
                    last_depth = -999  # Dummy variable to track the previous depth
                    x_pos = 0.01       # Starting X position (far left)
                    
                    for _, row in well_soil.iterrows():
                        depth_m = row['stop_depth_cm'] / 100.0
                        texture = str(row['soil_texture_code']) + ' ' + str(row['gravel_amount_percent'])
                        
                        # If this line is within 0.06m of the last one, shift text right
                        if abs(depth_m - last_depth) < 0.06:
                            x_pos += 0.09 
                        else:
                            x_pos = 0.01  # Reset to far left if there's plenty of space
                        
                        # Plot the red horizontal line
                        ax3.axhline(depth_m, color='red', linestyle='--', linewidth=1.0, zorder=3)
                        
                        # Add the text label using the dynamic x_pos
                        ax3.text(x_pos, depth_m, texture, 
                                 transform=ax3.get_yaxis_transform(), 
                                 color='red', fontsize=8, fontweight='bold', 
                                 va='bottom', ha='left', zorder=4)
                        
                        last_depth = depth_m  # Update last_depth for the next loop iteration

            ax3.invert_yaxis()
            
        ax3.set_ylabel('Depth to Water (m)')
            
        ax3.set_ylabel('Depth to Water (m)')
        ax3.set_xlabel('Date')
        ax3.grid(True, linestyle=':', alpha=0.6)
        
        # Apply automatic datetime spacing and formatting
        auto_locator = mdates.AutoDateLocator(minticks=4, maxticks=10)
        auto_formatter = mdates.AutoDateFormatter(auto_locator)
        ax3.xaxis.set_major_locator(auto_locator)
        ax3.xaxis.set_major_formatter(auto_formatter)
        plt.setp(ax3.get_xticklabels(), rotation=0, ha='center')

        # ---- COMBINED LEGEND ----
        lines_1, labels_1 = ax1.get_legend_handles_labels()
        lines_2, labels_2 = ax2.get_legend_handles_labels()
        ax1.legend(lines_1 + lines_2, labels_1 + labels_2, bbox_to_anchor=(1.15, 1), loc='upper left')

        # Unified single title assignment
        ax1.set_title(f'Daily ET {method_id} {well_id}', fontsize=12, fontweight='bold')

        plt.tight_layout() # Added to prevent the new bottom labels from overlapping the top graph

        # SAVING LOGIC 
        if save_dir is not None:
            save_path = Path(save_dir)
            
            # save eps
            fname_eps = f"ET_bar_horizon{method_id}_{well_id}_{year}_GW.eps"
            fig.savefig(save_path / fname_eps, format="eps", bbox_inches="tight")
            
            # save png
            fname_png = f"ET_bar_horizon{method_id}_{well_id}_{year}_GW.png"
            fig.savefig(save_path / fname_png, format="png", bbox_inches="tight", dpi=300)
            
            plt.close(fig)
        else:
            plt.show()

def plot_ET_cat(
    ET_df: pd.DataFrame, 
    lai_df: pd.DataFrame = None, 
    pet_df: pd.DataFrame = None,
    year: int = None, 
    save_dir=None,
    end_date: str = None,
):
    """
    Creates a separate plot (figure) for each category: meadow_id, plant_type, and hydrogeo_zone.
    Within each figure, generates a vertically stacked subplot for each designation showing 
    the daily mean ET as a line. Plots PET as a dashed line and LAI.rmWAI on the secondary Y-axis.
    Places the designation name as the title of each individual subplot.
    """
    categories = {
        "meadow_id": "Meadow ID",
        "plant_type": "Plant Type",
        "hydrogeo_zone": "Hydrogeological Zone"
    }
    
    # Categorize ET data
    ET_df = well_utils.get_well_categories(ET_df)

    # Ensure datetime format for plotting
    if not pd.api.types.is_datetime64_any_dtype(ET_df["date"]):
        ET_df["date"] = pd.to_datetime(ET_df["date"])

    # --- Filter ET dataframe by year ---
    if year is not None:
        ET_df = ET_df[ET_df["date"].dt.year == year].copy()
    
    # Filter out everything after the highlighted cutoff
    if end_date is not None:
        ET_df = ET_df[ET_df["date"] <= pd.to_datetime(end_date)].copy()

    if ET_df.empty:
        print(f"No ET data available for the year {year}.")
        return
        
    valid_et_dates = ET_df["date"].unique()

    # --- Process & filter LAI dataframe ---
    lai_data = None
    if lai_df is not None:
        lai_df = lai_df.copy()
        
        # Categorize LAI data so we can filter it by designation in the loop
        lai_df = well_utils.get_well_categories(lai_df)
        
        # Strip time to get just the date
        lai_df["date_only"] = pd.to_datetime(lai_df["datetime"]).dt.normalize()
        
        if year is not None:
            lai_df = lai_df[lai_df["date_only"].dt.year == year]
            
        lai_data = lai_df

    # --- Determine Global Max LAI for uniform scaling ---
    global_max_lai = 1.0 # Default fallback
    if lai_data is not None and not lai_data.empty:
        # Get the absolute max LAI across all data for this year
        global_max_lai = lai_data['LAI.rmWAI'].max()
        # Add a 10% buffer to the top for visual breathing room
        global_max_lai = global_max_lai * 1.1 

    # --- Process & filter PET dataframe ---
    pet_data = None
    if pet_df is not None:
        pet_df = pet_df.copy()
            
        if not pd.api.types.is_datetime64_any_dtype(pet_df["Date"]):
            pet_df["Date"] = pd.to_datetime(pet_df["Date"])
            
        if year is not None:
            pet_df = pet_df[pet_df["Date"].dt.year == year]
            
        # Keep ONLY dates that exist in the ET_df to avoid empty gaps
        pet_df = pet_df[pet_df["Date"].isin(valid_et_dates)]
        pet_data = pet_df.sort_values('Date')

    # Loop through each category to create a separate figure
    for col, title in categories.items():
        
        designations = ET_df[col].dropna().unique()
        n_desig = len(designations)
        
        if n_desig == 0:
            continue
            
        # Create a figure with vertically stacked subplots, sharing BOTH X and Y axes
        fig, axes = plt.subplots(
            nrows=n_desig, 
            ncols=1, 
            figsize=(11, 2.5 * n_desig), 
            sharex=True, 
            sharey=True
        )
        
        title_suffix = f" ({year})" if year is not None else ""
        # Push the suptitle a bit higher to make room for the legend and subplot title
        fig.suptitle(f"Daily ET for {title}{title_suffix}", fontsize=15, fontweight='bold', y=1.06)
        
        if n_desig == 1:
            axes = [axes]
            
        for ax, designation in zip(axes, designations):
            
            desig_data = ET_df[ET_df[col] == designation]
            agg_data = desig_data.groupby('date')['ET_gw_mm'].agg(['mean', 'min', 'max']).reset_index()
            agg_data = agg_data.sort_values('date')
            
            if agg_data.empty:
                continue
            
            # Calculate a 4-day rolling average to smooth the ET line
            smoothed_et = agg_data['mean'].rolling(window=4, center=True, min_periods=1).mean()
            
            # 2. Plot ONLY the Smoothed Mean ET line
            ax.plot(
                agg_data['date'], 
                smoothed_et, 
                color='blue', 
                linewidth=1.5, 
                label='ET'
            )
            
            # --- SHADE NaN VALUES ---
            # Create a boolean mask looking for NaNs in the un-smoothed aggregated mean
            nan_mask = agg_data['mean'].isna()
            
            ax.fill_between(
                agg_data['date'], 
                0, 1, 
                where=nan_mask, 
                transform=ax.get_xaxis_transform(), 
                facecolor='lightgrey', 
                alpha=0.5, 
                zorder=0,
                label='Filtered / Missing'
            )
            
            # 3. Plot Station PET
            if pet_data is not None and not pet_data.empty:
                pet_col = 'PET_mm_day' if 'PET_mm_day' in pet_data.columns else pet_data.columns[-1]
                ax.plot(
                    pet_data['Date'], 
                    pet_data[pet_col], 
                    color='grey', 
                    linestyle='--', 
                    linewidth=1.5, 
                    label='Station PET'
                )
            
            ax.set_ylabel("ET & PET (mm)")
            
            # --- SET DESIGNATION AS SUBPLOT TITLE ---
            ax.set_title(f"{designation}", fontsize=12, fontweight='bold', loc='left')
            
            # 4. Secondary Y-axis (LAI.rmWAI)
            if lai_data is not None and not lai_data.empty:
                # Filter LAI data specifically for this subplot's designation FIRST
                desig_lai = lai_data[lai_data[col] == designation].copy()
                
                if not desig_lai.empty:
                    # Sort chronologically within the designation
                    desig_lai = desig_lai.sort_values('date_only')
                    
                    # AGGREGATE CAMPAIGNS BY DESIGNATION:
                    desig_lai['campaign_group'] = (desig_lai['date_only'].diff().dt.days > 3).cumsum()
                    desig_lai['plot_date'] = desig_lai.groupby('campaign_group')['date_only'].transform('min')
                    
                    # Group by our newly clustered 'plot_date' to get the mean LAI.rmWAI
                    agg_lai = desig_lai.groupby('plot_date')['LAI.rmWAI'].mean().reset_index()
                    
                    ax2 = ax.twinx()
                    
                    # DIRECT PLOT: No circles (marker removed), standard smooth connecting line
                    ax2.plot(
                        agg_lai['plot_date'], 
                        agg_lai['LAI.rmWAI'], 
                        color='tab:green', 
                        linestyle='-',
                        linewidth=1.5,
                        label='LAI'
                    )

                    ax2.set_ylabel("LAI")
                    # Force every subplot to use the exact same LAI scale
                    ax2.set_ylim(0, global_max_lai) 

        # Collect unique handles and labels from all axes (including the LAI twin axes)
        handles, labels = [], []
        for a in fig.axes:
            for handle, label in zip(*a.get_legend_handles_labels()):
                if label not in labels:
                    handles.append(handle)
                    labels.append(label)
                    
        # Place one global legend outside the subplots, just below the suptitle
        fig.legend(
            handles, 
            labels, 
            loc='upper center', 
            bbox_to_anchor=(0.5, 1.02), 
            ncol=4, # Increased to 4 to nicely fit the new "Filtered / Missing" label 
            frameon=False
        )
        
        # Format the shared bottom X-axis
        axes[-1].set_xlabel("Date")
        fig.autofmt_xdate()
        
        # Adjust vertical space to make room for subplot titles
        plt.subplots_adjust(hspace=0.25)
        
        # Save or show the category figure
        if save_dir is not None:
            save_path = Path(save_dir)
            year_str = f"_{year}" if year is not None else ""
            
            # Define the base filename WITHOUT the extension
            base_fname = f"ET_Subplots_smooth_{col}{year_str}"
            
            # Save as PNG
            fig.savefig(save_path / f"{base_fname}.png", format="png", bbox_inches="tight", dpi=300)
            
            # Save as EPS
            fig.savefig(save_path / f"{base_fname}.eps", format="eps", bbox_inches="tight", dpi=300)
            
            plt.close(fig)
        else:
            plt.show()

def plot_gw_ET_overlay(gw_df, et_df, year):
    # See DRAFT in chatgpt here: https://chatgpt.com/s/t_6988e9118c34819181d813da8c21634b
    
    return

def update_wells(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validates files with well_ids
    Returns a valided dataframe with corrected well_ids.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with well_ids 
    """
    # Validate the well_ids to ensure no bad data slipped through
    #Load Sy data

    # Correct the well_ids using the STATIC function 
    df = well_utils.correct_well_ids_static(df)
    
    # Validate the well_ids to ensure no bad data slipped through
    df = well_utils.validate_well_ids(df, id_col="well_id")
    return  df 

def apply_et_capillary_limits(
    ET_df: pd.DataFrame, 
    pet_df: pd.DataFrame,
    df_well_logs: pd.DataFrame, 
    df_extinction: pd.DataFrame, 
    pet_col: str = "PET_mm_day" 
) -> pd.DataFrame:
    """
    Filters ET_df for 2025, merges PET and groundwater depth data, 
    identifies the limiting soil layer above the water table, 
    and adjusts ET_gw_mm based on decoupling (d') and extinction (d'') thresholds.
    """
    # 1. Apply your existing function to get 'plant_type'
    df = well_utils.get_well_categories(ET_df)
    
    # 2. Filter strictly for the year 2025 where PET data is available
    df['year'] = pd.to_numeric(df['year'], errors='coerce')
    df_2025 = df[df['year'] == 2025].copy()
    
    # 3. Standardize dates for merging
    df_2025['date'] = pd.to_datetime(df_2025['date'])
    
    pet_clean = pet_df.copy()
    pet_clean['Date'] = pd.to_datetime(pet_clean['Date'])
    

    # 4. Merge PET and Groundwater Data into ET_df matching by date and well_id
    merged_df = df_2025.merge(
        pet_clean[['Date', 'well_id', pet_col]], 
        left_on=['date', 'well_id'], 
        right_on=['Date', 'well_id'], 
        how='left'
    )

    # 5. Map specific plant types to the broad categories (Grass/Forest)
    def map_to_cover(plant):
        if plant in ["Sedge", "Mixed Herbaceous"]:
            return "Grass"
        elif plant in ["Willow", "Lodgepole Pine"]:
            return "Forest"
        return "Grass" # Fallback
        
    merged_df['cover_type'] = merged_df['plant_type'].apply(map_to_cover)
    
    # 6. Prepare well logs: Convert depth from cm to mm to match gw_00
    logs = df_well_logs.copy()
    if 'start_depth_mm' not in logs.columns:
        logs['start_depth_mm'] = logs['start_depth_cm'] * 10.0
        logs['stop_depth_mm'] = logs['stop_depth_cm'] * 10.0

    # 7. Define the row-by-row logic
    def calculate_adjusted_et(row):
        wtd_mm = row['gw_00'] 
        well = row['well_id']
        cover = row['cover_type']
        current_et = row['ET_gw_mm']
        date_str = row['date'].strftime('%Y-%m-%d')
        
        # Pull merged PET, fallback to current ET if missing
        pet = row[pet_col] if pd.notna(row[pet_col]) else current_et
        
        if pd.isna(wtd_mm):
            return current_et
            
        # Filter well logs for layers ABOVE the water table
        vadose_zone = logs[(logs['well_id'] == well) & (logs['start_depth_mm'] < wtd_mm)]
        
        # Exclude Highly Organic (HO) layers
        vadose_mineral = vadose_zone[vadose_zone['soil_texture_code'] != 'HO']
        
        if vadose_mineral.empty:
            return current_et 
            
        textures = vadose_mineral['soil_texture_code'].unique()
        ext_params = df_extinction[df_extinction['Soil Texture Code'].isin(textures)]
        
        if ext_params.empty:
            return current_et
            
        # Identify the limiting layer (the one with the SMALLEST d'')
        d_double_prime_col = f"{cover} d'' (mm)"
        d_prime_col = f"{cover} d' (mm)"
        
        min_d_double_prime = ext_params[d_double_prime_col].min()
        
        # Extract thresholds
        limiting_row = ext_params[ext_params[d_double_prime_col] == min_d_double_prime].iloc[0]
        d_prime = limiting_row[d_prime_col]
        d_double_prime = limiting_row[d_double_prime_col]
        
        # Apply the thresholds and print the updates
        if wtd_mm <= d_prime:
            # Fully coupled: ET operates at potential
            print(f"Well: {well} | Date: {date_str} -> Converted to PET. Value: {pet:.3f} mm")
            return pet
        elif wtd_mm >= d_double_prime:
            # Fully decoupled: Capillary connection broken
            print(f"Well: {well} | Date: {date_str} -> Converted to 0. Value: 0.0 mm")
            return 0.0
        else:
            # Falling rate stage: leave as originally calculated
            return current_et

    # 8. Apply the function across all rows to create the adjusted column
    merged_df['ET_gw_mm'] = merged_df.apply(calculate_adjusted_et, axis=1)
    
    return merged_df[
    [
        "date",
        "doy",
        "year",
        "well_id",
        "ET_gw_mm",
        "R_mm",
        "S_mm",
        "Sy_star",
        "method_id",
        "gw_00"
    ]
].dropna()

    # ---- MAIN PROCEDURES ---

def main():
   

    # I/O: load subdaily groundwater input (source data) file
    subdaily_gw_df = pd.read_csv(groundwater_subdaily_filepath,
                                 parse_dates=["DateTime"]
                                 ).rename(columns={"DateTime": "datetime"})   
    # Load precipitation data
    precip_df = load_precip_for_years(weather_subdaily_filepath, 2025)
    daily_precip_df = daily_cumulative_precip(precip_df)
    
    # pre-process gw from subdaily into key daily values
    daily_gw_df = get_daily_gw_levels(subdaily_gw_df)
    print("got gw levels")
  
    # #calculate average Sy for each well
    df_soil_sy = pd.read_csv(sy_data_filepath)
    duke_df = pd.read_csv(duky_sy_data_dir)
    df_well_logs = pd.read_csv(well_data_filepath)
    calculated_sy_df = average_sy(df_soil_sy, df_well_logs)

    PET_df = pd.read_csv(pet_well_data_filepath)
    pet_station_df = pd.read_csv(pet_station_data_filepath)
    #weather_df = get_daily_temperature(weather_subdaily_filepath)
    lai_df = pd.read_csv(lai_data_filepath)
    # #save average Sy values for each well 
    # calculated_sy_df.to_csv(sy_save_filepath, index=False)
    df_extinction = pd.read_csv(extinction_data_filepath)
    # 1. Calculate raw ET for ALL days
    #raw_ET_df = estimate_ET_White_Duke_Sy(daily_gw_df, df_well_logs, duke_df)
    #raw_ET_df = apply_et_capillary_limits(raw_ET_df, PET_df, df_well_logs, df_extinction, pet_col="PET_mm_day")
    raw_ET_df = estimate_ET_White_wavg_Sy(daily_gw_df, calculated_sy_df)
    #raw_ET_df = apply_et_capillary_limits(raw_ET_df, PET_df, df_well_logs, df_extinction, pet_col="PET_mm_day")
    # # 2. Filter out the storm events
    ET_no_rain = filter_ET_by_precip(raw_ET_df, daily_precip_df, threshold_mm=3.0, recovery_days=3)

    # 3. Filter out days where the well went dry (dropping data when water is within 7cm of bottom)
    daily_ET_df = filter_ET_by_well_depth(ET_no_rain , daily_gw_df, df_well_logs, buffer_mm=100.0)



    # Plot
    plot_ET_cat(
        ET_df=daily_ET_df, 
        lai_df = lai_df,
        pet_df=pet_station_df,
        year=2025, 
        end_date=None,
        save_dir=save_plots_dir
    )
    print("ET category plots with PET generated successfully!")

    # plot_ET_prop_bar(daily_ET_df, 
    #         PET_df,
    #         pet_station_df,
    #         subdaily_gw_df,
    #         "White_Duke", 
    #         2025,  
    #         df_well_logs, 
    #         save_dir=save_plots_dir)
    # print("ET plotted for White average Sy")

   
    # Save to csv? Do we want a new one or write over the one from above?
    # Then plot this new estimate, use an appropriate name, check if the 2nd param affects filename and not just the title
    print("COMPLETE!!")
   

# --- END FUNCTIONS

if __name__ == "__main__":
    main()
