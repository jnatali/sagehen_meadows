#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct  3 12:45:42 2024

##########  GROUNDWATER FIELD DATA PROCESSING SCRIPT  ##########  

This module processes manual groundwater well readings from a water level
meter to determine the groundwater level relative to the ground surface,
based on measurements of the distance between the welltop to the ground.

This code is under development and follows basic procedural programming,
leverages Pandas DataFrames and csv files with well-defined column names.

Major Functions:
- VALIDATES well_id's, manual field data file has match in unique_id list
- VALIDATES welltop_to_ground measurement exists for each well
- DETERMINES groundwater level
- SAVES groundwater level calcs in groundwater_biweekly_FULL.csv
- ADDS a daily? 8am transducer reading if flagged (transducer_binary=True)
- PLOTS groundwater levels

Requires 4 data files:
1. Unique well ids: 'well_unique_id.txt' -- TODO: REMOVE, see well_utils 
2. Well Dimensions: 'well_dimensions.csv'
3. RAW manual groundwater data (in cm) for all years: 
                                                'groundwater_biweekly_RAW.csv'
4. Well meter offsets (in cm): 'well_meter_offsets.csv'

TODOs documented in github repo issue tracking.

RECENT UPDATES:
    01/30/2026 JN added import from well_utils 
                to leverage process_well_ids() function;
                tested on 2025 data. Looks good. 
                Still need to use on 2018-24 data to rename wells.

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
import re
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from well_utils import process_well_ids


# --- USE PRESSURE TRANSDUCER DATA? ---
transducer_binary = False

if transducer_binary:
    transducer_data_dir = '../../data/field_observations/groundwater/subdaily_loggers/relative_to_ground/'

# --- INITIALIZE FILE VARIABLES ---

# Setup directory (dir) structure and file names based on structure in github

# ## Directories and input filenames for ALL data
## JN 01/30/2026 NOTE: Have not yet run 2018-24 data with well renaming
# groundwater_data_dir = '../../data/field_observations/groundwater/biweekly_manual/'
# groundwater_plot_dir = '../../data/field_observations/groundwater/plots/biweekly_manual/'
# groundwater_rawdata_filename = groundwater_data_dir + 'groundwater_biweekly_RAW.csv'
# 2025 data:
# groundwater_rawdata_filename = groundwater_data_dir + 'groundwater_manual_2025_RAW.csv'

# # Output filenames for 2018-2024 data
# groundwater_fulldata_filename = groundwater_data_dir + 'groundwater_biweekly_FULL.csv'
# groundwater_plot_filename = groundwater_plot_dir + 'groundwater_biweekly_2018-2024.pdf'

# Output filenames for 2025 data
#groundwater_fulldata_filename = groundwater_data_dir + 'groundwater_manual_2025_FULL.csv'

# Directories and input filenames for ALL data
groundwater_data_dir = '../../data/field_observations/groundwater/manual/'
groundwater_raw_data_dir = groundwater_data_dir + 'RAW/'

# Output filenames for ALL data
groundwater_output_filename = groundwater_data_dir + 'PROCESSED/groundwater_manual.csv'
groundwater_summary_filename = groundwater_data_dir + 'PROCESSED/groundwater_manual_summary.csv'
groundwater_plot_dir = '../../results/plots/groundwater/manual/'
groundwater_plot_filename = groundwater_plot_dir + 'groundwater_manual_plots.pdf'

# Validation/Correction filenames
well_unique_id_filename = groundwater_data_dir + '../well_unique_id.txt'
well_dimension_filename = groundwater_data_dir + '../well_dimensions.csv'
meter_offset_filename = groundwater_data_dir + '../well_meter_offsets.csv'


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
 
