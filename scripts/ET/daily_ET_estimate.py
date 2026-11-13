#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DAILY ET CALCULATION SCRIPT
Created on  Sat 7 Feb 11:37 AM
@author: jnatali, klsmittle

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

import seaborn as sns


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

et_data_dir = PROJECT_ROOT / 'data/et/'
sy_data_filepath = et_data_dir / 'sy_lookup.csv' 

sy_save_filepath = et_data_dir / 'sy_by_well.csv'

soil_data_dir = PROJECT_ROOT / 'data/field_observations/soil/'
soil_data_filepath = soil_data_dir / 'soil_survey_PROCESSED.csv'

pet_well_data_filepath = et_data_dir / 'pet_by_well_results.csv'

pet_station_data_filepath = et_data_dir / 'pet_station_results.csv'

save_plots_dir = PROJECT_ROOT / 'results/plots/ET/White_Van_Gun/'

save_csv_dir = PROJECT_ROOT / 'data/calculated_time_series/ET/ET_daily_2025_White_constantSy.csv'

duke_et_data_dir = PROJECT_ROOT / 'data/et/duke_lookup.csv'

van_guch_filepath = PROJECT_ROOT / et_data_dir / 'van_genuchten_lookup.csv'

lai_data_dir = PROJECT_ROOT / 'data/field_observations/vegetation/LAI/'
lai_data_filepath = lai_data_dir / 'LAI_2025_Corrected.csv'

extinction_data_dir = PROJECT_ROOT / 'data/et/'
extinction_data_filepath = extinction_data_dir / 'Shah_extinction_depth.csv'


# Define typical root depths for plant functional types (in cm).
# Adjust these values based on your site's specific ecology.
PLANT_ROOT_DEPTHS = {
    'Willow': 0.0,             # Deep-rooted: bypasses shallow gravel
    'Sedge': 0.0,               # Medium-rooted
    'Mixed Herbaceous': 0.0     # Shallow-rooted
}

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
    a validated dataframe with daily groundwater variables 
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

    #ensure that wells are updated with their most recent names
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

def get_PET(data_df: pd.DataFrame,
            pet_df: pd.DataFrame, 
            station_PET_df: pd.DataFrame, 
            year: int, 
            pet_col: str = "PET_mm_day") -> pd.DataFrame:
    """
    Merges well-specific PET and station PET dataframes for a given year.

    Parameters
    ----------
    data_df : pd.DataFrame
        DataFrame containing the main dataset.
    pet_df : pd.DataFrame
        DataFrame containing well-specific PET data.
    station_PET_df : pd.DataFrame
        DataFrame containing station PET data.
    year : int
        Year to filter the data on.
    pet_col : str, optional
        Column name for PET values in the input dataframes. Default is "PET_mm_day".

    Returns
    -------
    pd.DataFrame
        Merged DataFrame with well-specific and station PET values for the specified year.
    """
    # Clean and standardize the primary PET dataframe dates
    pet_clean = pet_df.copy()
    pet_clean["Date"] = pd.to_datetime(pet_clean["Date"])

    # If a station PET dataframe is provided, clean and standardize it too
    if station_PET_df is not None:
        station_PET_clean = station_PET_df.copy()

        station_PET_clean["Date"] = pd.to_datetime(
            station_PET_clean["Date"]
        )

        # Filter the station PET data strictly for the requested year
        station_PET_clean_year = station_PET_clean[
            station_PET_clean["Date"].dt.year == year
        ].copy()

        # Rename the station PET column to differentiate it from the well-specific PET column during merge
        station_PET_clean_year = station_PET_clean_year.rename(
            columns={pet_col: "station_PET_mm_day"}
        )

    # MERGE DATASETS
    # Left merge the primary PET data into the daily groundwater dataframe
    # Match on both 'date' and 'well_id' so each well gets its specific daily PET
    merged_df = data_df.merge(
        pet_clean[["Date", "well_id", pet_col]],
        left_on=["date", "well_id"],
        right_on=["Date", "well_id"],
        how="left",
    )

    # Left merge the station PET data (matches only by date, as station applies globally)
    if station_PET_df is not None:
        merged_df = merged_df.merge(
            station_PET_clean_year[["Date", "station_PET_mm_day"]],
            left_on=["date"],
            right_on=["Date"],
            how="left",
        )
    return merged_df

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

