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

Sy_data_dir = PROJECT_ROOT / 'data/field_observations/soil/'
Sy_data_filepath = Sy_data_dir / 'Sy_wa.csv'

#save_dir = PROJECT_ROOT / 'results/plots/ET/White_avg'
save_dir = PROJECT_ROOT / 'data/field_observations/soil/'
load_dir = PROJECT_ROOT / 'data/field_observations/soil/Cleaned_wells_complete.csv'

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

    assert "ground_to_water_m" in gw_df.columns
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
    

def estimate_ET_White_constant_Sy(daily_df) -> pd.DataFrame:
    """
    Calculate ET in cm/day for each well in subdaily groundwater logger data.

    Parameters: daily groundwater dataframe with gw levels at key times
    
    Returns:
    populated "ET estimate" dataframe
    """
    METHOD_ID = "White_constantSy"
    
    df = daily_df.copy()
    
    # Calculate R, overnight recharge rate in cm/day
    df["R_cm"] = 24.0 * (df["gw_00"] - df["gw_04"]) / 4.0
    
    # Calculate s, daily storage change (cm)
    df["S_cm"] = df["gw_00"] - df["gw_24"]
    
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

def estimate_ET_White_wavg_Sy(daily_df, filepath: str) -> pd.DataFrame:
    """
    Calculate ET in cm/day for each well in subdaily groundwater logger data
    using White (1932) method and a specific yield for each well that's a weighted
    average based on soil profile field data and Sy* estimates from 
    Loheide et al (2008) <to verify> and <who else?>

    Parameters: daily groundwater dataframe with gw levels at key times
    
    Returns:
    populated "ET estimate" dataframe
    """
    METHOD_ID = "White_wavg"
    
    df = daily_df.copy()
    
    # Calculate R, overnight recharge rate in cm/day
    df["R_cm"] = 24.0 * (df["gw_00"] - df["gw_04"]) / 4.0
    
    # Calculate s, daily storage change (cm)
    df["S_cm"] = df["gw_00"] - df["gw_24"]
    
    # Set constants for this method
    df["method_id"] = METHOD_ID

    #Load Sy data
    sy_df = update_wells_no_dt(filepath)

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
            "method_id",
        ]
    ].dropna()
  
def plot_ET(
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
        
        # TODO: check. why call this 2x?
        ax1.plot(
            well_df["date"],
            well_df["ET_gw_cm"],
        )
    
       # ---- ET line ----
        ax1.plot(
            well_df["date"],
            well_df["ET_gw_cm"],
            linewidth=1.0
        )
        ax1.set_ylabel("ET (cm)")
        ax1.set_xlabel("Date")

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
        
        #ax1.axhline(0, linewidth=0.8)
        fig.autofmt_xdate()
        
        if save_dir is not None:
            fname = f"ET_{method_id}_{well_id}_{'_'.join(map(str, years))}.eps"
            fig.savefig(save_dir / fname, format="eps", bbox_inches="tight")
            plt.close(fig)
        else:
            plt.show()
    
def plot_gw_ET_overlay(gw_df, et_df, year):
    # See DRAFT in chatgpt here: https://chatgpt.com/s/t_6988e9118c34819181d813da8c21634b
    
    return

def update_wells_no_dt(filepath: str) -> pd.DataFrame:
    """
    Validates files with well_ids and NO datetime info 
    Returns a valided dataframe with corrected well_ids.

    Parameters
    ----------
    filepath : str
        Path to CSV file with well_ids and no datetime info
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
   
   new_df = update_wells_no_dt(load_dir)
   new_df.to_csv(save_dir / "cleaned_wells_COMPLETE.csv", index=False)
   print("WELL IDS CORRECTED AND VALIDATED, SAVED TO CSV")
"""
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
    
    # Calculate daily ET using different methods and Plot
    ## Start with White using same Sy for all wells
    #daily_ET_df = estimate_ET_White_constant_Sy(daily_gw_df)
    #daily_ET_df.to_csv(ET_calc_filepath, index=False)
    #print("calculated and saved ET")
    
    ## Add White using weight average Sy for each well
    daily_ET_df = estimate_ET_White_wavg_Sy(daily_gw_df, Sy_data_filepath)
    plot_ET(daily_ET_df, 
            "White_wavg", 
            2025, 
            precip_df=daily_precip_df, 
            save_dir=save_dir)
    print("PRECIP + ET plotted for White constant Sy")

   
    # Save to csv? Do we want a new one or write over the one from above?
    # Then plot this new estimate, use an appropriate name, check if the 2nd param affects filename and not just the title
    print("COMPLETE!!")
    """

# --- END FUNCTIONS

if __name__ == "__main__":
    main()