def load_groundwater_data(groundwater_raw_data_dir) -> pd.DataFrame:
    """
    Load groundwater data from a directory. 
    This will load data for all years represented in the directory.
    Filenames in the directory must follow the convention:
        'groundwater_manual_YYYY_RAW.csv'
    
    See required_columns variable for the csv's column naming convention.

    Parameters:
    String that represents the file path for a data directory with raw
    manual data entries.

    Returns:
    DataFrame that preserves column structure from the .csv
    Concatenates all data from all years with a welltop_to_water_cm entry
        for each unique well_id + timestamp combo
    """
    data_dir = Path(groundwater_raw_data_dir)

    if not data_dir.exists():
        raise FileNotFoundError(f"Directory not found: {data_dir}")
    
    # Fetch filenames that fit naming convention
    pattern = re.compile(r"groundwater_manual_(\d{4})_RAW\.csv")
    
    files = []
    for f in data_dir.iterdir():
        match = pattern.fullmatch(f.name)
        if match:
            files.append((f, int(match.group(1))))
    
    if not files:
        raise ValueError("No files matching 'groundwater_manual_YYYY_RAW.csv' found.")
    
    dfs = []
    
    required_columns = {
        "well_id",
        "timestamp",
        "welltop_to_water_cm",
        "water_binary",
        "meter_id",
        "soil moisture",
        "notes",
    }
    
    # Loop through files, read in csv, average welltop_to_water_cm if needed
    for file_path, year in sorted(files, key=lambda x: x[1]):

        df = pd.read_csv(file_path)

        # Validate csv column names
        missing = required_columns - set(df.columns)
        if missing:
            raise ValueError(
                f"{file_path.name} missing required columns: {missing}"
            )

        # Parse timestamp
        df["timestamp"] = pd.to_datetime(
            df["timestamp"],
            format="mixed",
            errors="raise"
        )

        df["year"] = year

        # Average duplicate measurements per well_id + timestamp
        grouped = (
            df
            .groupby(["well_id", "timestamp"], as_index=False)
            .agg({
                "welltop_to_water_cm": "mean",
                "water_binary": "first",
                "meter_id": "first",
                "soil moisture": "first",
                "notes": "first",
                "year": "first"
            })
        )

        dfs.append(grouped)

    combined = pd.concat(dfs, ignore_index=True)
    
    # Report summary of loaded files
    print(f"Loaded {len(files)} years of RAW groundwater data.")
    print(f"Total rows after aggregation: {len(combined)}")
    print(f"Wells: {combined['well_id'].nunique()}")
    
    return combined


# def validate_well_id(well_unique_id, groundwater_data) -> bool:
#     """
#     Check that all well_id's in gw_rawdata and well_dimension are
#     found in well_unique_id; if not, print in a WARNING and save in a CSV.

#     Parameters:
#     well_unique_id (dataframe): a list of all the unique well identifiers
#     groundwater_data (dataframe): groundwater well reading entries; each
#                                   entry uniquely identified by well_id and 
#                                   timestamp

#     Returns:
#     validated (binary): true if no issues, false if not valid
#     """
    
#     # TODO: code this function, for now assume OK and return True
#     print('WARNING: Did not validate well id, function not yet defined.')
#     return True

# def validate_well_dimension(well_unique_id, well_dimension) -> bool:  
#     """
#     Check that every well_id in gw_rawdata has a matching welltop_to_ground;
#     if not, print in a WARNING and save well_id and date in a CSV.

#     Parameters:
#     well_unique_id (pd.DataFrame()): a list of all the unique well identifiers
#     groundwater_dimension (pd.DataFrame()): groundwater dimensional characteristics
#                                        per well_id

#     Returns:
#     validated (binary): true if no issues, false if not valid
#     """
    
#     # TODO: code this function, for now assume OK and return True
#     print('WARNING: Did not validate well dimension, function not yet defined.')
#     return True

def validate_groundwater_depth(gw_well_df) -> pd.DataFrame:
    """
    Validate that if ground_to_water_cm is populated,
    water_binary must be True 
    and ground_to_water_cm must be <= well_depth_cm.
        
    Returns
    -------
    pd.DataFrame
        Subset of rows that violate rules.
        Empty DataFrame if no violations found.
    """
    depth_buffer_cm = 2 # allow groundwater to be within 2 cm of well depth
    merged = gw_well_df.copy()
    
    # ---- VALIDATE Rule #1: Water flag consistency
    water_conflict_mask = (
        merged["ground_to_water_cm"].notna()
        & (merged["water_binary"] != True)
        )

    # ---- VALIDATE Rule #2: Must not exceed well depth
    depth_violation_mask = (
        merged["ground_to_water_cm"].notna()
        & merged["well_depth_cm"].notna()
        & (merged["ground_to_water_cm"] > (merged["well_depth_cm"] + depth_buffer_cm))
        )
    
    # Combine masks
    any_violation = water_conflict_mask | depth_violation_mask
    
    # Create dataframe of all violations
    violations = merged.loc[any_violation].copy()
    
    if violations.empty:
        return violations
    
    # if not violations.empty:
    #     raise ValueError(
    #         f"{len(violations)} groundwater validation errors detected."
    #     )

    # Label violation types
    violations["water_flag"] = water_conflict_mask[any_violation].values
    violations["exceeds_depth"] = depth_violation_mask[any_violation].values
    
    # ---- RULE VIOLATION Reporting
    print("\nGROUNDWATER VALIDATION WARNINGS\n")

    if water_conflict_mask.any():
        print(f"Water flag violations: {water_conflict_mask.sum()}")
        print(
            violations.loc[water_conflict_mask,
                   ["well_id", "timestamp", "ground_to_water_cm"]]
            .sort_values(["well_id", "timestamp"])
            .to_string(index=False)
        )
        print()

    if depth_violation_mask.any():
        print(f"Depth exceedance violations: {depth_violation_mask.sum()}")
        print(
            violations.loc[depth_violation_mask,
                   ["well_id", "timestamp",
                    "ground_to_water_cm", "well_depth_cm"]]
            .sort_values(["well_id", "timestamp"])
            .to_string(index=False)
        )
        print()

    print(f"Total unique violating rows: {len(violations)}\n")
    
    return violations
     