def calculate_short_deployment_white_vars(daily_df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies the 3-day White method workaround for short 2021 logger deployments.
    Uses 'R_mm' and 'S_mm' columns to match downstream Duke Sy requirements.
    Fails loudly if critical data or dates are missing.
    """
    # ==========================================
    # 1. STRICT DATA TRIPWIRES
    # ==========================================
    if daily_df.empty:
        raise ValueError("DATA ERROR: The provided dataframe is completely empty.")
        
    if daily_df['date'].isna().any():
        raise ValueError("DATA ERROR: Found missing (NaT/NaN) dates in the dataset. Clean your dates before running.")
        
    # Updated to look for the specific R_mm and S_mm columns
    required_cols = ['R_mm', 'S_mm']
    for col in required_cols:
        if col not in daily_df.columns:
            raise ValueError(f"DATA ERROR: Missing required column '{col}' in the dataset.")

    # ==========================================
    # 2. ISOLATE DEPLOYMENT CHUNKS
    # ==========================================
    df = daily_df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by=['well_id', 'date'])
    
    # Calculate days between rows to find gaps
    df['gap_days'] = df.groupby('well_id')['date'].diff().dt.days
    df['is_new_deployment'] = (df['gap_days'] > 1) | df['gap_days'].isna()
    df['deployment_id'] = df.groupby('well_id')['is_new_deployment'].cumsum()
    
    processed_frames = []
    
   
    # 3. APPLY 3-DAY WORKAROUND
   
    for (well, dep_id), dep_data in df.groupby(['well_id', 'deployment_id']):
        
        if len(dep_data) == 3:
            # Tripwire specifically for the 3-day calculation using R_mm and S_mm
            if dep_data[['R_mm', 'S_mm']].isna().any().any():
                 raise ValueError(f"DATA ERROR: Well {well} has a 3-day deployment but is missing R_mm or S_mm data.")
                 
            # --- RECHARGE (R) CALCULATION ---
            # Extract the nightly recharge for the first two nights using the correct column
            r_night_1 = dep_data.iloc[0]['R_mm']
            r_night_2 = dep_data.iloc[1]['R_mm']
            r_avg = (r_night_1 + r_night_2) / 2.0
            
            # --- STORAGE (S) CALCULATION ---
            # Extract the full 24-hour storage change from the middle day
            s_single_day = dep_data.iloc[1]['S_mm']
            
            # Overwrite the middle day's values with the processed 3-day workaround values
            dep_data.loc[dep_data.index[1], 'R_mm'] = r_avg
            dep_data.loc[dep_data.index[1], 'S_mm'] = s_single_day
            
            # PHYSICALLY DELETE DAY 1 AND DAY 3
            # By slicing the dataframe to only include the middle row (index 1), 
            # the partial days are dropped before being added to processed_frames
            dep_data = dep_data.iloc[[1]]
            
        processed_frames.append(dep_data)
        
    final_df = pd.concat(processed_frames, ignore_index=True)
    
    return final_df.drop(columns=['gap_days', 'is_new_deployment', 'deployment_id'])

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

import pandas as pd

def estimate_ET_White_Duke_Sy(
    daily_df: pd.DataFrame, 
    soil_df: pd.DataFrame, 
    rawls_df: pd.DataFrame,
    pet_df: pd.DataFrame,
    station_PET_df: pd.DataFrame = None,
    year: int = 2025   
) -> pd.DataFrame:
    """
    Calculates ET using Duke's equation for Specific Yield (Sy), based on 
    the soil parameters of the single horizon where the water table is currently fluctuating.
    
    Includes a capillary truncation check for overlying gravel layers ('GR').
    If the water table is inside the effective capillary fringe, the White method is bypassed 
    and ET is set to equal atmospheric PET.
    
    Includes a strict fail-fast design: the script will crash and raise a ValueError 
    if any required data (soil horizons, water table, PET, or recharge parameters) is missing.
    """
    METHOD_ID = "White_Duke"
    
    # Create clean copies
    df = daily_df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df[df['date'].dt.year == year].copy()
    # Assuming update_wells is a custom function defined elsewhere in your script
    df = update_wells(df)

    soil_clean = soil_df.copy()

    df = calculate_storage_recharge(df)
    df = calculate_short_deployment_white_vars(df)
    df = get_PET(df, pet_df, station_PET_df, year)

    # Create dictionary lookup for Rawls parameters
    rawls_lookup = rawls_df.set_index('soil_texture_code').to_dict(orient='index')
    
    # Store calculated values
    calculated_sy_list = []
    calculated_et_list = []      

    # Loop through each daily groundwater record
    for _, row in df.iterrows():
        current_well = row['well_id']
        current_date = row['date'].date()
        
        # Ensure groundwater depth exists before calculating
        if 'gw_00' not in row or pd.isna(row['gw_00']):
            raise ValueError(f"DATA ERROR: Missing groundwater depth (gw_00) for well '{current_well}' on {current_date}.")
            
        # Groundwater depth is stored in mm in 'gw_00'. Convert it to cm to match soil depths.
        raw_wt_cm = row['gw_00'] / 10.0
        
        # ---------------------------------------------------------
        # REGIME 0: STANDING WATER (Negative or Zero Depth)
        # ---------------------------------------------------------
        if raw_wt_cm <= 0.0:
            # Water is at or above the ground surface. Bypass soil properties entirely.
            layer_sy = 0.0 
            
            pet_val = row['PET_mm_day'] if 'PET_mm_day' in row else pd.NA
            station_pet_val = row['station_PET_mm_day'] if 'station_PET_mm_day' in row else pd.NA
            
            if pd.notna(pet_val):
                daily_et = pet_val
            elif pd.notna(station_pet_val):
                daily_et = station_pet_val
            else:
                raise ValueError(
                    f"DATA ERROR: Missing both local and station PET data for well '{current_well}' "
                    f"on {current_date} during a standing water event."
                )
            
            # Append the results and immediately skip to the next day
            calculated_sy_list.append(layer_sy)
            calculated_et_list.append(daily_et)
            continue
            
        # ---------------------------------------------------------
        # For all normal days, wt_depth_cm is safely strictly positive
        wt_depth_cm = raw_wt_cm

        # Filter the soil survey to find horizons belonging to ONLY this well
        well_horizons = soil_clean[soil_clean['well_id'] == current_well].copy()
        
        if well_horizons.empty:
            print(f"DATA ERROR: No soil horizons defined for well '{current_well}'.")
            # Append NaNs and continue to the next day here so the script doesn't crash below
            calculated_sy_list.append(np.nan)
            calculated_et_list.append(np.nan)
            continue

        # Find the single horizon containing the current water table
        active_horizon = well_horizons[
            (well_horizons['start_depth_cm'] <= wt_depth_cm) & 
            (well_horizons['stop_depth_cm'] > wt_depth_cm)
        ]

        if active_horizon.empty:
            print(
                f"DATA ERROR: Water table depth ({wt_depth_cm} cm) for well '{current_well}' on {current_date} "
                f"falls completely outside the recorded soil logs. Cannot calculate Sy. Skipping day."
            )
            # Append NaNs to keep the lists exactly the same length as the DataFrame
            calculated_sy_list.append(np.nan)
            calculated_et_list.append(np.nan)
            
            # skip to the next day in the loop
            continue

        # Extract the single row as a Series and get texture code
        horizon = active_horizon.iloc[0]
        texture_code = str(horizon['soil_texture_code']).strip()

        # Capillary Truncation Check: Find any gravel sitting ABOVE the active water table.
        # Gravel has pores too large to support a capillary fringe, acting as a hydraulic barrier.
        gravel_above = well_horizons[
            (well_horizons['stop_depth_cm'] < wt_depth_cm) & 
            (well_horizons['soil_texture_code'].isin(['GR']))
        ]

        # Fetch Parameters and Set Effective Air-Entry Pressure (ha)
        if texture_code in ['GR', 'HO']:
            # The water table is currently inside a gravel layer. 
            # Gravel cannot hold a capillary fringe above the water table.
            is_gravel_active = True
            ha_eff = 0.0
            layer_sy = 0.23 # Fixed generic specific yield for medium gravel
        else:
            is_gravel_active = False
            
            if texture_code not in rawls_lookup:
                raise ValueError(f"DATA ERROR: Soil code '{texture_code}' for well '{current_well}' not in Rawls lookup.")
            
            params = rawls_lookup[texture_code]
            
            try:
                # Physical Soil Parameters (from Rawls)
                # phi (Porosity): The total volume fraction of empty space in the soil.
                phi = params['phi']
                
                # Sr (Residual Saturation): The fraction of water permanently held by tight capillary forces.
                sr = params['Sr']
                
                # ha_cm (Air-entry pressure): The maximum natural height of the saturated capillary fringe.
                ha_cm = params['ha_cm']
                
                # lam (Lambda): Pore-size distribution index. Controls how fast water drains as suction increases.
                lam = params['lambda']
            except KeyError as missing_key:
                raise ValueError(f"DATA ERROR: Parameter {missing_key} missing for soil texture '{texture_code}'.")
                
            # max_sy: The absolute maximum water the soil can release if drained completely by gravity.
            max_sy = phi - sr

            # Calculate Effective Air-Entry Pressure (ha_eff)
            # If gravel sits above the water table, the capillary fringe stops at the gravel boundary.
            # We shrink the air-entry pressure to match the available vertical space.
            if not gravel_above.empty:
                gravel_bottom_cm = gravel_above['stop_depth_cm'].max()
                dist_to_gravel = wt_depth_cm - gravel_bottom_cm
                ha_eff = min(ha_cm, max(0.0, dist_to_gravel))
            else:
                ha_eff = ha_cm

        # Calculate Specific Yield and ET
        
        if is_gravel_active:
            # GRAVEL REGIME: No capillary rise, fixed Sy. 
            # Bypasses PET and Duke's equation entirely.
            daily_et = layer_sy * (row["R_mm"] + row["S_mm"])
            
        elif wt_depth_cm <= ha_eff:
            # REGIME 1: Normal soil saturated to surface
            layer_sy = 0.0
            
            pet_val = row['PET_mm_day'] if 'PET_mm_day' in row else pd.NA
            station_pet_val = row['station_PET_mm_day'] if 'station_PET_mm_day' in row else pd.NA
            
            if pd.notna(pet_val):
                daily_et = pet_val
            elif pd.notna(station_pet_val):
                daily_et = station_pet_val
            else:
                raise ValueError(
                    f"DATA ERROR: Missing both local and station PET data for well '{current_well}' "
                    f"on {current_date} during a surface-saturated event."
                )
                
        else:
            # REGIME 2: Normal soil unsaturated drainage
            if 'R_mm' not in row or pd.isna(row['R_mm']) or 'S_mm' not in row or pd.isna(row['S_mm']):
                raise ValueError(
                    f"DATA ERROR: Missing recharge (R_mm) or storage (S_mm) for well '{current_well}' on {current_date}."
                )
                
            # Apply Duke's equation
            depth_factor = 1.0 - ((ha_eff / wt_depth_cm) ** lam)
            layer_sy = max_sy * depth_factor
            daily_et = layer_sy * (row["R_mm"] + row["S_mm"])

        # --- NEW CHECK: Calculated ET vs PET ---
        pet_val = row['PET_mm_day'] if 'PET_mm_day' in row else pd.NA
        station_pet_val = row['station_PET_mm_day'] if 'station_PET_mm_day' in row else pd.NA
        
        # Use local PET if available, otherwise use station PET
        active_pet = pet_val if pd.notna(pet_val) else station_pet_val
        
        if pd.notna(active_pet) and daily_et > active_pet:
            print(
                f"WARNING: Calculated ET ({daily_et:.2f} mm) > PET ({active_pet:.2f} mm) "
                f"for well '{current_well}' on {current_date}. Soil Layer: '{texture_code} at depth {wt_depth_cm} cm'."
            )

        # Append to our daily lists
        calculated_sy_list.append(layer_sy)
        calculated_et_list.append(daily_et)

    # Attach the arrays of calculated values as new columns 
    df['Sy_star'] = calculated_sy_list 
    df['ET_gw_mm'] = calculated_et_list
    df['method_id'] = METHOD_ID
    

    
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
    ]

def estimate_ET_White_VG_Smoothed(
    daily_df: pd.DataFrame, 
    soil_df: pd.DataFrame, 
    vg_df: pd.DataFrame, 
    pet_df: pd.DataFrame,
    station_PET_df: pd.DataFrame = None,
    year: int = 2025,
    smoothing_window: int = 2  
) -> pd.DataFrame:
    """
    Calculates daily groundwater evapotranspiration (ET_g) using a modified White method.
    This dynamically calculates specific yield using van Genuchten parameters and a 
    kinematic drainage time correction to account for delayed yield in heavy soils.
    """
    
    METHOD_ID = "White_VG"
    
    df = daily_df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df[df['date'].dt.year == year].copy()
    
    df = df.sort_values(by=['well_id', 'date'])
    df = update_wells(df)
    soil_clean = soil_df.copy()


    df['gw_00_smooth'] = df.groupby('well_id')['gw_00'].transform(
        lambda x: x.rolling(window=smoothing_window, min_periods=1, center=False).mean()
    )
    
    # 2. OVERWRITE THE RAW DATA SO THE WHITE METHOD ONLY SEES THE CLEAN SIGNAL
    df['gw_00'] = df['gw_00_smooth']

    # 3.  CALCULATE RECHARGE
    df = calculate_storage_recharge(df)
    df = get_PET(df, pet_df, station_PET_df, year)

    # 4. Smooth the resulting daily components 
    df['R_mm_smooth'] = df.groupby('well_id')['R_mm'].transform(
        lambda x: x.rolling(window=smoothing_window, min_periods=1, center=False).mean()
    )
    df['S_mm_smooth'] = df.groupby('well_id')['S_mm'].transform(
        lambda x: x.rolling(window=smoothing_window, min_periods=1, center=False).mean()
    )

    vg_lookup = vg_df.set_index('soil_texture_code').to_dict(orient='index')
    
    calculated_sy_list = []
    calculated_et_list = []      

    for _, row in df.iterrows():
        current_well = row['well_id']
        
        # Skip calculations if the smoothed groundwater data is missing for the day.
        if 'gw_00_smooth' not in row or pd.isna(row['gw_00_smooth']):
            calculated_sy_list.append(np.nan)
            calculated_et_list.append(np.nan)
            continue
            
        wt_depth_cm = row['gw_00_smooth'] / 10.0
        
        # Determine the most localized Potential Evapotranspiration (PET) value available.
        pet_val = row['PET_mm_day'] if 'PET_mm_day' in row else pd.NA
        station_pet_val = row['station_PET_mm_day'] if 'station_PET_mm_day' in row else pd.NA
        active_pet = pet_val if pd.notna(pet_val) else station_pet_val

        # If the water table is at or above the ground surface, bypass the soil mechanics and set ET directly to PET.
        if wt_depth_cm <= 0.0:
            calculated_sy_list.append(0.0)
            calculated_et_list.append(active_pet if pd.notna(active_pet) else 0.0)
            continue
            
        well_horizons = soil_clean[soil_clean['well_id'] == current_well].copy()
        
        # Skip if no soil profile data is available for this well.
        if well_horizons.empty:
            calculated_sy_list.append(np.nan)
            calculated_et_list.append(np.nan)
            continue

        active_horizon = well_horizons[
            (well_horizons['start_depth_cm'] <= wt_depth_cm) & 
            (well_horizons['stop_depth_cm'] > wt_depth_cm)
        ]
        
        # Skip if the water table sits outside the defined soil profile depths.
        if active_horizon.empty:
            calculated_sy_list.append(np.nan)
            calculated_et_list.append(np.nan)
            continue

        # Calculate the dynamically scaled specific yield based on soil texture and drainage time.
        layer_sy = get_composite_sy_kinematic(wt_depth_cm, well_horizons, vg_lookup, observation_time_days=1.0)
        
        # Convert the observed storage and recharge signals into physical water depth using the calculated specific yield.
        raw_daily_et = layer_sy * (row["R_mm_smooth"] + row["S_mm_smooth"])
        
        # Prevent ET from dropping below zero due to noise or sudden positive storage fluctuations.
        daily_et = max(0.0, raw_daily_et)
        
        # # Cap the calculated evapotranspiration so it does not exceed the maximum atmospheric demand (PET).
        # if pd.notna(active_pet):
        #     daily_et = min(daily_et, active_pet)

        calculated_sy_list.append(layer_sy)
        calculated_et_list.append(daily_et)

    df['Sy_star'] = calculated_sy_list 
    df['ET_gw_mm'] = calculated_et_list
    df['method_id'] = METHOD_ID
    
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
    ]

def estimate_ET_Shaw(
    daily_df: pd.DataFrame,
    pet_df: pd.DataFrame,
    df_well_logs: pd.DataFrame,
    df_extinction: pd.DataFrame,
    station_PET_df: pd.DataFrame = None,
    pet_col: str = "PET_mm_day",
    year: int = 2025,
) -> pd.DataFrame:
    """Calculates Groundwater Evapotranspiration (GWET) based on the Shaw method
    (Equation 17). This function evaluates the limiting soil layer in the
    vadose zone and calculates ET directly from Potential Evapotranspiration
    (PET). If specific well PET is missing, it falls back to station PET and
    notifies the user.
    """

    # PREPARE AND FILTER DATA USING HELPER
    merged_df, logs = prepare_merged_et_df(
        df_input=daily_df,
        pet_df=pet_df,
        station_PET_df=station_PET_df,
        df_well_logs=df_well_logs,
        pet_col=pet_col,
        year=year,
    )


    def apply_shaw_equation(row):
        """Applies Equation 17 for a single day at a single well.

        GWET/PET = 1 (for d <= d'') GWET/PET = y0 + exp(-b(d - d'')) (for d >
        d'')
        """
        wtd_mm = row["gw_00"]
        well = row["well_id"]
        cover = row["cover_type"]
        date_str = row["date"].strftime("%Y-%m-%d")

        # Safely extract the fallback station PET, returning NaN if it doesn't exist
        station_PET = (
            row["station_PET_mm_day"]
            if "station_PET_mm_day" in row
            else np.nan
        )

        # Determine the active PET to use for the calculation
        if pd.notna(row[pet_col]):
            # Primary PET data is available
            active_pet = row[pet_col]
        elif pd.notna(station_PET):
            # Primary is missing, use fallback and print a notification statement
            active_pet = station_PET
            print(
                f"Notice: Missing specific PET for Well {well} on {date_str}. Substituted with Station PET ({active_pet:.3f} mm)."
            )
        else:
            # No PET data available at all to drive ET, return NaN
            return np.nan

        # If water table depth is missing, we cannot calculate GWET
        if pd.isna(wtd_mm):
            return np.nan
        try:
            # ISOLATE VADOSE ZONE: Filter soil logs to only include layers ABOVE the current water table
            vadose_zone = logs[
                (logs["well_id"] == well) & (logs["start_depth_mm"] < wtd_mm)
            ]
            # Exclude Highly Organic ('HO') layers as they usually don't dictate the capillary block
            vadose_mineral = vadose_zone[vadose_zone["soil_texture_code"] != "HO"]
        except KeyError as missing_key:
                raise ValueError(
                    f"DATA ERROR: The data is missing for  {well} on {date_str}. Please check the soil logs and ensure all required columns are present."
                )

        # Get the unique soil texture codes currently present in the vadose zone
        textures = vadose_mineral["soil_texture_code"].unique()

        # Lookup the extinction parameters (y0, b, d'') for these specific textures
        ext_params = df_extinction[
            df_extinction["Soil Texture Code"].isin(textures)
        ]

        # If no matching parameters are found in the lookup table, assume fully coupled
        if ext_params.empty:
            return active_pet

        # DYNAMIC COLUMN NAMES: Identify the correct columns based on the land cover type
        d_double_prime_col = f"{cover} d'' (mm)"
        y0_col = f"{cover} y0"           # Removed the underscore
        b_col = f"{cover} b (cm-1)"      # Added the units to match the header exactly

        # IDENTIFY LIMITING LAYER: The layer with the tightest capillary constraint (smallest d'')
        min_d_double_prime = ext_params[d_double_prime_col].min()

        # Isolate the row in the parameters table corresponding to this limiting layer
        limiting_row = ext_params[
            ext_params[d_double_prime_col] == min_d_double_prime
        ].iloc[0]

        # Extract the specific parameters needed for Equation 17
        d_double_prime_mm = limiting_row[d_double_prime_col]
        y0 = limiting_row[y0_col]
        b = limiting_row[b_col]

        # APPLY EQUATION 17
        if wtd_mm <= d_double_prime_mm:
            # Phase 1: Water table is shallower than d''. Roots have full access to water.
            # GWET / PET = 1 -> GWET = PET
            return active_pet
        else:
            # Phase 2: Water table is deeper than d''. Roots rely on decaying capillary rise.
            # Equation uses 'b' which is in units of cm^-1 (per Table 3).
            # Therefore, we MUST convert the depth difference (d - d'') from mm to cm!
            depth_diff_cm = (wtd_mm - d_double_prime_mm) / 10.0

            # Calculate the ratio: y0 + e^(-b * (d - d''))
            ratio = y0 + np.exp(-b * depth_diff_cm)

            # Mathematical safeguard: y0 can be slightly negative (e.g., -0.012).
            # At extreme depths, the exponential term approaches 0, which could make the total ratio negative.
            # ET cannot be negative, so we floor the ratio at 0.0.
            ratio = max(0.0, ratio)

            # Final GWET is the calculated ratio multiplied by the active PET
            return active_pet * ratio


    # Apply the row-by-row function across the entire dataframe to generate the new ET column
    merged_df["ET_gw_mm"] = merged_df.apply(apply_shaw_equation, axis=1)

    # Explicitly label the method used for future tracking
    merged_df["method_id"] = "Shaw_Eq17"

    # Ensure structural columns exist even if they weren't in the original daily_df
    # This prevents KeyError during the final column selection
    for col in ["R_mm", "S_mm", "Sy_star", "meadow_id", "hydrogeo_zone"]:
        if col not in merged_df.columns:
            merged_df[col] = np.nan

    # Return the final organized dataframe, dropping any rows where ET could not be calculated
    return merged_df[
        [
            "date",
            "doy",
            "year",
            "well_id",
            "meadow_id",
            "hydrogeo_zone",
            "plant_type",
            "ET_gw_mm",
            "R_mm",
            "S_mm",
            "Sy_star",
            "method_id",
            "gw_00",
        ]
    ].dropna(subset=["ET_gw_mm"])

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

    # Filter the other dataframes to the same year for consistency
    gw_df = process_date_and_year(gw_df, 'datetime', year)
    PET_well_df = process_date_and_year(PET_well_df, 'Date', year)
    pet_station_df = process_date_and_year(pet_station_df, 'Date', year)

    # Calculate proportion storage and recharge (Will result in NaNs for Shaw method)
    ET_df['S_mm_proportion'] = ET_df['Sy_star'] * ET_df['S_mm'] 
    ET_df['R_mm_proportion'] = ET_df['Sy_star'] * ET_df['R_mm']

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

        # Isolate the groundwater data for the current well_id
        well_gw = gw_df[gw_df['well_id'] == well_id].sort_values('date_dt')
        dates = well_df['date_dt'].tolist()

        # Calculate Net ET
        ET_net = well_df['ET_gw_mm']

        # ---- PLOTTING LEFT AXIS (ax1): Stacking or Single Bars ----
        # Check if S and R columns are mostly NaN (e.g., Shaw Method)
        if well_df[['S_mm', 'R_mm']].isna().all().all() or method_id == "Shaw_Eq17":
            # Plot a single solid bar for Total ET
            ax1.bar(dates, ET_net, width=1.0, color='mediumpurple', label='Total ET')
        else:
            # White Methods: Plot Stacked Proportional Bars
            total_abs = well_df['S_mm_proportion'].abs() + well_df['R_mm_proportion'].abs()

            # Calculate proportions safely (avoiding zero-division)
            s_prop = np.where(total_abs == 0, 0, well_df['S_mm_proportion'].abs() / total_abs)
            r_prop = np.where(total_abs == 0, 0, well_df['R_mm_proportion'].abs() / total_abs)

            # Scale proportions to the Net ET bar height (Works flawlessly with VG_Smoothed scaling logic)
            s_bar_heights = ET_net * s_prop
            r_bar_heights = ET_net * r_prop

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
        if ax1_max != 0:
            ax2_min = ax1_min * (ax2_max / ax1_max)
        else:
            ax2_min = 0
            
        # Apply the balanced limits
        ax2.set_ylim(ax2_min, ax2_max)

        # ---- PLOTTING GROUNDWATER (ax3) ----
        if not well_gw.empty:
            ax3.plot(well_gw['date_dt'], well_gw['ground_to_water_m'], color='navy', linewidth=1.2, label='10-Min Water Level', zorder=2)
            
            # Plot Soil Horizon Boundaries & Staggered Labels
            if soil_df is not None:
                well_soil = soil_df[soil_df['well_id'] == well_id].copy()
                
                if not well_soil.empty:
                    well_soil = well_soil.sort_values('stop_depth_cm')
                    
                    last_depth = -999  
                    x_pos = 0.01       
                    
                    for _, row in well_soil.iterrows():
                        depth_m = row['stop_depth_cm'] / 100.0
                        texture = str(row['soil_texture_code']) + ' ' + str(row['gravel_amount_percent'])
                        
                        if abs(depth_m - last_depth) < 0.06:
                            x_pos += 0.09 
                        else:
                            x_pos = 0.01  
                        
                        ax3.axhline(depth_m, color='red', linestyle='--', linewidth=1.0, zorder=3)
                        ax3.text(x_pos, depth_m, texture, 
                                 transform=ax3.get_yaxis_transform(), 
                                 color='red', fontsize=8, fontweight='bold', 
                                 va='bottom', ha='left', zorder=4)
                        
                        last_depth = depth_m  

            ax3.invert_yaxis()
            
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

        plt.tight_layout()

        # SAVING LOGIC 
        if save_dir is not None:
            save_path = Path(save_dir)
            fname_eps = f"ET_bar_{method_id}_{well_id}_{year}.eps"
            fig.savefig(save_path / fname_eps, format="eps", bbox_inches="tight")
            
            fname_png = f"ET_bar_{method_id}_{well_id}_{year}.png"
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
            base_fname = f"ET_Subplots_{col}{year_str}_attempt2"
            
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




def prepare_merged_et_df(
    df_input: pd.DataFrame,
    pet_df: pd.DataFrame,
    station_PET_df: pd.DataFrame = None,
    df_well_logs: pd.DataFrame = None,
    pet_col: str = "PET_mm_day",
    year: int = 2025,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Helper function to perform shared data cleaning, filtering, PET merging, 
    cover mapping, and well log depth conversions.
    """
    ##TODO ensure that all of the datetimes work out correctly and that the merge is correct.
    # Retrieve 'plant_type' and other well categories using your utility function
    df = well_utils.get_well_categories(df_input)

    # Ensure the 'year' column is numeric so we can filter exactly for the target year
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df_year = df[df["year"] == year].copy()

    # Convert dates to standard pandas datetime objects to ensure accurate merging
    df_year["date"] = pd.to_datetime(df_year["date"])
    merged_df = get_PET(df_year, pet_df, station_PET_df, year)
    # # Clean and standardize the primary PET dataframe dates
    # pet_clean = pet_df.copy()
    # pet_clean["Date"] = pd.to_datetime(pet_clean["Date"])

    # If a station PET dataframe is provided, clean and standardize it too
    # if station_PET_df is not None:
    #     station_PET_clean = station_PET_df.copy()
    #     station_PET_clean["Date"] = pd.to_datetime(
    #         station_PET_clean["Date"]
    #     )

    #     # Filter the station PET data strictly for the requested year
    #     station_PET_clean_year = station_PET_clean[
    #         station_PET_clean["Date"].dt.year == year
    #     ].copy()

    #     # Rename the PET column here so it doesn't collide with the primary PET column during merge
    #     station_PET_clean_year = station_PET_clean_year.rename(
    #         columns={pet_col: "station_PET_mm_day"}
    #     )

    # # MERGE DATASETS
    # # Left merge the primary PET data into the daily groundwater dataframe
    # # Match on both 'date' and 'well_id' so each well gets its specific daily PET
    # merged_df = df_year.merge(
    #     pet_clean[["Date", "well_id", pet_col]],
    #     left_on=["date", "well_id"],
    #     right_on=["Date", "well_id"],
    #     how="left",
    # )

    # # Left merge the station PET data (matches only by date, as station applies globally)
    # if station_PET_df is not None:
    #     merged_df = merged_df.merge(
    #         station_PET_clean_year[["Date", "station_PET_mm_day"]],
    #         left_on=["date"],
    #         right_on=["Date"],
    #         how="left",
    #     )

    # DEFINE LAND COVER & PREPARE SOIL LOGS
    def map_to_cover(plant):
        if plant in ["Sedge", "Mixed Herbaceous"]:
            return "Grass"
        elif plant in ["Willow", "Lodgepole Pine"]:
            return "Forest"
        # If the plant isn't explicitly defined above, crash and name the culprit
        raise ValueError(f"DATA ERROR: Unrecognized plant type '{plant}' found in dataset. Cannot map to cover_type.")

    merged_df["cover_type"] = merged_df["plant_type"].apply(map_to_cover)

    # Prepare well logs: Ensure depths are in millimeters to match the water table depth (gw_00)
    logs = df_well_logs.copy()
    if "start_depth_mm" not in logs.columns:
        logs["start_depth_mm"] = logs["start_depth_cm"] * 10.0
        logs["stop_depth_mm"] = logs["stop_depth_cm"] * 10.0

    return merged_df, logs



def plot_cumulative_et_bar(df: pd.DataFrame, save_dir: str = None, et_col: str = "ET_gw_mm", date_col: str = "date", figsize: tuple = (8, 6)):
    """
    Calculates the daily mean ET for each category (averaging across wells), 
    then sums those daily means to get the cumulative ET, plotting them as individual bar charts.
    Saves each chart separately if save_dir is provided.
    """
    # 1. Define configuration with refined, earth-tone color palettes
    meadow_palette = ["#D1C09F", "#487158"]                           # Muted tan, forest green
    hydro_palette = ["#C77464", "#5F748D", "#89AB8D"]                 # Muted brick red, slate blue, sage
    plant_palette = ["#859B6A", "#DDB73B", "#8C638A", "#A98471"]      # Olive green, mustard, muted purple, rust

    plot_config = [
        {"col": "meadow_id", "title": "Meadow", "palette": meadow_palette},
        {"col": "hydrogeo_zone", "title": "Hydrogeomorphic Zone", "palette": hydro_palette},
        {"col": "plant_type", "title": "Plant Functional Type", "palette": plant_palette}
    ]
    df = well_utils.get_well_categories(df)
    # 2. Ensure the necessary columns exist
    required_columns = [item["col"] for item in plot_config] + [et_col, date_col]
    missing_cols = [col for col in required_columns if col not in df.columns]
    
    if missing_cols:
        raise ValueError(
            f"Missing columns: {missing_cols}. "
            "Make sure the dataframe contains date and category columns."
        )

    sns.set_theme(style="whitegrid")

    # 3. Loop through configuration to create INDIVIDUAL plots
    for config in plot_config:
        col = config["col"]
        title = config["title"]
        
        # Step A: Get the mean ET for the category for each individual day
        daily_mean_df = df.groupby([date_col, col])[et_col].mean().reset_index()
        
        # Step B: Sum those daily means to get the cumulative total for the period
        cumulative_et = daily_mean_df.groupby(col)[et_col].sum().reset_index()

        # Create a new figure for EACH category
        fig, ax = plt.subplots(figsize=figsize)

        # Generate bar plot
        sns.barplot(
            data=cumulative_et, 
            x=col, 
            y=et_col, 
            ax=ax, 
            palette=config["palette"],
            hue=col,
            legend=False
        )
        
        # Place the cumulative amount at the top of each bar
        for container in ax.containers:
            ax.bar_label(container, fmt='%.1f', padding=3, fontweight='bold', color='#333333')

        # Apply formatting
        ax.set_title(f'Cumulative ET by {title}', fontsize=14, fontweight='bold', pad=15)
        ax.set_xlabel(f'{title}', fontsize=12)
        ax.set_ylabel('Cumulative Daily Mean ET (mm)', fontsize=12)
        
        # Ensure x-axis labels are horizontal (rotation=0)
        ax.tick_params(axis='x', rotation=0) 

        # Add line breaks to long plant type labels so horizontal text doesn't overlap
        if col == "plant_type":
            labels = [text.get_text().replace(' ', '\n') for text in ax.get_xticklabels()]
            ax.set_xticklabels(labels)

        # Adjust layout before saving/showing
        plt.tight_layout()

        # 4. Save or display the individual figure
        if save_dir is not None:
            save_path = Path(save_dir)
            save_path.mkdir(parents=True, exist_ok=True) # Ensure the directory exists
            
            # Define the base filename specific to the current category
            base_fname = f"ET_bar_plot_{col}"
            
            # Save as PNG
            fig.savefig(save_path / f"{base_fname}.png", format="png", bbox_inches="tight", dpi=300)
            
            # Save as EPS
            fig.savefig(save_path / f"{base_fname}.eps", format="eps", bbox_inches="tight")
            
            # Close the figure to free up memory
            plt.close(fig)
        else:
            plt.show()


def plot_cumulative_et_box(df: pd.DataFrame, well_col: str = "well_id", save_dir: str = None, et_col: str = "ET_gw_mm", figsize: tuple = (8, 6)):
    """
    Calculates the cumulative ET for each well, then creates box plots
    showing the distribution of those cumulative totals across categories.
    Saves each chart separately if save_dir is provided.
    """
    # 1. Define configuration with refined, earth-tone color palettes
    meadow_palette = ["#D1C09F", "#487158"]                           # Muted tan, forest green
    hydro_palette = ["#C77464", "#5F748D", "#89AB8D"]                 # Muted brick red, slate blue, sage
    plant_palette = ["#859B6A", "#DDB73B", "#8C638A", "#A98471"]      # Olive green, mustard, muted purple, rust

    plot_config = [
        {"col": "meadow_id", "title": "Meadow", "palette": meadow_palette},
        {"col": "hydrogeo_zone", "title": "Hydrogeomorphic Zone", "palette": hydro_palette},
        {"col": "plant_type", "title": "Plant Functional Type", "palette": plant_palette}
    ]
    df = well_utils.get_well_categories(df)
    
    # 2. Ensure the necessary columns exist
    required_columns = [item["col"] for item in plot_config] + [et_col, well_col]
    missing_cols = [col for col in required_columns if col not in df.columns]
    
    if missing_cols:
        raise ValueError(
            f"Missing columns: {missing_cols}. "
            "Make sure the dataframe contains the well identifier and category columns."
        )

    sns.set_theme(style="whitegrid")

    # 3. Loop through configuration to create INDIVIDUAL plots
    for config in plot_config:
        col = config["col"]
        title = config["title"]
        
        # Step A: Get cumulative ET for each individual well
        # We group by the category AND the well to sum the ET over the entire period
        cumulative_et_per_well = df.groupby([col, well_col])[et_col].sum().reset_index()

        # Create a new figure for EACH category
        fig, ax = plt.subplots(figsize=figsize)

        sns.boxplot(
            data=cumulative_et_per_well, 
            x=col, 
            y=et_col, 
            ax=ax, 
            palette=config["palette"],
            hue=col,
            legend=False,
            width=0.6,
            fliersize=5,
            showmeans=True, # Turns on the mean marker
            meanprops={
                "marker": "D", # Diamond shape
                "markerfacecolor": "white", 
                "markeredgecolor": "black",
                "markersize": 6
            }
        )
        
        # Apply formatting
        ax.set_title(f'Distribution of Cumulative ET by {title}', fontsize=14, fontweight='bold', pad=15)
        ax.set_xlabel(f'{title}', fontsize=12)
        ax.set_ylabel('Cumulative ET per Well (mm)', fontsize=12)
        
        # Ensure x-axis labels are horizontal (rotation=0)
        ax.tick_params(axis='x', rotation=0) 

        # Add line breaks to long plant type labels so horizontal text doesn't overlap
        if col == "plant_type":
            labels = [text.get_text().replace(' ', '\n') for text in ax.get_xticklabels()]
            ax.set_xticklabels(labels)

        # Adjust layout before saving/showing
        plt.tight_layout()

        # 4. Save or display the individual figure
        if save_dir is not None:
            save_path = Path(save_dir)
            save_path.mkdir(parents=True, exist_ok=True) # Ensure the directory exists
            
            # Define the base filename specific to the current category
            base_fname = f"ET_boxplot_{col}"
            
            # Save as PNG
            fig.savefig(save_path / f"{base_fname}.png", format="png", bbox_inches="tight", dpi=300)
            
            # Save as EPS
            fig.savefig(save_path / f"{base_fname}.eps", format="eps", bbox_inches="tight")
            
            # Close the figure to free up memory
            plt.close(fig)
        else:
            plt.show()

def calculate_vg_theta(h, theta_r, theta_s, alpha, n):
    """
    Calculates the volumetric water content (theta) at a specific suction head (h) 
    using the Mualem-van Genuchten soil water retention model.
    """
    # If the soil is at or below the water table, it is fully saturated.
    if h <= 0:
        return theta_s
        
    # The m parameter is derived directly from n using the standard Mualem assumption.
    m = 1.0 - (1.0 / n)
    return theta_r + (theta_s - theta_r) / ((1.0 + (alpha * h)**n)**m)

def get_composite_sy_kinematic(wt_depth_cm, well_horizons, vg_lookup, observation_time_days=1.0):
    """
    Numerically integrates the soil column over a fixed control volume to calculate 
    the effective specific yield (Sy) for a 1 cm water table drop. This applies a 
    kinematic drainage correction to account for slow-draining soils based on their 
    saturated hydraulic conductivity (Ks).
    """
    # A water table above the ground surface means open water, which has a specific yield of 0 for soil modeling purposes.
    if wt_depth_cm <= 0:
        return 0.0
        
    # Capillary Check: Determine if a gravel or open hole layer breaks the capillary rise. 
    # Any coarse layer completely above the water table will break the hydraulic connection.
    gravel_above = well_horizons[
        (well_horizons['stop_depth_cm'] < wt_depth_cm) & 
        (well_horizons['soil_texture_code'].isin(['GR', 'HO']))
    ]
    
    # Set the top boundary for integration. If a capillary break exists, we only integrate from the bottom of that break.
    top_integration_boundary = gravel_above['stop_depth_cm'].max() if not gravel_above.empty else 0.0
    
    total_effective_sy = 0.0
    
    # Divide the soil column into 1 cm slices from the top integration boundary down to the newly dropped water table.
    slices = np.arange(top_integration_boundary, wt_depth_cm + 1.0, 1.0)
    
    for z in slices:
        # Identify which soil horizon the current 1 cm slice falls into.
        layer = well_horizons[
            (well_horizons['start_depth_cm'] <= z) & 
            (well_horizons['stop_depth_cm'] > z)
        ]
        if layer.empty:
            continue
            
        texture_code = str(layer.iloc[0]['soil_texture_code']).strip()
        
        # Gravel and holes have a fixed, immediate specific yield and do not follow van Genuchten curves.
        if texture_code in ['GR', 'HO']:
            total_effective_sy += (0.23 / len(slices)) 
            continue
            
        # Ensure the soil texture exists in the van Genuchten lookup table to avoid silent failures.
        if texture_code not in vg_lookup:
            raise KeyError(f"DATA ERROR: Soil code '{texture_code}' not in lookup.")
            
        params = vg_lookup[texture_code]
        
        # Calculate the suction head and resulting moisture content before the 1 cm water table drop.
        h_current = wt_depth_cm - z 
        theta_current = calculate_vg_theta(
            h_current, params['theta_r'], params['theta_s'], params['alpha'], params['n']
        )
        
        # Calculate the suction head and resulting moisture content after the 1 cm water table drop.
        h_dropped = (wt_depth_cm + 1.0) - z
        theta_dropped = calculate_vg_theta(
            h_dropped, params['theta_r'], params['theta_s'], params['alpha'], params['n']
        )
        
        # The theoretical maximum specific yield if the soil is given infinite time to drain completely.
        sy_ultimate = max(0.0, theta_current - theta_dropped)
        
        # Ensure saturated hydraulic conductivity (Ks) exists to scale the drainage time.
        if 'Ks' not in params or pd.isna(params['Ks']):
            raise KeyError(f"DATA ERROR: 'Ks' (Conductivity) is missing for soil texture '{texture_code}' in van_genuchten_lookup.")
        ks_cm_day = params['Ks']
        
        if ks_cm_day > 0 and sy_ultimate > 0:
            # Calculate the characteristic drainage time for this specific 1 cm slice of soil.
            t_c = (sy_ultimate * 1.0) / ks_cm_day 
            
            # Scale the ultimate specific yield based on how much water can physically drain within the 24-hour observation window.
            sy_effective = sy_ultimate * (1.0 - np.exp(-observation_time_days / t_c))
        else:
            sy_effective = 0.0
            
        total_effective_sy += sy_effective
        
    # Ensure the final composite Sy remains bounded between physically possible limits (0 to 1).
    return max(0.0, min(total_effective_sy, 1.0))

# ---- MAIN ---
def main():
   
    # -- I/O
    # load subdaily groundwater input (source data) file
    subdaily_gw_df = pd.read_csv(groundwater_subdaily_filepath,
                                 parse_dates=["DateTime"]
                                 ).rename(columns={"DateTime": "datetime"})   
    
    # Load and calculate cumulative precip per day
    precip_df = load_precip_for_years(weather_subdaily_filepath, 2025)
    daily_precip_df = daily_cumulative_precip(precip_df)
    
    # Load PET and temp data
    PET_df = pd.read_csv(pet_well_data_filepath)
    pet_station_df = pd.read_csv(pet_station_data_filepath)
    weather_df = get_daily_temperature(weather_subdaily_filepath)
    
    
    # Load lookup tables for all ET methods
    duke_df = pd.read_csv(duke_et_data_dir)
    van_genuchten_df = pd.read_csv(van_guch_filepath)
    df_extinction = pd.read_csv(extinction_data_filepath)\
        
    # Load soil data for Sy calcs
    df_soil_sy = pd.read_csv(sy_data_filepath)
    df_soil_log = pd.read_csv(soil_data_filepath)    
    
    # -- CALCS
    # Calculate avg Sy for each well
    calculated_sy_df = average_sy(df_soil_sy, df_soil_log)
    
    # Pre-process gw from subdaily into key daily values
    daily_gw_df = get_daily_gw_levels(subdaily_gw_df)
    print("got gw levels")

    
    # Calculate raw ET for ALL days
    # raw_ET_df = estimate_ET_White_Duke_Sy(daily_gw_df, df_soil_log, duke_df, PET_df, pet_station_df, 2025)
    raw_ET_df = estimate_ET_White_VG_Smoothed(daily_gw_df, df_soil_log, 
                                              van_genuchten_df, PET_df, 
                                              pet_station_df, 2025)

    #raw_ET_df = estimate_ET_Shaw(daily_gw_df, PET_df, df_soil_log, df_extinction, pet_station_df)
    #raw_ET_df = apply_et_capillary_limits(raw_ET_df, PET_df, df_soil_log, df_extinction, pet_station_df, pet_col="PET_mm_day")
    
    # -- FILTER ET ESTIMATES
    # Filter days with precipitation plus a recovery buffer
    ET_no_rain = filter_ET_by_precip(raw_ET_df, daily_precip_df, 
                                     threshold_mm=1.0, recovery_days=3)

    # Filter days where the well went dry 
    #    (dropping data when water is within 10cm of bottom)
    daily_ET_df = filter_ET_by_well_depth(ET_no_rain , daily_gw_df, 
                                          df_soil_log, buffer_mm=100.0)
    
    print(daily_ET_df['date'].min(), "to", daily_ET_df['date'].max())

    #plot_cumulative_et_box(daily_ET_df, save_dir=save_plots_dir)
    # Plot
    # plot_ET_cat(
    #     ET_df=daily_ET_df, 
    #     lai_df = pd.read_csv(lai_data_filepath),
    #     pet_df=pet_station_df,
    #     year=2021, 
    #     end_date=None,
    #     save_dir=save_plots_dir
    # )
    
    #print("ET category plots with PET generated successfully!")
    #plot_cumulative_et_box(daily_ET_df, "well_id", save_plots_dir)
    plot_ET_prop_bar(daily_ET_df, 
            PET_df,
            pet_station_df,
            subdaily_gw_df,
            "White_VG", 
            2025,  
            df_soil_log, 
            weather_df,
            save_dir=save_plots_dir)
    print("ET plotted for White average Sy")

    # Save to csv? Do we want a new one or write over the one from above?
    # Then plot this new estimate, use an appropriate name, check if the 2nd param affects filename and not just the title
    print("COMPLETE!!")
   

# --- END FUNCTIONS

if __name__ == "__main__":
    main()
