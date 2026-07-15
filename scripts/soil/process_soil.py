#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
##########  FIELD SOIL SURVEY DATA PROCESSING SCRIPT  ##########  

This module validates and processes soil profile data for groundwater
wells in Sagehen meadows. Transforms RAW data into "clean" 
data ready for plotting.

This code is under development and follows basic procedural programming,
leverages Pandas DataFrames and csv files with well-defined column names.

NOTE: Assumes that if 'G' is in 'sub-class' column value,
      the content is about gravels. 

Requires X data files:
1. RAW soil profile data

TODOs documented in github repo issue tracking.
- Can we safely change check for 'G' to 'GR' to be more specific?

RECENT UPDATES:
    06/02/2026 JN added a "clean" function to prep data for plotting
                via the R script
    06/01/2026 JN added comments and documentation;
               JN added import from well_utils 
                to leverage process_well_ids() function;

"""
# --- DUNDERS ---
__author__ = 'Kara-Leah Smittle, Jennifer Natali'
__copyright__ = 'Copyright (C) 2026 Riverlab, UC Berkeley'
__license__ = 'NOT Licensed, Private Code under Development, DO NOT DISTRIBUTE'
__maintainer__ = 'Jennifer Natali'
__email__ = 'jennifer.natali@berkeley.edu'
__status__ = 'Development'



# ---- IMPORTS ---
import pandas as pd
#import matplotlib.pyplot as plt
#import seaborn as sns
#import numpy as np
import os
#import math
from pathlib import Path
import sys
import re
import warnings

# Initialize PROJECT_ROOT to allow local project module import
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))
from scripts.groundwater.well_utils import process_well_ids

# ---- INITIALIZE FILE VARIABLES ---

# Define Source File
OUTPUT_DIR = PROJECT_ROOT /  'data/field_observations/soil/RAW'
OUTPUT_FILE_PATTERN_RENAMED = OUTPUT_DIR / 'soil_survey_RENAMED.csv'
OUTPUT_FILE_PATTERN_CLEANED = OUTPUT_DIR / 'soil_survey_PROCESSED.csv'

# Define Source File
SOURCE_DIR = PROJECT_ROOT / 'data/field_observations/soil/RAW'
SOURCE_FILE_PATTERN = SOURCE_DIR / 'soil_survey_RAW.csv'

word_to_code_mapping = {
    'coarse sand': 'COS',
    'sand': 'S',
    'fine sand': 'FS',
    'very fine sand': 'VFS',
    'loamy coarse sand': 'LCOS',
    'loamy sand': 'LS',
    'loamy fine sand': 'LFS',
    'loamy very fine sand': 'LVFS',
    'coarse sandy loam': 'COSL',
    'sandy loam': 'SL',
    'fine sandy loam': 'FSL',
    'very fine sandy loam': 'VFSL',
    'loam': 'L',
    'silt loam': 'SIL',
    'silt': 'SI',
    'sandy clay loam': 'SCL',
    'clay loam': 'CL',
    'silty clay loam': 'SICL',
    'sandy clay': 'SC',
    'sandy clay to silty clay': 'SC',
    'silty clay': 'SIC',
    'clay silt': 'SIC',
    'clay': 'C',
    'ho': 'HO',
    'gr': 'GR',
    'fgr': 'GR',
    'vcb': 'GR',
    'mgr': 'GR',
    'xgr': 'GR',
    'xst': 'GR',
}

gravel_size_map = {
    #left end exclusive
    # General, Very, and Extremely Gravelly (>2 - 76 mm)
    'GR': (5, 20), 'VGR': (5, 20), 'XGR': (5, 20),
    'GRV': (5, 20), 'GRX': (5, 20),
    
    # Fine Gravelly (>2 - 5 mm)
    'FGR': (2, 5), 'GRF': (2, 5),
    
    # Medium Gravelly (>5 - 20 mm)
    'MGR': (5, 20), 'GRM': (5, 20),
    
    # Coarse Gravelly (>20 - 76 mm)
    'CGR': (20, 76), 'GRC': (20, 76)
}

gravel_amount_map = {
    # These are all right end exclusive
    # Standard Gravelly (15->35%)
    'GR': (0.15, 0.35), 'FGR': (0.15, 0.35), 'MGR': (0.15, 0.35), 
    'CGR': (0.15, 0.35), 'GRF': (0.15, 0.35), 'GRM': (0.15, 0.35), 
    'GRC': (0.15, 0.35),
    
    # Very Gravelly (35->60%)
    'VGR': (0.35, 0.60), 'GRV': (0.35, 0.60),
    
    # Extremely Gravelly (60->90%)
    'XGR': (0.60, 0.90), 'GRX': (0.60, 0.90)
}

# ---- FUNCTIONS ---

def populate_depths_cm(df):
    """
    Fill missing depth values in cm from inch columns.

    Existing cm values are preserved.
    """

    df = df.copy()

    depth_pairs = [
        ("start depth (cm)", "start depth (in)"),
        ("stop depth (cm)", "stop depth (in)")
    ]

    for cm_col, in_col in depth_pairs:

        if cm_col not in df.columns:
            raise ValueError(f"Missing required column: {cm_col}")

        if in_col not in df.columns:
            raise ValueError(f"Missing required column: {in_col}")

        df[cm_col] = pd.to_numeric(df[cm_col], errors="coerce")
        inches = pd.to_numeric(df[in_col], errors="coerce")

        # Fill missing cm values from inches
        missing_cm = df[cm_col].isna() & inches.notna()
        df.loc[missing_cm, cm_col] = inches.loc[missing_cm] * 2.54

        # Warn about rows where neither value exists
        missing_both = df[cm_col].isna() & inches.isna()

        if missing_both.any():
            warnings.warn(
                f"{missing_both.sum()} rows are missing both "
                f"'{cm_col}' and '{in_col}'."
            )

    return df

# Convert gravel amount values
def parse_gravel_amount(x):
    if pd.isna(x):
        return x

    # If already numeric, keep it
    if isinstance(x, (int, float)):
        return x

    x = str(x).strip()

    # Match ranges like "(0.15,0.35)" or "(0.15, 0.35)"
    match = re.match(r'^\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\)$', x)
    if match:
        return float(match.group(2))  # max value of the range

    # Otherwise treat as a single number
    try:
        return float(x)
    except ValueError:
        return x  # leave unexpected values unchanged

#Fill in 
def extract_gravel_info(subclass_str):
    """
    Checks for 'GR' and extracts info about gravel size categories

    Parameters: 
    
    Returns:
    """    
    # Return empty values if the row is empty (NaN)
    if pd.isna(subclass_str):
        return pd.Series([None, 0])
    
    # Split by comma in case there are still multiple items 
    words = [word.strip().upper() for word in subclass_str.split(',')]
    
    # Check each word to see if it contains 'G' and exists in our mapping
    for word in words:
        if 'GR' in word and word in gravel_size_map:
            # If found, return both the size and the amount
            return pd.Series([gravel_size_map[word], gravel_amount_map[word]])
            
    # Return empty if no gravel codes are found
    return pd.Series([None, 0])

def merge_identical_rows(df_clean):
    """
    - Given a df with columns for well_id, date, start_depth_cm, stop_depth_cm,
      and any other characterisics (as column names), 
      checks if the soil characteristic values are 
      the same for adjacent layers for given well_id and date (of the 
      measured soil profile), then merges
      them and resets the start and stop depth appropriately.
      
      e.g. row1 for a well_id and date has a stop_depth_cm of 70,
           and row 2 (same well_id and date) has a start_depth_cm of 70
           and otherwise identical values for other columns, then
           assign row1's stop_depth_cm to the value of row2's stop_depth_cm. 
    
    Parameters: df with columns for well_id, date, start_depth_cm, 
        stop_depth_cm,
        and any other characterisics (columns)
    
    Returns: "clean" soil df, ready for plotting with profile layers merged

    """    
    characteristic_cols = [
        col for col in df_clean.columns
        if col not in ("well_id", "date", "start_depth_cm", "stop_depth_cm")
        ]

    group_keys = ["well_id", "date"]
    
    df_sorted = df_clean.sort_values(
        group_keys + ["start_depth_cm"]
        ).reset_index(drop=True)
    
    merged_rows = []

    for _, group in df_sorted.groupby(group_keys, sort=False):
        rows = group.to_dict("records")
        current = rows[0].copy()

        for next_row in rows[1:]:
            depths_adjacent = current["stop_depth_cm"] == next_row[
                                                            "start_depth_cm"]
            
            chars_identical = all(
                (current[col] == next_row[col])
                or (pd.isna(current[col]) and pd.isna(next_row[col]))
                for col in characteristic_cols)

            if depths_adjacent and chars_identical:
                current["stop_depth_cm"] = next_row["stop_depth_cm"]
            else:
                merged_rows.append(current)
                current = next_row.copy()

        merged_rows.append(current)

    return pd.DataFrame(merged_rows, 
                        columns=df_clean.columns).reset_index(drop=True)

def clean_for_plotting(df_valid):
    """
    - Filters and renames required columns for plotting: start and stop depth, 
        texture, gravel amount in percent
    - Standardizes values for soil texture and gravel %age
    - Merges identical rows
    
    Parameters: full pandas dataframe of raw soils data
    
    Returns: nothing, but outputs two files
        1. a validated .csv with raw data but renamed wells and 
            translated gravel size, gravel percentages
        2. a cleaned .csv with limited columns and standardized values
    """    
    df = df_valid.copy()
    
    df["gravel_amount_percent"] = df["gravel amount"].apply(parse_gravel_amount)

    #create a mask that check is soil_texture column contains gravel
    has_gravel_mask = df['soil texture code'].str.contains('GR', case=False, na=False)

    #input 1 for gravel percentage if soil texture contains gravel
    df.loc[has_gravel_mask, "gravel_amount_percent"] = 1

    df = df.rename(columns={
        "start depth (cm)": "start_depth_cm",
        "stop depth (cm)": "stop_depth_cm",
        "soil texture code": "soil_texture_code"
    })
    
    desired_cols = [
        "well_id",
        "date",
        "start_depth_cm",
        "stop_depth_cm",
        "soil_texture_code",
        "gravel_amount_percent",
    ]
    
    df = df[[col for col in desired_cols if col in df.columns]]
    
    df = merge_identical_rows(df)
    
    return df
    
# ---- MAIN PROCEDURES---

# Load files
file_path = SOURCE_FILE_PATTERN
print(f"Loading data from: {file_path}")
df_raw = pd.read_csv(file_path)

output_path_validated = OUTPUT_FILE_PATTERN_RENAMED
output_path_cleaned = OUTPUT_FILE_PATTERN_CLEANED


# Validate and correct well_ids (well names), also drops invalid well_ids
df = process_well_ids(df_raw, datetime_col="date")
print('\nProcessed well_ids\n')

# Make sure the start and stop depths are all converted to cm
df = populate_depths_cm(df)

# Split the 'soil texture' column at the first comma and expand into two columns
df[['texture', 'sub-class']] = df['soil texture'].str.split(
                                                        ',', n=1, expand=True)
#strip any leftover whitespace 
df['texture'] = df['texture'].str.strip().str.lower()
df['sub-class'] = df['sub-class'].str.strip()

# takes the full words in 'soil texture', creates new column with short codes
df['soil texture code'] = df['texture'].map(word_to_code_mapping)

# Use warning to print out unmatched soil textures
unmatched = (
    df.loc[
        df['texture'].notna() &
        df['soil texture code'].isna(),
        'texture'
    ]
    .unique()
)

if len(unmatched) > 0:
    warnings.warn(
        f"\nUnmatched soil texture values: {sorted(unmatched)}\n",
        UserWarning,
        stacklevel=2,
    )

#Apply the function to create the two new columns
df[['gravel size', 'gravel amount']] = df['sub-class'].apply(extract_gravel_info)

df.to_csv(output_path_validated, index=False)
print(f"\nSaved renamed RAW data to: {output_path_validated}\n")

# Clean and save data
df_clean = clean_for_plotting(df)
df_clean.to_csv(output_path_cleaned, index=False)
print(f"\nSaved cleaned data for plotting: {output_path_cleaned}\n")