def correct_groundwater_depth(gw_df, bad_df) -> pd.DataFrame:
    """
    Apply correction policy to groundwater data.
    
    Current policy:
        Remove records where water_binary is False
        but ground_to_water_cm is populated.
    """
    df = gw_df.copy()

    if bad_df.empty:
        return df

    # Identify water-flag violations only
    water_flag_violations = bad_df[
        bad_df["water_flag"] == True
    ]

    if water_flag_violations.empty:
        return df

    # Build removal mask
    removal_index = water_flag_violations.index

    print(f"GROUNDATER CORRECTIONS: Removing {len(removal_index)} water flag violations.")

    corrected_df = df.drop(index=removal_index).copy()

    return corrected_df
    
# def calculate_from_ground(row, well_dimension):
        
#     # get well_dimension row(s) for the groundwater well_id
#     well_dimension_filtered = well_dimension[
#         well_dimension["well_id"] == row["well_id"]]
    
#     well_dimension_filtered = well_dimension_filtered[
#         well_dimension_filtered["valid"] == True]
    
#     # filter and sort well_dimension row(s) by matching groudwater date
#     well_dimension_filtered = well_dimension_filtered[
#         well_dimension_filtered["effective_timestamp"] <= row["timestamp"]].sort_values(by="effective_timestamp")
    
#     if well_dimension_filtered.empty:
#         print("WARNING: No well height for %s on %s" % 
#             (row["well_id"],row["timestamp"]))
#         return None
#     else:
#         if row["well_id"] in ["KEF-XE3S", "KFF-XE8S"]:
#             print("CALCULATING water depth for %s on %s with %s well dimension entry" %
#               (row["well_id"],row["timestamp"],well_dimension_filtered.iloc[-1].effective_timestamp) )
        
#         if row["well_id"] in ["KW"]:
#             print("KW CASE TO CALCULATE water depth for %s on %s with %s well dimension entry" %
#                   (row["well_id"],row["timestamp"],well_dimension_filtered.iloc[-1].effective_timestamp) )
        
#         well_height = well_dimension_filtered.iloc[-1].welltop_to_ground_cm
#         ground_to_water_cm = row["welltop_to_water_cm"] - well_height
  
#         # For each reading, add the appropriate meter offset (based on
#         #    gw_rawdata.meter_id) to adjust ground_to_water_cm.
#         #
#         # NOTE: For now, add 3cm offset for any meter except solinst or nm (no meter)
#         # TODO: Examine range of meter_offset, did I consistently measure from 
#         #       the top or bottom of the sensor?! Re-test the meters if possible.
#         if row["meter_id"] not in ['nm','solinst']:
#             ground_to_water_cm = ground_to_water_cm + 3
        
#         return ground_to_water_cm

    
def get_groundwater_level(gw_df, dimension_df) -> pd.DataFrame():
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
    
    groundwater_data = gw_df.copy()
    well_dimension = dimension_df[
        ["well_id",
         "valid",
        "effective_timestamp",
        "welltop_to_ground_cm",
        "well_depth_cm"]
        ].copy()
    
    # # Setup groundwater_data for new column value
    # groundwater_data["ground_to_water_cm"] = np.NaN
    
    # Setup for selection by date
    groundwater_data["timestamp"] = pd.to_datetime(groundwater_data["timestamp"])

    well_dimension["effective_timestamp"] = pd.to_datetime(
        well_dimension["effective_timestamp"])
    
    # Only use valid dimension records
    well_dimension = well_dimension[well_dimension["valid"] == True]
    
    # Sort for merge_asof
    groundwater_data = groundwater_data.sort_values(["timestamp", "well_id"])
    well_dimension = well_dimension.sort_values(
        ["effective_timestamp", "well_id"])
    
    # Time-aware join
    merged = pd.merge_asof(
        groundwater_data,
        well_dimension,
        left_on="timestamp",
        right_on="effective_timestamp",
        by="well_id",
        direction="backward",
        allow_exact_matches=True
    )
    
    # Warn if dimension missing
    missing_dim = merged["welltop_to_ground_cm"].isna()
    if missing_dim.any():
        print(f"WARNING: {missing_dim.sum()} records missing well dimension.")

    # Vectorized groundwater calculation
    merged["ground_to_water_cm"] = (
        merged["welltop_to_water_cm"]
        - merged["welltop_to_ground_cm"])
    
    # Apply meter offset (vectorized)
    offset_mask = ~merged["meter_id"].isin(["nm", "solinst"])
    merged.loc[offset_mask, "ground_to_water_cm"] += 3
        
    violations = validate_groundwater_depth(merged)
    corrected = correct_groundwater_depth(merged, violations)
    
    return corrected

def report_groundwater_summary(gw_df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate annual groundwater summary statistics.

    Parameters
    ----------
    gw_df : pd.DataFrame
        Must contain:
            - well_id
            - timestamp (datetime)
            - ground_to_water_cm

    Returns
    -------
    pd.DataFrame
        Annual summary statistics table.
    """

    df = gw_df.copy()

    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    df["year"] = df["timestamp"].dt.year

    summary_rows = []

    for year, year_df in df.groupby("year"):

        valid = year_df["ground_to_water_cm"].notna()
        valid_df = year_df.loc[valid]

        wells_per_year = valid_df["well_id"].nunique()
        total_measurements = len(valid_df)

        start_date = valid_df["timestamp"].min()
        end_date = valid_df["timestamp"].max()

        # ---- Depth diagnostics ----
        mean_depth = valid_df["ground_to_water_cm"].mean()
        std_depth = valid_df["ground_to_water_cm"].std()
        median_depth = valid_df["ground_to_water_cm"].median()
        min_depth = valid_df["ground_to_water_cm"].min()
        max_depth = valid_df["ground_to_water_cm"].max()
        
        # ---- Time-of-day diagnostics ----
        hours = valid_df["timestamp"].dt.hour
        
        mean_hour = hours.mean()
        median_hour = hours.median()
        earliest_hour = hours.min()
        latest_hour = hours.max()
        
        n_before_10 = (hours < 10).sum()
        n_after_10 = (hours >= 10).sum()
        n_after_11 = (hours >= 11).sum()
        n_after_12 = (hours >= 12).sum()
        
        pct_before_10 = n_before_10 / total_measurements * 100
        pct_after_10 = n_after_10 / total_measurements * 100
        pct_after_11 = n_after_11 / total_measurements * 100
        pct_after_12 = n_after_12 / total_measurements * 100

        # ---- Completeness
        counts_per_well = (
            valid_df.groupby("well_id")
            .size()
        )

        max_measurements = counts_per_well.max()
        wells_at_max = (counts_per_well == max_measurements).sum()
        pct_wells_at_max = wells_at_max / wells_per_year * 100

        wells_single_measurement = (counts_per_well == 1).sum()

        summary_rows.append({
            "year": year,
            "n_wells": wells_per_year,
            "n_measurements": total_measurements,
            "start_date": start_date,
            "end_date": end_date,
            "mean_hour": mean_hour,
            "mean_ground_to_water_cm": mean_depth,
            "std_ground_to_water_cm": std_depth,
            "median_ground_to_water_cm": median_depth,
            "min_ground_to_water_cm": min_depth,
            "max_ground_to_water_cm": max_depth,
            "max_measurements_per_well": max_measurements,
            "wells_with_max_measurements": wells_at_max,
            "pct_wells_with_max_measurements": pct_wells_at_max,
            "wells_with_single_measurement": wells_single_measurement,
            "n_before_10am": n_before_10,
            "pct_before_10am": pct_before_10,
            "n_after_10am": n_after_10,
            "pct_after_10am": pct_after_10,
            "n_after_11am": n_after_11,
            "pct_after_11am": pct_after_11,
            "n_after_noon": n_after_12,
            "pct_after_noon": pct_after_12,
            "median_hour": median_hour,
            "earliest_hour": earliest_hour,
            "latest_hour": latest_hour
        })

    summary_df = pd.DataFrame(summary_rows).sort_values("year")

    # -------- Print structured report --------
    print("\nGROUNDWATER ANNUAL SUMMARY\n")

    for _, row in summary_df.iterrows():
        print(f"Year: {int(row.year)}")
        print(f"  Wells with data: {row.n_wells}")
        print(f"  Total measurements: {row.n_measurements}")
        print(f"  Date range: {row.start_date.date()} → {row.end_date.date()}")
        print(f"  Mean ± SD depth (cm): {row.mean_ground_to_water_cm:.2f} ± {row.std_ground_to_water_cm:.2f}")
        print(f"  Median depth (cm): {row.median_ground_to_water_cm:.2f}")
        print(f"  Min / Max depth (cm): {row.min_ground_to_water_cm:.2f} / {row.max_ground_to_water_cm:.2f}")
        print(f"  Max measurements per well: {row.max_measurements_per_well}")
        print(f"  Wells at max sampling effort: {row.wells_with_max_measurements} "
              f"({row.pct_wells_with_max_measurements:.1f}%)")
        print(f"  Wells with single measurement: {row.wells_with_single_measurement}")
        print(f"  Measurements before 10:00: {row.n_before_10am} "
              f"({row.pct_before_10am:.1f}%)")
        print(f"  Measurements after 10:00: {row.n_after_10am} "
              f"({row.pct_after_10am:.1f}%)")
        print(f"  Measurements after 11:00: {row.n_after_11am} "
              f"({row.pct_after_11am:.1f}%)")
        print(f"  Measurements after 12:00: {row.n_after_noon} "
              f"({row.pct_after_noon:.1f}%)")
        print(f"  Mean hour: {row.mean_hour:.1f}")
        print(f"  Median hour: int{row.median_hour}")
        print(f"  Earliest hour: {row.earliest_hour}")
        print(f"  Latest hour: {row.latest_hour}")
        print()

    return summary_df

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
    groundwater_data = groundwater_data.rename(columns={"soil moisture": "soil_moisture"})
    groundwater_data[['well_id',
                      'timestamp',
                      'ground_to_water_cm',
                      'water_binary',
                      'soil_moisture',
                      'notes']].to_csv(groundwater_output_filename, index=False)
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
    cmap = plt.get_cmap("viridis")
    
    # Generate evenly spaced colors based on year length
    plot_colors = cmap(np.linspace(0, 1, len(years)))
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


# --- MAIN ---
# Define a main() function to allow import of functions
# without executing the full script.

def main():
    
    # Load input (source data) files    
    groundwater_data = load_groundwater_data(groundwater_raw_data_dir)
    well_dimension = pd.read_csv(well_dimension_filename)

    # ---- PROCESS well_id's and well_dimension.welltop_to_ground
    # 
    #    Check that all well_id's from gw raw data and well_dimension are
    #    found in well_unique_id, then correct well_ids.
    
    groundwater_data = process_well_ids(groundwater_data)
    well_dimension = process_well_ids(well_dimension)
    print('Processed well_ids')
           
    # ---- DETERMINE welltop_to_ground_cm
    groundwater_data = get_groundwater_level(groundwater_data, 
                                                   well_dimension)    
    
    # ---- PLOT data
    plot_groundwater_per_well(groundwater_data)
    
    # ---- REPORT data summary
    report_groundwater_summary(groundwater_data).to_csv(groundwater_summary_filename)
    
    # ---- SAVE all manual groundwater data following conventions
    save_groundwater(groundwater_data)

    # --- DO THIS IN ANOTHER SCRIPT!! ADD transducer data ---
    # print('# OF UNIQUE WELLS: %s' % len(groundwater_data['well_id'].unique()))
    # if transducer_binary:
    #     transducer_data = get_transducer_data()
    #     print('# of TRANSDUCER ENTRIES: %s' % len(transducer_data))
    #     print('# of ENTRIES: %s' % len(groundwater_data))
    #     groundwater_data = pd.concat([groundwater_data, transducer_data], ignore_index=True)
    #     print('# of ENTRIES AFTER MERGE: %s' % len(groundwater_data))
    #     save_groundwater(groundwater_data)
    

if __name__ == "__main__":
    main()

